"""TRELLIS.2 mesh generation operator."""

import os
import bpy  # pylint: disable=import-error
import mathutils  # pylint: disable=import-error
import json
import uuid
import urllib.request
import urllib.parse
import threading
import traceback
from datetime import datetime
import math
import io
import websocket
from PIL import Image

from ..utils import get_generation_dirs, sg_modal_active
from ..timeout_config import get_timeout
from .._generator_utils import setup_studio_lighting, redraw_ui, upload_image_to_comfyui
from ..texturing.gallery import _PreviewGalleryOverlay

_ADDON_PKG = __package__.rsplit('.', 1)[0]

class Trellis2Generate(bpy.types.Operator):
    """Generate a 3D mesh from a reference image using TRELLIS.2 via ComfyUI.

    Requires the PozzettiAndrea/ComfyUI-TRELLIS2 custom node pack installed on the ComfyUI server.
    Uploads the input image, runs the full TRELLIS.2 pipeline (background removal, conditioning,
    shape generation, texture generation, GLB export), downloads the resulting GLB file, and
    imports it into the Blender scene."""
    bl_idname = "object.trellis2_generate"
    bl_label = "Generate 3D Mesh (TRELLIS.2)"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _thread = None
    _error = None
    _glb_data = None
    _is_running = False
    _cancelled = False
    _active_ws = None  # WebSocket reference for cancel-time close
    _progress = 0.0
    _stage = "Initializing"
    workflow_manager: object = None

    # ── Preview gallery state ─────────────────────────────────────────
    _gallery_overlay: _PreviewGalleryOverlay | None = None
    _gallery_event: threading.Event | None = None
    _gallery_ready: bool = False
    _gallery_action: str | None = None  # 'select' | 'more' | 'cancel'
    _gallery_selected_bytes: bytes | None = None
    _gallery_selected_seed: int | None = None
    _progress_remap: tuple | None = None  # (base, span) for gallery sub-range scaling

    # ── 3-tier progress ──────────────────────────────────────────────
    _overall_progress: float = 0.0
    _overall_stage: str = "Initializing"
    _phase_progress: float = 0.0
    _phase_stage: str = ""
    _detail_progress: float = 0.0
    _detail_stage: str = ""
    _current_phase: int = 0
    _total_phases: int = 3  # 2 when gen_from == 'image'

    def _update_overall(self):
        """Recompute *_overall_progress* from current phase + phase progress."""
        layout = getattr(self, '_phase_layout', '')
        if layout == 'txt2img+trellis+texturing':  # 3 phases
            starts  = {1: 0,  2: 15, 3: 65}
            weights = {1: 15, 2: 50, 3: 35}
        elif layout == 'trellis+texturing':  # 2 phases: big mesh, then texturing
            starts  = {1: 0,  2: 65}
            weights = {1: 65, 2: 35}
        elif layout == 'txt2img+trellis':  # 2 phases: quick txt2img, then big mesh+native tex
            starts  = {1: 0,  2: 15}
            weights = {1: 15, 2: 85}
        else:  # Single phase — scale to full 0-100
            starts  = {1: 0}
            weights = {1: 100}
        s = starts.get(self._current_phase, 0)
        w = weights.get(self._current_phase, 0)
        self._overall_progress = s + (self._phase_progress / 100.0) * w
        self._overall_progress = max(0.0, min(self._overall_progress, 100.0))
        # Keep legacy _progress in sync for any code that reads it
        self._progress = self._overall_progress

    @classmethod
    def poll(cls, context):
        if cls._is_running:
            return True  # Allow cancellation
        addon_prefs = context.preferences.addons[_ADDON_PKG].preferences
        if not addon_prefs.server_address or not addon_prefs.server_online:
            cls.poll_message_set("ComfyUI server is not connected")
            return False
        if not os.path.exists(addon_prefs.output_dir):
            cls.poll_message_set("Output directory not set or does not exist (check addon preferences)")
            return False
        if bpy.app.online_access == False:
            cls.poll_message_set("Blender's online access is disabled (File → Preferences → System)")
            return False
        gen_from = getattr(context.scene, 'trellis2_generate_from', 'image')
        if gen_from == 'image' and not context.scene.trellis2_input_image:
            cls.poll_message_set("No input image selected for TRELLIS.2 generation")
            return False
        if sg_modal_active(context):
            cls.poll_message_set("Another operation is in progress")
            return False
        return True

    def execute(self, context):
        if Trellis2Generate._is_running:
            # Cancel — tell the server to stop and close the WebSocket
            # so the background thread unblocks from ws.recv().
            Trellis2Generate._cancelled = True
            Trellis2Generate._is_running = False

            # Send /interrupt to ComfyUI (same as standard texturing cancel)
            try:
                server_address = context.preferences.addons[_ADDON_PKG].preferences.server_address
                data = json.dumps({"client_id": str(uuid.uuid4())}).encode('utf-8')
                req = urllib.request.Request("http://{}/interrupt".format(server_address), data=data)
                urllib.request.urlopen(req)
            except Exception:
                pass  # Best effort — server may already be gone

            # Close the active WebSocket so the thread's ws.recv() raises
            ws = Trellis2Generate._active_ws
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass
                Trellis2Generate._active_ws = None

            # Wake up the gallery event in case the thread is blocked there
            if self._gallery_event:
                self._gallery_action = 'cancel'
                self._gallery_event.set()

            self.report({'WARNING'}, "TRELLIS.2 generation cancelled")
            return {'FINISHED'}

        scene = context.scene
        gen_from = getattr(scene, 'trellis2_generate_from', 'image')
        tex_mode = getattr(scene, 'trellis2_texture_mode', 'native')

        # Validate input image (only required in image mode)
        image_path = None
        if gen_from == 'image':
            image_path = bpy.path.abspath(scene.trellis2_input_image)
            if not os.path.exists(image_path):
                self.report({'ERROR'}, f"Input image not found: {image_path}")
                return {'CANCELLED'}

        Trellis2Generate._is_running = True
        context.scene.sg_last_gen_error = False
        self._error = None
        self._glb_data = None
        self._progress = 0.0
        self._stage = "Initializing"
        self._texture_mode = tex_mode
        from ..workflows import WorkflowManager
        self.workflow_manager = WorkflowManager(self)

        # Gallery state reset
        self._gallery_overlay = None
        self._gallery_event = threading.Event()
        self._gallery_ready = False
        self._gallery_action = None
        self._gallery_selected_bytes = None
        self._gallery_selected_seed = None

        # 3-tier progress init
        has_txt2img = (gen_from == 'prompt')
        has_texturing = (tex_mode in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein'))
        if has_txt2img and has_texturing:
            self._total_phases = 3
            self._phase_layout = 'txt2img+trellis+texturing'
        elif has_txt2img:
            self._total_phases = 2
            self._phase_layout = 'txt2img+trellis'
        elif has_texturing:
            self._total_phases = 2
            self._phase_layout = 'trellis+texturing'
        else:
            self._total_phases = 1
            self._phase_layout = 'trellis_only'
        self._current_phase = 0
        self._overall_progress = 0.0
        self._overall_stage = "Initializing"
        self._phase_progress = 0.0
        self._phase_stage = ""
        self._detail_progress = 0.0
        self._detail_stage = ""

        # Compute revision directory on the main thread (may write output_timestamp)
        from ..utils import get_generation_dirs
        gen_dirs = get_generation_dirs(context)
        revision_dir = gen_dirs.get("revision", "")

        # Start generation in background thread
        self._thread = threading.Thread(
            target=self._run_trellis2,
            args=(context, image_path, gen_from, revision_dir),
            daemon=True
        )
        self._thread.start()

        # Register modal timer
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)

        return {'RUNNING_MODAL'}

    def _cleanup_gallery(self):
        """Remove the gallery overlay and free GPU resources."""
        if self._gallery_overlay:
            self._gallery_overlay.cleanup()
            self._gallery_overlay = None

    def modal(self, context, event):
        # ── Gallery mode: intercept mouse + keyboard ──────────────
        if self._gallery_overlay is not None:
            if event.type == 'MOUSEMOVE':
                if self._gallery_overlay.handle_mouse_move(
                        event.mouse_region_x, event.mouse_region_y):
                    for area in context.screen.areas:
                        area.tag_redraw()
                return {'RUNNING_MODAL'}

            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                action = self._gallery_overlay.handle_click(
                    event.mouse_region_x, event.mouse_region_y)
                if action == 'select':
                    self._gallery_selected_bytes = self._gallery_overlay.selected_image_bytes
                    self._gallery_selected_seed = self._gallery_overlay.selected_seed
                    self._gallery_action = 'select'
                    self._cleanup_gallery()
                    self._gallery_ready = False
                    self._gallery_event.set()
                    return {'RUNNING_MODAL'}
                elif action == 'more':
                    self._gallery_action = 'more'
                    self._cleanup_gallery()
                    self._gallery_ready = False
                    self._gallery_event.set()
                    return {'RUNNING_MODAL'}
                elif action == 'cancel':
                    self._gallery_action = 'cancel'
                    self._cleanup_gallery()
                    self._gallery_ready = False
                    self._gallery_event.set()
                    return {'RUNNING_MODAL'}
                return {'RUNNING_MODAL'}

            if event.type == 'ESC' and event.value == 'PRESS':
                self._gallery_action = 'cancel'
                self._cleanup_gallery()
                self._gallery_ready = False
                self._gallery_event.set()
                return {'RUNNING_MODAL'}

            if event.type == 'TIMER':
                for area in context.screen.areas:
                    area.tag_redraw()
            return {'RUNNING_MODAL'}

        # ── Normal mode ───────────────────────────────────────────
        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        # Redraw UI for progress updates
        for area in context.screen.areas:
            area.tag_redraw()

        # Check if gallery is ready (thread waiting for user input)
        if self._gallery_ready and self._gallery_overlay is None:
            gallery_data = getattr(self, '_gallery_data', None)
            if gallery_data:
                pil_imgs, seeds = gallery_data
                self._gallery_overlay = _PreviewGalleryOverlay(pil_imgs, seeds)
                for area in context.screen.areas:
                    area.tag_redraw()
            return {'RUNNING_MODAL'}

        # Check if thread is still running
        if self._thread and self._thread.is_alive():
            return {'RUNNING_MODAL'}

        # Thread finished - clean up timer
        context.window_manager.event_timer_remove(self._timer)
        self._timer = None
        was_cancelled = Trellis2Generate._cancelled
        Trellis2Generate._is_running = False
        Trellis2Generate._cancelled = False
        Trellis2Generate._active_ws = None
        self._cleanup_gallery()

        # User cancelled — exit silently (no error toast)
        if was_cancelled:
            context.scene.generation_status = 'idle'
            context.scene.sg_last_gen_error = True
            return {'FINISHED'}

        if self._error:
            self.report({'ERROR'}, f"TRELLIS.2 error: {self._error}")
            context.scene.sg_last_gen_error = True
            return {'CANCELLED'}

        if self._glb_data is None or (isinstance(self._glb_data, dict) and "error" in self._glb_data):
            error_msg = self._glb_data.get("error", "Unknown error") if isinstance(self._glb_data, dict) else "No data received"
            self.report({'ERROR'}, f"TRELLIS.2 failed: {error_msg}")
            context.scene.sg_last_gen_error = True
            return {'CANCELLED'}

        # Surface mesh-corruption warning to the user (set by workflows.py
        # when the GLB validator detects artifacts but recovery failed).
        _mesh_warning = getattr(self, '_warning', None)
        if _mesh_warning:
            self.report({'WARNING'}, _mesh_warning)
            self._warning = None  # consumed

        # Save GLB to revision directory and import into Blender
        try:
            from ..utils import get_generation_dirs
            gen_dirs = get_generation_dirs(context)
            save_dir = gen_dirs.get("revision", "")
            if not save_dir:
                save_dir = context.preferences.addons[_ADDON_PKG].preferences.output_dir
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            glb_filename = f"trellis2_{timestamp}.glb"
            glb_path = os.path.join(save_dir, glb_filename)

            with open(glb_path, 'wb') as f:
                f.write(self._glb_data)

            # Store the TRELLIS.2 input image path for downstream use (IPAdapter/Qwen style)
            input_img = getattr(self, '_input_image_path', None)
            if input_img:
                context.scene.trellis2_last_input_image = input_img

            print(f"[TRELLIS2] Saved GLB to: {glb_path} ({len(self._glb_data)} bytes)")

            # Import GLB into Blender
            bpy.ops.import_scene.gltf(filepath=glb_path)

            # --- Normalise imported mesh to a reasonable Blender-unit size ---
            target_bu = getattr(context.scene, 'trellis2_import_scale', 2.0)
            if target_bu > 0:
                imported_objects = [obj for obj in context.selected_objects]
                if imported_objects:
                    # Compute combined world-space bounding box across all
                    # imported objects (meshes, empties, armatures …).
                    all_corners = []
                    for obj in imported_objects:
                        for corner in obj.bound_box:
                            all_corners.append(obj.matrix_world @ mathutils.Vector(corner))
                    if all_corners:
                        xs = [c.x for c in all_corners]
                        ys = [c.y for c in all_corners]
                        zs = [c.z for c in all_corners]
                        extent = max(
                            max(xs) - min(xs),
                            max(ys) - min(ys),
                            max(zs) - min(zs),
                        )
                        if extent > 1e-6:
                            scale_factor = target_bu / extent
                            # Find the root objects (those without an imported parent)
                            roots = [o for o in imported_objects if o.parent not in imported_objects]
                            for root in roots:
                                root.scale *= scale_factor
                            # Apply scale so downstream code sees unit scale
                            bpy.ops.object.select_all(action='DESELECT')
                            for obj in imported_objects:
                                obj.select_set(True)
                            bpy.context.view_layer.objects.active = imported_objects[0]
                            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                            print(f"[TRELLIS2] Scaled mesh to {target_bu} BU (factor {scale_factor:.4f})")

            # --- Apply shading mode to imported meshes ---
            _shade_mode = getattr(context.scene, 'trellis2_shade_mode', 'flat')
            if _shade_mode == 'smooth':
                bpy.ops.object.shade_smooth()
            elif _shade_mode == 'auto_smooth':
                bpy.ops.object.shade_auto_smooth()

            # --- Optional studio lighting for native PBR textures ---
            tex_mode = getattr(self, '_texture_mode', 'native')
            if tex_mode == 'native' and getattr(context.scene, 'trellis2_auto_lighting', False):
                self._setup_studio_lighting(context, target_bu)

            # --- Phase 3: If diffusion texturing, auto-place cameras + start generation ---
            if tex_mode in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein'):
                # Place cameras NOW (while operator context is still valid)
                camera_count = getattr(context.scene, 'trellis2_camera_count', 8)
                imported_objects = [obj for obj in context.selected_objects]

                if imported_objects:
                    bpy.context.view_layer.objects.active = imported_objects[0]
                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in imported_objects:
                        obj.select_set(True)

                # Force viewport to standard front view so AddCameras uses a
                # consistent reference direction for sorting and auto-prompts.
                # TRELLIS.2 always imports meshes in standard orientation so the
                # viewport should match.
                # Find the 3D viewport area + WINDOW region so add_cameras
                # gets a full context (region_data etc.) even when invoked
                # from a timer-driven modal callback.
                _v3d_area = None
                _v3d_region = None
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                rv3d = space.region_3d
                                if rv3d:
                                    # Blender front view (Numpad 1): -Y looking at +Y
                                    rv3d.view_rotation = mathutils.Quaternion(
                                        (0.7071068, 0.7071068, 0.0, 0.0)
                                    )
                                    rv3d.view_perspective = 'PERSP'
                        _v3d_area = area
                        for reg in area.regions:
                            if reg.type == 'WINDOW':
                                _v3d_region = reg
                                break
                        break

                try:
                    _pm = getattr(context.scene, 'trellis2_placement_mode', 'normal_weighted')
                    _cam_kwargs = {
                        'placement_mode': _pm,
                        'num_cameras': camera_count,
                        'auto_prompts': getattr(context.scene, 'trellis2_auto_prompts', True),
                        'review_placement': False,
                        'purge_others': True,
                        'exclude_bottom': getattr(context.scene, 'trellis2_exclude_bottom', True),
                        'exclude_bottom_angle': getattr(context.scene, 'trellis2_exclude_bottom_angle', 1.5533),
                        'auto_aspect': getattr(context.scene, 'trellis2_auto_aspect', 'per_camera'),
                        'occlusion_mode': getattr(context.scene, 'trellis2_occlusion_mode', 'none'),
                        'consider_existing': getattr(context.scene, 'trellis2_consider_existing', True),
                        'clamp_elevation': getattr(context.scene, 'trellis2_clamp_elevation', False),
                        'max_elevation_angle': getattr(context.scene, 'trellis2_max_elevation', 1.2217),
                        'min_elevation_angle': getattr(context.scene, 'trellis2_min_elevation', -0.1745),
                    }
                    if _pm == 'greedy_coverage':
                        _cam_kwargs['coverage_target'] = getattr(context.scene, 'trellis2_coverage_target', 0.95)
                        _cam_kwargs['max_auto_cameras'] = getattr(context.scene, 'trellis2_max_auto_cameras', 12)
                    if _pm == 'fan_from_camera':
                        _cam_kwargs['fan_angle'] = getattr(context.scene, 'trellis2_fan_angle', 90.0)

                    # Use temp_override so add_cameras gets proper region_data.
                    # Temporarily bypass the sg_modal_active() poll guard so
                    # add_cameras can run while this TRELLIS.2 modal is active.
                    from .. import utils as _sg_utils
                    _sg_utils._sg_bypass_modal_check = True
                    try:
                        if _v3d_area and _v3d_region:
                            with bpy.context.temp_override(area=_v3d_area, region=_v3d_region):
                                bpy.ops.object.add_cameras(**_cam_kwargs)
                        else:
                            bpy.ops.object.add_cameras(**_cam_kwargs)
                    finally:
                        _sg_utils._sg_bypass_modal_check = False

                except Exception as cam_err:
                    print(f"[TRELLIS2] Warning: Camera placement failed: {cam_err}")
                    traceback.print_exc()

                # Defer texture generation so Blender digests the new cameras
                self._schedule_texture_generation(context)
                self.report({'INFO'}, f"TRELLIS.2: Mesh imported. Camera placement done, texture generation starting...")
            else:
                self.report({'INFO'}, f"TRELLIS.2: Imported 3D mesh from {glb_filename}")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import GLB: {e}")
            traceback.print_exc()
            return {'CANCELLED'}

    # -----------------------------------------------------------------
    # Studio lighting (three-point rig for PBR showcase)
    # -----------------------------------------------------------------
    def _setup_studio_lighting(self, context, import_scale):
        """Create a three-point studio lighting setup around the imported mesh."""
        return setup_studio_lighting(context, scale=import_scale)

    def _schedule_texture_generation(self, context):
        """Defer texture generation via a timer so Blender can digest the new cameras.

        Camera placement has already happened in ``modal()``.  This only
        selects all cameras and starts ``object.test_stable``.
        Sets scene-level pipeline flags so the UI can show the overall
        progress bar on top of the ComfyUIGenerate bars.
        """
        # Compute the overall-% at which texturing begins
        if self._total_phases == 3:
            phase_start = 65.0
        elif self._total_phases == 2:
            phase_start = 65.0
        else:
            phase_start = 0.0

        scene = context.scene
        scene.trellis2_pipeline_active = True
        scene.trellis2_pipeline_phase_start_pct = phase_start
        scene.trellis2_pipeline_total_phases = self._total_phases

        def _deferred_generate():
            try:
                # Defensive VRAM flush before loading the diffusion checkpoint.
                # The TRELLIS post-generation flush should have freed VRAM,
                # but if it silently failed the models are still resident (Gap C).
                # Also clear history to release cached node outputs.
                try:
                    srv = bpy.context.preferences.addons[_ADDON_PKG].preferences.server_address
                    # 1. Set unload flags
                    flush_data = json.dumps({"unload_models": True, "free_memory": True}).encode('utf-8')
                    flush_req = urllib.request.Request(
                        f"http://{srv}/free", data=flush_data,
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(flush_req, timeout=get_timeout('api'))
                    # 2. Clear history/cache
                    hist_data = json.dumps({"clear": True}).encode('utf-8')
                    hist_req = urllib.request.Request(
                        f"http://{srv}/history", data=hist_data,
                        headers={"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(hist_req, timeout=get_timeout('api'))
                    # 3. Wait for VRAM release
                    import time
                    time.sleep(3)
                    print("[TRELLIS2] Pre-texturing VRAM flush sent (unload+history clear)")
                except Exception as flush_err:
                    print(f"[TRELLIS2] Pre-texturing flush warning: {flush_err}")

                bpy.ops.object.select_all(action='DESELECT')
                scene_cams = [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
                for obj in scene_cams:
                    obj.select_set(True)

                from .. import utils as _sg_utils
                _sg_utils._sg_bypass_modal_check = True
                try:
                    bpy.ops.object.test_stable('INVOKE_DEFAULT')
                finally:
                    _sg_utils._sg_bypass_modal_check = False
                print("[TRELLIS2] Texture generation started")
            except Exception as e:
                print(f"[TRELLIS2] Warning: Texture generation failed to start: {e}")
                traceback.print_exc()
            return None  # Run once

        # Remember which cameras exist before texturing so we can delete
        # the ones we placed if the user opted in.
        _pre_tex_cameras = {obj.name for obj in bpy.context.scene.objects if obj.type == 'CAMERA'}

        def _pipeline_watcher():
            """Clear the pipeline flag when texturing finishes or is cancelled."""
            if bpy.context.scene.generation_status in ('idle', 'waiting'):
                bpy.context.scene.trellis2_pipeline_active = False
                print("[TRELLIS2] Pipeline complete — overall bar removed")

                # Delete auto-placed cameras if the user requested it
                if getattr(bpy.context.scene, 'trellis2_delete_cameras', False):
                    to_remove = [obj for obj in bpy.context.scene.objects
                                 if obj.type == 'CAMERA' and obj.name in _pre_tex_cameras]
                    if to_remove:
                        bpy.ops.object.select_all(action='DESELECT')
                        for obj in to_remove:
                            obj.select_set(True)
                        bpy.ops.object.delete()
                        print(f"[TRELLIS2] Deleted {len(to_remove)} auto-placed cameras")

                return None  # Stop timer
            return 1.0  # Check again in 1s

        bpy.app.timers.register(_deferred_generate, first_interval=0.5)
        bpy.app.timers.register(_pipeline_watcher, first_interval=2.0)

    def _run_trellis2(self, context, image_path, gen_from, revision_dir):
        """Background thread: runs the TRELLIS.2 pipeline.

        If *gen_from* is ``'prompt'`` the method first generates an input
        image via a lightweight txt2img ComfyUI workflow, saves it to the
        revision directory and passes that to the TRELLIS.2 mesh workflow.

        When the preview gallery is enabled (``trellis2_preview_gallery_enabled``),
        the prompt path generates N images with different seeds and pauses to
        let the user pick one via the viewport overlay before continuing.
        """
        import random as _rng
        try:
            # --- Phase 1: Image acquisition ---
            if gen_from == 'prompt':
                self._current_phase = 1
                self._phase_stage = "Generating Input Image"
                self._phase_progress = 0
                self._detail_progress = 0
                self._detail_stage = "Flushing stale models"
                self._overall_stage = f"Phase 1/{self._total_phases}: Input Image"
                self._update_overall()

                # Flush any stale models from prior runs before loading a
                # diffusion checkpoint for txt2img (Gap A).
                try:
                    server_addr = context.preferences.addons[_ADDON_PKG].preferences.server_address
                    self.workflow_manager._flush_comfyui_vram(server_addr, label="Pre-txt2img")
                except Exception:
                    pass

                self._detail_stage = "Starting txt2img"

                gallery_enabled = getattr(context.scene, 'trellis2_preview_gallery_enabled', False)
                gallery_count = max(1, int(getattr(context.scene, 'trellis2_preview_gallery_count', 4)))

                if gallery_enabled and gallery_count >= 1:
                    # ── Preview gallery loop ──────────────────────────
                    img_result = None  # will hold the chosen image bytes

                    # Seed a local RNG for deterministic gallery sequences.
                    # Same scene seed ➜ same gallery images every run.
                    base_seed = int(getattr(context.scene, 'seed', 0))
                    if base_seed == 0:
                        gallery_rng = _rng.Random()       # truly random
                    else:
                        gallery_rng = _rng.Random(base_seed)  # deterministic

                    while True:
                        pil_images = []
                        seeds = []
                        # Reset progress for each batch
                        self._phase_progress = 0
                        self._update_overall()
                        for i in range(gallery_count):
                            self._detail_stage = f"Generating preview {i + 1}/{gallery_count}"
                            # Set up remapping so WebSocket progress (0-100 per image)
                            # maps to the correct slice of the overall phase bar.
                            base = (i / gallery_count) * 90
                            span = (1 / gallery_count) * 90
                            self._progress_remap = (base, span)
                            self._phase_progress = base
                            self._update_overall()

                            rand_seed = gallery_rng.randint(1, 2**31 - 1)
                            result = self.workflow_manager.generate_txt2img(
                                context, seed_override=rand_seed)
                            if isinstance(result, dict) and "error" in result:
                                self._error = f"txt2img failed (seed {rand_seed}): {result['error']}"
                                return

                            pil_img = Image.open(io.BytesIO(result))
                            pil_images.append(pil_img)
                            seeds.append(rand_seed)

                        # Clear remapping before waiting
                        self._progress_remap = None

                        # Hand off to the main thread for user selection
                        self._gallery_data = (pil_images, seeds)
                        self._gallery_ready = True
                        self._detail_stage = "Waiting for selection"
                        self._phase_progress = 95
                        self._update_overall()

                        # Block until the modal sets the event
                        self._gallery_event.wait()
                        self._gallery_event.clear()

                        if self._gallery_action == 'select':
                            img_result = self._gallery_selected_bytes
                            chosen_seed = self._gallery_selected_seed
                            if chosen_seed is not None:
                                context.scene.seed = chosen_seed
                            break
                        elif self._gallery_action == 'more':
                            # Loop around and generate another batch
                            continue
                        else:  # cancel
                            self._error = "Preview gallery cancelled"
                            return

                    if img_result is None:
                        self._error = "No image selected from gallery"
                        return
                else:
                    # ── Single image (legacy path) ───────────────────
                    img_result = self.workflow_manager.generate_txt2img(context)
                    if isinstance(img_result, dict) and "error" in img_result:
                        self._error = f"txt2img failed: {img_result['error']}"
                        return

                # Phase 1 complete
                self._phase_progress = 100
                self._update_overall()

                # Early exit if cancelled during txt2img
                if self._cancelled:
                    return

                # Save the generated image bytes to the revision directory
                save_dir = revision_dir if revision_dir else (
                    context.preferences.addons[_ADDON_PKG].preferences.output_dir
                )
                os.makedirs(save_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(save_dir, f"trellis2_input_{timestamp}.png")
                with open(image_path, 'wb') as f:
                    f.write(img_result)
                print(f"[TRELLIS2] Saved txt2img result to: {image_path}")

                # Flush VRAM so the txt2img model (SDXL/Flux) is evicted
                # before TRELLIS loads its own models via raw PyTorch.
                # Without this, both models coexist and OOM on <=16 GB GPUs.
                # (Gap B – between txt2img and TRELLIS Phase 1)
                self._detail_stage = "Flushing txt2img models"
                try:
                    server_addr = context.preferences.addons[_ADDON_PKG].preferences.server_address
                    self.workflow_manager._flush_comfyui_vram(server_addr, label="Post-txt2img")
                except Exception:
                    pass

                # Early exit if cancelled during txt2img
                if self._cancelled:
                    return

            # --- Phase 2 (or 1 if no txt2img): TRELLIS.2 mesh generation ---
            trellis_phase = 2 if gen_from == 'prompt' else 1
            self._current_phase = trellis_phase
            self._phase_stage = "TRELLIS.2 Mesh Generation"
            self._phase_progress = 0
            self._detail_progress = 0
            self._detail_stage = "Uploading image"
            self._overall_stage = f"Phase {trellis_phase}/{self._total_phases}: 3D Mesh"
            self._update_overall()

            # Store the final input image path for later use (IPAdapter/Qwen style)
            self._input_image_path = image_path

            result = self.workflow_manager.generate_trellis2(context, image_path)

            # Suppress error reporting when the user cancelled
            if self._cancelled:
                return

            if isinstance(result, dict) and "error" in result:
                self._error = result["error"]
            else:
                self._glb_data = result

        except Exception as e:
            if self._cancelled:
                return  # Swallow exceptions caused by cancel-time WS close
            self._error = str(e)
            traceback.print_exc()