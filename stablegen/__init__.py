""" This script registers the addon. """
import bpy # pylint: disable=import-error
from .stablegen import StableGenPanel, ApplyPreset, SavePreset, DeletePreset, get_preset_items, update_parameters
from .render_tools import BakeTextures, AddCameras, SwitchMaterial, ExportOrbitGIF, CollectCameraPrompts, CameraPromptItem 
from .utils import AddHDRI, ApplyModifiers, CurvesToMesh
from .generator import ComfyUIGenerate
import os
from bpy.app.handlers import persistent

bl_info = {
    "name": "StableGen",
    "category": "Object",
    "author": "Ondrej Sakala",
    "version": (0, 0, 4),
    'blender': (4, 2, 0)
}

def update_combined(self, context): # Combined with load_handler to load controlnet unit on first setup
    update_parameters(self, context)
    load_handler(None)
    return None

class StableGenAddonPreferences(bpy.types.AddonPreferences):
    """     
    Preferences for the StableGen addon.     
    """
    bl_idname = __package__

    model_dir: bpy.props.StringProperty(
        name="Model Directory",
        description="Directory containing SD models",
        default="",
        subtype='DIR_PATH',
        update=update_combined
    ) # type: ignore

    lora_dir: bpy.props.StringProperty(
        name="LoRA Directory",
        description="Directory containing LoRA models",
        default="",
        subtype='DIR_PATH',
        update=update_combined
    ) # type: ignore

    server_address: bpy.props.StringProperty(
        name="Server Address",
        description="Address of the ComfyUI server",
        default="127.0.0.1:8188",
        update=update_parameters
    ) # type: ignore

    output_dir: bpy.props.StringProperty(
        name="Output Directory",
        description="Directory to save generated outputs",
        default="",
        subtype='DIR_PATH',
        update=update_parameters
    ) # type: ignore

    controlnet_mapping: bpy.props.StringProperty(
        name="ControlNet Mapping",
        description="JSON mapping of controlnet type to model files. Example: {\"depth\": [\"controlnet_depth_sdxl.safetensors\", \"control_v11f1p_sd15_depth.pth\"], \"canny\": [\"sdxl_canny.safetensors\"]}\
            \nOnly following types are currently supported: depth, canny",
        default='{"depth": ["controlnet_depth_sdxl.safetensors", "sdxl_depth_alt.safetensors","sdxl_promax.safetensors", "controlnet_flux1_union_pro.safetensors"], "canny": ["sdxl_promax.safetensors", "controlnet_flux1_union_pro.safetensors"], "normal": ["sdxl_promax.safetensors"]}',
        update=update_parameters
    )  # type: ignore
    
    save_blend_file: bpy.props.BoolProperty(
        name="Save Blend File",
        description="Save the current Blender file with packed textures",
        default=False,
        update=update_parameters
    ) # type: ignore

    def draw(self, context):
        """     
        Draws the preferences panel.         
        :param context: Blender context.         
        :return: None     
        """
        layout = self.layout
        layout.prop(self, "model_dir")
        layout.prop(self, "server_address")
        layout.prop(self, "output_dir")
        layout.separator()
        layout.prop(self, "lora_dir")
        layout.prop(self, "controlnet_mapping")
        layout.prop(self, "save_blend_file")

def update_model_list(self, context):
    """     
    Updates the list of models in the model folder.         
    :param self: Reference to the current instance.         
    :param context: Blender context.         
    :return: List of models.     
    """
    addon_prefs = context.preferences.addons[__package__].preferences
    model_dir = addon_prefs.model_dir
    if os.path.isdir(model_dir):
        models = [f for f in os.listdir(model_dir) if f.endswith('.safetensors')]
        return [(model, model, "") for model in models]
    return []

def update_union(self, context):
    if "union" in self.model_name.lower() or "promax" in self.model_name.lower():
        self.is_union = True
    else:
        self.is_union = False

def update_controlnet(self, context):
    update_parameters(self, context)
    update_union(self, context)
    return None

class ControlNetUnit(bpy.types.PropertyGroup):
    unit_type: bpy.props.StringProperty(
        name="Type",
        description="ControlNet type (e.g. 'depth', 'canny')",
        default="",
        update=update_parameters
    )  # type: ignore
    model_name: bpy.props.EnumProperty(
        name="Model",
        description="Select the ControlNet model",
        items=lambda self, context: get_controlnet_models(context, self.unit_type),
        update=update_controlnet
    ) # type: ignore
    strength: bpy.props.FloatProperty(
        name="Strength",
        description="Strength of the ControlNet effect",
        default=0.5,
        min=0.0,
        max=3.0,
        update=update_parameters
    )  # type: ignore
    start_percent: bpy.props.FloatProperty(
        name="Start",
        description="Start percentage (/100)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )  # type: ignore
    end_percent: bpy.props.FloatProperty(
        name="End",
        description="End percentage (/100)",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )  # type: ignore
    is_union: bpy.props.BoolProperty(
        name="Is Union Type",
        description="Is this a union ControlNet?",
        default=False,
        update=update_parameters
    ) # type: ignore
    use_union_type: bpy.props.BoolProperty(
        name="Use Union Type",
        description="Use union type for ControlNet",
        default=True,
        update=update_parameters
    ) # type: ignore

class LoRAUnit(bpy.types.PropertyGroup):
    model_name: bpy.props.EnumProperty(
        name="LoRA Model",
        description="Select the LoRA model file",
        items=lambda self, context: get_lora_models(self, context),
        update=update_parameters
    ) # type: ignore
    model_strength: bpy.props.FloatProperty(
        name="Model Strength",
        description="Strength of the LoRA's effect on the model's weights",
        default=1.0,
        min=0.0,
        max=100.0, # Adjusted max based on typical LoRA usage
        update=update_parameters
    )  # type: ignore
    clip_strength: bpy.props.FloatProperty(
        name="CLIP Strength",
        description="Strength of the LoRA's effect on the CLIP/text conditioning",
        default=1.0,
        min=0.0,
        max=100.0, # Adjusted max
        update=update_parameters
    )  # type: ignore

def get_controlnet_models(context, unit_type):
    """
    Get available ControlNet models for a given type.
    """
    addon_prefs = context.preferences.addons[__package__].preferences
    try:
        import json
        mapping = json.loads(addon_prefs.controlnet_mapping)
        if unit_type in mapping:
            return [(model, model, "") for model in mapping[unit_type]]
    except json.JSONDecodeError:
        return []
    return []

def get_lora_models(self, context):
    """
    Populates the EnumProperty items with LoRA models from the lora_dir.
    """
    addon_prefs = context.preferences.addons[__package__].preferences
    lora_dir = addon_prefs.lora_dir
    loras = []
    if os.path.isdir(lora_dir):
        for f in os.listdir(lora_dir):
            if f.endswith(('.safetensors')): # Common LoRA extensions
                loras.append((f, f, ""))
    if not loras:
        loras.append(("NONE", "No LoRAs Found in Directory", "Please set the LoRA directory in preferences"))
    return loras

class AddControlNetUnit(bpy.types.Operator):
    bl_idname = "stablegen.add_controlnet_unit"
    bl_label = "Add ControlNet Unit"
    bl_description = "Add a ControlNet Unit. Only one unit per type is allowed."

    unit_type: bpy.props.EnumProperty(
        name="Type",
        items=[('depth', 'Depth', ''), ('canny', 'Canny', ''), ('normal', 'Normal', '')],
        default='depth',
        update=update_parameters
    ) # type: ignore

    model_name: bpy.props.EnumProperty(
        name="Model",
        description="Select the ControlNet model",
        items=lambda self, context: get_controlnet_models(context, self.unit_type),
        update=update_parameters
    ) # type: ignore

    def invoke(self, context, event):
        # Always prompt for unit type and model selection
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "unit_type")
        models = get_controlnet_models(context, self.unit_type)
        if len(models) > 1:
            layout.prop(self, "model_name")

    def execute(self, context):
        units = context.scene.controlnet_units
        # Only add if not already present
        for unit in units:
            if unit.unit_type == self.unit_type:
                self.report({'WARNING'}, f"Unit '{self.unit_type}' already exists.")
                return {'CANCELLED'}
        new_unit = units.add()
        new_unit.unit_type = self.unit_type
        new_unit.model_name = self.model_name
        new_unit.strength = 0.5
        new_unit.start_percent = 0.0
        new_unit.end_percent = 1.0
        if "union" in new_unit.model_name.lower() or "promax" in new_unit.model_name.lower():
            new_unit.is_union = True
        context.scene.controlnet_units_index = len(units) - 1
        # Force redraw of the UI
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}
    
class RemoveControlNetUnit(bpy.types.Operator):
    bl_idname = "stablegen.remove_controlnet_unit"
    bl_label = "Remove ControlNet Unit"
    bl_description = "Remove the selected ControlNet Unit"

    unit_type: bpy.props.EnumProperty(
        name="Type",
        items=[('depth', 'Depth', ''), ('canny', 'Canny', ''), ('normal', 'Normal', '')],
        default='depth',
        update=update_parameters
    )  # type: ignore

    def invoke(self, context, event):
        units = context.scene.controlnet_units
        if len(units) == 1:
            self.unit_type = units[0].unit_type
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "unit_type")

    def execute(self, context):
        units = context.scene.controlnet_units
        for index, unit in enumerate(units):
            if unit.unit_type == self.unit_type:
                units.remove(index)
                context.scene.controlnet_units_index = min(max(0, index - 1), len(units) - 1)
                # Force redraw of the UI
                update_parameters(self, context)
                for area in context.screen.areas:
                    area.tag_redraw()
                return {'FINISHED'}
        self.report({'WARNING'}, f"No unit of type '{self.unit_type}' found.")
        return {'CANCELLED'}
    
class AddLoRAUnit(bpy.types.Operator):
    bl_idname = "stablegen.add_lora_unit"
    bl_label = "Add LoRA Unit"
    bl_description = "Add a LoRA to the chain. Disabled if no LoRAs are available or all available LoRAs have been added."

    @classmethod
    def poll(cls, context):
        scene = context.scene
        addon_prefs = context.preferences.addons[__package__].preferences
        lora_dir = addon_prefs.lora_dir

        if not lora_dir or not os.path.isdir(lora_dir):
            cls.poll_message_set("LoRA directory not set or invalid in preferences.")
            return False

        # Get actual LoRA files, not the enum items which might include placeholders
        available_lora_files = []
        try:
            for f in os.listdir(lora_dir):
                if f.endswith(('.safetensors')):
                    available_lora_files.append(f)
        except FileNotFoundError: # Should be caught by os.path.isdir, but good practice
            cls.poll_message_set("LoRA directory not found.")
            return False
        except PermissionError:
            cls.poll_message_set("Permission denied for LoRA directory.")
            return False


        num_available_loras = len(available_lora_files)
        num_current_lora_units = len(scene.lora_units)

        if num_available_loras == 0:
            cls.poll_message_set("No LoRA model files found in the specified directory.")
            return False

        if num_current_lora_units >= num_available_loras:
            cls.poll_message_set("All available LoRA models have been added.")
            return False
            
        return True

    def execute(self, context):
        loras = context.scene.lora_units
        new_lora = loras.add()
        
        # Attempt to set a default model if available from the actual files
        lora_dir = context.preferences.addons[__package__].preferences.lora_dir
        available_lora_files = []
        if os.path.isdir(lora_dir):
            for f in os.listdir(lora_dir):
                if f.endswith(('.safetensors')):
                    available_lora_files.append(f)
        
        if available_lora_files:
            # Try to assign a LoRA that isn't already used, if possible,
            # or just the first one if all are new.
            current_lora_model_names = {unit.model_name for unit in loras if unit.model_name != "NONE"}
            assigned = False
            for lora_file_name in available_lora_files:
                if lora_file_name not in current_lora_model_names:
                    try:
                        new_lora.model_name = lora_file_name
                        assigned = True
                        break
                    except TypeError: # Happens if the model_name enum is not yet updated with this specific file
                        pass 
            if not assigned: # Fallback to first available if all unique ones are taken or error
                 try:
                    new_lora.model_name = available_lora_files[0]
                 except TypeError: # Enum not ready
                    pass # It will pick the default "NONE" or whatever EnumProperty does
        
        new_lora.model_strength = 1.0
        new_lora.clip_strength = 1.0
        context.scene.lora_units_index = len(loras) - 1 # Select the new unit
        update_parameters(self, context) # Assuming this function exists and updates presets/UI state
        for area in context.screen.areas: # Force UI refresh
            area.tag_redraw()
        return {'FINISHED'}
    
class RemoveLoRAUnit(bpy.types.Operator):
    bl_idname = "stablegen.remove_lora_unit"
    bl_label = "Remove Selected LoRA Unit"
    bl_description = "Remove the selected LoRA from the chain"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        # Operator can run if there are LoRA units AND the current index is valid
        return len(scene.lora_units) > 0 and \
               0 <= scene.lora_units_index < len(scene.lora_units)

    def execute(self, context):
        loras = context.scene.lora_units
        index = context.scene.lora_units_index
        if 0 <= index < len(loras):
            loras.remove(index)
            context.scene.lora_units_index = min(max(0, index - 1), len(loras) - 1)
            update_parameters(self, context)
            for area in context.screen.areas:
                area.tag_redraw()
            return {'FINISHED'}
        self.report({'WARNING'}, "No LoRA unit selected or list is empty.")
        return {'CANCELLED'}

# load handler to set default ControlNet unit
@persistent
def load_handler(dummy):
    if bpy.context.scene:
        scene = bpy.context.scene
        if hasattr(scene, "controlnet_units") and not scene.controlnet_units:
            default_unit = scene.controlnet_units.add()
            default_unit.unit_type = 'depth'
        # If possible, also set 'sdxl_lightning_8step_lora.safetensors'
        if hasattr(scene, "lora_units") and not scene.lora_units:
            # Need to check if the file exists in the directory
            addon_prefs = bpy.context.preferences.addons[__package__].preferences
            lora_dir = addon_prefs.lora_dir
            if os.path.isdir(lora_dir):
                for f in os.listdir(lora_dir):
                    if f == 'sdxl_lightning_8step_lora.safetensors':
                        new_lora = scene.lora_units.add()
                        new_lora.model_name = f
                        new_lora.model_strength = 1.0
                        new_lora.clip_strength = 1.0
                        break

def register():
    """     
    Registers the addon.         
    :return: None     
    """
    bpy.utils.register_class(StableGenAddonPreferences)
    bpy.utils.register_class(StableGenPanel)
    bpy.utils.register_class(ComfyUIGenerate)
    bpy.utils.register_class(BakeTextures)
    bpy.utils.register_class(AddCameras)
    bpy.utils.register_class(SwitchMaterial)
    bpy.utils.register_class(AddHDRI)
    bpy.utils.register_class(ApplyModifiers)
    bpy.utils.register_class(CurvesToMesh)
    bpy.utils.register_class(ControlNetUnit)
    bpy.utils.register_class(LoRAUnit)
    bpy.utils.register_class(CameraPromptItem)
    bpy.utils.register_class(CollectCameraPrompts)
    bpy.types.Scene.comfyui_prompt = bpy.props.StringProperty(
        name="ComfyUI Prompt",
        description="Enter the text prompt for ComfyUI generation",
        default="gold cube",
        update=update_parameters
    )
    bpy.types.Scene.comfyui_negative_prompt = bpy.props.StringProperty(
        name="ComfyUI Negative Prompt",
        description="Enter the negative text prompt for ComfyUI generation",
        default="",
        update=update_parameters
    )
    bpy.types.Scene.model_name = bpy.props.EnumProperty(
        name="Model Name",
        description="Select the SD model",
        items=update_model_list,
        update=update_parameters
    )
    bpy.types.Scene.seed = bpy.props.IntProperty(
        name="Seed",
        description="Seed for image generation",
        default=42,
        min=0,
        max=1000000,
        update=update_parameters
    )
    bpy.types.Scene.control_after_generate = bpy.props.EnumProperty(
        name="Control After Generate",
        description="Control behavior after generation",
        items=[
            ('fixed', 'Fixed', ''),
            ('increment', 'Increment', ''),
            ('decrement', 'Decrement', ''),
            ('randomize', 'Randomize', '')
        ],
        default='fixed',
        update=update_parameters
    )
    bpy.types.Scene.steps = bpy.props.IntProperty(
        name="Steps",
        description="Number of steps for generation",
        default=8,
        min=0,
        max=200,
        update=update_parameters
    )
    bpy.types.Scene.cfg = bpy.props.FloatProperty(
        name="CFG",
        description="Classifier-Free Guidance scale",
        default=1.5,
        min=0.0,
        max=100.0,
        update=update_parameters
    )
    bpy.types.Scene.sampler = bpy.props.EnumProperty(
        name="Sampler",
        description="Sampler for generation",
        items=[
            ('euler', 'Euler', ''),
            ('euler_ancestral', 'Euler A', ''),
            ('dpmpp_sde', 'DPM++ SDE', ''),
            ('dpmpp_2m', 'DPM++ 2M', ''),
            ('dpmpp_2s_ancestral', 'DPM++ 2S Ancestral', ''),
        ],
        default='dpmpp_2s_ancestral',
        update=update_parameters
    )
    bpy.types.Scene.scheduler = bpy.props.EnumProperty(
        name="Scheduler",
        description="Scheduler for generation",
        items=[
            ('sgm_uniform', 'SGM Uniform', ''),
            ('karras', 'Karras', ''),
            ('beta', 'Beta', ''),
        ],
        default='sgm_uniform',
        update=update_parameters
    )
    bpy.types.Scene.show_advanced_params = bpy.props.BoolProperty(
        name="Show Advanced Parameters",
        description="Show or hide advanced parameters",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.show_generation_params = bpy.props.BoolProperty(
        name="Show Generation Parameters",
        description="Most important parameters",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.auto_rescale = bpy.props.BoolProperty(
        name="Auto Rescale Resolution",
        description="Automatically rescale resolution to appropriate size for the selected model",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.use_ipadapter = bpy.props.BoolProperty(
        name="Use IPAdapter",
        description="""Use IPAdapter for image generation. Requires an external reference image. Can improve consistency, can be useful for generating images with similar styles.\n\n - Has priority over mode specific IPAdapter.""",
        default=False,
        update=update_parameters
    )
    #IPAdapter image
    bpy.types.Scene.ipadapter_image = bpy.props.StringProperty(
        name="Reference Image",
        description="Path to the reference image",
        default="",
        subtype='FILE_PATH',
        update=update_parameters
    )
    bpy.types.Scene.ipadapter_strength = bpy.props.FloatProperty(
        name="IPAdapter Strength",
        description="Strength for IPAdapter",
        default=1.0,
        min=-1.0,
        max=3.0,
        update=update_parameters
    )
    bpy.types.Scene.ipadapter_start = bpy.props.FloatProperty(
        name="IPAdapter Start",
        description="Start percentage for IPAdapter (/100)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.ipadapter_end = bpy.props.FloatProperty(
        name="IPAdapter End",
        description="End percentage for IPAdapter (/100)",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.ipadapter_weight_type = bpy.props.EnumProperty(
        name="IPAdapter Weight Type",
        description="Weight type for IPAdapter",
        items=[
            ('standard', 'Standard', ''),
            ('prompt', 'Prompt is more important', ''),
            ('style', 'Style transfer', ''),
        ],
        default='style',
        update=update_parameters
    )
    bpy.types.Scene.sequential_ipadapter = bpy.props.BoolProperty(
        name="Use IPAdapter",
        description="""Uses IPAdapter to improve consistency between images.\n\n - Applicable for Separate, Sequential and Refine modes.\n - Uses either the first generated image or the most recent one as a reference for the rest of the images.\n - If 'Regenerate IPAdapter' is enabled, the first viewpoint will be regenerated with IPAdapter to match the rest of the images.\n - If 'Use IPAdapter (External Image)' is enabled, this setting is effectively overriden.""",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.sequential_ipadapter_mode = bpy.props.EnumProperty(
        name="IPAdapter Mode",
        description="Mode for IPAdapter in sequential generation",
        items=[
            ('first', 'Use first generated image', ''),
            ('recent', 'Use most recent generated image', ''),
        ],
        default='first',
        update=update_parameters
    )
    bpy.types.Scene.sequential_ipadapter_regenerate = bpy.props.BoolProperty(
        name="Regenerate IPAdapter",
        description="IPAdapter generations may differ from the original image. This option regenerates the first viewpoint with IPAdapter to match the rest of the images.",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.sequential_ipadapter_regenerate_wo_controlnet = bpy.props.BoolProperty(
        name="Generate IPAdapter reference without ControlNet",
        description="Generate the first viewpoint with IPAdapter without ControlNet. This is useful for generating a reference image that is not affected by ControlNet. Can possibly generate higher quality reference.",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.generation_method = bpy.props.EnumProperty(
        name="Generation Mode",
        description="Choose the mode for generating images",
        items=[
            ('separate', 'Generate Separately', 'Generates images one by one for each viewpoint. Each image is generated independently using only its own control signals (e.g., depth map) without context from other views. All images are applied at the end.'),
            ('sequential', 'Generate Sequentially', 'Generates images viewpoint by viewpoint. After the first view, each subsequent view is generated using inpainting, guided by a visibility mask and an RGB render of the texture projected from previous viewpoints to maintain consistency.'),
            ('grid', 'Generate Using Grid', 'Combines control signals from all viewpoints into a single grid, generates a single image, then splits it back into individual viewpoint textures. Faster but lower resolution per view. Includes an optional second pass to refine each split image individually at full resolution for improved quality.'),
            ('refine', 'Refine/Restyle Texture (Img2Img)', 'Uses the current rendered texture appearance as input for an img2img generation pass.\n\nBehavior depends on "Preserve Original Textures" (Advanced Parameters -> Generation Mode Specifics):\n\nON: Layers new details over the existing texture (preserves uncovered areas).\n - Works only with StableGen generated textures.\n\nOFF: Replaces the previous material with the new result (good for restyling).\n - Works on any existing material setup.'),
            ('uv_inpaint', 'UV Inpaint Missing Areas', 'Identifies untextured areas on a standard UV map using a visibility calculation. Performs baking if not baked already. Performs diffusion inpainting directly on the UV texture map to fill only these missing regions, using the surrounding texture as context.'),
        ],
        default='sequential',
        update=update_parameters
    )
    bpy.types.Scene.refine_images = bpy.props.BoolProperty(
        name="Refine Images",
        description="Refine images after generation",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.refine_steps = bpy.props.IntProperty(
        name="Refine Steps",
        description="Number of steps for refining",
        default=8,
        min=0,
        max=200,
        update=update_parameters
    )
    bpy.types.Scene.refine_sampler = bpy.props.EnumProperty(
        name="Refine Sampler",
        description="Sampler for refining",
        items=[
            ('euler', 'Euler', ''),
            ('euler_ancestral', 'Euler A', ''),
            ('dpmpp_sde', 'DPM++ SDE', ''),
            ('dpmpp_2m', 'DPM++ 2M', ''),
            ('dpmpp_2s_ancestral', 'DPM++ 2S Ancestral', ''),
        ],
        default='dpmpp_2s_ancestral',
        update=update_parameters
    )
    bpy.types.Scene.refine_scheduler = bpy.props.EnumProperty(
        name="Refine Scheduler",
        description="Scheduler for refining",
        items=[
            ('sgm_uniform', 'SGM Uniform', ''),
            ('karras', 'Karras', ''),
            ('beta', 'Beta', ''),
        ],
        default='sgm_uniform',
        update=update_parameters
    )
    bpy.types.Scene.denoise = bpy.props.FloatProperty(
        name="Denoise",
        description="Denoise level for refining",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.refine_cfg = bpy.props.FloatProperty(
        name="Refine CFG",
        description="Classifier-Free Guidance scale for refining",
        default=1.5,
        min=0.0,
        max=100.0,
        update=update_parameters
    )
    bpy.types.Scene.refine_prompt = bpy.props.StringProperty(
        name="Refine Prompt",
        description="Prompt for refining (leave empty to use same prompt as generation)",
        default="",
        update=update_parameters
    )
    bpy.types.Scene.refine_upscale_method = bpy.props.EnumProperty(
        name="Refine Upscale Method",
        description="Upscale method for refining",
        items=[
            ('nearest-exact', 'Nearest Exact', ''),
            ('bilinear', 'Bilinear', ''),
            ('bicubic', 'Bicubic', ''),
            ('lanczos', 'Lanczos', ''),
        ],
        default='lanczos',
        update=update_parameters
    )
    bpy.types.Scene.generation_status = bpy.props.EnumProperty(
        name="Generation Status",
        description="Status of the generation process",
        items=[
            ('idle', 'Idle', ''),
            ('running', 'Running', ''),
            ('waiting', 'Waiting for cancel', ''),
            ('error', 'Error', '')
        ],
        default='idle',
        update=update_parameters
    )
    bpy.types.Scene.generation_progress = bpy.props.FloatProperty(
        name="Generation Progress",
        description="Current progress of image generation",
        default=0.0,
        min=0.0,
        max=100.0,
        update=update_parameters
    )
    bpy.types.Scene.overwrite_material = bpy.props.BoolProperty(
        name="Overwrite Material",
        description="Overwrite existing material",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.refine_preserve = bpy.props.BoolProperty(
        name="Preserve Original Texture",
        description="Preserve the original textures when refining in places where the new texture isn't available",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.discard_factor = bpy.props.FloatProperty(
        name="Discard Factor",
        description="If the texture is facing the camera at an angle greater than this value, it will be discarded. This is useful for preventing artifacts from the very edge of the generated texture appearing when keeping high discard factor (use ~65 for best results when generating textures around an object)",
        default=90.0,
        min=0.0,
        max=180.0,
        update=update_parameters
    )
    bpy.types.Scene.weight_exponent = bpy.props.FloatProperty(
        name="Weight Exponent",
        description="Controls the falloff curve for viewpoint weighting based on the angle to the surface normal (θ). "
                     "Weight = |cos(θ)|^Exponent. Higher values prioritize straight-on views more strongly, creating sharper transitions. "
                     "1.0 = standard |cos(θ)| weighting..",
        default=3.0,
        min=0.1,
        max=1000.0,
        update=update_parameters
    )
    bpy.types.Scene.bake_texture = bpy.props.BoolProperty(
        name="Bake Texture",
        description="Bake the texture to the model. This is forced if there are more than 8 cameras. Use this to prevent UV map slot limit errors.",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.bake_texture_size = bpy.props.IntProperty(
        name="Bake Texture Size",
        description="Size of the baked texture",
        default=2048,
        min=256,
        max=8192,
        update=update_parameters
    )
    bpy.types.Scene.bake_unwrap_method = bpy.props.EnumProperty(
        name="Bake Unwrap Method",
        description="Method for unwrapping the model for baking",
        items=[
            ('none', 'None', ''),
            ('smart', 'Smart UV Project', ''),
            ('basic', 'Unwrap', ''),
            ('lightmap', 'Lightmap Pack', ''),
            ('pack', 'Pack Islands', '')
        ],
        default='none',
        update=update_parameters
    )
    bpy.types.Scene.bake_unwrap_overlap_only = bpy.props.BoolProperty(
        name="Ony Unwrap Overlapping UVs",
        description="Only unwrap UVs that overlap",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.allow_modify_existing_textures = bpy.props.BoolProperty(
        name="Allow modifying existing textures",
        description="Disconnect compare node in export_visibility so that smooth output is not pure 1 areas",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.ask_object_prompts = bpy.props.BoolProperty(
        name="Ask for object prompts",
        description="Use object-specific prompts; if disabled, the normal prompt is used for all objects",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.fallback_color = bpy.props.FloatVectorProperty(
        name="Fallback Color",
        description="Color to use as fallback in texture generation",
        subtype='COLOR',
        default=(0.5, 0.5, 0.5),  # Changed from 4 values to 3 values
        min=0.0, max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.sequential_smooth = bpy.props.BoolProperty(
        name="Sequential Smooth",
        description="""Use smooth visibility map for sequential generation mode. Disabling this uses a binary visibility map and may need more mask blurring to reduce artifacts.
        
 - Visibility map is a mask that indicates which pixels have textures already projected from previous viewpoints.
 - Both methods are using weights which are calculated based on the angle between the surface normal and the camera view direction.
 - 'Smooth' uses these calculated weights directly (0.0-1.0 range, giving gradual transitions). The transition point can be further tuned by the 'Smooth Factor' parameters.
 - Disabling 'Smooth' thresholds these weights to create a hard-edged binary mask (0.0 or 1.0).""",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.weight_exponent_mask = bpy.props.BoolProperty(
        name="Weight Exponent Mask",
        description="Use weight exponent for visibility map generation. Uses 1.0 if disabled.",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.canny_threshold_low = bpy.props.IntProperty(
        name="Canny Threshold Low",
        description="Low threshold for Canny edge detection",
        default=0,
        min=0,
        max=255,
        update=update_parameters
    )
    bpy.types.Scene.canny_threshold_high = bpy.props.IntProperty(
        name="Canny Threshold High",
        description="High threshold for Canny edge detection",
        default=80,
        min=0,
        max=255,
        update=update_parameters
    )
    bpy.types.Scene.sequential_factor_smooth = bpy.props.FloatProperty(
        name="Smooth Visibility Black Point",
        description="Controls the black point (start) of the Color Ramp used for the smooth visibility mask in sequential mode. Defines the weight threshold below which areas are considered fully invisible/untextured from previous views. Higher values create a sharper transition start.",
        default=0.15,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.sequential_factor_smooth_2 = bpy.props.FloatProperty(
        name="Smooth Visibility White Point",
        description="Controls the white point (end) of the Color Ramp used for the smooth visibility mask in sequential mode. Defines the weight threshold above which areas are considered fully visible/textured from previous views. Lower values create a sharper transition end.",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.sequential_factor = bpy.props.FloatProperty(
        name="Binary Visibility Threshold",
        description="Threshold value used when 'Sequential Smooth' is OFF. Calculated visibility weights below this value are treated as 0 (invisible), and those above as 1 (visible), creating a hard-edged binary mask.",
        default=0.7,
        min=0.0,
        max=1.0,
        update=update_parameters
    )
    bpy.types.Scene.differential_noise = bpy.props.BoolProperty(
        name="Differential Noise",
        description="Adds latent noise mask to the image before inpainting. This must be used with low factor smooth mask or with a high blur mask radius. Disabling this effectively discrads the mask and only uses the inapaint conditioning.",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.grow_mask_by = bpy.props.IntProperty(
        name="Grow Mask By",
        description="Grow mask by this amount (ComfyUI)",
        default=3,
        min=0,
        update=update_parameters
    )
    bpy.types.Scene.mask_blocky = bpy.props.BoolProperty(
        name="Blocky Visibility Map",
        description="Uses a blocky visibility map. This will downscale the visibility map according to the 8x8 grid which Stable Diffusion uses in latent space. Highly experimental.",
        default=False,
        update=update_parameters
    )
    bpy.types.Scene.differential_diffusion = bpy.props.BoolProperty(
        name="Differential Diffusion",
        description="Replace standard inpainting with a differential diffusion based workflow\n\n - Generally works better and reduces artifacts.\n - Using a Smooth Visibilty Map is recommended for Sequential Mode.",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.blur_mask = bpy.props.BoolProperty(
        name="Blur Mask",
        description="Blur mask before inpainting (ComfyUI)",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.blur_mask_radius = bpy.props.IntProperty(
        name="Blur Mask Radius",
        description="Radius for mask blurring (ComfyUI)",
        default=1,
        min=1,
        max=31,
        update=update_parameters
    )
    bpy.types.Scene.blur_mask_sigma = bpy.props.FloatProperty(
        name="Blur Mask Sigma",
        description="Sigma for mask blurring (ComfyUI)",
        default=1.0,
        min=0.1,
        update=update_parameters
    )
    bpy.types.Scene.sequential_custom_camera_order = bpy.props.StringProperty(
        name="Custom Camera Order",
        description="""Custom camera order for Sequential Mode. Format: 'index1,index2,index3,...'
        
 - This will permanently change the order of the cameras in the scene.""",
        default="",
        update=update_parameters
    )
    bpy.types.Scene.clip_skip = bpy.props.IntProperty(
        name="CLIP Skip",
        description="CLIP skip value for generation",
        default=1,
        min=1,
        update=update_parameters
    )
    bpy.types.Scene.stablegen_preset = bpy.props.EnumProperty(
        name="Preset",
        description="Select a preset for easy mode",
        items=get_preset_items,
        default=0
    )

    bpy.types.Scene.active_preset = bpy.props.StringProperty(
    name="Active Preset",
    default="DEFAULT"
    )

    bpy.types.Scene.model_architecture = bpy.props.EnumProperty(
        name="Model Architecture",
        description="Select the model architecture to use for generation",
        items=[
            ('sdxl', 'SDXL', ''),
            ('flux1', 'Flux 1 (beta support)', '')
        ],
        default='sdxl',
        update=update_parameters
    )
    
    bpy.types.Scene.output_timestamp = bpy.props.StringProperty(
        name="Output Timestamp",
        description="Timestamp for generation output directory",
        default=""
    )
    
    bpy.types.Scene.camera_prompts = bpy.props.CollectionProperty(
        type=CameraPromptItem,
        name="Camera Prompts",
        description="Stores viewpoint descriptions for each camera"
    ) # type: ignore
    
    bpy.types.Scene.use_camera_prompts = bpy.props.BoolProperty(
        name="Use Camera Prompts",
        description="Use camera prompts for generating images",
        default=True,
        update=update_parameters
    )
    bpy.types.Scene.show_core_settings = bpy.props.BoolProperty(
        name="Core Generation Settings",
        description="Parameters used for the image generation process. Also includes LoRAs for faster generation.",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_lora_settings = bpy.props.BoolProperty(
        name="LoRA Settings",
        description="Settings for custom LoRA management.",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_scene_understanding_settings = bpy.props.BoolProperty(
        name="Viewpoint Blending Settings",
        description="Settings for how the addon blends different viewpoints together.",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_output_material_settings = bpy.props.BoolProperty(
        name="Output & Material Settings",
        description="Settings for output characteristics and material handling, including texture processing and final image resolution.",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_image_guidance_settings = bpy.props.BoolProperty(
        name="Image Guidance (IPAdapter & ControlNet)",
        description="Configuration for advanced image guidance techniques, allowing more precise control via reference images or structural inputs.",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_masking_inpainting_settings = bpy.props.BoolProperty(
        name="Inpainting Options",
        description="Parameters for inpainting and mask manipulation to refine specific image areas. (Visible for UV Inpaint & Sequential modes).",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.show_mode_specific_settings = bpy.props.BoolProperty(
        name="Generation Mode Specifics",
        description="Parameters exclusively available for the selected Generation Mode, allowing tailored control over mode-dependent behaviors.",
        default=False,
        update=update_parameters
    )
    
    bpy.types.Scene.apply_bsdf = bpy.props.BoolProperty(
        name ="Apply BSDF",
        description="""Apply the BSDF shader to the material
    - when set to FALSE, the material will be emissive and will not be affected by the scene lighting
    - when set to TRUE, the material will be affected by the scene lighting""",
        default=False,
        update=update_parameters
    )
    
    # IPADAPTER parameters


    bpy.types.Scene.controlnet_units = bpy.props.CollectionProperty(type=ControlNetUnit)
    bpy.utils.register_class(AddControlNetUnit)
    bpy.utils.register_class(RemoveControlNetUnit)
    bpy.types.Scene.lora_units = bpy.props.CollectionProperty(type=LoRAUnit)
    bpy.utils.register_class(AddLoRAUnit)
    bpy.utils.register_class(RemoveLoRAUnit)
    bpy.types.Scene.controlnet_units_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.lora_units_index = bpy.props.IntProperty(default=0)
    bpy.utils.register_class(ApplyPreset)
    bpy.utils.register_class(SavePreset)
    bpy.utils.register_class(DeletePreset) 
    bpy.utils.register_class(ExportOrbitGIF)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():   
    """     
    Unregisters the addon.         
    :return: None     
    """
    del bpy.types.Scene.comfyui_prompt
    del bpy.types.Scene.comfyui_negative_prompt
    del bpy.types.Scene.model_name
    del bpy.types.Scene.seed
    del bpy.types.Scene.control_after_generate
    del bpy.types.Scene.steps
    del bpy.types.Scene.cfg
    del bpy.types.Scene.sampler
    del bpy.types.Scene.scheduler
    del bpy.types.Scene.show_advanced_params
    del bpy.types.Scene.show_generation_params
    del bpy.types.Scene.auto_rescale
    del bpy.types.Scene.generation_method
    del bpy.types.Scene.use_ipadapter
    del bpy.types.Scene.refine_images
    del bpy.types.Scene.refine_steps
    del bpy.types.Scene.refine_sampler
    del bpy.types.Scene.refine_scheduler
    del bpy.types.Scene.denoise
    del bpy.types.Scene.refine_cfg
    del bpy.types.Scene.refine_prompt
    del bpy.types.Scene.refine_upscale_method
    del bpy.types.Scene.generation_status
    del bpy.types.Scene.generation_progress
    del bpy.types.Scene.overwrite_material
    del bpy.types.Scene.refine_preserve
    del bpy.types.Scene.discard_factor
    del bpy.types.Scene.weight_exponent
    del bpy.types.Scene.bake_texture
    del bpy.types.Scene.bake_texture_size
    del bpy.types.Scene.bake_unwrap_method
    del bpy.types.Scene.bake_unwrap_overlap_only
    del bpy.types.Scene.allow_modify_existing_textures
    del bpy.types.Scene.ask_object_prompts
    del bpy.types.Scene.fallback_color
    del bpy.types.Scene.controlnet_units
    del bpy.types.Scene.controlnet_units_index
    del bpy.types.Scene.lora_units
    del bpy.types.Scene.lora_units_index
    del bpy.types.Scene.weight_exponent_mask
    del bpy.types.Scene.sequential_smooth
    del bpy.types.Scene.canny_threshold_low
    del bpy.types.Scene.canny_threshold_high
    del bpy.types.Scene.sequential_factor_smooth
    del bpy.types.Scene.sequential_factor_smooth_2
    del bpy.types.Scene.sequential_factor
    del bpy.types.Scene.grow_mask_by
    del bpy.types.Scene.mask_blocky
    del bpy.types.Scene.differential_diffusion
    del bpy.types.Scene.differential_noise
    del bpy.types.Scene.blur_mask
    del bpy.types.Scene.blur_mask_radius
    del bpy.types.Scene.blur_mask_sigma
    del bpy.types.Scene.sequential_custom_camera_order
    del bpy.types.Scene.ipadapter_strength
    del bpy.types.Scene.ipadapter_start
    del bpy.types.Scene.ipadapter_end
    del bpy.types.Scene.sequential_ipadapter
    del bpy.types.Scene.sequential_ipadapter_mode
    del bpy.types.Scene.sequential_ipadapter_regenerate
    del bpy.types.Scene.ipadapter_weight_type
    del bpy.types.Scene.clip_skip
    del bpy.types.Scene.stablegen_preset
    del bpy.types.Scene.model_architecture
    del bpy.types.Scene.output_timestamp
    del bpy.types.Scene.camera_prompts
    del bpy.types.Scene.use_camera_prompts
    del bpy.types.Scene.show_core_settings
    del bpy.types.Scene.show_lora_settings
    del bpy.types.Scene.show_scene_understanding_settings
    del bpy.types.Scene.show_output_material_settings
    del bpy.types.Scene.show_image_guidance_settings
    del bpy.types.Scene.show_masking_inpainting_settings
    del bpy.types.Scene.show_mode_specific_settings
    bpy.utils.unregister_class(ApplyPreset)
    bpy.utils.unregister_class(DeletePreset) 
    bpy.utils.unregister_class(SavePreset)
    bpy.utils.unregister_class(CurvesToMesh)
    bpy.utils.unregister_class(ApplyModifiers)
    bpy.utils.unregister_class(AddHDRI)
    bpy.utils.unregister_class(SwitchMaterial)
    bpy.utils.unregister_class(AddCameras)
    bpy.utils.unregister_class(BakeTextures)
    bpy.utils.unregister_class(ComfyUIGenerate)
    bpy.utils.unregister_class(StableGenPanel)
    bpy.utils.unregister_class(StableGenAddonPreferences)
    bpy.utils.unregister_class(ControlNetUnit)
    bpy.utils.unregister_class(AddControlNetUnit)
    bpy.utils.unregister_class(RemoveControlNetUnit)
    bpy.utils.unregister_class(LoRAUnit)
    bpy.utils.unregister_class(AddLoRAUnit)
    bpy.utils.unregister_class(RemoveLoRAUnit)
    bpy.utils.unregister_class(ExportOrbitGIF)
    bpy.utils.unregister_class(CameraPromptItem)
    bpy.utils.unregister_class(CollectCameraPrompts) 
    # Remove the load handler for default controlnet unit
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
   

if __name__ == "__main__":
    register()
