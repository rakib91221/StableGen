""" This script registers the addon. """
import bpy # pylint: disable=import-error
from .stablegen import StableGenPanel, ApplyPreset, SavePreset, DeletePreset, get_preset_items, update_parameters
from .render_tools import BakeTextures, AddCameras, SwitchMaterial, ExportOrbitGIF, CollectCameraPrompts, CameraPromptItem 
from .utils import AddHDRI, ApplyModifiers, CurvesToMesh
from .generator import ComfyUIGenerate, Reproject, Regenerate
import os
from bpy.app.handlers import persistent

bl_info = {
    "name": "StableGen",
    "category": "Object",
    "author": "Ondrej Sakala",
    "version": (0, 0, 8),
    'blender': (4, 2, 0)
}

classes = [
    StableGenPanel,
    ApplyPreset,
    SavePreset,
    DeletePreset,
    BakeTextures,
    AddCameras,
    SwitchMaterial,
    ExportOrbitGIF,
    CollectCameraPrompts,
    CameraPromptItem,
    AddHDRI,
    ApplyModifiers,
    CurvesToMesh,
    ComfyUIGenerate,
    Reproject,
    Regenerate
]

def update_combined(self, context): # Combined with load_handler to load controlnet unit on first setup
    update_parameters(self, context)
    load_handler(None)

    # Checkpoint model reset
    current_checkpoint = context.scene.model_name
    checkpoint_items = update_model_list(self, context)
    valid_checkpoint_ids = {item[0] for item in checkpoint_items}

    placeholder_id = 'NONE_AVAILABLE'

    if current_checkpoint not in valid_checkpoint_ids:
        if placeholder_id in valid_checkpoint_ids:
            context.scene.model_name = placeholder_id
        elif checkpoint_items: # If no placeholder but other items, pick first
            context.scene.model_name = checkpoint_items[0][0]

    # LoRA unit reset
    if hasattr(context.scene, 'lora_units'):
        lora_items = get_lora_models(self, context)
        valid_lora_ids = {item[0] for item in lora_items}

        for id, lora_unit in enumerate(context.scene.lora_units):
            if lora_unit.model_name not in valid_lora_ids or lora_unit.model_name == "NONE_AVAILABLE":
                # Remove the unit
                context.scene.lora_units.remove(id)
    # Check if the current LoRA unit index is valid
    if context.scene.lora_units_index >= len(context.scene.lora_units) or context.scene.lora_units_index < 0:
        context.scene.lora_units_index = max(0, len(context.scene.lora_units) - 1)

    return None

class StableGenAddonPreferences(bpy.types.AddonPreferences):
    """     
    Preferences for the StableGen addon.     
    """
    bl_idname = __package__

    comfyui_dir: bpy.props.StringProperty(
        name="ComfyUI Directory",
        description="Path to the ComfyUI directory.",
        default="",
        subtype='DIR_PATH',
        update=update_combined
    ) # type: ignore

    external_checkpoints_dir: bpy.props.StringProperty(
        name="External Checkpoints Directory (Optional)",
        description="Path to an additional directory for checkpoint models. Ensure ComfyUI is also configured to see this path (e.g., via extra_model_paths.yaml).",
        default="",
        subtype='DIR_PATH',
        update=update_combined,
    ) # type: ignore

    external_loras_dir: bpy.props.StringProperty(
        name="External LoRAs Directory (Optional)",
        description="Path to an additional directory for LoRA models. Ensure ComfyUI is also configured to see this path.",
        default="",
        subtype='DIR_PATH',
        update=update_combined,
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
        layout.prop(self, "comfyui_dir")
        layout.prop(self, "output_dir")
        layout.prop(self, "server_address")
        layout.prop(self, "controlnet_mapping")
        layout.prop(self, "save_blend_file")
        layout.separator()
        split = layout.split(factor=0.5)
        split.label(text=self.bl_rna.properties['external_checkpoints_dir'].name)
        split.prop(self, "external_checkpoints_dir", text="")
        
        split = layout.split(factor=0.5)
        split.label(text=self.bl_rna.properties['external_loras_dir'].name)
        split.prop(self, "external_loras_dir", text="")


def get_models_from_directory(scan_root_path: str, valid_extensions: tuple, type_for_description: str, path_prefix_for_id: str = ""):
    """
    Scans a given root directory (and its subdirectories) for model files.
    Returns paths relative to scan_root_path, optionally prefixed.

    Args:
        scan_root_path (str): The absolute root path to start scanning from.
        valid_extensions (tuple): Tuple of valid lowercase file extensions.
        type_for_description (str): String like "Checkpoint" or "LoRA" for UI descriptions.
        path_prefix_for_id (str): A prefix to add to the identifier if needed to distinguish sources 
    """
    items = []
    if not (scan_root_path and os.path.isdir(scan_root_path)):
        # Don't add error items here, let the caller handle empty results
        return items

    try:
        for root, _, files in os.walk(scan_root_path):
            for f_name in files:
                if f_name.lower().endswith(valid_extensions):
                    full_path = os.path.join(root, f_name)
                    # Path relative to the specific scan_root_path (ComfyUI or external)
                    relative_path = os.path.relpath(full_path, scan_root_path)
                    
                    # The identifier sent to ComfyUI should be this relative_path
                    # if scan_root_path is a path ComfyUI recognizes.
                    identifier = path_prefix_for_id + relative_path 
                    display_name = identifier # Show the full "prefixed" path if prefix is used

                    items.append((identifier, display_name, f"{type_for_description}: {display_name}"))
    except PermissionError:
        print(f"Permission Denied for {scan_root_path}") # Log it
    except Exception as e:
        print(f"Error Scanning {scan_root_path}: {e}") # Log it
    
    return items

def merge_and_deduplicate_models(model_lists: list):
    """
    Merges multiple lists of model items and de-duplicates based on the identifier.
    Keeps the first encountered entry in case of duplicate identifiers.
    """
    merged_items = []
    seen_identifiers = set()
    for model_list in model_lists:
        for identifier, name, description in model_list:
            # Filter out placeholder/error items from get_models_from_directory if they existed
            if identifier.startswith("NO_") or identifier.startswith("PERM_") or identifier.startswith("SCAN_") or identifier == "NONE_FOUND":
                continue
            if identifier not in seen_identifiers:
                merged_items.append((identifier, name, description))
                seen_identifiers.add(identifier)
    
    if not merged_items: # If after all scans and merges, still nothing
        merged_items.append(("NONE_AVAILABLE", "No Models Found", "Check ComfyUI and External Directories in Preferences"))
    
    merged_items.sort(key=lambda x: x[1]) # Sort by display name
    return merged_items

def update_model_list(self, context):
    """
    Populates EnumProperty items with checkpoint models from ComfyUI/models/checkpoints.
    Returns a list of (identifier, name, description) tuples.
    """
    addon_prefs = context.preferences.addons[__package__].preferences
    comfyui_base_dir = addon_prefs.comfyui_dir
    external_ckpts_dir = addon_prefs.external_checkpoints_dir
    
    all_model_items = []

    # 1. Scan ComfyUI standard checkpoints path
    if comfyui_base_dir and os.path.isdir(comfyui_base_dir):
        if context.scene.model_architecture == 'sdxl':
            comfy_ckpts_path = os.path.join(comfyui_base_dir, "models", "checkpoints")
            types = ('.safetensors', '.ckpt', '.pth', '.sft')
        else:
            comfy_ckpts_path = os.path.join(comfyui_base_dir, "models", "unet") # For FLUX1
            types = ('.safetensors', '.ckpt', '.pth', '.sft', '.gguf')
        all_model_items.append(
            get_models_from_directory(comfy_ckpts_path, types, "Checkpoint")
        )

    # 2. Scan External Checkpoints Path
    if external_ckpts_dir and os.path.isdir(external_ckpts_dir):
        all_model_items.append(
            get_models_from_directory(external_ckpts_dir, types, "Ext. Checkpoint")
        )
    
    return merge_and_deduplicate_models(all_model_items)

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
    addon_prefs = context.preferences.addons[__package__].preferences
    comfyui_base_dir = addon_prefs.comfyui_dir
    external_loras_dir = addon_prefs.external_loras_dir

    all_lora_items = []

    # 1. Scan ComfyUI standard LoRAs path
    if comfyui_base_dir and os.path.isdir(comfyui_base_dir):
        comfy_loras_path = os.path.join(comfyui_base_dir, "models", "loras")
        all_lora_items.append(
            get_models_from_directory(comfy_loras_path, ('.safetensors', '.ckpt', '.pt', '.pth'), "LoRA")
        )


    # 2. Scan External LoRAs Path
    if external_loras_dir and os.path.isdir(external_loras_dir):
        all_lora_items.append(
            get_models_from_directory(external_loras_dir, ('.safetensors', '.ckpt', '.pt', '.pth'), "Ext. LoRA")
        )
        
    return merge_and_deduplicate_models(all_lora_items)

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
        addon_prefs = context.preferences.addons.get(__package__)

        if not addon_prefs: # Should not happen if addon is enabled
            return False
        addon_prefs = addon_prefs.preferences
        
        comfyui_dir = addon_prefs.comfyui_dir
        external_loras_dir = addon_prefs.external_loras_dir

        # Initial check: at least one base directory must be set
        if not (comfyui_dir and os.path.isdir(comfyui_dir)) and \
           not (external_loras_dir and os.path.isdir(external_loras_dir)):
            cls.poll_message_set("Neither ComfyUI nor External LoRA directory is set/valid.")
            return False

        # Get the merged list of LoRAs.
        # Assuming get_lora_models is robust and returns placeholders if dirs are bad.
        lora_enum_items = get_lora_models(scene, context) 
        
        # Count actual available LoRAs, excluding placeholders/errors
        # Placeholders used in get_models_from_directory and merge_and_deduplicate_models
        placeholder_ids = {"NONE_AVAILABLE", "NO_COMFYUI_DIR_LORA", "NO_LORAS_SUBDIR", "PERM_ERROR", "SCAN_ERROR", "NONE_FOUND"} # Add any others used by your helpers
        
        available_lora_files_count = sum(1 for item in lora_enum_items if item[0] not in placeholder_ids)

        if available_lora_files_count == 0:
            cls.poll_message_set("No LoRA model files found in any specified directory (including subdirectories).")
            return False

        num_current_lora_units = len(scene.lora_units)
        # Prevent adding more units than distinct available LoRA files
        if num_current_lora_units >= available_lora_files_count:
            cls.poll_message_set("All available distinct LoRA models appear to have corresponding units.")
            return False
            
        return True

    def execute(self, context):
        loras = context.scene.lora_units
        new_lora = loras.add()
        
        # Get available LoRAs (these are (identifier, name, description) tuples)
        all_lora_enum_items = get_lora_models(context.scene, context)
        
        placeholder_ids = {"NONE_AVAILABLE", "NO_COMFYUI_DIR_LORA", "NO_LORAS_SUBDIR", "PERM_ERROR", "SCAN_ERROR", "NONE_FOUND"}
        available_lora_identifiers = [item[0] for item in all_lora_enum_items if item[0] not in placeholder_ids]
        
        if available_lora_identifiers:
            current_lora_model_identifiers_in_use = {unit.model_name for unit in loras if unit.model_name and unit.model_name not in placeholder_ids}
            
            assigned_model = None
            # Try to assign a LoRA that isn't already in use by another unit
            for lora_id in available_lora_identifiers:
                if lora_id not in current_lora_model_identifiers_in_use:
                    assigned_model = lora_id
                    break
            
            # If all available LoRAs are "in use" or no unused one was found, assign the first available one
            if not assigned_model:
                assigned_model = available_lora_identifiers[0]

            if assigned_model:
                try:
                    new_lora.model_name = assigned_model
                except TypeError: 
                    # This might happen if the enum items list isn't perfectly in sync
                    print(f"AddLoRAUnit Execute: TypeError assigning model '{assigned_model}'. Enum might not be ready.")
                    pass 
        
        new_lora.model_strength = 1.0
        new_lora.clip_strength = 1.0
        context.scene.lora_units_index = len(loras) - 1 # Select the newly added unit
        
        # Ensure parameters are updated which might affect preset status
        update_parameters(self, context) 
        
        # Force UI redraw
        for area in context.screen.areas: 
            if area.type == 'VIEW_3D': # Redraw 3D views, common place for the panel
                area.tag_redraw()
            elif area.type == 'PROPERTIES': # Redraw properties editor if panel is there
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
        addon_prefs = bpy.context.preferences.addons[__package__].preferences
        if hasattr(scene, "controlnet_units") and not scene.controlnet_units:
            default_unit = scene.controlnet_units.add()
            default_unit.unit_type = 'depth'
        # Default LoRA Unit
        if hasattr(scene, "lora_units") and not scene.lora_units:
            default_lora_filename_to_find = 'sdxl_lightning_8step_lora.safetensors'
            all_available_loras_enums = get_lora_models(scene, bpy.context) 
            
            found_lora_identifier_to_load = None
            for identifier, name, description in all_available_loras_enums:
                # Identifiers are relative paths like "subdir/model.safetensors" or "model.safetensors"
                # Check if the identifier (which is the relative path) ends with the desired filename
                if identifier.endswith(default_lora_filename_to_find):
                    # Ensure it's not a placeholder/error identifier
                    if identifier not in ["NONE_AVAILABLE", "NO_COMFYUI_DIR_LORA", "NO_LORAS_SUBDIR", "PERM_ERROR", "SCAN_ERROR"]:
                        found_lora_identifier_to_load = identifier
                        break 
            
            if found_lora_identifier_to_load:
                new_lora_unit = None 
                try:
                    new_lora_unit = scene.lora_units.add()
                    new_lora_unit.model_name = found_lora_identifier_to_load
                    new_lora_unit.model_strength = 1.0
                    new_lora_unit.clip_strength = 1.0
                    # print(f"StableGen Load Handler: Default LoRA '{found_lora_identifier_to_load}' added.")
                except TypeError:
                    # This can happen if Enum items are not fully synchronized at this early stage of loading.
                    print(f"StableGen Load Handler: TypeError setting default LoRA '{found_lora_identifier_to_load}'. Enum items might not be fully ready.")
                    if new_lora_unit and scene.lora_units and new_lora_unit == scene.lora_units[-1]:
                        scene.lora_units.remove(len(scene.lora_units)-1) # Attempt to remove partially added unit
                except Exception as e:
                    print(f"StableGen Load Handler: Unexpected error setting default LoRA '{found_lora_identifier_to_load}': {e}")
                    if new_lora_unit and scene.lora_units and new_lora_unit == scene.lora_units[-1]:
                        scene.lora_units.remove(len(scene.lora_units)-1)

classes_to_append = [StableGenAddonPreferences, ControlNetUnit, LoRAUnit, AddControlNetUnit, RemoveControlNetUnit, AddLoRAUnit, RemoveLoRAUnit]
for cls in classes_to_append:
    classes.append(cls)

def register():
    """     
    Registers the addon.         
    :return: None     
    """
    for cls in classes:
        bpy.utils.register_class(cls)

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
        description="Select the SDXL checkpoint",
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
            ('normal', 'Normal', ''),
            ('simple', 'Simple', ''),
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
            ('normal', 'Normal', ''),
            ('simple', 'Simple', ''),
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
        default=(0.0, 0.0, 0.0),
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
    
    bpy.types.Scene.generation_mode = bpy.props.EnumProperty(
        name="Generation Mode",
        description="Controls the generation behavior",
        items=[
            ('standard', 'Standard', 'Standard generation process'),
            ('regenerate_selected', 'Regenerate Selected', 'Regenerate only specific viewpoints, keeping the rest from the previous run'),
            ('project_only', 'Project Only', 'Only project existing textures onto the model without generating new ones')
        ],
        default='standard',
        update=update_parameters
    )

    bpy.types.Scene.early_priority_strength = bpy.props.FloatProperty(
        name="Prioritize Initial Views",
        description="""Strength of the priority applied to initial views. Higher values will make the earlier cameras more important than the later ones. Every view will be prioritized over the next one.
    - Very high values may cause various artifacts.""",
        default=0.5,
        min=0.0,
        max=1.0,
        update=update_parameters
    )

    bpy.types.Scene.early_priority = bpy.props.BoolProperty(
        name="Priority Strength",
        description="""Enable blending priority for earlier cameras.
    - This may prevent artifacts caused by later cameras overwriting earlier ones.
    - You will have to place the important cameras first.""",
        default=False,
        update=update_parameters
    )

    bpy.types.Scene.texture_objects = bpy.props.EnumProperty(
        name="Objects to Texture",
        description="Select the objects to texture",
        items=[
            ('all', 'All Visible', 'Texture all visible objects in the scene'),
            ('selected', 'Selected', 'Texture only selected objects'),
        ],
        default='all',
        update=update_parameters
    )

    bpy.types.Scene.use_flux_lora = bpy.props.BoolProperty(
        name="Use FLUX Depth LoRA",
        description="Use FLUX.1-Depth-dev LoRA for depth conditioning instead of ControlNet. This disables all ControlNet units.",
        default=True,
        update=update_parameters
    )

    # IPADAPTER parameters

    bpy.types.Scene.controlnet_units = bpy.props.CollectionProperty(type=ControlNetUnit)
    bpy.types.Scene.lora_units = bpy.props.CollectionProperty(type=LoRAUnit)
    bpy.types.Scene.controlnet_units_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.lora_units_index = bpy.props.IntProperty(default=0)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():   
    """     
    Unregisters the addon.         
    :return: None     
    """
    del bpy.types.Scene.use_flux_lora
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
    del bpy.types.Scene.generation_mode
    del bpy.types.Scene.early_priority_strength
    del bpy.types.Scene.early_priority
    del bpy.types.Scene.texture_objects
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    # Remove the load handler for default controlnet unit
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
   

if __name__ == "__main__":
    register()
