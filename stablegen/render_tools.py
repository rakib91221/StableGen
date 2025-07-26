""" This file contains the operators and panels for the StableGen addon """
# disable import-error because pylint doesn't recognize the blenders internal modules
import os
import bpy, bmesh  # pylint: disable=import-error
import numpy as np
import math
import time
import mathutils
from mathutils import Matrix
import blf
from .utils import get_file_path, get_dir_path, remove_empty_dirs
import tempfile
import shutil
from PIL import Image

# Import wheels
import cv2 
import imageio
import imageio_ffmpeg


def apply_uv_inpaint_texture(context, obj, baked_image_path):
    """
    Applies the UV inpainted texture to the active material by replacing
    the fallback color node in the node tree.
    """
    mat = obj.active_material
    if not mat or not mat.use_nodes:
        return
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Locate the Output Material node
    output_node = None
    for node in nodes:
        if node.type == 'OUTPUT_MATERIAL':
            output_node = node
            break
    if not output_node or not output_node.inputs["Surface"].links:
        return

    # Traverse from the output input to find a MIX_RGB node with unlinked Color2
    mix_node = None
    before_output = output_node.inputs["Surface"].links[0].from_node
    if before_output.type == 'BSDF_PRINCIPLED':
        current_node = output_node.inputs[0].links[0].from_node.inputs[0].links[0].from_node
    else:
        # Already a color mix node
        current_node = before_output
    while current_node:
        # Base case: Found a MIX_RGB node with unlinked Color2 or linked to image texture
        if (current_node.type == 'MIX_RGB' and 
            (not current_node.inputs["Color2"].is_linked or current_node.inputs["Color2"].links[0].from_node.type == 'TEX_IMAGE')):
            mix_node = current_node
            break
        # If possible, traverse one step back using the first input link
        if current_node.inputs["Color2"].links:
            current_node = current_node.inputs["Color2"].links[0].from_node
        else:
            current_node = None

    if not mix_node:
        return

    # Insert the texture node feeding into the mix node
    tex_node = nodes.new("ShaderNodeTexImage")
    try:
        img = bpy.data.images.load(baked_image_path)
    except Exception as e:
        print("Failed to load image", baked_image_path, e)
        return
    tex_node.image = img
    tex_node.location = (mix_node.location[0] - 300, mix_node.location[1])
    # Remove any existing links on Color2 and connect new texture output
    for link in mix_node.inputs["Color2"].links:
        links.remove(link)
    links.new(tex_node.outputs["Color"], mix_node.inputs["Color2"])
    # Add UV map node
    uv_map_node = nodes.new("ShaderNodeUVMap")
    # Find first UV map which doesn't start with "ProjectionUV"
    uv_map_name = None
    for uv_map in obj.data.uv_layers:
        if uv_map.name.startswith("ProjectionUV"):
            continue
        uv_map_name = uv_map.name
        break
    if uv_map_name:
        uv_map_node.uv_map = uv_map_name
    else:
        uv_map_node.uv_map = obj.data.uv_layers.active.name
    uv_map_node.location = (tex_node.location[0] - 300, tex_node.location[1] - 200)
    # Connect UV map node to texture node
    links.new(uv_map_node.outputs["UV"], tex_node.inputs["Vector"])

def export_emit_image(context, to_export, camera_id=None, bg_color=(0.5, 0.5, 0.5), view_transform='Standard'):
        """     
        Exports a emit-only render of the scene from a camera's perspective.         
        :param context: Blender context.         
        :param camera_id: ID of the camera.         
        :return: None     
        """
        print("Exporting emit render")
        # Set animation frame to 1
        bpy.context.scene.frame_set(1)

        # Store original materials and create temporary ones
        original_materials = {}
        original_active_material = {}
        temporary_materials = {}
        
        # Check if there is BSDF applied
        
        # We need to temporarily disconnect BDSF nodes and connect their inputs directly to the output
       
        for obj in to_export:
            # Store original materials
            original_materials[obj] = list(obj.data.materials)
            original_active_material[obj] = obj.active_material
        
            # Copy active material and switch to it
            mat = obj.active_material
            if not mat:
                continue
            mat_copy = mat.copy()

            # Clear materials and assign temp material
            obj.data.materials.clear()
            obj.data.materials.append(mat_copy)
            
            # Store the temporary material for later deletion
            temporary_materials[obj] = mat_copy

            # Enable use of nodes
            mat_copy.use_nodes = True
            nodes = mat_copy.node_tree.nodes
            links = mat_copy.node_tree.links

            # Find the output node
            output = None
            for node in nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output = node
                    break
                
                # Check the type of the node which connects to output
            before_output = output.inputs[0].links[0].from_node
            if before_output.type == 'BSDF_PRINCIPLED':
                # Find the last color mix node
                color_mix = output.inputs[0].links[0].from_node.inputs[0].links[0].from_node
            else:
                # Already a color mix node
                color_mix = before_output
                continue

            # Find the last color mix node
            color_mix = output.inputs[0].links[0].from_node.inputs[0].links[0].from_node
            # Connect the color mix node directly to the output
            links.new(color_mix.outputs[0], output.inputs[0])
                
        output_dir = get_dir_path(context, "inpaint")["visibility"] if "visibility" in str(camera_id) else get_dir_path(context, "inpaint")["render"]
        output_file = f"render{camera_id}" if camera_id is not None else "render"

        # Store and set world settings
        world = context.scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            context.scene.world = world

        # Store original settings
        original_engine = context.scene.render.engine
        original_film_transparent = context.scene.render.film_transparent
        original_use_nodes = world.use_nodes
        original_color = world.color.copy() if not world.use_nodes else None

        # Now setting the world color should work
        world.color = bg_color
        # Disable world nodes temporarily
        world.use_nodes = False
        # Switch to CYCLES render engine and configure settings
        context.scene.render.engine = 'CYCLES'
        # Enable OSL
        context.scene.cycles.use_osl = True
        context.scene.cycles.device = 'CPU'
        context.scene.render.film_transparent = False
        # Change color management to standard
        bpy.context.scene.display_settings.display_device = 'sRGB'
        bpy.context.scene.view_settings.view_transform = view_transform
        context.scene.cycles.samples = 1  # Minimum samples for speed
        # Configure view layer settings for diffuse-only
        view_layer = context.view_layer
        view_layer.use_pass_diffuse_color = False
        view_layer.use_pass_diffuse_direct = False
        view_layer.use_pass_diffuse_indirect = False
        
        # Disable all other passes
        view_layer.use_pass_ambient_occlusion = False
        view_layer.use_pass_shadow = False
        view_layer.use_pass_emit = True
        view_layer.use_pass_environment = True
 

        # Set up nodes for diffuse-only output
        context.scene.use_nodes = True
        nodes = context.scene.node_tree.nodes
        links = context.scene.node_tree.links
        
        # Clear existing nodes
        nodes.clear()
        
        # Create nodes
        render_layers = nodes.new('CompositorNodeRLayers')
        mix_node = nodes.new('CompositorNodeMixRGB')
        mix_node.blend_type = 'ADD'
        mix_node.inputs[0].default_value = 1
        output_node = nodes.new('CompositorNodeOutputFile')
        output_node.base_path = output_dir
        output_node.file_slots[0].path = output_file
    
        # Connect emission to output
        links.new(render_layers.outputs['Emit'], mix_node.inputs[1])
        links.new(render_layers.outputs['Env'], mix_node.inputs[2])
        links.new(mix_node.outputs[0], output_node.inputs[0])
            
        # Render
        bpy.ops.render.render(write_still=True)
        
        if context.scene.mask_blocky:
            # If this is a visibility mask, expand it to blocks
            if "visibility" in str(camera_id):
                # Load the rendered image
                image_path = os.path.join(output_dir, f"{output_file}.png")
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                
                image_path = image_path.replace(".png", "0001.png")

                # Expand the mask to blocks
                expanded_mask = expand_mask_to_blocks(image_path, block_size=8)
                
                # Scale float32 to uint8 [0, 255]
                expanded_mask = (expanded_mask * 255).astype(np.uint8)
                
                cv2.imwrite(image_path, expanded_mask)

        # Restore original settings
        context.scene.render.engine = original_engine
        context.scene.render.film_transparent = original_film_transparent
        if original_use_nodes:
            world.use_nodes = True
        elif original_color:
            world.color = original_color
        bpy.context.scene.view_settings.view_transform = 'Standard'

        # Restore original materials
        for obj, materials in original_materials.items():
            obj.data.materials.clear()
            # First append the original active material
            if original_active_material[obj]:
                obj.data.materials.append(original_active_material[obj])
            for mat in materials:
                if mat != original_active_material[obj]:
                    obj.data.materials.append(mat)
                    
        # Clean up temporary materials
        for _, temp_mat in temporary_materials.items():
            if temp_mat and temp_mat.name in bpy.data.materials:
                bpy.data.materials.remove(temp_mat)

        print(f"Emmision render saved to: {os.path.join(output_dir, output_file)}.png")

def export_render(context, camera_id=None):
    """
    Renders the scene from a camera's perspective using Workbench.
    Creates temporary materials for consistent rendering.
    :param context: Blender context.
    :param camera_id: ID of the camera for the output filename.
    :return: None
    """
    print("Exporting render using Workbench")

    # Store original materials and create temporary ones
    original_materials = {}
    original_active_material = {}
    for obj in context.scene.objects:
        if obj.type == 'MESH':
            # Store original materials
            original_materials[obj] = list(obj.data.materials)
            original_active_material[obj] = obj.active_material

            # Create temporary material
            temp_mat = bpy.data.materials.new(name="TempRenderMaterial")
            temp_mat.use_nodes = True # Even Workbench uses nodes for basic color
            nodes = temp_mat.node_tree.nodes
            links = temp_mat.node_tree.links

            # Clear default nodes
            for node in nodes:
                nodes.remove(node)

            # Create basic material output and diffuse BSDF (Workbench respects Base Color)
            mat_output = nodes.new('ShaderNodeOutputMaterial')
            diffuse = nodes.new('ShaderNodeBsdfDiffuse') # Simple diffuse color
            diffuse.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1.0) # Default grey
            diffuse.inputs['Roughness'].default_value = 0.5
            links.new(diffuse.outputs['BSDF'], mat_output.inputs['Surface'])

            # Clear materials and assign temp material
            obj.data.materials.clear()
            obj.data.materials.append(temp_mat)

    # Set animation frame to 1
    context.scene.frame_set(1)

    # Setup output path
    output_dir = get_dir_path(context, "misc")
    output_file = f"render{camera_id}" if camera_id is not None else "render"

    # Store original render settings
    original_engine = context.scene.render.engine
    original_workbench_settings = {
        'lighting': context.scene.display.shading.light,
        'color_type': context.scene.display.shading.color_type
    }

    # Switch to WORKBENCH render engine and configure settings
    context.scene.render.engine = 'BLENDER_WORKBENCH'
    # Configure Workbench for a flat, consistent look if needed
    context.scene.display.shading.light = 'STUDIO'
    context.scene.display.shading.color_type = 'SINGLE'

    render_layer = context.view_layer
    original_combined = render_layer.use_pass_combined

    # Enable combined pass for Workbench
    render_layer.use_pass_combined = True

    # Set up output nodes (Compositor setup remains the same)
    context.scene.use_nodes = True
    nodes = context.scene.node_tree.nodes
    links = context.scene.node_tree.links
    nodes.clear()

    render_layers = nodes.new('CompositorNodeRLayers')
    output_node = nodes.new('CompositorNodeOutputFile')
    output_node.base_path = output_dir
    output_node.file_slots[0].path = output_file
    links.new(render_layers.outputs['Image'], output_node.inputs[0])

    # Render
    bpy.ops.render.render(write_still=True)

    # Restore original materials
    for obj, materials in original_materials.items():
        obj.data.materials.clear()
        # First append the original active material
        if original_active_material[obj]:
            obj.data.materials.append(original_active_material[obj])
        for mat in materials:
            if mat != original_active_material[obj]:
                obj.data.materials.append(mat)

    # Restore original render settings
    render_layer.use_pass_combined = original_combined

    # Clean up temporary materials
    # Use a while loop to safely remove materials while iterating
    temp_mats = [m for m in bpy.data.materials if m.name.startswith("TempRenderMaterial")]
    for mat in temp_mats:
        bpy.data.materials.remove(mat)


    # Restore original render settings
    context.scene.render.engine = original_engine
    context.scene.display.shading.light = original_workbench_settings['lighting']
    context.scene.display.shading.color_type = original_workbench_settings['color_type']


    print(f"Render saved to: {os.path.join(output_dir, output_file)}0001.png") # Blender adds frame number

def export_canny(context, camera_id=None, low_threshold=0, high_threshold=80):
    """
    Uses export_render and openCV to generate a Canny edge detection image.
    :param context: Blender context.
    :param camera_id: ID of the camera for the output filename.
    :param low_threshold: Low threshold for edge detection.
    :param high_threshold: High threshold for edge detection.
    :return: None
    """
    # Render the scene
    export_render(context, camera_id)

    # Load the rendered image
    output_dir_render = get_dir_path(context, "misc")
    output_dir_canny = get_dir_path(context, "controlnet")["canny"]
    output_file = f"render{camera_id}0001" if camera_id is not None else "render"
    image_path = os.path.join(output_dir_render, f"{output_file}.png")
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # Apply Canny edge detection
    edges = cv2.Canny(image, low_threshold, high_threshold)

    # Save the edge detection image
    output_file = f"canny{camera_id}0001" if camera_id is not None else "canny"
    cv2.imwrite(os.path.join(output_dir_canny, f"{output_file}.png"), edges)

    print(f"Canny edge detection saved to: {os.path.join(output_dir_canny, output_file)}.png")


def expand_mask_to_blocks(mask_file_path, block_size=8):
    """
    Loads a mask image from a file path and processes it so that any
    block_size x block_size grid cell containing any non-black pixel (value > 0)
    becomes fully white (1.0).

    Args:
        mask_file_path (str): The path to the mask image file.
        block_size (int): The size of the grid blocks (default: 8).

    Returns:
        np.ndarray | None: The processed mask as a NumPy array (float32, normalized [0, 1]).
                           Returns None if the file cannot be loaded or processed.
    """
    if not isinstance(mask_file_path, str):
        print(f"Error: mask_file_path must be a string. Got: {type(mask_file_path)}")
        return None
    if not os.path.exists(mask_file_path):
        print(f"Error: Mask file not found at {mask_file_path}")
        return None
    if not os.path.isfile(mask_file_path):
         print(f"Error: Path provided is not a file: {mask_file_path}")
         return None

    try:
        # Load the image using Pillow
        with Image.open(mask_file_path) as img:
            # Convert to grayscale ('L') which typically represents intensity
            mask_pil = img.convert("L")
            # Convert PIL Image to numpy array
            mask_array = np.array(mask_pil)

        # --- Normalize mask to float32 [0, 1] ---
        # Ensures comparison with 0.0 is reliable regardless of original bit depth
        if mask_array.dtype == np.uint8:
            mask_array = mask_array.astype(np.float32) / 255.0
        elif np.issubdtype(mask_array.dtype, np.integer):
            max_val = np.iinfo(mask_array.dtype).max
            mask_array = mask_array.astype(np.float32) / max_val if max_val > 0 else mask_array.astype(np.float32)
        elif not np.issubdtype(mask_array.dtype, np.floating):
            print(f"Warning: Unsupported mask dtype {mask_array.dtype} after loading. Trying to convert.")
            mask_array = mask_array.astype(np.float32) # Attempt conversion
        # Ensure it's precisely within [0, 1] after potential float conversion
        mask_array = np.clip(mask_array, 0.0, 1.0)
        # --- End normalization ---

        max_value = 1.0 # Output will be normalized float [0, 1]

        height, width = mask_array.shape
        # Create output mask initialized to zeros (black), ensure float32 type
        output_mask = np.zeros_like(mask_array, dtype=np.float32)

        # --- Core block processing logic ---
        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                # Define block boundaries, handle image edges
                y_start = y
                y_end = min(y + block_size, height)
                x_start = x
                x_end = min(x + block_size, width)

                # Extract the current block
                block = mask_array[y_start:y_end, x_start:x_end]

                # Check if *any* pixel value in the block is greater than 0.0
                if np.any(block > 0.0):
                    # If yes, set the corresponding block in the output mask to 1.0 (white)
                    output_mask[y_start:y_end, x_start:x_end] = max_value
        # --- End of core logic ---

        return output_mask

    except FileNotFoundError:
        print(f"Error: Mask file not found at {mask_file_path}")
        return None
    except Exception as e:
        print(f"Error loading or processing mask file {mask_file_path}: {e}")
        return None


def export_visibility(context, to_export, obj=None, camera_visibility=None):
    """     
    Exports the visibility of the mesh by temporarily altering the shading nodes.
    :param context: Blender context.
    :param filepath: Path to the output file.
    :param obj: Blender object.
    :param camera_visibility: Camera object for visibility calculation.
    :return: None
    """
    # Store original materials and create temporary ones
    original_materials = {}
    original_active_material = {}
    temporary_materials = {}

    def prepare_material(obj):
        mat = obj.active_material
        if not mat:
            return False
        
        # Store original materials
        original_materials[obj] = list(obj.data.materials)
        original_active_material[obj] = obj.active_material  # Store original active material

        # Store original active mat

        # Copy active material and switch to it
        mat = obj.active_material
        if not mat:
            return False
        mat_copy = mat.copy()

        # Clear materials and assign temp material
        obj.data.materials.clear()
        obj.data.materials.append(mat_copy)
        
        # Store temporary material for later deletion
        temporary_materials[obj] = mat_copy
        
        # Enable use of nodes
        mat_copy.use_nodes = True
        nodes = mat_copy.node_tree.nodes
        links = mat_copy.node_tree.links

        # Find the output node
        output = None
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output = node
                break

        if not output:
            return False
        
        # Determine which input to used based on existence of BSDF node before the output
        if output.inputs[0].links and output.inputs[0].links[0].from_node.type == 'BSDF_PRINCIPLED':
            color_mix = output.inputs[0].links[0].from_node.inputs[0].links[0].from_node
            input = output.inputs[0].links[0].from_node.inputs[0]
        else:
            color_mix = output.inputs[0].links[0].from_node
            input = output.inputs[0]
        # Add equal node between color mix and bsdf
        equal = nodes.new("ShaderNodeMath")
        
        # Use compare operation to filter to only 1 or 0
        
        if context.scene.generation_method == 'sequential' and context.scene.sequential_smooth:
            # Add color ramp node
            compare = nodes.new("ShaderNodeValToRGB")
            compare.color_ramp.interpolation = 'LINEAR'
            compare.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
            compare.color_ramp.elements[0].position = context.scene.sequential_factor_smooth if context.scene.generation_method == 'sequential' else 0.5
            compare.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
            compare.color_ramp.elements[1].position = context.scene.sequential_factor_smooth_2 if context.scene.generation_method == 'sequential' else 1.0
            links.new(color_mix.outputs[0], compare.inputs[0])
            links.new(compare.outputs[0], input)
        elif not context.scene.allow_modify_existing_textures or context.scene.generation_method == 'sequential':
            equal.operation = 'COMPARE'
            equal.inputs[1].default_value = 1
            equal.inputs[2].default_value = context.scene.sequential_factor if context.scene.generation_method == 'sequential' else 0.0
            equal.location = (color_mix.location[0], color_mix.location[1])
            links.new(color_mix.outputs[0], equal.inputs[0])
            links.new(equal.outputs[0], input)
        else:
            links.new(color_mix.outputs[0], input)

        while True:
            # Remove color ramp connected to fac, connect directly to color ramp's fac
            color_ramp = color_mix.inputs[0].links[0].from_node
            fac_node = color_ramp.inputs[0].links[0].from_node
            # Add subtract node
            subtract = nodes.new("ShaderNodeMath")
            subtract.operation = 'SUBTRACT'
            subtract.location = (color_ramp.location[0], color_ramp.location[1])
            subtract.inputs[0].default_value = 1
            links.new(fac_node.outputs[0], subtract.inputs[1])
            links.new(subtract.outputs[0], color_mix.inputs["Fac"])
            nodes.remove(color_ramp)
            # Disconnect color1
            links.remove(color_mix.inputs[1].links[0])
            color_mix.inputs["Color1"].default_value = (0, 0, 0, 1)
            if not (color_mix.inputs["Color2"].links and (color_mix.inputs[2].links[0].from_node.type == 'MIX_RGB')):
                color_mix.inputs["Color2"].default_value = (1, 1, 1, 1)
                break
            else:
                color_mix = color_mix.inputs["Color2"].links[0].from_node
        # If there is previous tex_image node, remove it (for cases when this function is called multiple times)
        if color_mix.inputs["Color2"].is_linked:
            nodes.remove(color_mix.inputs["Color2"].links[0].from_node)
            
        for node in nodes:
            if node.type == 'SCRIPT' and "Power" in node.inputs:
                try:
                    # Set according to weight_exponent_mask
                    node.inputs["Power"].default_value = context.scene.weight_exponent if context.scene.weight_exponent_mask else 1.0
                except Exception as e:
                    print(f"  - Warning: Failed to set Power for node '{node.name}'. Error: {e}")
               
        return True
    
    # Prepare the material

    if not obj:
        # Prepare for all objects
        for obj in to_export:
            if not prepare_material(obj):
                return False
    else:
        if not prepare_material(obj):
            return False
        
    # Bake or render the texture
    if not camera_visibility:
        output_dir = get_dir_path(context, "uv_inpaint")["visibility"]
        output_file = f"{obj.name}_baked_visibility"
        prepare_baking(context)
        bake_texture(context, obj, suffix="_visibility", texture_resolution=1024, view_transform='Raw', output_dir=output_dir)
        # Use openCV to normalize the image
        image_path = os.path.join(output_dir, f"{output_file}.png")
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        # Normalize the image
        image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
        # Save the image
        cv2.imwrite(image_path, image)
    else:
        # Make sure the camera is active and set to render
        cameras = [obj for obj in context.scene.objects if obj.type == 'CAMERA']
        cameras.sort(key=lambda x: x.name)
        camera_visibility_index = [i for i, camera in enumerate(cameras) if camera == camera_visibility][0]
        camera_render_index = (camera_visibility_index + 1) % len(cameras)
        camera_render = cameras[camera_render_index]
        context.scene.camera = camera_render
        export_emit_image(context, to_export, camera_id=f"{camera_render_index}_visibility", bg_color=(1, 1, 1), view_transform='Raw')

    # Restore original materials
    for obj, materials in original_materials.items():
        obj.data.materials.clear()
        # First append the original active material
        if original_active_material[obj]:
            obj.data.materials.append(original_active_material[obj])
        for mat in materials:
            if mat != original_active_material[obj]:
                obj.data.materials.append(mat)
                
    # Clean up temporary materials
    for _, temp_mat in temporary_materials.items():
        if temp_mat and temp_mat.name in bpy.data.materials:
            bpy.data.materials.remove(temp_mat)

    return True

class AddCameras(bpy.types.Operator):
    """Add cameras along a circle and adjust their positions
    
    Uses the active camera as a reference. If there is no active camera, a new one is created based on the viewport.
    
    Tips: 
    - Try to frame the object / scene with minimal margin around it.
    - Aim to achieve a uniform coverage of the object / scene. 
    - Areas not visible from any camera won't get textured. (Can still be UV-inpainted)
    - Aspect ratio is set by Blender's output settings."""
    bl_category = "ControlNet"
    bl_idname = "object.add_cameras"
    bl_label = "Add Cameras"
    bl_options = {'REGISTER', 'UNDO'}

    num_cameras: bpy.props.IntProperty(
        name="Number of Cameras",
        description="Number of cameras to add (including reference camera if none exists)",
        default=4,
        min=1,
        max=100
    ) # type: ignore

    center_type: bpy.props.EnumProperty(
        name="Center Type",
        description="Type of center for the cameras",
        items=[
            ('object', "Object", "Use the active object as the center"),
            ('view center', "View Center", "Use the view center as the center"),
        ],
        default='object'
    ) # type: ignore

    purge_others: bpy.props.BoolProperty(
        name="Remove Other Cameras",
        description="Delete all existing cameras except the active/reference camera before adding new ones",
        default=True
    ) # type: ignore

    _timer = None
    _last_time = 0.0
    _camera_index = 0
    _cameras = []
    _initial_camera = None
    _draw_handle = None

    def draw_callback(self, context):
        try:
            count = len(self._cameras)
            idx = self._camera_index
        except Exception:
            return
        if count == 0:
            return
        font_id = 0
        msg = f"Camera: {idx+1}/{count}  |  Press SPACE to confirm"
        region = context.region
        rw, rh = region.width, region.height
        text_width, text_height = blf.dimensions(font_id, msg)
        x = (rw - text_width) / 2
        y = rh * 0.10
        blf.position(font_id, x, y, 0)
        blf.size(20, 72)
        blf.draw(font_id, msg)

    def execute(self, context):
        # delete other cameras if requested
        if self.purge_others:
            scene = context.scene
            # gather all camera objects except the active/reference
            to_remove = [obj for obj in bpy.data.objects if obj.type == 'CAMERA' and obj != scene.camera]
            for cam in to_remove:
                # unlink from all collections
                for col in list(cam.users_collection):
                    col.objects.unlink(cam)
                # remove the object
                bpy.data.objects.remove(cam, do_unlink=True)
            # also purge unused camera data
            for cam_data in list(bpy.data.cameras):
                if not cam_data.users:
                    bpy.data.cameras.remove(cam_data)

        if self.center_type == 'object':
            obj = context.object
            if not obj:
                self.report({'WARNING'}, "No active object found. Using view center instead.")
                self.center_type = 'view center'

        # add draw handler
        if AddCameras._draw_handle is None:
            AddCameras._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback, (context,), 'WINDOW', 'POST_PIXEL')

        # determine center location
        if self.center_type == 'object':
            obj = context.object
            cursor_loc = context.scene.cursor.location.copy()
            context.scene.cursor.location = obj.location.copy()
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
            center_location = obj.location.copy()
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = cursor_loc
            center_location = obj.matrix_world.translation + obj.matrix_world.to_3x3() @ (center_location - obj.matrix_world.translation)
        else:
            center_location = context.region_data.view_location.copy()

        # set or create reference camera
        self._initial_camera = context.scene.camera
        using_viewport_ref = False
        if not self._initial_camera:
            rv3d = context.region_data
            cam_data = bpy.data.cameras.new(name='Camera_0')
            cam_obj = bpy.data.objects.new('Camera_0', cam_data)
            context.collection.objects.link(cam_obj)
            cam_obj.matrix_world = rv3d.view_matrix.inverted()
            context.scene.camera = cam_obj
            self._initial_camera = cam_obj
            using_viewport_ref = True

        # capture transform & settings
        ref_mat = self._initial_camera.matrix_world.copy()
        initial_pos = self._initial_camera.location.copy()
        cam_settings = self._initial_camera.data

        # how many around circle
        total = self.num_cameras
        count = total - 1 if using_viewport_ref else total

        # compute circle
        radius = (initial_pos - center_location).length
        angle_initial = math.atan2(initial_pos.y - center_location.y, initial_pos.x - center_location.x)
        angle_step = 2 * math.pi / (count + 1)

        self._cameras.clear()
        self._cameras.append(self._initial_camera)
        self._camera_index = 0

        for i in range(count):
            angle = (i + 1) * angle_step + angle_initial
            cam_data_new = bpy.data.cameras.new(name=f'Camera_{i+1}')
            cam_obj_new = bpy.data.objects.new(f'Camera_{i+1}', cam_data_new)
            context.collection.objects.link(cam_obj_new)
            if using_viewport_ref:
                delta = (i + 1) * angle_step
                T1 = Matrix.Translation(-center_location)
                Rz = Matrix.Rotation(delta, 4, 'Z')
                T2 = Matrix.Translation(center_location)
                cam_obj_new.matrix_world = T2 @ Rz @ T1 @ ref_mat
            else:
                x = center_location.x + radius * math.cos(angle)
                y = center_location.y + radius * math.sin(angle)
                z = initial_pos.z
                cam_obj_new.location = (x, y, z)
                direction = center_location - cam_obj_new.location
                rot = direction.to_track_quat('-Z', 'Y')
                cam_obj_new.rotation_euler = rot.to_euler()
            # copy settings
            cam_obj_new.data.type = cam_settings.type
            cam_obj_new.data.lens = cam_settings.lens
            cam_obj_new.data.sensor_width = cam_settings.sensor_width
            cam_obj_new.data.sensor_height = cam_settings.sensor_height
            cam_obj_new.data.clip_start = cam_settings.clip_start
            cam_obj_new.data.clip_end = cam_settings.clip_end
            self._cameras.append(cam_obj_new)

        # frame camera in viewport
        rv3d = context.region_data
        context.scene.camera = self._cameras[0]
        if rv3d.view_perspective != 'CAMERA':
            bpy.ops.view3d.view_camera()
        bpy.ops.view3d.view_center_camera()
        try:
            rv3d.view_camera_zoom = 1.0
        except Exception:
            pass

        # start fly nav
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        self._last_time = time.time()
        bpy.ops.view3d.fly('INVOKE_DEFAULT')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if time.time() - self._last_time < 0.2:
                return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            fly_running = any(op.bl_idname == 'VIEW3D_OT_fly'
                              for w in context.window_manager.windows
                              for op in w.modal_operators)
            if not fly_running:
                self._camera_index += 1
                if self._camera_index >= len(self._cameras):
                    context.window_manager.event_timer_remove(self._timer)
                    if AddCameras._draw_handle:
                        bpy.types.SpaceView3D.draw_handler_remove(AddCameras._draw_handle, 'WINDOW')
                        AddCameras._draw_handle = None
                    context.scene.camera = self._initial_camera
                    self.report({'INFO'}, "Cameras added successfully.")
                    return {'FINISHED'}
                context.scene.camera = self._cameras[self._camera_index]
                self._last_time = time.time()
                bpy.ops.view3d.fly('INVOKE_DEFAULT')
            return {'PASS_THROUGH'}

        return {'PASS_THROUGH'}

    @classmethod
    def poll(cls, context):
        # Check for any running modal operator
        operator = None
        for window in context.window_manager.windows:
                for op in window.modal_operators:
                    if op.bl_idname == 'OBJECT_OT_test_stable' or op.bl_idname == 'OBJECT_OT_collect_camera_prompts' or op.bl_idname == 'OBJECT_OT_bake_textures' or op.bl_idname == 'OBJECT_OT_add_cameras':
                        operator = op
                        break
                if operator:
                    break
        if operator:
            return False
        return not any(op.bl_idname == cls.bl_idname
                       for w in context.window_manager.windows
                       for op in w.modal_operators)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


    
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
        
# Define the PropertyGroup to store camera prompts
class CameraPromptItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Camera Name",
        description="Name of the camera object"
    ) # type: ignore
    prompt: bpy.props.StringProperty(
        name="View Description",
        description="Description of the view from this camera"
    ) # type: ignore

class CollectCameraPrompts(bpy.types.Operator):
    """Cycles through cameras and prompts for a viewpoint description for each. This can help when specific perspectives fail to generate correctly.
    
    - These prompts will be appended before the main prompt for each camera generation.
    - Applicable for separate, sequential and refine (also within grid mode) modes.
    - Examples: 'front view', 'close-up on face', 'from above'."""
    bl_idname = "object.collect_camera_prompts"
    bl_label = "Collect Camera View Prompts"
    bl_options = {'REGISTER', 'UNDO'}

    camera_prompt: bpy.props.StringProperty(
        name="View Description",
        description="Describe the view from this camera (e.g., 'front view', 'close-up on face', 'from above')",
        default=""
    ) # type: ignore

    # Internal state
    _cameras: list = []
    _camera_index: int = 0

    @classmethod
    def poll(cls, context):
        # Check for any running modal operator
        operator = None
        for window in context.window_manager.windows:
                for op in window.modal_operators:
                    if op.bl_idname == 'OBJECT_OT_test_stable' or op.bl_idname == 'OBJECT_OT_add_cameras' or op.bl_idname == 'OBJECT_OT_bake_textures' or op.bl_idname == 'OBJECT_OT_collect_camera_prompts':
                        operator = op
                        break
                if operator:
                    break
        if operator:
            return False
        return any(obj.type == 'CAMERA' for obj in context.scene.objects)

    def invoke(self, context, event):
        # Get all camera objects and sort them by name
        self._cameras = sorted([obj for obj in context.scene.objects if obj.type == 'CAMERA'], key=lambda x: x.name)

        if not self._cameras:
            self.report({'ERROR'}, "No cameras found in the scene.")
            return {'CANCELLED'}

        # Initialize state
        self._camera_index = 0

        # Set the first camera and pre-fill prompt if exists
        current_cam = self._cameras[self._camera_index]

        # Find existing prompt or set default
        existing_item = next((item for item in context.scene.camera_prompts if item.name == current_cam.name), None)
        self.camera_prompt = existing_item.prompt if existing_item else ""

        context.scene.camera = current_cam
        switch_viewport_to_camera(context, current_cam) # Switch viewport
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        if self._camera_index < len(self._cameras):
            layout.label(text=f"Camera: {self._cameras[self._camera_index].name} ({self._camera_index + 1}/{len(self._cameras)})")
            layout.prop(self, "camera_prompt")

    def execute(self, context):
        cam_name = self._cameras[self._camera_index].name

        # Find existing item or add a new one
        prompt_item = next((item for item in context.scene.camera_prompts if item.name == cam_name), None)
        if not prompt_item:
            prompt_item = context.scene.camera_prompts.add()
            prompt_item.name = cam_name

        prompt_item.prompt = self.camera_prompt.strip() # Store trimmed prompt

        self._camera_index += 1
        if self._camera_index < len(self._cameras):
            next_cam = self._cameras[self._camera_index]
            # Pre-fill next prompt
            existing_item = next((item for item in context.scene.camera_prompts if item.name == next_cam.name), None)
            self.camera_prompt = existing_item.prompt if existing_item else ""
            # Ensure scene camera is set for next dialog and switch view
            context.scene.camera = next_cam
            switch_viewport_to_camera(context, next_cam) # Switch viewport
            return context.window_manager.invoke_props_dialog(self, width=400) # Show next dialog
        else:
            self.report({'INFO'}, f"Collected prompts for {len(self._cameras)} cameras.")
            return {'FINISHED'}
    

class SwitchMaterial(bpy.types.Operator):
    """Switches the material of all objects to a desired index."""

    bl_idname = "object.switch_material"
    bl_label = "Switch Material"
    bl_options = {'REGISTER', 'UNDO'}

    material_index: bpy.props.IntProperty(
        name="Material Index",
        description="Index of the material to switch to",
        default=0,
        min=0
    ) # type: ignore

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        """     
        Executes the operator.         
        :param context: Blender context.         
        :return: {'FINISHED'}     
        """
        # Select all objects
        bpy.ops.object.select_all(action='SELECT')
        

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if self.material_index < len(obj.data.materials):
                obj.active_material_index = self.material_index
                # Store original materials
                original_materials = list(obj.data.materials)
                # Store the material to be set as active
                to_be_active_material = obj.active_material
                # Clear materials and assign the material at the specified index
                obj.data.materials.clear()
                obj.data.materials.append(to_be_active_material)
                # Restore original materials
                for mat in original_materials:
                    if mat != to_be_active_material:
                        obj.data.materials.append(mat)
                
        # Deselct all objects
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}
    
def prepare_baking(context):
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.use_osl = True
    bpy.context.scene.cycles.device = 'CPU'

    # Set bake type to diffuse and contributions to color only
    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    bpy.context.scene.render.bake.view_from = 'ABOVE_SURFACE'

    # Set steps to 1 for faster baking
    bpy.context.scene.cycles.samples = 1

def unwrap(obj, method, overlap_only):
        """     
        Unwraps the UVs of the given object using the selected method.         
        :param obj: Blender object.         
        :return: None     
        """
        if method == 'none':
            return
        
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        # Set object as active and select it
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        is_new = False

        # If all UN maps are ProjectionUV, add new one
        if all(["ProjectionUV" in uv.name for uv in obj.data.uv_layers]):
            # Add a new UV map
            obj.data.uv_layers.new(name=f"BakeUV")
            is_new = True
            obj.data.uv_layers.active_index = len(obj.data.uv_layers) - 1
            # Set it for rendering
            obj.data.uv_layers.active = obj.data.uv_layers[-1]
        
        bpy.ops.object.mode_set(mode='EDIT')

        # Ensure UV selection sync is OFF
        bpy.context.scene.tool_settings.use_uv_select_sync = False

        if overlap_only:
            # Deselect
            bpy.ops.uv.select_all(action='DESELECT')
            # Check if the object has overlapping UVs, if not, skip unwrapping
            bpy.ops.uv.select_overlap()
            # Get a BMesh representation of the mesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            # Use the active UV layer (this is a BMUVLayer)
            uv_layer = bm.loops.layers.uv.active
            uv_layer = bm.loops.layers.uv.active
            if not uv_layer:
                bpy.ops.object.mode_set(mode='OBJECT')
                return
            
            # Check for ANY selected UV elements
            has_overlap = any(
                loop[uv_layer].select 
                for face in bm.faces 
                for loop in face.loops
            )

            if not has_overlap:
                bpy.ops.object.mode_set(mode='OBJECT')
                return

        bpy.context.scene.tool_settings.use_uv_select_sync = True
        # Select all faces
        bpy.ops.mesh.select_all(action='SELECT')
        
        if method == 'basic':
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
        elif method == 'smart':
            bpy.ops.uv.smart_project()
        elif method == 'lightmap':
            bpy.ops.uv.lightmap_pack()
        elif method == 'pack':
            bpy.ops.uv.pack_islands()

        bpy.ops.uv.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

def bake_texture(context, obj, texture_resolution, suffix = "", view_transform = 'Standard', output_dir = None):
        """     
        Bakes the texture of the given object.         
        :param context: Blender context.         
        :param obj: Blender object.         
        :return: True if successful, False otherwise. 
        """
        bpy.context.scene.display_settings.display_device = 'sRGB'
        # Backup original view transform
        original_view_transform = bpy.context.scene.view_settings.view_transform
        # Backup whether the object was enabled for rendering
        original_render = obj.hide_render
    
        bpy.context.scene.view_settings.view_transform = view_transform
        # Set the object to be rendered
        obj.hide_render = False

        # Create a new image for baking
        image_name = f"{obj.name}_baked{suffix}" 
        image = bpy.data.images.new(name=image_name, width=texture_resolution, height=texture_resolution)

        # Create a new texture node in the object's material
        if not obj.data.materials:
            # Cancel
            print("No materials found")
            return False
        else:
            # Temporarily remove all original materials
            mat = obj.active_material.copy()
            original_materials = list(obj.data.materials)
            original_active_material = obj.active_material
            obj.data.materials.clear()
            obj.data.materials.append(mat)

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.image = image
        tex_image.location = (0, 0)

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        # Set object as active and select it
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        # Set the image node as the active bake target
        nodes.active = tex_image    
        
        # Check if there is a BSDF node before the output node
        output = None
        had_bsdf = False
        for node in nodes:
            if node.type == 'OUTPUT_MATERIAL':
                output = node
                break
            
        before_output = output.inputs[0].links[0].from_node if output and output.inputs[0].is_linked else None
        if before_output and before_output.type != 'BSDF_PRINCIPLED':
            bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf_node.location = (before_output.location[0] + 200, before_output.location[1])
            # Connect the before output node to the BSDF node
            links.new(before_output.outputs[0], bsdf_node.inputs[0])
            # Connect the BSDF node to the output node
            links.new(bsdf_node.outputs[0], output.inputs[0])
            
        # Bake the texture
        bpy.ops.object.bake(type='DIFFUSE', save_mode='EXTERNAL', filepath=image.filepath, width=texture_resolution, height=texture_resolution)
       
        # Save the image if required
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if suffix == "":
            image.filepath_raw = os.path.join(output_dir, f"{obj.name}.png")
        else:
            image.filepath_raw = os.path.join(output_dir, f"{obj.name}_baked{suffix}.png")
        image.file_format = 'PNG'
        image.save()

        # Remove tex_image node
        nodes.remove(tex_image)

        # Restore original view transform
        bpy.context.scene.view_settings.view_transform = original_view_transform
        # Restore original render settings
        obj.hide_render = original_render

        # Restore original materials
        obj.data.materials.clear()
        # First append the original active material
        if original_active_material:
            obj.data.materials.append(original_active_material)
        for mat in original_materials:
            if mat != original_active_material:
                obj.data.materials.append(mat)
                
        return True

class BakeTextures(bpy.types.Operator):
    """Bakes textures using the cycles render engine.
    
    - This will convert the textures to use a UV map. The first non-projection UV map will be used. If there are none, a new one will be created.
    - Textures will be output to the "baked" directory in the output path.
    - This will make the generated textures available in the Material Preview viewport shading mode."""
    bl_idname = "object.bake_textures"
    bl_label = "Bake Textures"
    bl_options = {'REGISTER', 'UNDO'}

    texture_resolution: bpy.props.IntProperty(
        name="Texture Resolution",
        description="Resolution of the baked textures",
        default=2048,
        min=128,
        max=8192
    ) # type: ignore

    try_unwrap: bpy.props.EnumProperty(
        name="Unwrap Method",
        description="Method to unwrap UVs before baking",
        items=[
            ('none', 'None', 'Skip UV unwrapping'),
            ('basic', 'Basic Unwrap', 'Use basic angle-based unwrapping'),
            ('smart', 'Smart UV Project', 'Use Smart UV Project with default parameters'),
            ('lightmap', 'Lightmap Pack', 'Use Lightmap Pack with default parameters'),
            ('pack', 'Pack Islands', 'Use Pack Islands with default parameters')
        ],
        default='none'
    ) # type: ignore

    add_material: bpy.props.BoolProperty(
        name="Add Material",
        description="Add the baked texture as a material to the objects",
        default=True
    ) # type: ignore

    overlap_only: bpy.props.BoolProperty(
        name="Overlap Only",
        description="Only unwrap objects with overlapping UVs",
        default=False
    ) # type: ignore

    _timer = None
    _objects = []
    _current_index = 0
    _phase = 'unwrap'

    # Add properties to track progress
    _progress = 0.0
    _stage = ""
    _current_object = 0
    _total_objects = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress = 0
        self._stage = ""
        self._current_object = 0
        self._total_objects = 0

    @classmethod
    def poll(self, context):
        """     
        Checks if the operator can be executed
        :param context: Blender context.
        :return: True if the operator can be executed, False otherwise.
        """
        # Check for any running modal operator
        operator = None
        for window in context.window_manager.windows:
                for op in window.modal_operators:
                    if op.bl_idname == 'OBJECT_OT_test_stable' or op.bl_idname == 'OBJECT_OT_add_cameras' or op.bl_idname == 'OBJECT_OT_collect_camera_prompts' or op.bl_idname == 'OBJECT_OT_bake_textures':
                        operator = op
                        break
                if operator:
                    break
        if operator:
            return False
        
        addon_prefs = context.preferences.addons[__package__].preferences
        if not os.path.exists(addon_prefs.output_dir):
            return False
        
        # Check if there are any textures to bake
        return True

    def invoke(self, context, event):
        """     
        Invokes the operator.         
        :param context: Blender context.         
        :param event: Blender event.         
        :return: {'RUNNING_MODAL'}     
        """
        if context.scene.texture_objects == 'all':
            self._objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
        else: # 'selected'
            self._objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        self._current_index = 0
        self._phase = 'unwrap'
        self._total_objects = len(self._objects)
        self._stage = "Preparing"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        """     
        Executes the operator.         
        :param context: Blender context.         
        :return: {'RUNNING_MODAL'}     
        """

        self.original_engine = bpy.context.scene.render.engine
        self.original_shading = bpy.context.space_data.shading.type
        # Set render engine to CYCLES
        bpy.context.scene.render.engine = 'CYCLES'
        # Set viewport shading to "MATERIAL_PREVIEW"
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        break
        prepare_baking(context)

        # Start modal operation
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """     
        Handles modal events.         
        :param context: Blender context.         
        :param event: Blender event.         
        :return: {'PASS_THROUGH'}     
        """
        if event.type == 'TIMER':
            def redraw():
                for area in context.screen.areas:
                    area.tag_redraw()
            redraw()

            if self._current_index < len(self._objects):
                obj = self._objects[self._current_index]
                if self._phase == 'unwrap':
                    self._stage = f"Unwrapping {obj.name}"
                    self._progress = 0
                    redraw()
                    unwrap(obj, self.try_unwrap, self.overlap_only)
                    self._progress = 100
                elif self._phase == 'bake':
                    self._stage = f"Baking {obj.name}"
                    self._progress = 0
                    redraw()
                    if not bake_texture(context, obj, self.texture_resolution, output_dir=get_dir_path(context, "baked")):
                        self.report({'ERROR'}, f"Failed to bake texture for {obj.name}. No materials found.")
                        context.window_manager.event_timer_remove(self._timer)
                        return {'CANCELLED'}
                    self._progress = 100
                elif self._phase == 'apply_material' and self.add_material:
                    self._stage = f"Applying Material to {obj.name}"
                    self._progress = 0
                    redraw()
                    self.add_baked_material(context, obj)
                    self._progress = 100
                self._current_index += 1
                if self._current_index < len(self._objects):
                    self._current_object = self._current_index
            else:
                if self._phase == 'unwrap':
                    self.report({'INFO'}, "Baking textures...")
                    self._phase = 'bake'
                    self._current_index = 0
                elif self._phase == 'bake':
                    self.report({'INFO'}, "Applying materials...")
                    self._phase = 'apply_material'
                    self._current_index = 0
                else:
                    context.window_manager.event_timer_remove(self._timer)
                    bpy.context.scene.render.engine = self.original_engine
                    # Restore original shading type
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    space.shading.type = self.original_shading
                                    break
                    self.report({'INFO'}, "Textures baked successfully.")
                    remove_empty_dirs(context)
                    return {'FINISHED'}
        return {'PASS_THROUGH'}

    def add_baked_material(self, context, obj):
        mat = bpy.data.materials.new(name=f"{obj.name}_baked")
        obj.data.materials.append(mat)

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        # Remove all existing nodes
        for node in nodes:
            nodes.remove(node)

        # Switch the active material to the new material (Switch to edit mode, select all, assign the material)
        obj.active_material_index = len(obj.material_slots) - 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.material_slot_assign()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Add output node
        output_node = nodes.new("ShaderNodeOutputMaterial")
        output_node.location = (600, 0)

        # Add principled shader node
        principled_node = nodes.new("ShaderNodeBsdfPrincipled")
        principled_node.location = (400, 0)
        principled_node.inputs["Roughness"].default_value = 1.0


        # Add uv map node
        uv_map_node = nodes.new("ShaderNodeUVMap")
        # If there is "BakeUV" uv map, use it
        if "BakeUV" in [uv.name for uv in obj.data.uv_layers]:
            uv_map_node.uv_map = "BakeUV"
        else:
            uv_map_node.uv_map = obj.data.uv_layers[0].name
        uv_map_node.location = (-200, 0)

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Add image texture node
        tex_image = nodes.new("ShaderNodeTexImage")
        # Load the saved image
        tex_image.image = bpy.data.images.load(get_file_path(context, "baked", object_name=obj.name))
        tex_image.location = (0, 0)

        # Connect nodes
        links.new(uv_map_node.outputs["UV"], tex_image.inputs["Vector"])
   
        if context.scene.apply_bsdf:
            links.new(tex_image.outputs["Color"], principled_node.inputs["Base Color"])
            links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])
        else:
            links.new(tex_image.outputs["Color"], output_node.inputs["Surface"])
        
    
class ExportOrbitGIF(bpy.types.Operator):
    """Exports a GIF and MP4 animation orbiting the active object"""
    bl_idname = "object.export_orbit_gif"
    bl_label = "Export Orbit GIF/MP4"
    bl_options = {'REGISTER', 'UNDO'}

    duration: bpy.props.FloatProperty(
        name="Duration (seconds)",
        description="Duration of the 360-degree orbit",
        default=5.0,
        min=0.1,
        max=60.0
    ) # type: ignore

    frame_rate: bpy.props.IntProperty(
        name="Frame Rate (fps)",
        description="Frames per second for the animation",
        default=24,
        min=1,
        max=60
    ) # type: ignore

    resolution_percentage: bpy.props.IntProperty(
        name="Resolution %",
        description="Percentage of the scene's render resolution to use",
        default=50,
        min=10,
        max=100,
        subtype='PERCENTAGE'
    ) # type: ignore

    samples: bpy.props.IntProperty(
        name="Samples",
        description="Number of render samples per frame",
        default=32,
        min=1,
        max=4096
    ) # type: ignore
    
    engine: bpy.props.EnumProperty(
        name="Render Engine",
        description="Render engine to use",
        items=[
            ('BLENDER_WORKBENCH', "Workbench", "Use Workbench render engine"),
            ('BLENDER_EEVEE_NEXT', "Eevee", "Use Eevee render engine"),
            ('CYCLES', "Cycles", "Use Cycles render engine")
        ],
        default='CYCLES'
    ) # type: ignore

    _timer = None
    _rendering = False
    _cancelled = False # Added flag to track cancellation
    _handle_complete = None
    _handle_cancel = None
    _initial_settings = {}
    _temp_empty = None # Added for the pivot empty
    _output_path = "" # Internal variable to store the final GIF path
    _output_path_mp4 = "" # Internal variable to store the final MP4 path
    _temp_dir = "" # Temporary directory for frames
    _frame_paths = [] # List to store paths of rendered frames
    _original_camera_parent = None # Store original camera parent
    _original_camera_matrix = None # Store original camera matrix

    @classmethod
    def poll(cls, context):
        # Check if imageio is available
        try:
            import imageio
            # Optionally check for ffmpeg plugin if strict MP4 support is needed
            # This basic check is usually sufficient as imageio tries to find ffmpeg
        except ImportError:
            return False
        # Check for active object (Mesh or Empty) and active camera
        return context.active_object is not None and context.active_object.type in {'MESH', 'EMPTY'} and context.scene.camera is not None

    def invoke(self, context, event):
        # Check dependency again in invoke to provide feedback
        try:
            import imageio
            # Check if ffmpeg is likely available for MP4 export
            if not imageio.plugins.ffmpeg.is_available():
                 self.report({'WARNING'}, "FFmpeg plugin for imageio not found. MP4 export might fail. Install 'imageio-ffmpeg'.")
        except ImportError:
            self.report({'ERROR'}, "Python module 'imageio' not found. Please install it (e.g., 'pip install imageio imageio-ffmpeg').")
            return {'CANCELLED'}
        except Exception as e:
             self.report({'WARNING'}, f"Could not check imageio ffmpeg availability: {e}. MP4 export might fail.")


        # Check for active camera
        if not context.scene.camera:
            self.report({'ERROR'}, "No active camera found in the scene.")
            return {'CANCELLED'}

        # Determine output paths using get_dir_path
        try:
            revision_dir = get_dir_path(context, "revision")
            os.makedirs(revision_dir, exist_ok=True)
            self._output_path = os.path.join(revision_dir, "orbit.gif")
            self._output_path_mp4 = os.path.join(revision_dir, "orbit.mp4") # MP4 path
        except Exception as e:
            self.report({'ERROR'}, f"Could not determine output directory: {e}")
            return {'CANCELLED'}

        # Create temporary directory for frames
        try:
            self._temp_dir = tempfile.mkdtemp(prefix="blender_gif_")
        except Exception as e:
            self.report({'ERROR'}, f"Could not create temporary directory: {e}")
            self.cleanup(context) # Clean up if temp dir fails
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self)

    def setup_animation(self, context):
        obj = context.active_object
        scene = context.scene
        active_camera = scene.camera # Use the scene's active camera

        if not active_camera: # Should be caught by poll/invoke, but double-check
             raise RuntimeError("No active camera found during setup.")

        # Store original camera state
        self._original_camera_parent = active_camera.parent
        self._original_camera_matrix = active_camera.matrix_world.copy()

        # Calculate Center (Center of Mass or Bounds)
        cursor_location = scene.cursor.location.copy()
        # Use object bounds center for better visual centering
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = obj
        obj.select_set(True)
        # Use geometry center for pivot, less prone to being skewed by outliers than bounds
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
        center_location = obj.matrix_world.translation.copy()
        # Restore cursor location (origin setting might change cursor)
        scene.cursor.location = cursor_location

        # Create Temporary Empty at Center
        self._temp_empty = bpy.data.objects.new("OrbitPivot", None)
        self._temp_empty.location = center_location
        scene.collection.objects.link(self._temp_empty)
        # Update matrices after linking and setting location
        context.view_layer.update()

        # Calculate camera's local transform relative to the empty *before* parenting
        cam_original_world_matrix = self._original_camera_matrix.copy()
        empty_world_matrix_inv = self._temp_empty.matrix_world.inverted()
        cam_local_matrix = empty_world_matrix_inv @ cam_original_world_matrix

        # Parent Active Camera to Empty
        active_camera.parent = self._temp_empty
        # Set the camera's local transform (matrix_basis)
        active_camera.matrix_basis = cam_local_matrix

        # Set Up Animation Timing
        total_frames = int(self.duration * self.frame_rate)
        scene.frame_start = 1
        scene.frame_end = total_frames
        scene.render.fps = self.frame_rate

        # Animate Empty's Rotation
        self._temp_empty.rotation_euler = (0, 0, 0)
        self._temp_empty.keyframe_insert(data_path="rotation_euler", index=2, frame=1) # Keyframe Z rotation at frame 1

        self._temp_empty.rotation_euler = (0, 0, math.radians(360))
        # Keyframe Z rotation at end frame + 1 for full circle and correct interpolation
        self._temp_empty.keyframe_insert(data_path="rotation_euler", index=2, frame=total_frames + 1)

        # Set Interpolation to Linear for smooth rotation
        if self._temp_empty.animation_data and self._temp_empty.animation_data.action:
            for fcurve in self._temp_empty.animation_data.action.fcurves:
                if fcurve.data_path == "rotation_euler" and fcurve.array_index == 2: # Z rotation
                    for kf_point in fcurve.keyframe_points:
                        kf_point.interpolation = 'LINEAR'
                    # Ensure extrapolation is also linear if needed (usually default)
                    fcurve.extrapolation = 'LINEAR'


    def execute(self, context):
        scene = context.scene
        render = scene.render
        cycles = scene.cycles # Get cycles settings

        # Store Initial Settings
        self._initial_settings = {
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'fps': render.fps,
            'camera': scene.camera, # Store the camera object itself
            'filepath': render.filepath,
            'file_format': render.image_settings.file_format,
            'color_mode': render.image_settings.color_mode,
            'resolution_percentage': render.resolution_percentage,
            'use_overwrite': render.use_overwrite,
            'use_placeholder': render.use_placeholder,
            'samples': cycles.samples, # Store original samples
            'engine': scene.render.engine, # Store original engine
            'film_transparent': render.film_transparent, # Store original film transparency
            'light': scene.display.shading.light, # Store original shading light
            'color_type': scene.display.shading.color_type # Store original shading color type
        }

        scene.render.engine = self.engine # Use selected engine
        
        if scene.render.engine == 'BLENDER_WORKBENCH':
            context.scene.display.shading.light = 'STUDIO'
            context.scene.display.shading.color_type = 'SINGLE'

        # Apply Render Settings for PNG sequence
        render.filepath = os.path.join(self._temp_dir, "frame_") # Base path for frames
        render.image_settings.file_format = 'PNG' # Render as PNG sequence
        render.image_settings.color_mode = 'RGBA' # Use RGBA (needed for potential alpha, even if we make background opaque)
        render.resolution_percentage = self.resolution_percentage
        render.use_overwrite = True
        render.use_placeholder = False
        render.film_transparent = True 
        cycles.samples = self.samples # Set samples for rendering

        # Setup Animation
        try:
            self.setup_animation(context)
        except Exception as e:
            # Clean up partially created objects if setup fails
            self.cleanup(context)
            self.report({'ERROR'}, f"Animation setup failed: {e}")
            # Print traceback for debugging
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        # Start Rendering
        self._rendering = True
        self._cancelled = False # Reset cancellation flag
        self._frame_paths.clear() # Clear list for new render
        self._handle_complete = bpy.app.handlers.render_complete.append(self.render_complete_handler)
        self._handle_cancel = bpy.app.handlers.render_cancel.append(self.render_cancel_handler)
        # Add handler for each rendered frame to collect paths
        bpy.app.handlers.render_post.append(self.render_post_handler)


        # Use timer to check render status without blocking UI completely
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)

        # Start the render process
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

        self.report({'INFO'}, f"Rendering frames to temporary directory...")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if not self._rendering:
                # Render finished or cancelled
                context.window_manager.event_timer_remove(self._timer)

                files_created = False
                # Check if frames exist AND it wasn't cancelled before trying to create files
                if self._frame_paths and not self._cancelled:
                    files_created = self.create_output_files() # Call create_output_files

                # Perform cleanup regardless
                self.cleanup(context)

                # Check for error AFTER cleanup, using the cancellation flag
                if not files_created and not self._cancelled: # Use self._cancelled flag
                     self.report({'ERROR'}, "No frames rendered or collected, or output file creation failed.")
                elif files_created: # Report success only if files were made
                     self.report({'INFO'}, f"GIF saved to {self._output_path}, MP4 saved to {self._output_path_mp4}")


                return {'FINISHED'}
        # Allow render window events to pass through
        return {'PASS_THROUGH'}


    def cleanup(self, context):
        # Remove handlers first to prevent them running during cleanup
        if self._handle_complete in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self._handle_complete)
        if self._handle_cancel in bpy.app.handlers.render_cancel:
            bpy.app.handlers.render_cancel.remove(self._handle_cancel)
        if self.render_post_handler in bpy.app.handlers.render_post:
             bpy.app.handlers.render_post.remove(self.render_post_handler)
        self._handle_complete = None
        self._handle_cancel = None

        # Restore initial settings
        scene = context.scene
        render = scene.render
        cycles = scene.cycles # Get cycles settings
        original_camera = self._initial_settings.get('camera')

        # Restore camera parent and transform BEFORE restoring scene.camera setting
        if original_camera and original_camera.name in bpy.data.objects:
            try:
                # Check if it's still parented to the temp empty before unparenting
                if original_camera.parent == self._temp_empty:
                    original_camera.parent = self._original_camera_parent
                    # Restore world matrix after unparenting
                    original_camera.matrix_world = self._original_camera_matrix
                else:
                    # If parent changed unexpectedly, just restore matrix
                    print("Warning: Camera parent changed during render, restoring world matrix only.")
                    original_camera.matrix_world = self._original_camera_matrix
                # Clear potentially stale parent inverse matrix
                original_camera.matrix_parent_inverse.identity()

            except Exception as e:
                print(f"Warning: Could not restore camera state for '{original_camera.name}': {e}")

        # Restore other settings
        for key, value in self._initial_settings.items():
            if key == 'camera':
                 # Restore the scene's active camera object if it exists
                 if value and value.name in bpy.data.objects:
                      scene.camera = value
                 continue # Already handled transform/parent above
            try:
                # Handle nested properties correctly
                if key == 'file_format':
                    setattr(render.image_settings, 'file_format', value)
                elif key == 'color_mode':
                    setattr(render.image_settings, 'color_mode', value)
                elif key == 'samples': # Restore samples
                    setattr(cycles, key, value)
                elif key == 'engine': # Restore engine
                    setattr(render, key, value)
                elif key == 'film_transparent': # Restore film transparency
                    setattr(render, key, value)
                elif hasattr(render, key):
                    setattr(render, key, value)
                elif hasattr(scene, key):
                    setattr(scene, key, value)
            except Exception as e:
                print(f"Warning: Could not restore setting '{key}': {e}")

        self._initial_settings = {} # Clear stored settings
        self._original_camera_parent = None
        self._original_camera_matrix = None

        # Remove temporary empty
        if self._temp_empty:
            # Remove animation data
            if self._temp_empty.animation_data and self._temp_empty.animation_data.action:
                action = self._temp_empty.animation_data.action
                # Check if action exists before removing
                if action and action.name in bpy.data.actions:
                     bpy.data.actions.remove(action)
            # Unlink and remove object
            if self._temp_empty.name in context.scene.collection.objects:
                context.scene.collection.objects.unlink(self._temp_empty)
            if self._temp_empty.name in bpy.data.objects:
                bpy.data.objects.remove(self._temp_empty, do_unlink=True)
            self._temp_empty = None


        self._rendering = False # Ensure rendering flag is reset
        self._cancelled = False # Reset cancellation flag

        # Clean up temporary directory if it exists
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                print(f"Removed temporary directory: {self._temp_dir}")
            except Exception as e:
                print(f"Warning: Could not remove temporary directory '{self._temp_dir}': {e}")
        self._temp_dir = ""
        self._frame_paths.clear() # Clear frame paths


    def render_post_handler(self, scene, _):
        """Called after each frame is rendered."""
        if self._rendering and self._temp_dir: # Check temp_dir exists
            frame_num = scene.frame_current
            # Construct the expected filename based on Blender's padding
            filename = f"frame_{frame_num:04d}.png"
            filepath = os.path.join(self._temp_dir, filename)
            if os.path.exists(filepath):
                self._frame_paths.append(filepath)
            else:
                # Check if render path uses frame number suffix differently
                # Use scene.render.frame_path() which respects output settings
                alt_filepath = scene.render.frame_path(frame=frame_num)
                if os.path.exists(alt_filepath):
                     self._frame_paths.append(alt_filepath)
                     # print(f"Used alternative frame path: {alt_filepath}") # Less verbose
                else:
                     print(f"Warning: Frame file not found after render: {filepath} or {alt_filepath}")


    def render_complete_handler(self, scene, _):
        try:
            # Only respond if we're still in the rendering phase
            if not getattr(self, "_rendering", False):
                return

            print("Frame rendering complete.")
            # Signal that rendering is done so modal can wrap up
            self._rendering = False

            # Unregister this handler so it won't fire after operator finishes
            # Check if handler exists before removing
            if hasattr(self, 'render_complete_handler') and self.render_complete_handler in bpy.app.handlers.render_complete:
                try:
                    bpy.app.handlers.render_complete.remove(self.render_complete_handler)
                except ValueError:
                    pass # Ignore if already removed elsewhere
        except ReferenceError:
            # RNA is gone ignore
            pass
        except Exception as e:
             print(f"Error in render_complete_handler: {e}") # Log other potential errors


    def render_cancel_handler(self, scene, _):
        if self._rendering: # Check if it was our render job that was cancelled
            self.report({'WARNING'}, "Render cancelled by user.")
            self._cancelled = True # Set the cancellation flag
            self._rendering = False # Signal modal loop to finish and cleanup
            # Unregister this handler
            if hasattr(self, 'render_cancel_handler') and self.render_cancel_handler in bpy.app.handlers.render_cancel:
                 try:
                      bpy.app.handlers.render_cancel.remove(self.render_cancel_handler)
                 except ValueError:
                      pass # Ignore if already removed


    def create_output_files(self):
        """Creates the GIF and MP4 from the rendered frames using imageio. Returns True on success, False otherwise."""
        if not self._frame_paths:
            # Error is reported in modal loop if needed
            return False

        print(f"Assembling output files from {len(self._frame_paths)} frames...")
        gif_success = False
        mp4_success = False

        try:
            # Sort frames numerically just in case paths weren't added perfectly in order
            self._frame_paths.sort()

            images = []
            for filename in self._frame_paths:
                try:
                    images.append(imageio.imread(filename))
                except FileNotFoundError:
                    print(f"Warning: Frame file disappeared before processing: {filename}")
                    continue # Skip missing frame

            if not images: # Check if any images were actually loaded
                 self.report({'ERROR'}, "No valid frame images found to create output files.")
                 return False

            # Calculate duration per frame for imageio (in seconds)
            frame_duration = 1.0 / self.frame_rate

            # --- Create GIF ---
            print(f"Creating GIF: {self._output_path}")
            try:
                 # imageio v3+ uses 'duration' in seconds per frame
                 imageio.mimsave(self._output_path, images, fps=self.frame_rate, loop=0, disposal=2) # loop=0 means infinite loop
                 print(f"GIF saved successfully.")
                 gif_success = True
            except TypeError:
                      # Fallback if 'duration' is not accepted 
                      imageio.mimsave(self._output_path, images, duration=frame_duration, loop=0)
                      print(f"GIF saved successfully (fallback duration).")
                      gif_success = True
            except Exception as e:
                 self.report({'ERROR'}, f"Failed to create GIF: {e}")
                 # Print traceback for debugging GIF errors
                 import traceback
                 traceback.print_exc()

            # --- Create MP4 ---
            print(f"Creating MP4: {self._output_path_mp4}")
            try:
                imageio.mimsave(self._output_path_mp4, images, format='mp4', fps=self.frame_rate, quality=8)
                print(f"MP4 saved successfully.")
                mp4_success = True
            except ImportError:
                 self.report({'ERROR'}, "Python module 'imageio' or its 'ffmpeg' plugin not found/configured correctly. Cannot create MP4.")
            except Exception as e:
                 self.report({'ERROR'}, f"Failed to create MP4: {e}")
                 # Print traceback for debugging MP4 errors
                 import traceback
                 traceback.print_exc()


            return gif_success and mp4_success # Return True only if both succeed

        except ImportError:
            # This top-level catch handles if imageio itself wasn't imported initially
            self.report({'ERROR'}, "Python module 'imageio' not found. Cannot create output files.")
            return False
        except Exception as e:
            # Catch other potential errors during image loading or sorting
            self.report({'ERROR'}, f"Failed during output file creation process: {e}")
            import traceback
            traceback.print_exc()
            return False