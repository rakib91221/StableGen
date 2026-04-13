"""Batch image-to-3D generation for TRELLIS.2."""

import os
import bpy  # pylint: disable=import-error

# Supported input image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}

# ── Module-level batch state ─────────────────────────────────────────────────
_batch_state = {
    'active': False,
    'images': [],
    'index': -1,       # -1 = not yet started; incremented before each gen
    'total': 0,
    'cancelled': False,
    'rename_meshes': True,
    'pre_objects': set(),   # object ids present before current generation
    'settling': False,      # waiting a few ticks for Trellis2Generate to start
    'settle_count': 0,
}

_SETTLE_TICKS = 12   # ticks to wait after invoking the operator
_TICK_INTERVAL = 0.5 # seconds between timer callbacks


def _scan_images(folder):
    """Return a sorted list of supported image file paths in *folder*."""
    if not os.path.isdir(folder):
        return []
    result = []
    for name in sorted(os.listdir(folder)):
        if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
            result.append(os.path.join(folder, name))
    return result


def _redraw():
    """Request a UI redraw on all 3D viewports."""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:  # noqa: BLE001
        pass


def _sync_wm():
    """Push current batch state into WindowManager display properties."""
    try:
        wm = bpy.context.window_manager
        wm.sg_batch_running = _batch_state['active']
        wm.sg_batch_index = _batch_state['index'] + 1  # 1-based for display
        wm.sg_batch_total = _batch_state['total']
        _redraw()
    except Exception:  # noqa: BLE001
        pass


def _rename_new_objects(image_path):
    """Rename objects imported in the last generation to the input filename stem."""
    state = _batch_state
    stem = os.path.splitext(os.path.basename(image_path))[0]
    try:
        scene = bpy.context.scene
        pre_ids = state['pre_objects']
        new_objs = [
            obj for obj in scene.objects
            if id(obj) not in pre_ids
        ]
        mesh_objs = [o for o in new_objs if o.type == 'MESH']
        if not mesh_objs:
            mesh_objs = new_objs  # fallback: rename whatever was imported
        if len(mesh_objs) == 1:
            mesh_objs[0].name = stem
            if mesh_objs[0].data:
                mesh_objs[0].data.name = stem
        else:
            for i, obj in enumerate(mesh_objs):
                obj.name = f"{stem}_{i + 1:02d}"
                if obj.data:
                    obj.data.name = f"{stem}_{i + 1:02d}"
        print(f"[BatchGen] Renamed {len(mesh_objs)} object(s) to '{stem}...'")
    except Exception as exc:  # noqa: BLE001
        print(f"[BatchGen] Warning: could not rename objects: {exc}")


def _trigger_next():
    """Record pre-generation objects, set input image, invoke Trellis2Generate."""
    state = _batch_state
    image_path = state['images'][state['index']]

    # Snapshot current object IDs so we can identify new ones after import
    try:
        state['pre_objects'] = {id(obj) for obj in bpy.context.scene.objects}
    except Exception:  # noqa: BLE001
        state['pre_objects'] = set()

    try:
        bpy.context.scene.trellis2_input_image = image_path
        print(f"[BatchGen] {state['index'] + 1}/{state['total']}: "
              f"{os.path.basename(image_path)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[BatchGen] Error setting input image: {exc}")
        state['cancelled'] = True
        return

    try:
        bpy.ops.object.trellis2_generate('EXEC_DEFAULT')
        state['settling'] = True
        state['settle_count'] = 0
    except Exception as exc:  # noqa: BLE001
        print(f"[BatchGen] Error invoking generate for image "
              f"{state['index'] + 1}: {exc}, skipping")


def _batch_tick():
    """bpy.app.timers callback – drives the batch state machine."""
    from .trellis2 import Trellis2Generate  # late import to avoid circular dep

    state = _batch_state

    # ── Cancelled / stopped ──────────────────────────────────────────────────
    if state['cancelled'] or not state['active']:
        state['active'] = False
        state['cancelled'] = False
        _sync_wm()
        print("[BatchGen] Batch stopped")
        return None  # unregister timer

    # ── Settling: waiting for Trellis2Generate to start running ─────────────
    if state['settling']:
        state['settle_count'] += 1
        if Trellis2Generate._is_running:
            # Operator started successfully, stop settling
            state['settling'] = False
        elif state['settle_count'] >= _SETTLE_TICKS:
            # Timed out waiting for operator — skip this image
            print(f"[BatchGen] Image {state['index'] + 1} failed to start, skipping")
            state['settling'] = False
        return _TICK_INTERVAL

    # ── Still generating ─────────────────────────────────────────────────────
    if Trellis2Generate._is_running:
        return _TICK_INTERVAL

    # ── Generation finished (or first tick before first gen) ─────────────────
    if state['index'] >= 0:
        # Check for error
        try:
            had_error = bpy.context.scene.sg_last_gen_error
        except Exception:  # noqa: BLE001
            had_error = False
        if had_error:
            print(f"[BatchGen] Image {state['index'] + 1} failed, skipping rename")
        elif state['rename_meshes']:
            _rename_new_objects(state['images'][state['index']])

    next_index = state['index'] + 1

    if next_index >= state['total']:
        # ── All done ─────────────────────────────────────────────────────────
        state['active'] = False
        _sync_wm()
        print(f"[BatchGen] Complete! {state['total']} image(s) processed.")
        return None  # stop timer

    state['index'] = next_index
    _sync_wm()
    _trigger_next()
    return _TICK_INTERVAL


# ── Operators ────────────────────────────────────────────────────────────────

class TRELLIS2_OT_BatchSelectFolder(bpy.types.Operator):
    """Select a folder of images for batch TRELLIS.2 generation"""
    bl_idname = "object.trellis2_batch_select_folder"
    bl_label = "Select Image Folder for Batch"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(subtype='DIR_PATH')  # type: ignore

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        folder = self.directory.rstrip('/\\')
        context.scene.trellis2_batch_folder = folder
        images = _scan_images(folder)
        context.scene.trellis2_batch_count = len(images)
        if images:
            context.scene.trellis2_input_image = images[0]
            self.report({'INFO'}, f"Found {len(images)} image(s) in folder")
        else:
            self.report({'WARNING'}, "No supported images found in folder")
        return {'FINISHED'}


class TRELLIS2_OT_BatchGenerate(bpy.types.Operator):
    """Generate 3D models for all images in the selected batch folder"""
    bl_idname = "object.trellis2_batch_generate"
    bl_label = "Generate Batch"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if _batch_state['active']:
            return False
        from .trellis2 import Trellis2Generate
        if Trellis2Generate._is_running:
            return False
        folder = getattr(context.scene, 'trellis2_batch_folder', '')
        count = getattr(context.scene, 'trellis2_batch_count', 0)
        return bool(folder) and count > 0

    def execute(self, context):
        folder = context.scene.trellis2_batch_folder
        images = _scan_images(folder)
        if not images:
            self.report({'ERROR'}, "No images found in batch folder")
            return {'CANCELLED'}

        _batch_state.update({
            'active': True,
            'cancelled': False,
            'images': images,
            'index': -1,
            'total': len(images),
            'rename_meshes': getattr(context.scene, 'trellis2_batch_rename_meshes', True),
            'pre_objects': set(),
            'settling': False,
            'settle_count': 0,
        })
        _sync_wm()
        print(f"[BatchGen] Starting: {len(images)} image(s) from '{folder}'")
        bpy.app.timers.register(_batch_tick, first_interval=0.1)
        return {'FINISHED'}


class TRELLIS2_OT_BatchCancel(bpy.types.Operator):
    """Cancel the running batch generation"""
    bl_idname = "object.trellis2_batch_cancel"
    bl_label = "Cancel Batch"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _batch_state['active']

    def execute(self, context):
        _batch_state['cancelled'] = True
        self.report({'WARNING'}, "Batch generation cancelling after current model...")
        return {'FINISHED'}


class TRELLIS2_OT_BatchClear(bpy.types.Operator):
    """Clear the batch folder selection"""
    bl_idname = "object.trellis2_batch_clear"
    bl_label = "Clear Batch Folder"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.trellis2_batch_folder = ""
        context.scene.trellis2_batch_count = 0
        return {'FINISHED'}


batch_classes = [
    TRELLIS2_OT_BatchSelectFolder,
    TRELLIS2_OT_BatchGenerate,
    TRELLIS2_OT_BatchCancel,
    TRELLIS2_OT_BatchClear,
]


def unregister_batch():
    """Stop any running batch timer. Called from addon unregister."""
    _batch_state['cancelled'] = True
    _batch_state['active'] = False
    try:
        if bpy.app.timers.is_registered(_batch_tick):
            bpy.app.timers.unregister(_batch_tick)
    except Exception:  # noqa: BLE001
        pass
