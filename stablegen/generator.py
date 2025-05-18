import os
import bpy  # pylint: disable=import-error
import numpy as np

import uuid
import json
import urllib.request
import urllib.parse
import threading
from datetime import datetime

import math
from PIL import Image

from .util.helpers import prompt_text, prompt_text_img2img  # pylint: disable=relative-beyond-top-level
from .render_tools import export_emit_image, export_visibility, export_canny, bake_texture, prepare_baking, unwrap # pylint: disable=relative-beyond-top-level
from .utils import get_last_material_index, get_generation_dirs, get_file_path, get_dir_path, remove_empty_dirs # pylint: disable=relative-beyond-top-level
from .project import project_image # pylint: disable=relative-beyond-top-level

# Import wheels
import websocket

def redraw_ui(context):
    """Redraws the UI to reflect changes in the operator's progress and status."""
    for area in context.screen.areas:
        area.tag_redraw()

class ComfyUIGenerate(bpy.types.Operator):
    """Generate textures using ComfyUI (to all mesh objects using all cameras in the scene)
    
    - Multiple modes are available. Choose by setting Generation Mode in the UI.
    - This includes texture generation and projection to the mesh objects.
    - By default, the generated textures will only be visible in the Rendered viewport shading mode."""
    bl_idname = "object.test_stable"
    bl_label = "Generate using ComfyUI"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _progress = 0
    _error = None
    _is_running = False
    _threads_left = 0
    _cameras = None
    _grid_width = 0
    _grid_height = 0
    _material_id = -1
    proceed_with_high_res: bpy.props.BoolProperty(default=False)

    # Add properties to track progress
    _progress = 0.0
    _stage =  ""
    _current_image = 0
    _total_images = 0
    _wait_event = None

    # Add new properties at the top of the class
    _object_prompts: dict = {}
    show_prompt_dialog: bpy.props.BoolProperty(default=True)
    current_object_name: bpy.props.StringProperty()
    current_object_prompt: bpy.props.StringProperty(
        name="Object Prompt",
        description="Enter a specific prompt for this object",
        default=""
    ) # type: ignore
    # New properties for prompt collection
    _mesh_objects: list = []
    mesh_index: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._total_images = 0
        self._current_image = 0
        self._stage = ""
        self._progress = 0
        self._wait_event = threading.Event()
                
    @classmethod
    def poll(cls, context):
        """     
        Polls whether the operator can be executed.         
        :param context: Blender context.         
        :return: True if the operator can be executed, False otherwise.     
        """
        # Check for other modal operators
        operator = None
        for window in context.window_manager.windows:
                for op in window.modal_operators:
                    if op.bl_idname == 'OBJECT_OT_add_cameras' or op.bl_idname == 'OBJECT_OT_bake_textures' or op.bl_idname == 'OBJECT_OT_collect_camera_prompts' or context.scene.generation_status == 'waiting':
                        operator = op
                        break
                if operator:
                    break
        if operator:
            return False
        # Check if output directory, model directory, and server address are set
        addon_prefs = context.preferences.addons[__package__].preferences
        if not os.path.exists(addon_prefs.output_dir):
            return False
        if not os.path.exists(addon_prefs.model_dir):
            return False
        if not addon_prefs.server_address:
            return False
        if bpy.app.online_access == False: # Check if online access is disabled
            return False
        return True

    def execute(self, context):
        """     
        Executes the operator.         
        :param context: Blender context.         
        :return: {'RUNNING_MODAL'}     
        """
        if ComfyUIGenerate._is_running:
            self.cancel_generate(context)
            return {'FINISHED'}
        
        # Timestamp for output directory
        context.scene.output_timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        
        # If UV inpainting and we're in prompt collection mode, collect prompts first.
        if context.scene.generation_method == 'uv_inpaint' and self.show_prompt_dialog:
            self._object_prompts[self.current_object_name] = self.current_object_prompt
            if self.mesh_index < len(self._mesh_objects) - 1:
                self.mesh_index += 1
                self.current_object_name = self._mesh_objects[self.mesh_index]
                self.current_object_prompt = ""
                return context.window_manager.invoke_props_dialog(self, width=400)
            else:
                self.show_prompt_dialog = False

        
        context.scene.generation_status = 'running'
        ComfyUIGenerate._is_running = True

        print("Executing ComfyUI Generation")

        render = bpy.context.scene.render
        resolution_x = render.resolution_x
        resolution_y = render.resolution_y
        total_pixels = resolution_x * resolution_y

        if context.scene.auto_rescale and ((total_pixels > 1_200_000 or total_pixels < 800_000) or (resolution_x % 8 != 0 or resolution_y % 8 != 0)):
            scale_factor = (1_000_000 / total_pixels) ** 0.5
            render.resolution_x = int(resolution_x * scale_factor)
            render.resolution_y = int(resolution_y * scale_factor)
            # ComfyUI requires resolution to be divisible by 8
            render.resolution_x -= render.resolution_x % 8
            render.resolution_y -= render.resolution_y % 8
            self.report({'INFO'}, f"Resolution automatically rescaled to {render.resolution_x}x{render.resolution_y}.")
            self.proceed_with_high_res = True  # Automatically proceed after rescale

        elif total_pixels > 1_200_000 and not self.proceed_with_high_res:  # 1MP + 20%
            self.proceed_with_high_res = True  # Set to true to avoid repeated pop-ups
            self.report({'WARNING'}, "High resolution detected. Resolutions above 1MP may reduce performance and quality. To proceed, run the operator again.")
            context.scene.generation_status = 'idle'
            ComfyUIGenerate._is_running = False
            return {'CANCELLED'}
        
        self._cameras = [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
        if not self._cameras:
            self.report({'ERROR'}, "No cameras found in the scene.")
            context.scene.generation_status = 'idle'
            ComfyUIGenerate._is_running = False
            return {'CANCELLED'}
        # Sort cameras by name
        self._cameras.sort(key=lambda x: x.name)
        
        # Check if there is at least one ControlNet unit
        controlnet_units = getattr(context.scene, "controlnet_units", [])
        if not controlnet_units:
            self.report({'ERROR'}, "At least one ControlNet unit is required to run the operator.")
            context.scene.generation_status = 'idle'
            ComfyUIGenerate._is_running = False
            return {'CANCELLED'}
        
        # If there are curves within the scene, warn the user
        if any(obj.type == 'CURVE' for obj in bpy.context.scene.objects):
            self.report({'WARNING'}, "Curves detected in the scene. This may cause issues with the generation process. Consider removing them before proceeding.")
        
        print(f"Generating images for {len(self._cameras)} cameras")

        uv_slots_needed = len(self._cameras)

        # Find all mesh objects, check their material ids and store the highest one
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    material_id = get_last_material_index(obj)
                    if (material_id > self._material_id):
                        self._material_id = material_id
                # Check if there are enough UV map slots
                if not context.scene.bake_texture and context.scene.generation_method != 'uv_inpaint':
                    if not context.scene.overwrite_material or (context.scene.generation_method == 'refine' and context.scene.refine_preserve):
                        if 8 - len(obj.data.uv_layers) < uv_slots_needed:
                            self.report({'ERROR'}, "Not enough UV map slots for all cameras.")
                            context.scene.generation_status = 'idle'
                            ComfyUIGenerate._is_running = False
                            return {'CANCELLED'}
                    else:
                        # Make a set to count unique uv maps
                        uv_maps = set()
                        mesh = obj.data
                        uv_maps = [uv_layer.name for uv_layer in mesh.uv_layers]
                        if len(uv_maps) == 1:
                            # Probably a baked texture, check if there is enough uv slots
                            if 8 - len(obj.data.uv_layers) - 1 < uv_slots_needed:
                                self.report({'ERROR'}, "Not enough UV map slots for all cameras.")
                                context.scene.generation_status = 'idle'
                                ComfyUIGenerate._is_running = False
                                return {'CANCELLED'}
                        elif 8 - len(obj.data.uv_layers) + len(uv_maps) < uv_slots_needed:
                                print(f"8 - {len(obj.data.uv_layers)} + {len(uv_maps)} < {uv_slots_needed}")
                                self.report({'ERROR'}, "Not enough UV map slots for all cameras.")
                                context.scene.generation_status = 'idle'
                                ComfyUIGenerate._is_running = False
                                return {'CANCELLED'}
                            
                else:
                    if 8 - len(obj.data.uv_layers) < 1:
                        self.report({'ERROR'}, "Not enough UV map slots for baking. At least 1 slot is required.")

        if not context.scene.overwrite_material or self._material_id == -1 or (context.scene.generation_method == 'refine' and context.scene.refine_preserve):
            self._material_id += 1

        if context.scene.generation_method == 'sequential' and context.scene.sequential_custom_camera_order != "":
            # The format is: index1,index2,index3,...,indexN
            camera_order = context.scene.sequential_custom_camera_order.split(',')
            # Check if there is index for each camera
            if len(camera_order) != len(self._cameras):
                self.report({'ERROR'}, "The number of indices in the custom camera order must match the number of cameras.")
                context.scene.generation_status = 'idle'
                ComfyUIGenerate._is_running = False
                return {'CANCELLED'}
            # Make a backup of all cameras, remove and then add them in the custom order
            cameras = self._cameras.copy()
            cameras_backup = [camera.copy() for camera in cameras]
            for camera in cameras:
                bpy.data.objects.remove(camera)
            self._cameras = []
            # Re-add the cameras in the custom order
            for i, index in enumerate(camera_order):
                camera = cameras_backup[int(index)]
                # Rename the camera to match the index
                camera.name = f"Camera_{i}"
                self._cameras.append(camera)
                bpy.context.scene.collection.objects.link(camera)

        # If there is depth controlnet unit
        if any(unit["unit_type"] == "depth" for unit in controlnet_units):
            if context.scene.generation_method != 'uv_inpaint':
                # Export depth maps for each camera
                for i, camera in enumerate(self._cameras):
                    bpy.context.scene.camera = camera
                    self.export_depthmap(context, camera_id=i)
                if context.scene.generation_method == 'grid':
                    self.combine_maps(context, self._cameras, type="depth")
        # If there is canny controlnet unit
        if any(unit["unit_type"] == "canny" for unit in controlnet_units):
            if context.scene.generation_method != 'uv_inpaint':
                # Export canny maps for each camera
                for i, camera in enumerate(self._cameras):
                    bpy.context.scene.camera = camera
                    export_canny(context, camera_id=i, low_threshold=context.scene.canny_threshold_low, high_threshold=context.scene.canny_threshold_high)
                if context.scene.generation_method == 'grid':
                    self.combine_maps(context, self._cameras, type="canny")
        # If there is normal controlnet unit
        if any(unit["unit_type"] == "normal" for unit in controlnet_units):
            if context.scene.generation_method != 'uv_inpaint':
                # Export normal maps for each camera
                for i, camera in enumerate(self._cameras):
                    bpy.context.scene.camera = camera
                    self.export_normal(context, camera_id=i)
                if context.scene.generation_method == 'grid':
                    self.combine_maps(context, self._cameras, type="normal")

        # Prepare for generating
        if context.scene.generation_method == 'grid':
            self._threads_left = 1
        if context.scene.generation_method == 'uv_inpaint':
            mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
            self._threads_left = len(mesh_objects)
        else:
            self._threads_left = len(self._cameras)
        

        # Refine mode preparation
        if context.scene.generation_method == 'refine':
            for i, camera in enumerate(self._cameras):
                bpy.context.scene.camera = camera
                export_emit_image(context, camera_id=i)

        # UV inpainting mode preparation
        if context.scene.generation_method == 'uv_inpaint':
            # Check if there are baked textures for all objects
            mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
            
            if self.show_prompt_dialog:
                # Start the prompt collection process with the first object
                if not self._object_prompts:  # Only if prompts haven't been collected
                    self.current_object_name = mesh_objects[0].name
                    return context.window_manager.invoke_props_dialog(self, width=400)
            
            # Continue with normal execution if all prompts are collected
            for obj in mesh_objects:
                # Use get_file_path to check for baked texture existence
                baked_texture_path = get_file_path(context, "baked", object_name=obj.name)
                if not os.path.exists(baked_texture_path):
                    # Bake the texture if it doesn't exist
                    prepare_baking(context)
                    unwrap(obj, method='pack', overlap_only=True)
                    bake_texture(context, obj, texture_resolution=2048, output_dir=get_dir_path(context, "baked"))
                    
                # Export visibility masks for each object
                export_visibility(context, obj)
        
        self.prompt_text = context.scene.comfyui_prompt

        self._progress = 0.0
        self._stage = "Starting"
        redraw_ui(context)
        self._current_image = 0
        self._total_images = len(self._cameras)
        if context.scene.generation_method == 'grid':
            self._total_images = 1
            if context.scene.refine_images:
                self._total_images += len(self._cameras)  # Add refinement steps
        elif context.scene.generation_method == 'uv_inpaint':
            self._total_images = len(mesh_objects)

        # Add modal timer
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)       
        print("Starting thread") 
        if context.scene.generation_method == 'grid':
            self._thread = threading.Thread(target=self.async_generate, args=(context,))
        else:
            self._thread = threading.Thread(target=self.async_generate, args=(context, 0))
        
        self._thread.start()

        return {'RUNNING_MODAL'}


    def modal(self, context, event):
        """     
        Handles modal events.         
        :param context: Blender context.         
        :param event: Blender event.         
        :return: {'PASS_THROUGH'}     
        """
        if event.type == 'TIMER':
            redraw_ui(context)

            if not self._thread.is_alive():
                context.window_manager.event_timer_remove(self._timer)
                ComfyUIGenerate._is_running = False
                if self._error:
                    if self._error == "'25'" or self._error == "'111'":
                        # Probably canceled by user, quietly return
                        context.scene.generation_status = 'idle'
                        self.report({'WARNING'}, "Generation cancelled.")
                        remove_empty_dirs(context)
                        return {'CANCELLED'}
                    self.report({'ERROR'}, self._error)
                    remove_empty_dirs(context)
                    context.scene.generation_status = 'idle'
                    return {'CANCELLED'}
                self.report({'INFO'}, "Generation complete.")
                context.scene.display_settings.display_device = 'sRGB'
                context.scene.view_settings.view_transform = 'Standard'
                context.scene.generation_status = 'idle'
                # Clear output directories which are not needed anymore
                addon_prefs = context.preferences.addons[__package__].preferences
                # Save blend file in the output directory if enabled
                if addon_prefs.save_blend_file:
                    blend_dir = get_dir_path(context, "revision")
                    # Save the current blend file in the output directory
                    scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                    if not scene_name:
                        scene_name = context.scene.name
                    blend_file_path = os.path.join(blend_dir, f"{scene_name}_{context.scene.output_timestamp}.blend")
                    # Clean-up unused data blocks
                    bpy.ops.outliner.orphans_purge(do_recursive=True)
                    # Pack resources and save the blend file
                    bpy.ops.file.pack_all()
                    bpy.ops.wm.save_as_mainfile(filepath=blend_file_path, copy=True)
                remove_empty_dirs(context)
                return {'FINISHED'}
            
            # Handle prompt collection for UV inpainting
            if context.scene.generation_method == 'uv_inpaint' and self.show_prompt_dialog:
                mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
                current_index = next((i for i, obj in enumerate(mesh_objects) 
                                    if obj.name == self.current_object_name), -1)
                
                # Store the current prompt
                self._object_prompts[self.current_object_name] = self.current_object_prompt
                
                # Move to next object or finish
                if current_index < len(mesh_objects) - 1:
                    self.current_object_name = mesh_objects[current_index + 1].name
                    self.current_object_prompt = ""
                    return context.window_manager.invoke_props_dialog(self, width=400)
                else:
                    self.show_prompt_dialog = False
                    return self.execute(context)

        return {'PASS_THROUGH'}
    
    def cancel_generate(self, context):
        """     
        Cancels the generation process using api.interupt().    
        :param context: Blender context.         
        :return: None     
        """
        server_address = context.preferences.addons[__package__].preferences.server_address
        client_id = str(uuid.uuid4())
        data = json.dumps({"client_id": client_id}).encode('utf-8')
        req =  urllib.request.Request("http://{}/interrupt".format(server_address), data=data)
        context.scene.generation_status = 'waiting'
        ComfyUIGenerate._is_running = False
        urllib.request.urlopen(req)
        remove_empty_dirs(context)

    def async_generate(self, context, camera_id = None):
        """     
        Asynchronously generates the image using ComfyUI.         
        :param context: Blender context.         
        :return: None     
        """
        output_dir = context.preferences.addons[__package__].preferences.output_dir

        self._error = None
        try:
            mesh_objects = None
            if (context.scene.generation_method == 'uv_inpaint'):
                mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

            depth_path = None
            canny_path = None
            normal_path = None
            mask_path = None
            render_path = None
            while self._threads_left > 0:
                if context.scene.steps != 0:
                    # Generate image without ControlNet if needed
                    if camera_id == 0 and (context.scene.generation_method == 'sequential' or context.scene.generation_method == 'separate' or context.scene.generation_method == 'refine')\
                            and context.scene.sequential_ipadapter and context.scene.sequential_ipadapter_regenerate and not context.scene.use_ipadapter and context.scene.sequential_ipadapter_mode == 'first'\
                                and context.scene.model_architecture == 'sdxl':
                        self._stage = "Generating Reference Image"
                        # Don't use ControlNet for the first image if sequential_ipadapter_regenerate_wo_controlnet is enabled
                        if context.scene.sequential_ipadapter_regenerate_wo_controlnet:
                            original_strengths = [unit.strength for unit in context.scene.controlnet_units]
                            for unit in context.scene.controlnet_units:
                                unit.strength = 0.0
                    else:
                        self._stage = "Generating Image"
                    self._progress = 0
                    # Prepare paths using new get_file_path function
                    if context.scene.generation_method != 'uv_inpaint':
                        # Get paths for controlnet images for the current camera or grid
                        depth_path = get_file_path(context, "controlnet", subtype="depth", camera_id=camera_id) if camera_id is not None else get_file_path(context, "controlnet", subtype="depth")
                        canny_path = get_file_path(context, "controlnet", subtype="canny", camera_id=camera_id) if camera_id is not None else get_file_path(context, "controlnet", subtype="canny")
                        normal_path = get_file_path(context, "controlnet", subtype="normal", camera_id=camera_id) if camera_id is not None else get_file_path(context, "controlnet", subtype="normal")
                    else:
                        # Get paths for UV inpainting for the current object
                        current_obj_name = mesh_objects[self._current_image].name
                        mask_path = get_file_path(context, "uv_inpaint", subtype="visibility", object_name=current_obj_name)
                        render_path = get_file_path(context, "baked", object_name=current_obj_name) # Use baked texture as input render
                    
                    # Generate the image
                    if context.scene.generation_method == 'refine':
                        render_path = get_file_path(context, "inpaint", subtype="render", camera_id=camera_id)
                        if context.scene.model_architecture == 'flux1':
                            image = self.refine_flux(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path, render_path=render_path)
                        else:
                            image = self.refine(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path, render_path=render_path)
                    elif context.scene.generation_method == 'uv_inpaint':
                        if context.scene.model_architecture == 'flux1':
                            image = self.refine_flux(context, mask_path=mask_path, render_path=render_path)
                        else:
                            image = self.refine(context, mask_path=mask_path, render_path=render_path)
                    elif context.scene.generation_method == 'sequential':
                        if self._current_image == 0:
                            if context.scene.model_architecture == 'flux1':
                                image = self.generate_flux(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path)
                            else:
                                image = self.generate(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path)
                        else:
                            # Get paths for the previous render and mask
                            render_path = get_file_path(context, "inpaint", subtype="render", camera_id=self._current_image)
                            mask_path = get_file_path(context, "inpaint", subtype="visibility", camera_id=self._current_image)
                            if context.scene.model_architecture == 'flux1':
                                image = self.refine_flux(context, depth_path=depth_path, render_path=render_path, mask_path=mask_path, canny_path=canny_path, normal_path=normal_path)
                            else:
                                image = self.refine(context, depth_path=depth_path, render_path=render_path, mask_path=mask_path, canny_path=canny_path, normal_path=normal_path)
                    else: # Grid or Separate
                        if context.scene.model_architecture == 'flux1':
                            image = self.generate_flux(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path)
                        else:
                            image = self.generate(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path)

                    if image == {"error": "conn_refused"}:
                        self._error = "Failed to connect to ComfyUI server."
                        return
                    
                    # Save the generated image using new path structure
                    if context.scene.generation_method == 'uv_inpaint':
                        image_path = get_file_path(context, "generated_baked", object_name=mesh_objects[self._current_image].name, material_id=self._material_id)
                    elif camera_id is not None:
                        image_path = get_file_path(context, "generated", camera_id=camera_id, material_id=self._material_id)
                    else: # Grid mode initial generation
                        image_path = get_file_path(context, "generated", filename="generated_image_grid") # Save grid to a specific name
                    
                    with open(image_path, 'wb') as f:
                        f.write(image)
                        
                    # Use hack to re-generate the image using IPAdapter to match IPAdapter style
                    if camera_id == 0 and (context.scene.generation_method == 'sequential' or context.scene.generation_method == 'separate' or context.scene.generation_method == 'refine')\
                            and context.scene.sequential_ipadapter and context.scene.sequential_ipadapter_regenerate and not context.scene.use_ipadapter and context.scene.sequential_ipadapter_mode == 'first'\
                                and context.scene.model_architecture == 'sdxl':
                                
                        # Restore original strengths
                        if context.scene.sequential_ipadapter_regenerate_wo_controlnet:
                            for i, unit in enumerate(context.scene.controlnet_units):
                                unit.strength = original_strengths[i]
                        self._stage = "Generating Image"
                        context.scene.use_ipadapter = True
                        context.scene.ipadapter_image = image_path
                        if context.scene.generation_method == "refine":
                            image = self.refine(context, depth_path=depth_path, render_path=render_path, mask_path=mask_path, canny_path=canny_path, normal_path=normal_path)
                        else:
                            image = self.generate(context, depth_path=depth_path, canny_path=canny_path, normal_path=normal_path)
                        context.scene.use_ipadapter = False
                        image_path = image_path.replace(".png", "_ipadapter.png")
                        with open(image_path, 'wb') as f:
                            f.write(image)
                    
                     # Sequential mode callback
                    if context.scene.generation_method == 'sequential':
                        def image_project_callback():
                            redraw_ui(context)
                            project_image(context, self._material_id, stop_index=self._current_image)
                            if self._current_image < len(self._cameras) - 1:
                                next_camera_id = self._current_image + 1
                                export_visibility(context, camera_visibility=self._cameras[self._current_image]) # Export mask for current view
                                export_emit_image(context, camera_id=next_camera_id) # Export render for next view
                            # Set the event to signal the end of the process
                            self._wait_event.set()
                            return None
                        bpy.app.timers.register(image_project_callback)
                        # Wait for the event to be set
                        self._wait_event.wait()
                        self._wait_event.clear()
                        # Update paths for the next iteration (if any)
                        if self._current_image < len(self._cameras) - 1:
                            next_camera_id = self._current_image + 1
                            render_path = get_file_path(context, "inpaint", subtype="render", camera_id=next_camera_id)
                            mask_path = get_file_path(context, "inpaint", subtype="visibility", camera_id=next_camera_id)
                            # Update controlnet paths for the next camera
                            depth_path = get_file_path(context, "controlnet", subtype="depth", camera_id=next_camera_id)
                            canny_path = get_file_path(context, "controlnet", subtype="canny", camera_id=next_camera_id)
                            normal_path = get_file_path(context, "controlnet", subtype="normal", camera_id=next_camera_id)
                        
                else: # steps == 0, skip generation
                    pass # No image generation needed

                if context.scene.generation_method == 'separate' or context.scene.generation_method == 'refine' or context.scene.generation_method == 'sequential':
                    self._current_image += 1
                    self._threads_left -= 1
                    if camera_id is not None: # Increment camera_id only if it was initially provided
                        camera_id += 1

                elif context.scene.generation_method == 'uv_inpaint':
                    self._current_image += 1
                    self._threads_left -= 1

                elif context.scene.generation_method == 'grid':
                    # Split the generated grid image back into multiple images
                    self.split_generated_grid(context, self._cameras)
                    if context.scene.refine_images:
                        for i, _ in enumerate(self._cameras):
                            self._stage = f"Refining Image {i+1}/{len(self._cameras)}"
                            self._current_image = i + 1
                            self._progress = 0
                            # Refine the split images 
                            refine_depth_path = get_file_path(context, "controlnet", subtype="depth", camera_id=i)
                            refine_canny_path = get_file_path(context, "controlnet", subtype="canny", camera_id=i)
                            refine_normal_path = get_file_path(context, "controlnet", subtype="normal", camera_id=i)
                            refine_render_path = get_file_path(context, "generated", camera_id=i, material_id=self._material_id) # Use the split image as render input

                            if context.scene.model_architecture == 'flux1':
                                image = self.refine_flux(context, depth_path=refine_depth_path, canny_path=refine_canny_path, normal_path=refine_normal_path, render_path=refine_render_path)
                            else:
                                image = self.refine(context, depth_path=refine_depth_path, canny_path=refine_canny_path, normal_path=refine_normal_path, render_path=refine_render_path)

                            if image == {"error": "conn_refused"}:
                                self._error = "Failed to connect to ComfyUI server."
                                return
                            # Overwrite the split image with the refined one
                            image_path = get_file_path(context, "generated", camera_id=i, material_id=self._material_id)
                            with open(image_path, 'wb') as f:
                                f.write(image)
                    self._threads_left = 0
                
        except Exception as e:
            self._error = str(e)
            return

        def image_project_callback():
            if context.scene.generation_method == 'sequential':
                return None
            self._stage = "Projecting Image"
            if context.scene.bake_texture:
                self._stage = "Baking Textures & Projecting"
            redraw_ui(context)
            if context.scene.generation_method != 'uv_inpaint':
                project_image(context, self._material_id)
            else:
                # Apply the UV inpainted textures to each mesh
                from .render_tools import apply_uv_inpaint_texture
                mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
                for obj in mesh_objects:
                    texture_path = get_file_path(
                        context, "generated_baked", object_name=obj.name, material_id=self._material_id
                    )
                    apply_uv_inpaint_texture(context, obj, texture_path)
            return None

        bpy.app.timers.register(image_project_callback)

        # Update seed based on control parameter
        if context.scene.control_after_generate == 'increment':
            context.scene.seed += 1
        elif context.scene.control_after_generate == 'decrement':
            context.scene.seed -= 1
        elif context.scene.control_after_generate == 'randomize':
            context.scene.seed = np.random.randint(0, 1000000)

    def generate(self, context, depth_path=None, canny_path=None, normal_path=None):
        """     
        Generates the image using ComfyUI.         
        :param context: Blender context.
        :param depth_path: Path to the depth map image.
        :param canny_path: Path to the canny edge image.
        :param normal_path: Path to the normal map image.
        :return: Generated image binary data.     
        """
        from .util.helpers import prompt_text

        # Setup connection parameters
        server_address = context.preferences.addons[__package__].preferences.server_address
        client_id = str(uuid.uuid4())
        # Get revision dir for debug file
        revision_dir = get_generation_dirs(context)["revision"]

        # Initialize the prompt template and get node mappings
        prompt, NODES = self._create_base_prompt(context)
        
        # Set model resolution
        self._configure_resolution(prompt, context, NODES)

        if context.scene.use_ipadapter or (context.scene.generation_method == 'separate' and context.scene.sequential_ipadapter and self._current_image > 0):
            # Configure IPAdapter settings
            self._configure_ipadapter(prompt, context, NODES)
        
        # Build controlnet chain
        prompt = self._build_controlnet_chain(prompt, context, depth_path, canny_path, normal_path, NODES)
        
        # Save prompt for debugging (in revision dir)
        self._save_prompt_to_file(prompt, revision_dir)
        
        # Execute generation and get results
        try:
            ws = self._connect_to_websocket(server_address, client_id)
            images = self._execute_prompt_and_get_images(ws, prompt, client_id, server_address, NODES)
            ws.close()
        except ConnectionRefusedError:
            return {"error": "conn_refused"}
        
        print(f"Image generated with prompt: {context.scene.comfyui_prompt}")
        
        # Return the generated image from the save_image node
        return images[NODES['save_image']][0]

    def _create_base_prompt(self, context):
        """Creates and configures the base prompt with user settings."""
        from .util.helpers import prompt_text
        
        # Load the base prompt template
        prompt = json.loads(prompt_text)
        
        # Node IDs organized by functional category
        NODES = {
            # Text Prompting
            'pos_prompt': "9",
            'neg_prompt': "10",
            'clip_skip': "247",
            
            # Sampling Control
            'sampler': "15",
            'seed_control': "15",  # Same as sampler node but for seed parameter
            
            # Model Loading
            'checkpoint': "6",
            'lora': "26",
            
            # Latent Space
            'latent': "16",
            
            # Image Output
            'save_image': "25",

            # IPAdapter
            'ipadapter': "236",
            'ipadapter_image': "237",
        }
        
        base_prompt_text = context.scene.comfyui_prompt
        # Camera Prompt Injection
        if context.scene.use_camera_prompts and context.scene.generation_method in ['separate', 'sequential', 'refine'] and self._cameras and self._current_image < len(self._cameras):
            current_camera_name = self._cameras[self._current_image].name
            # Find the prompt in the collection
            prompt_item = next((item for item in context.scene.camera_prompts if item.name == current_camera_name), None)
            if prompt_item and prompt_item.prompt:
                view_desc = prompt_item.prompt
                # Prepend the view description
                base_prompt_text = f"{view_desc}, {base_prompt_text}"
        
        # Set text prompts
        prompt[NODES['pos_prompt']]["inputs"]["text"] = base_prompt_text
        prompt[NODES['neg_prompt']]["inputs"]["text"] = context.scene.comfyui_negative_prompt
        
        # Set sampling parameters
        prompt[NODES['sampler']]["inputs"]["seed"] = context.scene.seed
        prompt[NODES['sampler']]["inputs"]["steps"] = context.scene.steps
        prompt[NODES['sampler']]["inputs"]["cfg"] = context.scene.cfg
        prompt[NODES['sampler']]["inputs"]["sampler_name"] = context.scene.sampler
        prompt[NODES['sampler']]["inputs"]["scheduler"] = context.scene.scheduler
        
        # Set clip skip
        prompt[NODES['clip_skip']]["inputs"]["stop_at_clip_layer"] = -context.scene.clip_skip
        
        # Set LoRA parameters
        self._configure_lora(prompt, context, NODES['lora'])
        
        # Set the model name
        prompt[NODES['checkpoint']]["inputs"]["ckpt_name"] = context.scene.model_name
        
        return prompt, NODES

    def _configure_lora(self, prompt, context, lora_node):
        """Configures the LoRA settings based on user selection."""
        lora_mapping = {
            'hyper_8step': "Hyper-SDXL-8steps-lora.safetensors",
            'lightning_8step': "sdxl_lightning_8step_lora.safetensors",
            'hyper_4step': "Hyper-SDXL-4steps-lora.safetensors",
            'lightning_4step': "sdxl_lightning_4step_lora.safetensors",
            'hyper_1step': "Hyper-SDXL-1step-lora.safetensors",
            'lightning_2step': "sdxl_lightning_2step_lora.safetensors"
        }
        
        if context.scene.lora_type in lora_mapping:
            prompt[lora_node]["inputs"]["lora_name"] = lora_mapping[context.scene.lora_type]
        else:
            # Disable LoRA if not selected
            prompt[lora_node]["inputs"]["strength_model"] = 0
            prompt[lora_node]["inputs"]["strength_clip"] = 0

    def _configure_resolution(self, prompt, context, NODES):
        """Sets the generation resolution based on mode."""
        if context.scene.generation_method == 'grid':
            # Use the resolution of the grid image
            prompt[NODES['latent']]["inputs"]["width"] = self._grid_width
            prompt[NODES['latent']]["inputs"]["height"] = self._grid_height
        else:
            # Use current render resolution
            prompt[NODES['latent']]["inputs"]["width"] = context.scene.render.resolution_x
            prompt[NODES['latent']]["inputs"]["height"] = context.scene.render.resolution_y

    def _configure_ipadapter(self, prompt, context, NODES):
        # Configure IPAdapter if enabled
        
        # Connect IPAdapter output to the appropriate node
        prompt[NODES['sampler']]["inputs"]["model"] = [NODES['ipadapter'], 0]
        
        # Set IPAdapter image source based on ipadapter_image
        if context.scene.use_ipadapter:
            image_path = bpy.path.abspath(context.scene.ipadapter_image)
            prompt[NODES['ipadapter_image']]["inputs"]["image"] = image_path
        elif context.scene.sequential_ipadapter:
            if context.scene.sequential_ipadapter_mode == 'first':
                prompt[NODES['ipadapter_image']]["inputs"]["image"] = get_file_path(context, "generated", camera_id=0, material_id=self._material_id)
            else:
                prompt[NODES['ipadapter_image']]["inputs"]["image"] = get_file_path(context, "generated", camera_id=self._current_image - 1, material_id=self._material_id)

        # Connect ipadapter image to the input
        prompt[NODES['ipadapter']]["inputs"]["image"] = [NODES['ipadapter_image'], 0]
        
        # Configure IPAdapter settings
        prompt[NODES['ipadapter']]["inputs"]["weight"] = context.scene.ipadapter_strength
        prompt[NODES['ipadapter']]["inputs"]["start_at"] = context.scene.ipadapter_start
        prompt[NODES['ipadapter']]["inputs"]["end_at"] = context.scene.ipadapter_end
        
        # Set weight type
        weight_type_mapping = {
            'standard': "standard",
            'prompt': "prompt is more important",
            'style': "style transfer"
        }
        prompt[NODES['ipadapter']]["inputs"]["weight_type"] = weight_type_mapping.get(context.scene.ipadapter_weight_type, "standard")

    def _build_controlnet_chain(self, prompt, context, depth_path, canny_path, normal_path, NODES):
        """Builds the ControlNet processing chain."""
        # Build controlnet chain with guidance images
        prompt, final_node = build_controlnet_chain_extended(
            context, prompt, NODES['pos_prompt'], NODES['neg_prompt'], NODES['checkpoint'],
            {"depth": depth_path, "canny": canny_path, "normal": normal_path}
        )
        
        # Connect final node outputs to the KSampler
        prompt[NODES['sampler']]["inputs"]["positive"] = [final_node, 0]
        prompt[NODES['sampler']]["inputs"]["negative"] = [final_node, 1]
        
        return prompt

    def _save_prompt_to_file(self, prompt, output_dir):
        """Saves the prompt to a file for debugging."""
        try:
            with open(os.path.join(output_dir, "prompt.json"), 'w') as f:
                json.dump(prompt, f, indent=2)  # Added indent for better readability
        except Exception as e:
            print(f"Failed to save prompt to file: {str(e)}")

    def _connect_to_websocket(self, server_address, client_id):
        """Establishes WebSocket connection to ComfyUI server."""
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
            return ws
        except Exception as e:
            print(f"WebSocket connection failed: {str(e)}")
            raise

    def _execute_prompt_and_get_images(self, ws, prompt, client_id, server_address, NODES):
        """Executes the prompt and collects generated images."""
        # Send the prompt to the queue
        prompt_id = self._queue_prompt(prompt, client_id, server_address)
        
        # Process the WebSocket messages and collect images
        output_images = {}
        current_node = ""
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                
                if message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            break  # Execution is complete
                        else:
                            current_node = data['node']
                            print(f"Executing node: {current_node}")
                            
                elif message['type'] == 'progress':
                    progress = (message['data']['value'] / message['data']['max']) * 100
                    if progress != 0:
                        self._progress = progress  # Update progress for UI
                        print(f"Progress: {progress:.1f}%")
            else:
                # Binary data (image)
                if current_node == NODES['save_image']:  # SaveImageWebsocket node
                    print("Receiving generated image")
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])  # Skip the first 8 bytes (header)
                    output_images[current_node] = images_output
        
        return output_images

    def _queue_prompt(self, prompt, client_id, server_address):
        """Queues the prompt for processing by ComfyUI."""
        try:
            data = json.dumps({
                "prompt": prompt,
                "client_id": client_id
            }).encode('utf-8')
            
            req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
            response = json.loads(urllib.request.urlopen(req).read())
            
            return response['prompt_id']
        except Exception as e:
            print(f"Failed to queue prompt: {str(e)}")
            raise
    
    def refine(self, context, depth_path=None, canny_path=None, mask_path=None, render_path=None, normal_path=None):
        """     
        Refines the image using ComfyUI.         
        :param context: Blender context.         
        :param depth_path: Path to the depth map image.
        :param canny_path: Path to the canny edge image.
        :param mask_path: Path to the mask image for inpainting.
        :param render_path: Path to the input render image.
        :param normal_path: Path to the normal map image.         
        :return: Refined image.     
        """
        # Setup connection parameters
        server_address = context.preferences.addons[__package__].preferences.server_address
        client_id = str(uuid.uuid4())
        output_dir = get_generation_dirs(context)["revision"]

        # Initialize the img2img prompt template and configure base settings
        prompt, NODES = self._create_img2img_base_prompt(context)
        
        # Configure based on generation method
        self._configure_refinement_mode(prompt, context, render_path, mask_path, NODES)

        if (context.scene.use_ipadapter or (context.scene.sequential_ipadapter and self._current_image > 0)) and context.scene.generation_method != 'uv_inpaint':
            # Configure IPAdapter settings
            self._configure_ipadapter_refine(prompt, context, NODES)
        
        # Set up image inputs for different controlnet types
        self._refine_configure_images(prompt, depth_path, canny_path, normal_path, render_path, NODES)
        
        # Build controlnet chain for refinement if needed
        if not context.scene.generation_method == 'uv_inpaint':
            prompt = self._refine_build_controlnet_chain(prompt, context, depth_path, canny_path, normal_path, NODES)
        else:
            if context.scene.differential_diffusion:
                prompt[NODES['sampler']]["inputs"]["positive"] = [NODES['inpaint_conditioning'], 0]
                prompt[NODES['sampler']]["inputs"]["negative"] = [NODES['inpaint_conditioning'], 1]
            else:
                prompt[NODES['sampler']]["inputs"]["positive"] = [NODES['pos_prompt'], 0]
                prompt[NODES['sampler']]["inputs"]["negative"] = [NODES['neg_prompt'], 0]
        
        # Save prompt for debugging
        with open(os.path.join(output_dir, "prompt.json"), 'w') as f:
            json.dump(prompt, f)
        
        # Execute generation and get results
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
            images = self._refine_get_images(ws, prompt, client_id, server_address, NODES)
            ws.close()
        except ConnectionRefusedError:
            return {"error": "conn_refused"}
        
        print(f"Image refined with prompt: {context.scene.refine_prompt if context.scene.refine_prompt else context.scene.comfyui_prompt}")
        
        # Return the refined image
        return images[NODES['save_image']][0]

    def _create_img2img_base_prompt(self, context):
        """Creates and configures the base prompt for img2img refinement."""
        from .util.helpers import prompt_text_img2img
        
        prompt = json.loads(prompt_text_img2img)
        
        # Node IDs organized by functional category
        NODES = {
            # Text Prompting
            'pos_prompt': "102",
            'neg_prompt': "103",
            'clip_skip': "247",
            
            # Sampling Control
            'sampler': "105",
            
            # Model Loading
            'checkpoint': "38",
            'lora': "37",
            
            # Image Processing
            'upscale_grid': "118",
            'upscale_uv': "23",
            'vae_encode': "116",
            'vae_encode_inpaint': "13",
            'inpaint_conditioning': "228",
            
            # Input Images
            'input_image': "1",
            'mask_image': "12",
            'render_image': "117",
            'depth_image': "108",
            
            # Mask Processing
            'grow_mask': "224",
            'blur': "226",
            'image_to_mask': "227",
            
            # Advanced Features
            'differential_diffusion': "229",
            'ipadapter': "236",
            'ipadapter_image': "237",
            
            # Output
            'save_image': "111"
        }
        
        base_prompt_text = context.scene.comfyui_prompt
        # Camera Prompt Injection
        if context.scene.use_camera_prompts and context.scene.generation_method in ['separate', 'sequential', 'refine', 'grid'] and self._cameras and self._current_image < len(self._cameras):
            current_camera_name = self._cameras[self._current_image].name
            # Find the prompt in the collection
            prompt_item = next((item for item in context.scene.camera_prompts if item.name == current_camera_name), None)
            if prompt_item and prompt_item.prompt:
                view_desc = prompt_item.prompt
                # Prepend the view description
                base_prompt_text = f"{view_desc}, {base_prompt_text}"
        
        # Set positive prompt based on generation method
        if context.scene.generation_method in ['refine', 'uv_inpaint', 'sequential']:
            prompt[NODES['pos_prompt']]["inputs"]["text"] = base_prompt_text
        else:
            prompt[NODES['pos_prompt']]["inputs"]["text"] = context.scene.refine_prompt if context.scene.refine_prompt != "" else context.scene.comfyui_prompt
        
        # Set negative prompt
        prompt[NODES['neg_prompt']]["inputs"]["text"] = context.scene.comfyui_negative_prompt
        
        # Set sampling parameters
        prompt[NODES['sampler']]["inputs"]["seed"] = context.scene.seed
        prompt[NODES['sampler']]["inputs"]["steps"] = context.scene.refine_steps if context.scene.generation_method == 'grid' else context.scene.steps
        prompt[NODES['sampler']]["inputs"]["cfg"] = context.scene.refine_cfg if context.scene.generation_method == 'grid' else context.scene.cfg
        prompt[NODES['sampler']]["inputs"]["sampler_name"] = context.scene.refine_sampler if context.scene.generation_method == 'grid' else context.scene.sampler
        prompt[NODES['sampler']]["inputs"]["scheduler"] = context.scene.refine_scheduler if context.scene.generation_method == 'grid' else context.scene.scheduler
        if context.scene.generation_method == 'grid' or context.scene.generation_method == 'refine':
            prompt[NODES['sampler']]["inputs"]["denoise"] = context.scene.denoise
        else:
            prompt[NODES['sampler']]["inputs"]["denoise"] = 1.0
        
        # Set clip skip
        prompt[NODES['clip_skip']]["inputs"]["stop_at_clip_layer"] = -context.scene.clip_skip
        
        # Set upscale method and dimensions
        prompt[NODES['upscale_grid']]["inputs"]["upscale_method"] = context.scene.refine_upscale_method
        prompt[NODES['upscale_grid']]["inputs"]["width"] = context.scene.render.resolution_x
        prompt[NODES['upscale_grid']]["inputs"]["height"] = context.scene.render.resolution_y
        prompt[NODES['upscale_uv']]["inputs"]["upscale_method"] = "nearest-exact"
        prompt[NODES['upscale_uv']]["inputs"]["width"] = 1024
        prompt[NODES['upscale_uv']]["inputs"]["height"] = 1024
    
        # Set the model name
        prompt[NODES['checkpoint']]["inputs"]["ckpt_name"] = context.scene.model_name
        
        # Configure LoRA
        self._configure_lora_for_refinement(prompt, context, NODES['lora'])
        
        return prompt, NODES

    def _configure_lora_for_refinement(self, prompt, context, lora_node):
        """Configures the LoRA settings for the refinement process."""
        lora_mapping = {
            'hyper_8step': "Hyper-SDXL-8steps-lora.safetensors",
            'lightning_8step': "sdxl_lightning_8step_lora.safetensors",
            'hyper_4step': "Hyper-SDXL-4steps-lora.safetensors",
            'lightning_4step': "sdxl_lightning_4step_lora.safetensors",
            'hyper_1step': "Hyper-SDXL-1step-lora.safetensors",
            'lightning_2step': "sdxl_lightning_2step_lora.safetensors"
        }
        
        if context.scene.lora_type in lora_mapping:
            prompt[lora_node]["inputs"]["lora_name"] = lora_mapping[context.scene.lora_type]
        else:
            # Disable LoRA if not selected
            prompt[lora_node]["inputs"]["strength_model"] = 0
            prompt[lora_node]["inputs"]["strength_clip"] = 0

    def _configure_refinement_mode(self, prompt, context, render_path, mask_path, NODES):
        """Configures the prompt based on the specific refinement mode."""
        # Configure based on generation method
        if context.scene.generation_method == 'refine':
            prompt[NODES['vae_encode']]["inputs"]["pixels"] = [NODES['render_image'], 0]  # Use render directly
        
        elif context.scene.generation_method == 'uv_inpaint' or context.scene.generation_method == 'sequential':
            # Connect latent to KSampler
            prompt[NODES['sampler']]["inputs"]["latent_image"] = [NODES['vae_encode_inpaint'], 0] if not context.scene.differential_diffusion else [NODES['inpaint_conditioning'], 2]
            
            # Configure differential diffusion if enabled
            if context.scene.differential_diffusion:
                prompt[NODES['sampler']]["inputs"]["model"] = [NODES['differential_diffusion'], 0]
            
            # Configure mask settings
            prompt[NODES['mask_image']]["inputs"]["image"] = mask_path
            prompt[NODES['input_image']]["inputs"]["image"] = render_path
            
            # Configure mask blur settings
            if not context.scene.blur_mask:
                prompt[NODES['inpaint_conditioning']]["inputs"]["mask"] = [NODES['grow_mask'], 0]  # Direct connection
                prompt[NODES['vae_encode_inpaint']]["inputs"]["mask"] = [NODES['grow_mask'], 0]   # Direct connection
            
            # Set blur parameters
            prompt[NODES['blur']]["inputs"]["sigma"] = context.scene.blur_mask_sigma
            prompt[NODES['blur']]["inputs"]["blur_radius"] = context.scene.blur_mask_radius
            
            # Set grow mask parameter
            prompt[NODES['grow_mask']]["inputs"]["expand"] = context.scene.grow_mask_by
            
            if context.scene.generation_method == 'uv_inpaint':
                # Configure UV inpainting specific prompts
                self._configure_uv_inpainting_mode(prompt, context, render_path, NODES)
            else:  # Sequential mode
                # Configure sequential mode settings
                self._configure_sequential_mode(prompt, context, render_path, NODES)

    def _configure_uv_inpainting_mode(self, prompt, context, render_path, NODES):
        """Configures the prompts for UV inpainting mode."""
        # Connect upscale to VAE / InpaintConditioning
        if not context.scene.differential_diffusion:
            prompt[NODES['vae_encode_inpaint']]["inputs"]["pixels"] = [NODES['upscale_uv'], 0]
        else:
            prompt[NODES['inpaint_conditioning']]["inputs"]["pixels"] = [NODES['upscale_uv'], 0]
            # Set the noise_mask flag according to context.scene.differential_noise
            prompt[NODES['inpaint_conditioning']]["inputs"]["noise_mask"] = context.scene.differential_noise

        # Create base UV prompt
        uv_prompt = f"seamless (UV-unwrapped texture) of {context.scene.comfyui_prompt}, consistent material continuity, no visible seams or stretching, PBR material properties"
        uv_prompt_neg = f"seam, stitch, visible edge, texture stretching, repeating pattern, {context.scene.comfyui_negative_prompt}"
        
        prompt[NODES['pos_prompt']]["inputs"]["text"] = uv_prompt
        prompt[NODES['neg_prompt']]["inputs"]["text"] = uv_prompt_neg
        
        # Get the current object name from the file path
        current_object_name = os.path.basename(render_path).split('.')[0]
        
        # Use the object-specific prompt if available
        object_prompt = self._object_prompts.get(current_object_name, context.scene.comfyui_prompt)
        if object_prompt:
            uv_prompt = f"(UV-unwrapped texture) of {object_prompt}, consistent material continuity, no visible seams or stretching, PBR material properties"
            uv_prompt_neg = f"seam, stitch, visible edge, texture stretching, repeating pattern, {context.scene.comfyui_negative_prompt}"
            prompt[NODES['pos_prompt']]["inputs"]["text"] = uv_prompt
            prompt[NODES['neg_prompt']]["inputs"]["text"] = uv_prompt_neg

    def _configure_ipadapter_refine(self, prompt, context, NODES):
        # Connect IPAdapter output to the appropriate node
        if context.scene.differential_diffusion and context.scene.generation_method != 'refine':
            prompt[NODES['differential_diffusion']]["inputs"]["model"] = [NODES['ipadapter'], 0]
        else:
            prompt[NODES['sampler']]["inputs"]["model"] = [NODES['ipadapter'], 0]
        
        if context.scene.use_ipadapter:
             # Set IPAdapter image source based on ipadapter_image
            image_path = bpy.path.abspath(context.scene.ipadapter_image)
            prompt[NODES['ipadapter_image']]["inputs"]["image"] = image_path
        else: # Mode-specific IPAdapter
            if context.scene.sequential_ipadapter_mode == 'first':
                prompt[NODES['ipadapter_image']]["inputs"]["image"] = get_file_path(context, "generated", camera_id=0, material_id=self._material_id)
            else:
                prompt[NODES['ipadapter_image']]["inputs"]["image"] = get_file_path(context, "generated", camera_id=self._current_image - 1, material_id=self._material_id)
        
        
        # Connect ipadapter image to the input
        prompt[NODES['ipadapter']]["inputs"]["image"] = [NODES['ipadapter_image'], 0]
        
        # Configure IPAdapter settings
        prompt[NODES['ipadapter']]["inputs"]["weight"] = context.scene.ipadapter_strength
        prompt[NODES['ipadapter']]["inputs"]["start_at"] = context.scene.ipadapter_start
        prompt[NODES['ipadapter']]["inputs"]["end_at"] = context.scene.ipadapter_end
        
        # Set weight type
        weight_type_mapping = {
            'standard': "standard",
            'prompt': "prompt is more important",
            'style': "style transfer"
        }
        prompt[NODES['ipadapter']]["inputs"]["weight_type"] = weight_type_mapping.get(context.scene.ipadapter_weight_type, "standard")
    
    def _configure_sequential_mode(self, prompt, context, render_path, NODES):
        """Configures the prompt for sequential generation mode."""
        # Connect image directly to VAE
        prompt[NODES['vae_encode_inpaint']]["inputs"]["pixels"] = [NODES['input_image'], 0]
        if context.scene.differential_diffusion:
            # Set the noise_mask flag according to context.scene.differential_noise
            prompt[NODES['inpaint_conditioning']]["inputs"]["noise_mask"] = context.scene.differential_noise

    def _refine_configure_images(self, prompt, depth_path, canny_path, normal_path, render_path, NODES):
        """Configures the input images for the refinement process."""
        # Set depth map
        if depth_path:
            prompt[NODES['depth_image']]["inputs"]["image"] = depth_path
        
        # Set render image
        if render_path:
            prompt[NODES['render_image']]["inputs"]["image"] = render_path

    def _refine_build_controlnet_chain(self, prompt, context, depth_path, canny_path, normal_path, NODES):
        """Builds the ControlNet chain for refinement process."""
        # Determine inputs for ControlNet chain
        pos_input = NODES['pos_prompt'] if (not context.scene.differential_diffusion or 
                              context.scene.generation_method in ["grid", "refine"]) else NODES['inpaint_conditioning']
        neg_input = NODES['neg_prompt'] if (not context.scene.differential_diffusion or 
                              context.scene.generation_method in ["grid", "refine"]) else NODES['inpaint_conditioning']
        vae_input = NODES['checkpoint']
        
        # Build the ControlNet chain
        prompt, final = build_controlnet_chain_extended(
            context, prompt, pos_input, neg_input, vae_input, 
            {"depth": depth_path, "canny": canny_path, "normal": normal_path}
        )
        
        # Connect final outputs to KSampler
        prompt[NODES['sampler']]["inputs"]["positive"] = [final, 0]
        prompt[NODES['sampler']]["inputs"]["negative"] = [final, 1]
        
        return prompt

    def _refine_get_images(self, ws, prompt, client_id, server_address, NODES):
        """Executes the refinement prompt and collects the results."""
        # Queue the prompt
        prompt_id = self._queue_prompt(prompt, client_id, server_address)
        
        # Process WebSocket messages
        output_images = {}
        current_node = ""
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                
                if message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            break  # Execution complete
                        else:
                            current_node = data['node']
                
                elif message['type'] == 'progress':
                    progress = (message['data']['value'] / message['data']['max']) * 100
                    if progress != 0:
                        self._progress = progress  # Update progress for UI
            else:
                # Binary data (image)
                if current_node == NODES['save_image']:  # Save image node
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])  # Skip header bytes
                    output_images[current_node] = images_output
        
        return output_images
    
    def export_depthmap(self, context, camera_id=None):
        """     
        Exports the depth map of the scene.         
        :param context: Blender context.         
        :param camera_id: ID of the camera.         
        :return: None     
        """
        print("Exporting depth map")
        # Save original settings to restore later.
        original_engine = bpy.context.scene.render.engine
        original_view_transform = bpy.context.scene.view_settings.view_transform
        original_film_transparent = bpy.context.scene.render.film_transparent

        # Set animation frame to 1
        bpy.context.scene.frame_set(1)

        output_dir = get_dir_path(context, "controlnet")["depth"]
        output_file = f"depth_map{camera_id}" if camera_id is not None else "depth_map"

        # Ensure the directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Get the active view layer
        view_layer = bpy.context.view_layer

        # Switch to WORKBENCH render engine
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'

        bpy.context.scene.display_settings.display_device = 'sRGB'
        bpy.context.scene.view_settings.view_transform = 'Raw'

        # Enable depth pass in the render settings
        view_layer.use_pass_z = True

        # Use the compositor to save the depth pass
        bpy.context.scene.use_nodes = True
        nodes = bpy.context.scene.node_tree.nodes
        links = bpy.context.scene.node_tree.links
        
        # Ensure animation format is not selected
        bpy.context.scene.render.image_settings.file_format = 'PNG'

        # Clear default nodes
        for node in nodes:
            nodes.remove(node)

        # Add render layers node
        render_layers_node = nodes.new(type="CompositorNodeRLayers")
        render_layers_node.location = (0, 0)

        # Add a normalize node (to scale depth values between 0 and 1)
        normalize_node = nodes.new(type="CompositorNodeNormalize")
        normalize_node.location = (200, 0)
        links.new(render_layers_node.outputs["Depth"], normalize_node.inputs[0])

        # Add an invert node to flip the depth map values
        invert_node = nodes.new(type="CompositorNodeInvert")
        invert_node.location = (400, 0)
        links.new(normalize_node.outputs[0], invert_node.inputs[1])

        # Add an output file node
        output_node = nodes.new(type="CompositorNodeOutputFile")
        output_node.location = (600, 0)
        output_node.base_path = output_dir
        output_node.file_slots[0].path = output_file
        output_node.format.file_format = "PNG"  # Save as PNG
        links.new(invert_node.outputs[0], output_node.inputs[0])

        # Render the scene
        bpy.ops.render.render(write_still=True)

        bpy.context.scene.view_settings.view_transform = 'Standard'

        print(f"Depth map saved to: {os.path.join(output_dir, output_file)}.png")
        
        # Restore original settings
        bpy.context.scene.render.engine = original_engine
        bpy.context.scene.view_settings.view_transform = original_view_transform
        bpy.context.scene.render.film_transparent = original_film_transparent

    def export_normal(self, context, camera_id=None):
        """
        Exports the normal map of the scene.
        Areas without geometry will show the neutral color (0.5, 0.5, 1.0).
        :param context: Blender context.
        :param camera_id: ID of the camera.
        :return: None
        """
        print("Exporting normal map")
        bpy.context.scene.frame_set(1)
        output_dir = get_dir_path(context, "controlnet")["normal"]
        output_file = f"normal_map{camera_id}" if camera_id is not None else "normal_map"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        view_layer = bpy.context.view_layer
        view_layer.use_pass_normal = True

        # Store original settings to restore later.
        original_engine = bpy.context.scene.render.engine
        original_view_transform = bpy.context.scene.view_settings.view_transform
        original_film_transparent = bpy.context.scene.render.film_transparent

        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
        bpy.context.scene.view_settings.view_transform = 'Raw'
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.use_nodes = True

        # Disable unnecessary passes.
        view_layer.use_pass_z = False
        view_layer.use_pass_uv = False
        view_layer.use_pass_combined = False
        view_layer.use_pass_emit = False
        view_layer.use_pass_environment = False
        view_layer.use_pass_mist = False

        # Clear existing nodes.
        nodes = bpy.context.scene.node_tree.nodes
        links = bpy.context.scene.node_tree.links
        for node in nodes:
            nodes.remove(node)

        # Create the Render Layers node (provides the baked normal pass).
        render_layers_node = nodes.new(type="CompositorNodeRLayers")
        render_layers_node.location = (0, 0)

        # Create an RGB node set to the neutral normal color (0.5, 0.5, 1.0, 1.0).
        bg_node = nodes.new(type="CompositorNodeRGB")
        bg_node.outputs[0].default_value = (0.5, 0.5, 1.0, 1.0)
        bg_node.location = (0, -200)

        alpha_over_node = nodes.new(type="CompositorNodeAlphaOver")
        alpha_over_node.location = (200, 0)
        # Link the normal pass to the top input.
        links.new(render_layers_node.outputs["Normal"], alpha_over_node.inputs[2])
        # Link the neutral background to the bottom input.
        links.new(bg_node.outputs[0], alpha_over_node.inputs[1])

        # Create the Output File node.
        output_node = nodes.new(type="CompositorNodeOutputFile")
        output_node.location = (400, 0)
        output_node.base_path = output_dir
        output_node.file_slots[0].path = output_file
        output_node.format.file_format = "PNG"
        links.new(alpha_over_node.outputs[0], output_node.inputs[0])
        links.new(render_layers_node.outputs["Alpha"], alpha_over_node.inputs[0])

        bpy.ops.render.render(write_still=True)

        # Restore original settings.
        bpy.context.scene.render.engine = original_engine
        bpy.context.scene.view_settings.view_transform = original_view_transform
        bpy.context.scene.render.film_transparent = original_film_transparent

        print(f"Normal map saved to: {os.path.join(output_dir, output_file)}.png")

    def combine_maps(self, context, cameras, type):
        """Combines depth maps into a grid."""
        if type == 'depth':
            grid_image_path = get_file_path(context, "controlnet", subtype="depth", camera_id=None, material_id=self._material_id)
        elif type == 'canny':
            grid_image_path = get_file_path(context, "controlnet", subtype="canny", camera_id=None, material_id=self._material_id)
        elif type == 'normal':
            grid_image_path = get_file_path(context, "controlnet", subtype="normal", camera_id=None, material_id=self._material_id)

        # Render depth maps for each camera and combine them into a grid
        depth_maps = []
        for i, camera in enumerate(cameras):
            bpy.context.scene.camera = camera
            if type == 'depth':
                depth_map_path = get_file_path(context, "controlnet", subtype="depth", camera_id=i, material_id=self._material_id)
            elif type == 'canny':
                depth_map_path = get_file_path(context, "controlnet", subtype="canny", camera_id=i, material_id=self._material_id)
            elif type == 'normal':
                depth_map_path = get_file_path(context, "controlnet", subtype="normal", camera_id=i, material_id=self._material_id)
            depth_maps.append(depth_map_path)

        # Combine depth maps into a grid
        grid_image = self.create_grid_image(depth_maps)
        grid_image = self.rescale_to_1mp(grid_image)
        grid_image.save(grid_image_path)
        print(f"Combined depth map grid saved to: {grid_image_path}")

    def create_grid_image(self, image_paths):
        """Creates a grid image from a list of image paths."""
        images = [Image.open(path) for path in image_paths]
        widths, heights = zip(*(i.size for i in images))

        # Calculate grid dimensions to make it as square as possible
        num_images = len(images)
        grid_width = math.ceil(math.sqrt(num_images))
        grid_height = math.ceil(num_images / grid_width)

        max_width = max(widths)
        max_height = max(heights)

        total_width = grid_width * max_width
        total_height = grid_height * max_height

        grid_image = Image.new('RGB', (total_width, total_height))

        x_offset = 0
        y_offset = 0
        for i, img in enumerate(images):
            grid_image.paste(img, (x_offset, y_offset))
            x_offset += max_width
            if (i + 1) % grid_width == 0:
                x_offset = 0
                y_offset += max_height

        return grid_image

    def rescale_to_1mp(self, image):
        """Rescales the image to approximately 1MP."""
        from PIL import Image

        width, height = image.size
        total_pixels = width * height
        scale_factor = (1_000_000 / total_pixels) ** 0.5

        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Ensure the new dimensions are divisible by 8 (ComfyUI requirement)
        new_width -= new_width % 8
        new_height -= new_height % 8

        self._grid_height = new_height
        self._grid_width = new_width

        return image.resize((new_width, new_height), Image.LANCZOS)

    def split_generated_grid(self, context, cameras):
        """Splits the generated grid image back into multiple images."""
        grid_image_path = get_file_path(context, "generated", camera_id=None, material_id=self._material_id)

        # Load the generated grid image
        from PIL import Image
        grid_image = Image.open(grid_image_path)

        # Calculate grid dimensions to make it as square as possible
        num_images = len(cameras)
        grid_width = math.ceil(math.sqrt(num_images))
        grid_height = math.ceil(num_images / grid_width)

        max_width = grid_image.width // grid_width
        max_height = grid_image.height // grid_height

        x_offset = 0
        y_offset = 0
        for i in range(num_images):
            bbox = (x_offset, y_offset, x_offset + max_width, y_offset + max_height)
            individual_image = grid_image.crop(bbox)
            individual_image_path = get_file_path(context, "generated", camera_id=i, material_id=self._material_id)
            individual_image.save(individual_image_path)
            print(f"Generated image for camera {i+1} saved to: {individual_image_path}")
            x_offset += max_width
            if (i + 1) % grid_width == 0:
                x_offset = 0
                y_offset += max_height

    def draw(self, context):
        layout = self.layout
        if context.scene.generation_method == 'uv_inpaint' and self.show_prompt_dialog:
            layout.label(text=f"Enter prompt for object: {self.current_object_name}")
            layout.prop(self, "current_object_prompt", text="")

    def invoke(self, context, event):
        if context.scene.generation_method == 'uv_inpaint':
            # Reset object prompts on every run
            self._object_prompts = {}
            self._mesh_objects = [obj.name for obj in bpy.context.scene.objects if obj.type == 'MESH']
            self.mesh_index = 0
            self.current_object_name = self._mesh_objects[0] if self._mesh_objects else ""
            # If "Ask for object prompts" is disabled, don’t prompt per object
            if not context.scene.ask_object_prompts:
                self.show_prompt_dialog = False
                return self.execute(context)
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def create_base_prompt_flux(self, context):
        """Creates and configures the base Flux prompt.
        Uses prompt_text_flux and does not include negative prompt or LoRA configuration.
        """
        from .util.helpers import prompt_text_flux
        prompt = json.loads(prompt_text_flux)
        # Define node IDs for Flux
        NODES = {
            'pos_prompt': "6",          # CLIPTextEncode for positive prompt
            'vae_loader': "10",         # VAELoader
            'dual_clip': "11",          # DualCLIPLoader
            'unet_loader': "12",        # UNETLoader
            'sampler': "13",            # SamplerCustomAdvanced
            'ksampler': "16",           # KSamplerSelect
            'scheduler': "17",          # BasicScheduler
            'guider': "22",             # BasicGuider
            'noise': "25",              # RandomNoise
            'flux_guidance': "26",      # FluxGuidance
            'latent': "30",             # EmptyLatentImage
            'save_image': "32"          # SaveImageWebsocket
        }
        
        base_prompt_text = context.scene.comfyui_prompt
        # Camera Prompt Injection
        if context.scene.use_camera_prompts and context.scene.generation_method in ['separate', 'sequential', 'refine'] and self._cameras and self._current_image < len(self._cameras):
            current_camera_name = self._cameras[self._current_image].name
            # Find the prompt in the collection
            prompt_item = next((item for item in context.scene.camera_prompts if item.name == current_camera_name), None)
            if prompt_item and prompt_item.prompt:
                view_desc = prompt_item.prompt
                # Prepend the view description
                base_prompt_text = f"{view_desc}, {base_prompt_text}"
        
        # Set positive prompt only (Flux doesn't use negative prompt)
        prompt[NODES['pos_prompt']]["inputs"]["text"] = base_prompt_text
        
        # Configure sampler parameters
        prompt[NODES['noise']]["inputs"]["noise_seed"] = context.scene.seed
        prompt[NODES['scheduler']]["inputs"]["steps"] = context.scene.steps
        prompt[NODES['scheduler']]["inputs"]["scheduler"] = context.scene.scheduler
        prompt[NODES['flux_guidance']]["inputs"]["guidance"] = context.scene.cfg
        prompt[NODES['ksampler']]["inputs"]["sampler_name"] = context.scene.sampler

        # Flux does not use negative prompt or LoRA.
        return prompt, NODES

    def generate_flux(self, context, depth_path=None, canny_path=None, normal_path=None):
        """Generates an image using Flux 1.
        Similar in structure to generate() but uses Flux nodes, skips negative prompt and LoRA.
        """
        from .util.helpers import prompt_text_flux
        server_address = context.preferences.addons[__package__].preferences.server_address
        client_id = str(uuid.uuid4())
        output_dir = context.preferences.addons[__package__].preferences.output_dir

        # Build Flux base prompt and node mapping.
        prompt, NODES = self.create_base_prompt_flux(context)
        
        self._configure_resolution(prompt, context, NODES)

        prompt, final_node = build_controlnet_chain_extended(
            context, prompt, NODES['pos_prompt'], NODES['pos_prompt'], NODES['vae_loader'],
            {"depth": depth_path, "canny": canny_path, "normal": normal_path}
        )
        # Connect final node to FluxGuidance
        prompt[NODES['flux_guidance']]["inputs"]["conditioning"] = [final_node, 0]
        # Note: No negative prompt is connected.
        # Save prompt for debugging.
        try:
            with open(os.path.join(output_dir, "prompt_flux.json"), 'w') as f:
                json.dump(prompt, f, indent=2)
        except Exception as e:
            print(f"Failed to save flux prompt: {e}")
        # Execute generation via websocket.
        try:
            ws = self._connect_to_websocket(server_address, client_id)
            images = self._execute_prompt_and_get_images(ws, prompt, client_id, server_address, NODES)
            ws.close()
        except ConnectionRefusedError:
            return {"error": "conn_refused"}
        print(f"Flux image generated with prompt: {context.scene.comfyui_prompt}")
        return images[NODES['save_image']][0]

    def _create_img2img_base_prompt_flux(self, context):
        """Creates and configures the base Flux prompt for img2img refinement."""
        from .util.helpers import prompt_text_img2img_flux
        
        prompt = json.loads(prompt_text_img2img_flux)
        
        # Node IDs organized by functional category for Flux
        NODES = {
            # Text Prompting
            'pos_prompt': "6",          # CLIPTextEncode for positive prompt
            
            # Model Components
            'vae_loader': "10",         # VAELoader
            'dual_clip': "11",          # DualCLIPLoader
            'unet_loader': "12",        # UNETLoader
            
            # Sampling Control
            'sampler': "13",            # SamplerCustomAdvanced
            'ksampler': "16",           # KSamplerSelect
            'scheduler': "17",          # BasicScheduler
            'guider': "22",             # BasicGuider
            'noise': "25",              # RandomNoise
            'flux_guidance': "26",      # FluxGuidance
            
            # Image Processing
            'vae_decode': "8",          # VAEDecode
            'vae_encode': "116",        # VAEEncode
            'vae_encode_inpaint': "44", # VAEEncodeForInpaint
            'upscale': "118",           # ImageScale for upscaling
            'upscale_uv': "43",         # ImageScale for UV maps
            
            # Input Images
            'input_image': "1",         # LoadImage for input
            'mask_image': "42",         # LoadImage for mask
            'render_image': "117",      # LoadImage for render
            
            # Mask Processing
            'grow_mask': "224",         # GrowMask
            'blur': "226",              # ImageBlur
            'image_to_mask': "227",     # ImageToMask
            'mask_to_image': "225",     # MaskToImage
            
            # Advanced Features
            'differential_diffusion': "50", # DifferentialDiffusion for Flux
            'inpaint_conditioning': "51",   # InpaintModelConditioning for Flux
            
            # Latent Space
            'latent': "30",             # EmptyLatentImage
            
            # Output
            'save_image': "32"          # SaveImageWebsocket
        }
        
        base_prompt_text = context.scene.comfyui_prompt
        # Camera Prompt Injection
        if context.scene.use_camera_prompts and context.scene.generation_method in ['separate', 'sequential', 'refine', 'grid'] and self._cameras and self._current_image < len(self._cameras):
            current_camera_name = self._cameras[self._current_image].name
            # Find the prompt in the collection
            prompt_item = next((item for item in context.scene.camera_prompts if item.name == current_camera_name), None)
            if prompt_item and prompt_item.prompt:
                view_desc = prompt_item.prompt
                # Prepend the view description
                base_prompt_text = f"{view_desc}, {base_prompt_text}"
        
        # Set positive prompt (Flux doesn't use negative prompt)
        prompt[NODES['pos_prompt']]["inputs"]["text"] = base_prompt_text
        
        # Configure sampler parameters
        prompt[NODES['noise']]["inputs"]["noise_seed"] = context.scene.seed
        prompt[NODES['scheduler']]["inputs"]["steps"] = context.scene.refine_steps if context.scene.generation_method == 'grid' else context.scene.steps
        prompt[NODES['scheduler']]["inputs"]["denoise"] = context.scene.denoise if context.scene.generation_method in ['grid', 'refine'] else 1.0
        prompt[NODES['flux_guidance']]["inputs"]["guidance"] = context.scene.refine_cfg if context.scene.generation_method == 'grid' else context.scene.cfg
        prompt[NODES['ksampler']]["inputs"]["sampler_name"] = context.scene.refine_sampler if context.scene.generation_method == 'grid' else context.scene.sampler
        prompt[NODES['scheduler']]["inputs"]["scheduler"] = context.scene.refine_scheduler if context.scene.generation_method == 'grid' else context.scene.scheduler
        
        # Configure upscale settings
        prompt[NODES['upscale']]["inputs"]["upscale_method"] = context.scene.refine_upscale_method
        prompt[NODES['upscale']]["inputs"]["width"] = context.scene.render.resolution_x
        prompt[NODES['upscale']]["inputs"]["height"] = context.scene.render.resolution_y
        
        # Configure UV upscale settings
        prompt[NODES['upscale_uv']]["inputs"]["upscale_method"] = "nearest-exact"
        prompt[NODES['upscale_uv']]["inputs"]["width"] = 1024
        prompt[NODES['upscale_uv']]["inputs"]["height"] = 1024
        
        # Configure mask settings
        prompt[NODES['grow_mask']]["inputs"]["expand"] = context.scene.grow_mask_by
        prompt[NODES['blur']]["inputs"]["blur_radius"] = context.scene.blur_mask_radius
        prompt[NODES['blur']]["inputs"]["sigma"] = context.scene.blur_mask_sigma
        
        return prompt, NODES

    def refine_flux(self, context, depth_path=None, canny_path=None, mask_path=None, render_path=None, normal_path=None):
        """     
        Refines the image using Flux 1 in ComfyUI.         
        :param context: Blender context.         
        :param depth_path: Path to the depth map image.
        :param canny_path: Path to the canny edge image.
        :param mask_path: Path to the mask image for inpainting.
        :param render_path: Path to the input render image.
        :param normal_path: Path to the normal map image.         
        :return: Refined image.     
        """
        # Setup connection parameters
        server_address = context.preferences.addons[__package__].preferences.server_address
        client_id = str(uuid.uuid4())
        output_dir = context.preferences.addons[__package__].preferences.output_dir

        # Initialize the img2img prompt template for Flux
        prompt, NODES = self._create_img2img_base_prompt_flux(context)
        
        # Configure based on generation method
        self._configure_refinement_mode_flux(prompt, context, render_path, mask_path, NODES)
        
        # Set up image inputs for different controlnet types
        self._refine_configure_images_flux(prompt, depth_path, canny_path, normal_path, render_path, NODES)
        
        # Build controlnet chain for refinement if needed
        if not context.scene.generation_method == 'uv_inpaint':
            prompt = self._refine_build_controlnet_chain_flux(prompt, context, depth_path, canny_path, normal_path, NODES)
        
        # Save prompt for debugging
        with open(os.path.join(output_dir, "prompt_flux_img2img.json"), 'w') as f:
            json.dump(prompt, f)
        
        # Execute generation and get results
        try:
            ws = self._connect_to_websocket(server_address, client_id)
            images = self._execute_prompt_and_get_images(ws, prompt, client_id, server_address, NODES)
            ws.close()
        except ConnectionRefusedError:
            return {"error": "conn_refused"}
        
        print(f"Image refined with Flux using prompt: {context.scene.comfyui_prompt}")
        
        # Return the refined image
        return images[NODES['save_image']][0]

    def _configure_refinement_mode_flux(self, prompt, context, render_path, mask_path, NODES):
        """Configures the prompt based on the specific refinement mode for Flux."""
        # Configure based on generation method
        if context.scene.generation_method == 'refine':
            # Configure for refine mode - load render directly
            prompt[NODES['render_image']]["inputs"]["image"] = render_path
            prompt[NODES['vae_encode']]["inputs"]["pixels"] = [NODES['render_image'], 0]
            # Connect latent to sampler
            prompt[NODES['sampler']]["inputs"]["latent_image"] = [NODES['vae_encode'], 0]
        
        elif context.scene.generation_method in ['uv_inpaint', 'sequential']:
            # Configure for inpainting modes
            prompt[NODES['mask_image']]["inputs"]["image"] = mask_path
            prompt[NODES['input_image']]["inputs"]["image"] = render_path
            
            # Configure mask processing
            if not context.scene.blur_mask:
                prompt[NODES['vae_encode_inpaint']]["inputs"]["mask"] = [NODES['grow_mask'], 0]
                if context.scene.differential_diffusion:
                    prompt[NODES['inpaint_conditioning']]["inputs"]["mask"] = [NODES['grow_mask'], 0]
            else:
                # Configure blur chain
                prompt[NODES['image_to_mask']]["inputs"]["image"] = [NODES['blur'], 0]
                prompt[NODES['vae_encode_inpaint']]["inputs"]["mask"] = [NODES['image_to_mask'], 0]
            
            # Different setups based on differential diffusion
            if context.scene.differential_diffusion:
                # Connect differential diffusion between model loader and other components
                prompt[NODES['guider']]["inputs"]["model"] = [NODES['differential_diffusion'], 0]
                prompt[NODES['scheduler']]["inputs"]["model"] = [NODES['differential_diffusion'], 0]
                
                # Connect inpaint conditioning to differential diffusion
                prompt[NODES['differential_diffusion']]["inputs"]["model"] = [NODES['unet_loader'], 0]
                
                # Configure inpaint conditioning with proper input image and mask
                prompt[NODES['inpaint_conditioning']]["inputs"]["pixels"] = [
                    NODES['upscale_uv'], 0
                ] if context.scene.generation_method == 'uv_inpaint' else [NODES['input_image'], 0]
                
                # Connect latent to sampler from inpaint conditioning
                prompt[NODES['sampler']]["inputs"]["latent_image"] = [NODES['inpaint_conditioning'], 2]
                
                # Connect conditioning to flux_guidance
                prompt[NODES['flux_guidance']]["inputs"]["conditioning"] = [NODES['inpaint_conditioning'], 0]
            else:
                # Standard setup without differential diffusion
                prompt[NODES['sampler']]["inputs"]["latent_image"] = [NODES['vae_encode_inpaint'], 0]
            
            if context.scene.generation_method == 'uv_inpaint':
                self._configure_uv_inpainting_mode_flux(prompt, context, render_path, NODES)
            else:  # Sequential mode
                self._configure_sequential_mode_flux(prompt, context, NODES)

    def _configure_uv_inpainting_mode_flux(self, prompt, context, render_path, NODES):
        """Configures the prompts for UV inpainting mode in Flux."""
        # UV inpainting specific configuration
        prompt[NODES['upscale_uv']]["inputs"]["image"] = [NODES['input_image'], 0]
        
        if not context.scene.differential_diffusion:
            prompt[NODES['vae_encode_inpaint']]["inputs"]["pixels"] = [NODES['upscale_uv'], 0]
        else:
            # Set the noise_mask flag according to context.scene.differential_noise
            prompt[NODES['inpaint_conditioning']]["inputs"]["noise_mask"] = context.scene.differential_noise
        
        # Create UV-specific prompt
        uv_prompt = f"seamless (UV-unwrapped texture) of {context.scene.comfyui_prompt}, consistent material continuity, no visible seams or stretching"
        prompt[NODES['pos_prompt']]["inputs"]["text"] = uv_prompt
        
        # Object-specific prompt if available
        current_object_name = os.path.basename(render_path).split('.')[0]
        object_prompt = self._object_prompts.get(current_object_name, context.scene.comfyui_prompt)
        if object_prompt:
            uv_prompt = f"(UV-unwrapped texture) of {object_prompt}, consistent material continuity, no visible seams or stretching"
            prompt[NODES['pos_prompt']]["inputs"]["text"] = uv_prompt

    def _configure_sequential_mode_flux(self, prompt, context, NODES):
        """Configures the prompt for sequential generation mode in Flux."""
        # Direct connection for sequential mode
        if not context.scene.differential_diffusion:
            prompt[NODES['vae_encode_inpaint']]["inputs"]["pixels"] = [NODES['input_image'], 0]
        else:
            # Set the noise_mask flag according to context.scene.differential_noise
            prompt[NODES['inpaint_conditioning']]["inputs"]["noise_mask"] = context.scene.differential_noise
        
        # Note: Flux doesn't support IPAdapter in the same way as SDXL

    def _refine_configure_images_flux(self, prompt, depth_path, canny_path, normal_path, render_path, NODES):
        """Configures the input images for the refinement process in Flux."""
        # Set render image if provided
        if render_path:
            prompt[NODES['render_image']]["inputs"]["image"] = render_path
        
        # Control images are handled by the controlnet chain builder

    def _refine_build_controlnet_chain_flux(self, prompt, context, depth_path, canny_path, normal_path, NODES):
        """Builds the ControlNet chain for refinement process with Flux."""
        input = NODES['pos_prompt'] if not context.scene.differential_diffusion else NODES['inpaint_conditioning']
        # For Flux, the controlnet chain connects to the guidance node
        prompt, final_node = build_controlnet_chain_extended(
            context, prompt, input, input, NODES['vae_loader'],
            {"depth": depth_path, "canny": canny_path, "normal": normal_path}
        )
        # Connect final node to FluxGuidance conditioning input
        prompt[NODES['flux_guidance']]["inputs"]["conditioning"] = [final_node, 0]
        return prompt

import json  # ensure json is imported

def build_controlnet_chain_extended(context, base_prompt, pos_input, neg_input, vae_input, image_dict):
    addon_prefs = context.preferences.addons[__package__].preferences
    try:
        mapping = json.loads(addon_prefs.controlnet_mapping)
    except Exception:
        mapping = {}
    
    # Get the dynamic collection of ControlNet units
    controlnet_units = getattr(context.scene, "controlnet_units", [])
    current_pos = pos_input
    current_neg = neg_input
    for idx, unit in enumerate(controlnet_units):
        # Generate unique keys for nodes in this chain unit.
        load_key = str(200 + idx * 3)       # LoadImage node
        loader_key = str(200 + idx * 3 + 1)   # ControlNetLoader node
        apply_key = str(200 + idx * 3 + 2)    # ControlNetApplyAdvanced node

        # Create the LoadImage node.
        base_prompt[load_key] = {
            "inputs": {
                "image": image_dict.get(unit.unit_type, ""),
                "upload": "image"
            },
            "class_type": "LoadImage",
            "_meta": {
                "title": f"Load Image ({unit.unit_type})"
            }
        }
        # Create the ControlNetLoader node.
        base_prompt[loader_key] = {
            "inputs": {
                "control_net_name": unit.model_name  # updated to use selected property
            },
            "class_type": "ControlNetLoader",
            "_meta": {
                "title": f"Load ControlNet ({unit.unit_type})"
            }
        }
        # Create the ControlNetApplyAdvanced node.
        base_prompt[apply_key] = {
            "inputs": {
                "strength": unit.strength,
                "start_percent": unit.start_percent,
                "end_percent": unit.end_percent,
                "positive": [current_pos, 0],
                "negative": [current_neg, 1] if (idx > 0 or current_neg == "228" or current_neg == "51") else [current_neg, 0],
                "control_net": [loader_key, 0],
                "image": [load_key, 0],
                "vae": [vae_input, 2] if context.scene.model_architecture == "sdxl" else [vae_input, 0],
            },
            "class_type": "ControlNetApplyAdvanced",
            "_meta": {
                "title": f"Apply ControlNet ({unit.unit_type})"
            }
        }
        # Update chain inputs: the output of this apply node becomes the new input.
        current_pos = apply_key
        current_neg = apply_key
        # If the controlnet is of the union type, connect the ControlNetApplyAdvanced input into the SetUnionControlNetType node (239)
        if unit.is_union and unit.use_union_type: 
            base_prompt[apply_key]["inputs"]["control_net"] = ["239", 0]
            base_prompt["239"]["inputs"]["control_net"] = [loader_key, 0]
            if unit.unit_type == "depth":
                base_prompt["239"]["inputs"]["type"] = "depth" 
            elif unit.unit_type == "canny":
                base_prompt["239"]["inputs"]["type"] = "canny/lineart/anime_lineart/mlsd"
            elif unit.unit_type == "normal":
                base_prompt["239"]["inputs"]["type"] = "normal"

    return base_prompt, current_pos