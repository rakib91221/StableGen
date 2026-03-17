"""Camera utility operators – switch viewport, clone, mirror, toggle labels."""

import bpy  # pylint: disable=import-error
import mathutils
from ..utils import sg_modal_active
from . import overlays as _overlays
from .overlays import (
    _sg_ensure_label_overlay, _sg_remove_label_overlay,
    _sg_ensure_crop_overlay, _sg_remove_crop_overlay,
    _setup_square_camera_display,
)
from .geometry import _store_per_camera_resolution

def switch_viewport_to_camera(context, camera):
    """Switches the first found 3D viewport to the specified camera's view."""
    if not camera:
        return
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            # Ensure we are in the right space and region
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    # Make sure the scene's active camera is set
                    context.scene.camera = camera
                    area.tag_redraw()
                    break
            break 

class CloneCamera(bpy.types.Operator):
    """Create a new camera at the active camera's position and enter fly mode to reposition it.
    
    If no camera exists, one is created from the current viewport.
    Useful for incrementally adding cameras one at a time."""
    bl_idname = "object.clone_camera"
    bl_label = "Clone Camera"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _camera = None
    _original_camera = None

    @classmethod
    def poll(cls, context):
        if sg_modal_active(context):
            cls.poll_message_set("Another operation is in progress")
            return False
        return True

    def execute(self, context):
        ref_cam = context.scene.camera
        self._original_camera = ref_cam

        if not ref_cam:
            # Create from viewport
            rv3d = context.region_data
            cam_data = bpy.data.cameras.new(name='Camera_clone')
            cam_obj = bpy.data.objects.new('Camera_clone', cam_data)
            context.collection.objects.link(cam_obj)
            cam_obj.matrix_world = rv3d.view_matrix.inverted()
        else:
            # Clone from active camera
            cam_data = bpy.data.cameras.new(name=f'{ref_cam.name}_clone')
            cam_obj = bpy.data.objects.new(cam_data.name, cam_data)
            context.collection.objects.link(cam_obj)
            cam_obj.matrix_world = ref_cam.matrix_world.copy()
            cam_obj.data.type = ref_cam.data.type
            cam_obj.data.lens = ref_cam.data.lens
            cam_obj.data.sensor_width = ref_cam.data.sensor_width
            cam_obj.data.sensor_height = ref_cam.data.sensor_height
            cam_obj.data.clip_start = ref_cam.data.clip_start
            cam_obj.data.clip_end = ref_cam.data.clip_end

        self._camera = cam_obj
        context.scene.camera = cam_obj

        rv3d = context.region_data
        if rv3d.view_perspective != 'CAMERA':
            bpy.ops.view3d.view_camera()
        bpy.ops.view3d.view_center_camera()
        try:
            rv3d.view_camera_zoom = 1.0
        except Exception:
            pass

        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        bpy.ops.view3d.fly('INVOKE_DEFAULT')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            fly_running = any(op.bl_idname == 'VIEW3D_OT_fly'
                              for w in context.window_manager.windows
                              for op in w.modal_operators)
            if not fly_running:
                context.window_manager.event_timer_remove(self._timer)
                if self._original_camera:
                    context.scene.camera = self._original_camera
                self.report({'INFO'}, f"Camera cloned: {self._camera.name}")
                return {'FINISHED'}
            return {'PASS_THROUGH'}
        return {'PASS_THROUGH'}


class MirrorCamera(bpy.types.Operator):
    """Create a mirror of the active camera across a chosen axis through the object/scene center.
    
    The new camera is placed symmetrically on the opposite side and oriented to look at the center."""
    bl_idname = "object.mirror_camera"
    bl_label = "Mirror Camera"
    bl_options = {'REGISTER', 'UNDO'}

    mirror_axis: bpy.props.EnumProperty(
        name="Mirror Axis",
        description="Axis to mirror across",
        items=[
            ('X', "X Axis", "Mirror left / right"),
            ('Y', "Y Axis", "Mirror front / back"),
            ('Z', "Z Axis", "Mirror top / bottom"),
        ],
        default='X'
    ) # type: ignore

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None and not sg_modal_active(context)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        cam = context.scene.camera
        obj = context.object

        # Determine center point
        if obj and obj.type == 'MESH':
            center = obj.matrix_world.translation.copy()
        else:
            center = mathutils.Vector((0, 0, 0))

        # Mirror position
        pos = cam.location.copy()
        axis_idx = 'XYZ'.index(self.mirror_axis)
        delta = pos - center
        delta[axis_idx] = -delta[axis_idx]
        new_pos = center + delta

        # Create new camera
        cam_data = bpy.data.cameras.new(name=f'{cam.name}_mirror_{self.mirror_axis}')
        cam_obj = bpy.data.objects.new(cam_data.name, cam_data)
        context.collection.objects.link(cam_obj)

        # Copy settings
        cam_obj.data.type = cam.data.type
        cam_obj.data.lens = cam.data.lens
        cam_obj.data.sensor_width = cam.data.sensor_width
        cam_obj.data.sensor_height = cam.data.sensor_height
        cam_obj.data.clip_start = cam.data.clip_start
        cam_obj.data.clip_end = cam.data.clip_end

        cam_obj.location = new_pos
        direction = center - new_pos
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        self.report({'INFO'}, f"Mirrored camera created: {cam_obj.name}")
        return {'FINISHED'}


class ToggleCameraLabels(bpy.types.Operator):
    """Toggle floating camera prompt labels in the 3D viewport.

    Shows or hides the per-camera prompt text (from Collect Camera Prompts
    or auto-generated view labels) next to each camera in the viewport."""
    bl_idname = "object.toggle_camera_labels"
    bl_label = "Toggle Camera Labels"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return any(o.type == 'CAMERA' for o in context.scene.objects) and not sg_modal_active(context)

    def execute(self, context):
        if _overlays._sg_label_draw_handle is not None:
            _sg_remove_label_overlay()
            self.report({'INFO'}, "Camera labels hidden")
        else:
            _sg_ensure_label_overlay()
            self.report({'INFO'}, "Camera labels visible")
        return {'FINISHED'}

        