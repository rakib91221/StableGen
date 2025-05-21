""" This file contains the operators and panels for the StableGen addon """
# disable import-error because pylint doesn't recognize the blenders internal modules
import os
import bpy  # pylint: disable=import-error
import mathutils  # pylint: disable=import-error
import math  # pylint: disable=import-error

# Stock presets
PRESETS = {
    "DEFAULT": {"description": "Default settings for general purpose generation", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)),  "discard_factor": 90.0, "weight_exponent": 3.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.15, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "MODEL IS IMPORTANT": {"description": "Same as default, but is more guided by the model", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 90.0, "weight_exponent": 3.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.15, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.75, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "CHARACTERS": {"description": "Optimized settings for character generation", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 80.0, "weight_exponent": 3.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.1, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "CHARACTERS (ALTERNATIVE MASKING)": {"description": "Optimized for character generation. Uses alternative masking parameters to be more consistent between images, but may produce more artifacts. Try if \"Characters\" fails.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 80.0, "weight_exponent": 3.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.5, "sequential_factor_smooth": 0.3499999940395355, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 10, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "QUICK DRAFT": {"description": "Optimized for speed", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 4, "cfg": 1.0, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 70.0, "weight_exponent": 3.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "grid", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.1, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 2, "blur_mask_sigma": 1.0, "grow_mask_by": 2, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Hyper-SDXL-4steps-lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "UV INPAINTING": {"description": "Recommended UV Inpainting setup. It is recommended to bake texutures manually before running the generation to fine-tune unwrapping and avoid lag when generating.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 10, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 80.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "uv_inpaint", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "3,0,1,2", "sequential_factor": 0.6000000238418579, "sequential_factor_smooth": 0.11000001430511475, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]}, # No ControlNet for UV Inpainting by default
    "ARCHITECTURE": {"description": "Prioritizes only the most straight-on camera for each point. This means details generated on flat surfaces will not get blurred by getting generated differently from two or more viewpoints. Does not use visibility masking. Each picture will get generated as new, consistency depends on IPAdapter + geometry.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.5, 0.5, 0.5)), "discard_factor": 80.0, "weight_exponent": 10.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "bake_texture": False, "bake_texture_size": 2048, "bake_unwrap_method": "none", "bake_unwrap_overlap_only": True, "generation_method": "separate", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": False, "sequential_custom_camera_order": "", "sequential_factor": 0.75, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "ipadapter_weight_type": "style", "ipadapter_strength": 0.800000011920929, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": False, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
}

# Global list of all generation parameter names to check for a preset.
GEN_PARAMETERS = [
    "control_after_generate",
    "model_architecture",
    "steps",
    "cfg",
    "sampler",
    "scheduler",
    "fallback_color",
    "discard_factor",
    "weight_exponent",
    "clip_skip",
    "auto_rescale",
    "overwrite_material",
    "bake_texture",
    "bake_texture_size",
    "bake_unwrap_method",
    "bake_unwrap_overlap_only",
    "generation_method", 
    "refine_images",
    "refine_steps",
    "refine_sampler",
    "refine_scheduler",
    "denoise",
    "refine_cfg",
    "refine_prompt",
    "refine_upscale_method",
    "sequential_smooth",
    "sequential_custom_camera_order",
    "sequential_factor",
    "sequential_factor_smooth",
    "sequential_factor_smooth_2",
    "sequential_ipadapter",
    "sequential_ipadapter_mode",
    "sequential_ipadapter_regenerate",
    "ipadapter_weight_type",
    "ipadapter_strength",
    "ipadapter_start",
    "ipadapter_end",
    "differential_diffusion",
    "differential_noise",
    "blur_mask",
    "blur_mask_radius",
    "blur_mask_sigma",
    "grow_mask_by",
    "canny_threshold_low",
    "canny_threshold_high",
]

def get_preset_items(self, context):
    items = []
    for key in PRESETS.keys():
        description = PRESETS[key].get("description", f"Preset {key}")
        items.append((key, key.title(), description))
    items.append(("CUSTOM", "Custom", "Custom configuration"))
    return items

def update_parameters(self, context):
    scene = context.scene
    # Build a dictionary of current parameter values
    current = {key: getattr(scene, key) for key in GEN_PARAMETERS if hasattr(scene, key)}
    
    # Compare current values with every stock preset's stored values
    for name, preset in PRESETS.items():
        # First check regular parameters
        if all(
            (lambda v1, v2: math.isclose(v1, v2, rel_tol=1e-7, abs_tol=0.0) if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) else v1 == v2)
            (current.get(key), preset.get(key))
            for key in GEN_PARAMETERS if key in preset
        ):
            # Now check ControlNet units if present in the preset
            if "controlnet_units" in preset:
                # Get current controlnet units as comparable data
                current_units = []
                for unit in scene.controlnet_units:
                    unit_data = {
                        "unit_type": unit.unit_type,
                        "model_name": unit.model_name,
                        "strength": unit.strength,
                        "start_percent": unit.start_percent,
                        "end_percent": unit.end_percent,
                        "is_union": unit.is_union,
                        "use_union_type": unit.use_union_type
                    }
                    
                    current_units.append(unit_data)
                
                # Compare unit count
                if len(current_units) != len(preset["controlnet_units"]):
                    continue  # Different number of units, not a match
                
                # Compare each unit's properties
                units_match = True
                for i, unit_data in enumerate(current_units):
                    preset_unit = preset["controlnet_units"][i]
                    for key, value in unit_data.items():
                        if key not in preset_unit or preset_unit[key] != value:
                            units_match = False
                            break
                    if not units_match:
                        break
                
            if not units_match:
                continue  # ControlNet units don't match, try next preset

            # Now check LoRA units if present in the preset
            if "lora_units" in preset:
                current_lora_units_data = []
                for lora_unit_obj in scene.lora_units:
                    current_lora_units_data.append({
                        "model_name": lora_unit_obj.model_name,
                        "model_strength": round(lora_unit_obj.model_strength, 7),
                        "clip_strength": round(lora_unit_obj.clip_strength, 7),
                    })

                preset_lora_units_data = preset["lora_units"]
                if len(current_lora_units_data) != len(preset_lora_units_data):
                    continue # Different number of LoRA units

                lora_units_match = True
                for i, current_lora_unit_data in enumerate(current_lora_units_data):
                    preset_lora_unit_data = preset_lora_units_data[i]
                    for key, value in current_lora_unit_data.items():
                        if key not in preset_lora_unit_data or preset_lora_unit_data[key] != value:
                            lora_units_match = False
                            break
                    if not lora_units_match:
                        break
                
                if not lora_units_match:
                    continue # LoRA units don't match, try next preset
            
            # All parameters and ControlNet and LoRA units match
            if scene.stablegen_preset != name:
                scene.stablegen_preset = name
                scene.active_preset = name
            return

    # No match found, set to custom
    scene.active_preset = "CUSTOM"
    scene.stablegen_preset = "CUSTOM"

class StableGenPanel(bpy.types.Panel):
    """     
    Creates the main UI panel for the StableGen addon.     
    """
    bl_label = "StableGen"
    bl_idname = "OBJECT_PT_stablegen"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "StableGen"
    bl_context = "objectmode"
    bl_ui_units_x = 600

    def draw_header(self, _):
        """     
        Draws the header of the panel.         
        :param _: Unused parameter.         
        :return: None     
        """
        self.layout.label(icon="WORLD_DATA")

    def draw(self, context):
        """     
        Draws the panel with reorganized Advanced Parameters.         
        :param context: Blender context.         
        :return: None     
        """
        layout = self.layout
        scene = context.scene # Get the scene for easier access

        # Detect the current width of the panel
        region = context.region
        width = region.width
        width_mode = 'narrow' if width < 420 else 'wide'
        
         # --- Action Buttons & Progress ---
        cam_tools_row = layout.row()
        cam_tools_row.operator("object.add_cameras", text="Add Cameras", icon="CAMERA_DATA")
        if width_mode == 'narrow':
            cam_tools_row = layout.row() 
        cam_tools_row.operator("object.collect_camera_prompts", text="Collect Camera Prompts", icon="FILE_TEXT")
        

        addon_prefs = context.preferences.addons[__package__].preferences
        config_error_message = None

        if not os.path.exists(addon_prefs.output_dir):
            config_error_message = "Output Path Invalid"
        elif not addon_prefs.server_address:
            config_error_message = "Server Address Missing"

        action_row = layout.row()
        action_row.scale_y = 2.0 # Scale the row vertically

        if config_error_message:
            action_row.operator("object.test_stable", text="Cannot generate: " + config_error_message, icon="X")
            action_row.enabled = False
        else:
            action_row.enabled = True

            if not bpy.app.online_access:
                action_row.operator("object.test_stable", text="Enable online access in preferences", icon="ERROR")
                action_row.enabled = False
            elif not scene.model_name or scene.model_name == "NONE_FOUND":
                action_row.operator("object.test_stable", text="Cannot generate: Model Directory Empty", icon="ERROR")
                action_row.enabled = False
            elif scene.generation_status == 'idle':
                action_row.operator("object.test_stable", text="Generate", icon="PLAY")
            elif scene.generation_status == 'running':
                action_row.operator("object.test_stable", text="Cancel Generation", icon="CANCEL")

                operator_instance = next((op for win in context.window_manager.windows for op in win.modal_operators if op.bl_idname == 'OBJECT_OT_test_stable'), None)
                if operator_instance:
                    progress_col = layout.column()
                    progress_text = f"{getattr(operator_instance, '_stage', 'Generating')} ({getattr(operator_instance, '_progress', 0):.0f}%)"
                    progress_factor = getattr(operator_instance, '_progress', 0) / 100.0
                    progress_col.progress(text=progress_text, factor=max(0.0, min(progress_factor, 1.0))) # Ensure factor is <= 1.0 (logic maintained)

                    total_images = getattr(operator_instance, '_total_images', 0)
                    if total_images > 1:
                        current_image_idx = getattr(operator_instance, '_current_image', 0)
                        current_image_decimal_progress = max(0.0, min(progress_factor, 1.0))
                        
                        # Ensure total_images is not zero to prevent division by zero
                        overall_progress_factor = (current_image_idx + current_image_decimal_progress) / total_images if total_images > 0 else 0
                        overall_progress_factor_clamped = max(0.0, min(overall_progress_factor, 1.0))

                        progress_col.progress(
                            text=f"Overall: Image {current_image_idx + 1}/{total_images}",
                            factor=overall_progress_factor_clamped # Ensure factor is <= 1.0 (logic maintained)
                        )
                        
            elif context.scene.generation_status == 'waiting':
                action_row.operator("object.test_stable", text="Waiting for Cancellation", icon="TIME")
            else:
                action_row.operator("object.test_stable", text="Fix Issues to Generate", icon="ERROR")
                action_row.enabled = False
        
        bake_row = layout.row()
        bake_row.operator("object.bake_textures", text="Bake Textures", icon="RENDER_STILL")
        bake_operator = next((op for win in context.window_manager.windows for op in win.modal_operators if op.bl_idname == 'OBJECT_OT_bake_textures'), None)
        if bake_operator:
            bake_progress_col = layout.column()
            bake_stage = getattr(bake_operator, '_stage', 'Baking')
            bake_progress = getattr(bake_operator, '_progress', 0) / 100.0
            bake_progress_col.progress(text=bake_stage, factor=bake_progress if bake_progress <=1.0 else 1.0) # Ensure factor is <= 1.0
            
            total_objects = getattr(bake_operator, '_total_objects', 0)
            if total_objects > 1:
                current_object = getattr(bake_operator, '_current_object', 0)
                # Ensure total_objects is not zero
                overall_bake_progress = ((current_object + bake_progress) / total_objects) if total_objects > 0 else 0
                bake_progress_col.progress(
                    text=f"{bake_stage}: Object {current_object + 1}/{total_objects}",
                    factor=overall_bake_progress if overall_bake_progress <=1.0 else 1.0 # Ensure factor is <= 1.0
                )

        # --- Preset Management ---
        preset_box = layout.box()
        row = preset_box.row(align=True)
        row.prop(scene, "stablegen_preset", text="Preset")
        
        # Conditional button: Apply for stock presets, Save for custom preset
        if not hasattr(scene, 'active_preset'):
            scene.active_preset = scene.stablegen_preset

        if scene.stablegen_preset == "CUSTOM":
            row.operator("stablegen.save_preset", text="Save Preset", icon="PLUS")
        else:
            if scene.active_preset != scene.stablegen_preset:
                row.operator("stablegen.apply_preset", text="Apply Preset", icon="CHECKMARK")
            
            is_stock_preset = PRESETS.get(scene.stablegen_preset, {}).get("custom", False) is False
            if not is_stock_preset and scene.stablegen_preset != "DEFAULT": 
                 row.operator("stablegen.delete_preset", text="Delete", icon="TRASH")


        # --- Main Parameters section ---
        if not hasattr(scene, 'show_generation_params'): 
            scene.show_generation_params = True
            
        main_params_box = layout.box()
        main_params_col = main_params_box.column()
        main_params_col.prop(scene, "show_generation_params", text="Main Parameters", icon="TRIA_DOWN" if scene.show_generation_params else "TRIA_RIGHT", emboss=False)
        if scene.show_generation_params:
            params_container = main_params_col.box()
            # Split for prompt
            split = params_container.split(factor=0.25)
            split.label(text="Prompt:")
            split.prop(scene, "comfyui_prompt", text="")
            
            if scene.model_architecture == 'sdxl':
                # Split for model name
                split = params_container.split(factor=0.25)
                split.label(text="Checkpoint:")
                split.prop(scene, "model_name", text="")

            # Split for model architecture
            split = params_container.split(factor=0.5)
            split.label(text="Architecture:")
            split.prop(scene, "model_architecture", text="")
            
            # Split for generation method
            split = params_container.split(factor=0.5)
            split.label(text="Generation Mode:")
            split.prop(scene, "generation_method", text="")

        # --- Helper to create collapsible sections ---
        def draw_collapsible_section(parent_layout, toggle_prop_name, title, icon="NONE"):
            if not hasattr(scene, toggle_prop_name):
                setattr(bpy.types.Scene, toggle_prop_name, bpy.props.BoolProperty(name=title, default=False))

            box = parent_layout.box()
            col = box.column()
            is_expanded = getattr(scene, toggle_prop_name, False)
            col.prop(scene, toggle_prop_name, text=title, icon="TRIA_DOWN" if is_expanded else "TRIA_RIGHT", emboss=False)
            if is_expanded:
                return col.box() # Return a new box for content if expanded
            return None

        core_settings_props = [
            "show_core_settings", "show_lora_settings", "show_scene_understanding_settings", 
            "show_output_material_settings", "show_image_guidance_settings",
            "show_masking_inpainting_settings", "show_mode_specific_settings"
        ]
        for prop_name in core_settings_props:
            if not hasattr(scene, prop_name):
                setattr(bpy.types.Scene, prop_name, bpy.props.BoolProperty(name=prop_name.replace("_", " ").title(), default=False))

        # --- ADVANCED PARAMETERS ---
        advanced_params_box = layout.box()
        advanced_params_box = advanced_params_box.column()
        advanced_params_box.prop(scene, "show_advanced_params", text="Advanced Parameters", icon="TRIA_DOWN" if scene.show_advanced_params else "TRIA_RIGHT", emboss=False)
        if context.scene.show_advanced_params:
        
            # --- Core Generation Settings ---
            
            content_box = draw_collapsible_section(advanced_params_box, "show_core_settings", "Core Generation Settings", icon="SETTINGS")
            if content_box:
                row = content_box.row()
                row.prop(scene, "seed", text="Seed")
                if width_mode == 'narrow':
                    row = content_box.row()
                row.prop(scene, "steps", text="Steps")
                if width_mode == 'narrow':
                    row = content_box.row()
                row.prop(scene, "cfg", text="CFG")

                split = content_box.split(factor=0.5)
                split.label(text="Negative Prompt:")
                split.prop(scene, "comfyui_negative_prompt", text="")
                
                split = content_box.split(factor=0.5)
                split.label(text="Control After Generate:")
                split.prop(scene, "control_after_generate", text="")

                split = content_box.split(factor=0.5)
                split.label(text="Sampler:")
                split.prop(scene, "sampler", text="")

                split = content_box.split(factor=0.5)
                split.label(text="Scheduler:")
                split.prop(scene, "scheduler", text="")
                
                row = content_box.row()
                row.prop(scene, "clip_skip", text="Clip Skip")

           # --- LoRA Settings ---
            content_box = draw_collapsible_section(advanced_params_box, "show_lora_settings", "LoRA Management", icon="MODIFIER")
            if content_box:
                row = content_box.row()
                row.alignment = 'CENTER'
                row.label(text="LoRA Units", icon="BRUSHES_ALL") # Using decimate icon for LoRA

                # Get ComfyUI directory and construct the specific path for LoRAs
                comfyui_dir = addon_prefs.comfyui_dir 
                actual_loras_path = ""
                if comfyui_dir and os.path.isdir(comfyui_dir):
                    actual_loras_path = os.path.join(comfyui_dir, "models", "loras")
                
                loras_path_is_set_and_valid = bool(actual_loras_path) and os.path.isdir(actual_loras_path)

                if scene.lora_units:
                    for i, lora_unit in enumerate(scene.lora_units):
                        is_selected_lora = (scene.lora_units_index == i)
                        unit_box = content_box.box()
                        row = unit_box.row()
                        row.prop(lora_unit, "model_name", text=f"LoRA {i+1}") # Shows selected model
                        
                        sub_row = unit_box.row(align=True)
                        sub_row.prop(lora_unit, "model_strength", text="Model Strength")
                        sub_row.prop(lora_unit, "clip_strength", text="CLIP Strength")

                        # Icon to indicate selection more clearly alongside the alert state
                        select_icon = 'CHECKBOX_HLT' if is_selected_lora else 'CHECKBOX_DEHLT'
                        
                        # Selection button (now more like a radio button)
                        op_select_lora = row.operator("wm.context_set_int", text="", icon=select_icon, emboss=True) # Keep emboss for the button itself
                        op_select_lora.data_path = "scene.lora_units_index"
                        op_select_lora.value = i

                btn_row_lora = content_box.row(align=True)

                if not scene.lora_units:
                    # Only one button if no LoRA units are present
                    button_text = "Add LoRA Unit" # Default text
                    
                    if not loras_path_is_set_and_valid:
                        button_text = "Set ComfyUI Directory in Preferences"
                    
                    # Draw the operator with the dynamically determined text
                    btn_row_lora.operator("stablegen.add_lora_unit", text=button_text, icon="ADD")
                    # The enabled state (greying out) will be handled by AddLoRAUnit.poll()
                else:
                    # Multiple buttons if LoRA units exist
                    btn_row_lora.operator("stablegen.add_lora_unit", text="Add Another LoRA", icon="ADD")
                    btn_row_lora.operator("stablegen.remove_lora_unit", text="Remove Selected", icon="REMOVE")

            # --- Image & Scene Understanding ---
            content_box = draw_collapsible_section(advanced_params_box, "show_scene_understanding_settings", "Viewpoint Blending Settings", icon="ZOOM_IN")
            if content_box:
                row = content_box.row(align=True)
                row.prop(scene, "use_camera_prompts", text="Use camera prompts", toggle=True, icon="CAMERA_DATA")
                
                row = content_box.row()
                row.prop(scene, "discard_factor", text="Discard-Over Angle")
                
                row = content_box.row()
                row.prop(scene, "weight_exponent", text="Weight Exponent")
                

            # --- Output & Material Settings ---
            content_box = draw_collapsible_section(advanced_params_box, "show_output_material_settings", "Output & Material Settings", icon="MATERIAL")
            if content_box:
                split = content_box.split(factor=0.5)
                split.label(text="Fallback Color:")
                split.prop(scene, "fallback_color", text="")
                
               
                row = content_box.row()
                row.prop(scene, "apply_bsdf", text="Apply BSDF", toggle=True, icon="SHADING_RENDERED")
                
                row = content_box.row()
                row.prop(scene, "auto_rescale", text="Auto Rescale Resolution", toggle=True, icon="ARROW_LEFTRIGHT")
                if width_mode == "narrow":
                    row = content_box.row()
                row.prop(scene, "overwrite_material", text="Overwrite Material", toggle=True, icon="FILE_REFRESH")

                row = content_box.row()
                row.prop(scene, "bake_texture", text="Bake Textures While Generating", toggle=True, icon="RENDER_STILL")
                if scene.bake_texture:
                    sub_box = content_box.box()
                    row = sub_box.row()
                    row.prop(scene, "bake_texture_size", text="Bake Texture Resolution")
                    split = sub_box.split(factor=0.5)
                    split.label(text="Bake Unwrap Method:")
                    split.prop(scene, "bake_unwrap_method", text="")
                    if scene.bake_unwrap_method != 'none':
                        row = sub_box.row()
                        row.prop(scene, "bake_unwrap_overlap_only", text="Unwrap only overlapping UVs", toggle=True, icon="UV_SYNC_SELECT")

            # --- Image Guidance (IPAdapter & ControlNet) ---
            content_box = draw_collapsible_section(advanced_params_box, "show_image_guidance_settings", "Image Guidance (IPAdapter & ControlNet)", icon="MODIFIER")
            if content_box:
                # IPAdapter Parameters
                if scene.model_architecture == 'sdxl' and not scene.generation_method == 'uv_inpaint':
                    ipadapter_main_box = content_box.box() # Group IPAdapter settings together
                    row = ipadapter_main_box.row()
                    row.prop(scene, "use_ipadapter", text="Use IPAdapter (External image)", toggle=True, icon="MOD_MULTIRES")
                    if scene.use_ipadapter:
                        sub_ip_box = ipadapter_main_box.box() 
                        row = sub_ip_box.row()
                        row.prop(scene, "ipadapter_image", text="Image")
                        row = sub_ip_box.row()
                        row.prop(scene, "ipadapter_strength", text="Strength")
                        if width_mode == 'narrow':
                            row = sub_ip_box.row()
                        row.prop(scene, "ipadapter_start", text="Start")
                        if width_mode == 'narrow':
                            row = sub_ip_box.row()
                        row.prop(scene, "ipadapter_end", text="End")
                        split = sub_ip_box.split(factor=0.5)
                        split.label(text="Weight Type:")
                        split.prop(scene, "ipadapter_weight_type", text="")
                
                content_box.separator() # Separator between IPAdapter and ControlNet if both are shown
                # ControlNet Parameters
                ctrl_box_group = content_box.box() # Group ControlNet settings together
                row = ctrl_box_group.row()
                row.alignment = 'CENTER'
                row.label(text="ControlNet Units", icon="NODETREE")
                for i, unit in enumerate(scene.controlnet_units): 
                    sub_unit_box = ctrl_box_group.box() # Each unit gets its own box
                    row = sub_unit_box.row()
                    row.label(text=f"Unit: {unit.unit_type.replace('_', ' ').title()}", icon="DOT") 
                    row.alignment = 'LEFT' 
                    
                    if width_mode == 'narrow':
                        split = sub_unit_box.split(factor=0.35, align=True) 
                    else:
                        split = sub_unit_box.split(factor=0.2, align=True) 
                    split.label(text="Model:")
                    split.prop(unit, "model_name", text="")
                    
                    row = sub_unit_box.row()
                    row.prop(unit, "strength", text="Strength")
                    if width_mode == 'narrow':
                        row = sub_unit_box.row()
                    row.prop(unit, "start_percent", text="Start")
                    if width_mode == 'narrow':
                        row = sub_unit_box.row()
                    row.prop(unit, "end_percent", text="End")
                    
                    if unit.unit_type == 'canny':
                        row = sub_unit_box.row()
                        row.prop(scene, "canny_threshold_low", text="Canny Low")
                        if width_mode == 'narrow':
                            row = sub_unit_box.row()
                        row.prop(scene, "canny_threshold_high", text="Canny High")
                    if hasattr(unit, 'is_union') and unit.is_union: 
                        row = sub_unit_box.row()
                        row.prop(unit, "use_union_type", text="Set Union Type", toggle=True, icon="MOD_BOOLEAN")
                
                btn_row = ctrl_box_group.row(align=True) 
                if width_mode == 'wide':
                    btn_row.operator("stablegen.add_controlnet_unit", text="Add Unit", icon="ADD")
                    btn_row.operator("stablegen.remove_controlnet_unit", text="Remove Unit", icon="REMOVE")
                else:
                    ctrl_box_group.operator("stablegen.add_controlnet_unit", text="Add ControlNet Unit", icon="ADD")
                    ctrl_box_group.operator("stablegen.remove_controlnet_unit", text="Remove Last ControlNet Unit", icon="REMOVE")


            # --- Inpainting Options (Conditional) ---
            if scene.generation_method == 'uv_inpaint' or scene.generation_method == 'sequential':
                content_box = draw_collapsible_section(advanced_params_box, "show_masking_inpainting_settings", "Inpainting Options", icon="MOD_MASK")
                if content_box: # content_box is the container for these settings
                    row = content_box.row()
                    row.prop(scene, "differential_diffusion", text="Use Differential Diffusion", toggle=True, icon="SMOOTHCURVE")
                    
                    if scene.differential_diffusion:
                        row = content_box.row()
                        row.prop(scene, "differential_noise", text="Add Latent Noise Mask", toggle=True, icon="MOD_NOISE")

                    if not (scene.differential_diffusion and not scene.differential_noise): 
                        row = content_box.row()
                        row.prop(scene, "mask_blocky", text="Use Blocky Mask", icon="MOD_MASK") 
                        
                        if width_mode == 'narrow':
                            row = content_box.row()
                            
                        row.prop(scene, "blur_mask", text="Blur Mask", toggle=True, icon="SURFACE_NSPHERE")

                        if scene.blur_mask:
                            row = content_box.row()
                            row.prop(scene, "blur_mask_radius", text="Blur Radius")
                            if width_mode == 'narrow':
                                row = content_box.row()
                            row.prop(scene, "blur_mask_sigma", text="Blur Sigma")

                        row = content_box.row() # Draw directly in content_box
                        row.prop(scene, "grow_mask_by", text="Grow Mask By")


            # --- Generation Mode Specifics ---
            mode_specific_outer_box = draw_collapsible_section(advanced_params_box, "show_mode_specific_settings", "Generation Mode Specifics", icon="OPTIONS")
            if mode_specific_outer_box: # This is the box where all mode-specific UIs should go
                
                # Grid Mode Parameters
                if scene.generation_method == 'grid':
                    # Draw Grid parameters directly into mode_specific_outer_box
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Grid Mode Parameters", icon="MESH_GRID")
                    
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "refine_images", text="Refine Images", toggle=True, icon="SHADERFX")
                    if scene.refine_images:
                        split = mode_specific_outer_box.split(factor=0.5)
                        split.label(text="Refine Sampler:")
                        split.prop(scene, "refine_sampler", text="")
                        
                        split = mode_specific_outer_box.split(factor=0.5)
                        split.label(text="Refine Scheduler:")
                        split.prop(scene, "refine_scheduler", text="")
                        
                        row = mode_specific_outer_box.row()
                        row.prop(scene, "denoise", text="Denoise")
                        if width_mode == 'narrow':
                            row = mode_specific_outer_box.row()
                        row.prop(scene, "refine_cfg", text="Refine CFG")
                        if width_mode == 'narrow':
                            row = mode_specific_outer_box.row()
                        row.prop(scene, "refine_steps", text="Refine Steps")

                        row = mode_specific_outer_box.row() 
                        split = mode_specific_outer_box.split(factor=0.25)
                        split.label(text="Refine Prompt:")
                        split.prop(scene, "refine_prompt", text="")
                        
                        split = mode_specific_outer_box.split(factor=0.5) 
                        split.label(text="Refine Upscale:") 
                        split.prop(scene, "refine_upscale_method", text="")

                # Separate Mode Parameters
                elif scene.generation_method == 'separate' and scene.model_architecture == 'sdxl':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Separate Mode Parameters", icon='FORCE_FORCE')
                    
                    row = mode_specific_outer_box.row() 
                    row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Separate Mode", toggle=True, icon="MODIFIER")
                    if scene.sequential_ipadapter: 
                        sub_ip_box_separate = mode_specific_outer_box.box()
                        
                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Mode:")
                        split.prop(scene, "sequential_ipadapter_mode", text="") 

                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Weight Type:")
                        split.prop(scene, "ipadapter_weight_type", text="") 
                        
                        row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_strength", text="Strength")
                        if width_mode == 'narrow':
                            row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_start", text="Start")
                        if width_mode == 'narrow':
                            row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_end", text="End")    
                        
                        if context.scene.sequential_ipadapter_mode == 'first':
                            row = sub_ip_box_separate.row()
                            row.prop(scene, "sequential_ipadapter_regenerate", text="Regenerate First Image", toggle=True, icon="FILE_REFRESH")
                            if context.scene.sequential_ipadapter_regenerate:
                                row = sub_ip_box_separate.row()
                                row.prop(scene, "sequential_ipadapter_regenerate_wo_controlnet", text="Generate reference without ControlNet", toggle=True, icon="HIDE_OFF")

                # Refine Mode Parameters
                elif scene.generation_method == 'refine':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Refine Mode Parameters", icon='SHADERFX')
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "denoise", text="Denoise") 
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "refine_preserve", text="Preserve Original Textures", toggle=True, icon="TEXTURE")
                    row = mode_specific_outer_box.row() 
                    row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Refine Mode", toggle=True, icon="MODIFIER")
                    if scene.sequential_ipadapter: 
                        sub_ip_box_separate = mode_specific_outer_box.box()
                        
                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Mode:")
                        split.prop(scene, "sequential_ipadapter_mode", text="") 

                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Weight Type:")
                        split.prop(scene, "ipadapter_weight_type", text="") 
                        
                        row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_strength", text="Strength")
                        if width_mode == 'narrow':
                            row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_start", text="Start")
                        if width_mode == 'narrow':
                            row = sub_ip_box_separate.row()
                        row.prop(scene, "ipadapter_end", text="End")    
                        
                        if context.scene.sequential_ipadapter_mode == 'first':
                            row = sub_ip_box_separate.row()
                            row.prop(scene, "sequential_ipadapter_regenerate", text="Regenerate First Image", toggle=True, icon="FILE_REFRESH")
                            if context.scene.sequential_ipadapter_regenerate:
                                row = sub_ip_box_separate.row()
                                row.prop(scene, "sequential_ipadapter_regenerate_wo_controlnet", text="Generate reference without ControlNet", toggle=True, icon="HIDE_OFF")
                
                # UV Inpainting Parameters
                elif scene.generation_method == 'uv_inpaint':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="UV Inpainting Parameters", icon="IMAGE_PLANE")
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "allow_modify_existing_textures", text="Allow Modifying Existing Textures", toggle=True, icon="TEXTURE")
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "ask_object_prompts", text="Ask for Object Specific Prompts", toggle=True, icon="QUESTION")

                # Sequential Mode Parameters
                elif scene.generation_method == 'sequential':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Sequential Mode Parameters", icon="SEQUENCE")
                    
                    split = mode_specific_outer_box.split(factor=0.5)
                    split.label(text="Custom Camera Order:")
                    split.prop(scene, "sequential_custom_camera_order", text="")
                    
                    if not (scene.differential_diffusion and not scene.differential_noise): 
                        row = mode_specific_outer_box.row()
                        row.prop(scene, "sequential_smooth", text="Use Smooth Visibility Map", toggle=True, icon="MOD_SMOOTH")
                        if width_mode == 'narrow':
                            row = mode_specific_outer_box.row()
                        row.prop(scene, "weight_exponent_mask", text="Exponent for Visibility Map", toggle=True, icon="IPO_EXPO") 
                        
                        if not scene.sequential_smooth:
                            row = mode_specific_outer_box.row()
                            row.prop(scene, "sequential_factor", text="Visibility Threshold") 
                        else:
                            row = mode_specific_outer_box.row()
                            row.prop(scene, "sequential_factor_smooth", text="Smooth Visibility Black Point")
                            if width_mode == 'narrow':
                                row = mode_specific_outer_box.row()
                            row.prop(scene, "sequential_factor_smooth_2", text="Smooth Visibility White Point")
                    
                    if scene.model_architecture == 'sdxl':
                        row = mode_specific_outer_box.row()
                        row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Sequential Mode", toggle=True, icon="MODIFIER")
                        if scene.sequential_ipadapter:
                            sub_ip_seq_box = mode_specific_outer_box.box()
                            
                            split = sub_ip_seq_box.split(factor=0.5)
                            split.label(text="Mode:")
                            split.prop(scene, "sequential_ipadapter_mode", text="")

                            split = sub_ip_seq_box.split(factor=0.5)
                            split.label(text="Weight Type:")
                            split.prop(scene, "ipadapter_weight_type", text="") 

                            row = sub_ip_seq_box.row()
                            row.prop(scene, "ipadapter_strength", text="Strength")
                            if width_mode == 'narrow':
                                row = sub_ip_seq_box.row()
                            row.prop(scene, "ipadapter_start", text="Start")
                            if width_mode == 'narrow':  
                                row = sub_ip_seq_box.row()
                            row.prop(scene, "ipadapter_end", text="End")     
                            
                            if context.scene.sequential_ipadapter_mode == 'first':
                                row = sub_ip_seq_box.row()
                                row.prop(scene, "sequential_ipadapter_regenerate", text="Regenerate First Image", toggle=True, icon="FILE_REFRESH")
                                if context.scene.sequential_ipadapter_regenerate:
                                    row = sub_ip_seq_box.row()
                                    row.prop(scene, "sequential_ipadapter_regenerate_wo_controlnet", text="Generate reference without ControlNet", toggle=True, icon="HIDE_OFF")   

        # --- Tools ---
        layout.separator()
        tools_box = layout.box()
        row = tools_box.row()
        row.alignment = 'CENTER'
        row.label(text="Tools", icon="TOOL_SETTINGS")
        
        row = tools_box.row() 
        row.operator("object.switch_material", text="Switch Material", icon="MATERIAL_DATA")
        if width_mode == 'narrow':
            row = tools_box.row()
        row.operator("object.add_hdri", text="Add HDRI Light", icon="WORLD")
        
        row = tools_box.row()
        row.operator("object.apply_all_mesh_modifiers", text="Apply All Modifiers", icon="MODIFIER_DATA") 
        if width_mode == 'narrow':
            row = tools_box.row()
        row.operator("object.curves_to_mesh", text="Convert Curves to Mesh", icon="CURVE_DATA")
        
        row = tools_box.row()
        row.operator("object.export_orbit_gif", text="Export Orbit GIF/MP4", icon="RENDER_ANIMATION")

        if width_mode == 'narrow':
            row = tools_box.row()
        row.operator("object.stablegen_reproject", text="Reproject Textures", icon="FILE_REFRESH")

        layout.separator()
          

class ApplyPreset(bpy.types.Operator):
    """Apply selected preset values to parameters"""
    bl_idname = "stablegen.apply_preset"
    bl_label = "Apply Preset"
    bl_description = "Set multiple parameters based on selected preset for easier configuration"

    def execute(self, context):
        preset = context.scene.stablegen_preset
        if preset in PRESETS:
            values = PRESETS[preset]
            
            # Apply regular parameters
            for key, value in values.items():
                if key not in ["controlnet_units", "lora_units", "description"] and hasattr(context.scene, key):
                    setattr(context.scene, key, value)
            
            # Apply ControlNet units if present in the preset
            if "controlnet_units" in values:
                # Clear existing units
                context.scene.controlnet_units.clear()
                
                # Add new units from preset
                controlnet_units = values["controlnet_units"]
                for unit_data in controlnet_units:
                    new_unit = context.scene.controlnet_units.add()
                    for key, value in unit_data.items():
                        try:
                            setattr(new_unit, key, value)
                        except TypeError:
                            self.report({'ERROR'}, f"Failed to set {key} for ControlNet unit: {value}. Model might be missing or might not be named correctly.")
                            return {'CANCELLED'}
                        
            if "lora_units" in values:
                # Clear existing LoRA units
                context.scene.lora_units.clear()
                
                # Add new LoRA units from preset
                lora_units = values["lora_units"]
                for lora_data in lora_units:
                    new_lora = context.scene.lora_units.add()
                    for key, value in lora_data.items():
                        try:
                            setattr(new_lora, key, value)
                        except TypeError:
                            self.report({'ERROR'}, f"Failed to set {key} for LoRA unit: {value}. Model might be missing or might not be named correctly.")
                            context.scene.lora_units.remove(len(context.scene.lora_units) - 1)
                            return {'CANCELLED'}
                        
            self.report({'INFO'}, f"Preset '{preset}' applied.")
        else:
            self.report({'INFO'}, "Custom preset active.")
        return {'FINISHED'}

class SavePreset(bpy.types.Operator):
    """Save the current parameter values as a custom preset"""
    bl_idname = "stablegen.save_preset"
    bl_label = "Save Custom Preset"
    
    preset_name: bpy.props.StringProperty(
        name="Preset Name",
        default="MyPreset"
    ) # type: ignore

    preset_description: bpy.props.StringProperty(
        name="Description",
        description="A short description of what this preset is good for",
        default=""
    ) # type: ignore
    
    include_controlnet: bpy.props.BoolProperty(
        name="Include ControlNet Units",
        default=True,
        description="Include ControlNet units in the preset"
    ) # type: ignore

    include_loras: bpy.props.BoolProperty(
        name="Include LoRA Units",
        default=True
    ) # type: ignore

    def execute(self, context):
        scene = context.scene
        key = self.preset_name.upper()
        
        # Save all parameters defined in GEN_PARAMETERS
        PRESETS[key] = {param: getattr(scene, param) for param in GEN_PARAMETERS if hasattr(scene, param)}
        
        # Add description
        PRESETS[key]["description"] = self.preset_description

        # Add custom flag
        PRESETS[key]["custom"] = True

        if self.include_controlnet:
            # Save ControlNet units
            controlnet_units = []
            for unit in scene.controlnet_units:
                unit_data = {
                    "unit_type": unit.unit_type,
                    "model_name": unit.model_name,
                    "strength": unit.strength,
                    "start_percent": unit.start_percent,
                    "end_percent": unit.end_percent,
                    "is_union": unit.is_union,
                    "use_union_type": unit.use_union_type
                }
                controlnet_units.append(unit_data)
            
            # Add controlnet units to the preset
            PRESETS[key]["controlnet_units"] = controlnet_units

        if self.include_loras: # Save LoRA units
            lora_units_data = []
            for lora_unit in scene.lora_units:
                lora_units_data.append({
                    "model_name": lora_unit.model_name,
                    "model_strength": lora_unit.model_strength,
                    "clip_strength": lora_unit.clip_strength,
                })

            # Add LoRA units to the preset
            PRESETS[key]["lora_units"] = lora_units_data
        
        scene.stablegen_preset = key
        scene.active_preset = key
        self.report({'INFO'}, f"Preset '{self.preset_name}' saved.")
        
        # Print in the console for debugging
        print(f'"{key}": {{', end="")
        print(f'"description": "{self.preset_description}", ', end="")
        for param in GEN_PARAMETERS:
            if hasattr(scene, param):
                value = getattr(scene, param)
                if isinstance(value, str):
                    print(f'"{param}": "{value}", ', end="")
                else:
                    print(f'"{param}": {value}, ', end="")
        
        # Print controlnet units in a compact format if included
        if self.include_controlnet:
            print(f'"controlnet_units": {controlnet_units},', end="")
        print("},")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name")
        layout.prop(self, "preset_description")
        layout.prop(self, "include_controlnet")
        layout.prop(self, "include_loras")

class DeletePreset(bpy.types.Operator):
    """Delete a custom preset"""
    bl_idname = "stablegen.delete_preset"
    bl_label = "Delete Preset"

    def execute(self, context):
        preset = context.scene.stablegen_preset
        if preset in PRESETS:
            del PRESETS[preset]
            context.scene.stablegen_preset = "CUSTOM"
            self.report({'INFO'}, f"Preset '{preset}' deleted.")
            update_parameters(self, context)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Preset not found.")
            return {'CANCELLED'}
