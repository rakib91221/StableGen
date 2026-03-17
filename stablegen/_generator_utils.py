"""Shared utilities for generation operators (ComfyUIGenerate, Trellis2Generate)."""

import os
import bpy  # pylint: disable=import-error
import mathutils  # pylint: disable=import-error
import json
import math
import traceback
import requests

from .timeout_config import get_timeout

def redraw_ui(context):
    """Redraws the UI to reflect changes in the operator's progress and status."""
    for area in context.screen.areas:
        area.tag_redraw()


def setup_studio_lighting(context, scale=1.0):
    """Create a three-point studio lighting rig (key, fill, rim).

    Re-usable from any generation mode (TRELLIS.2, PBR decomposition, etc.).

    Args:
        context: Blender context.
        scale: Scene scale factor — lights are placed at ``scale * 2.5`` distance.
    """
    S = max(scale, 0.5)
    dist = S * 2.5

    light_defs = [
        ("SG_Key",  200, 1.5 * S, (1.0, 0.96, 0.90),   45, 40),
        ("SG_Fill",  80, 2.5 * S, (0.90, 0.94, 1.0),   -60, 15),
        ("SG_Rim",  120, 0.8 * S, (1.0, 1.0, 1.0),     170, 55),
    ]

    collection = context.collection
    created = []

    for name, power, size, color, az_deg, el_deg in light_defs:
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

        az = math.radians(az_deg)
        el = math.radians(el_deg)
        x = dist * math.cos(el) * math.sin(az)
        y = -dist * math.cos(el) * math.cos(az)
        z = dist * math.sin(el)

        light_data = bpy.data.lights.new(name=name, type='AREA')
        light_data.energy = power
        light_data.size = size
        light_data.color = color

        light_obj = bpy.data.objects.new(name=name, object_data=light_data)
        collection.objects.link(light_obj)

        light_obj.location = (x, y, z)
        direction = mathutils.Vector((0, 0, 0)) - mathutils.Vector((x, y, z))
        rot = direction.to_track_quat('-Z', 'Y')
        light_obj.rotation_euler = rot.to_euler()

        created.append(light_obj)

    print(f"[StableGen] Studio lighting created: {[o.name for o in created]}")
    return created


def _pbr_setup_studio_lights(context, to_texture):
    """Calculate scene scale from target objects and set up studio lights."""
    max_dim = 1.0
    for obj in to_texture:
        if hasattr(obj, 'dimensions'):
            max_dim = max(max_dim, *obj.dimensions)
    setup_studio_lighting(context, scale=max_dim)


def upload_image_to_comfyui(server_address, image_path, image_type="input"):
    """
    Uploads an image file to the ComfyUI server's /upload/image endpoint.

    Args:
        server_address (str): The address:port of the ComfyUI server (e.g., "127.0.0.1:8188").
        image_path (str): The local path to the image file to upload.
        image_type (str): The type parameter for the upload (usually "input").

    Returns:
        dict: A dictionary containing the server's response (e.g., {'name': 'filename.png', 'subfolder': '', 'type': 'input'})
              Returns None if the upload fails or file doesn't exist.
    """
    if not os.path.exists(image_path):
        # This is expected for optional files, so don't log as an error
        # print(f"Debug: Image file not found at {image_path}, cannot upload.")
        return None
    if not os.path.isfile(image_path):
        print(f"[StableGen] Error: Path exists but is not a file: {image_path}")
        return None

    upload_url = f"http://{server_address}/upload/image"
    print(f"[StableGen] Uploading {os.path.basename(image_path)} to {upload_url}...")

    try:
        with open(image_path, 'rb') as f:
            # Determine mime type based on extension
            mime_type = 'application/octet-stream' # Default fallback
            if image_path.lower().endswith('.png'):
                mime_type = 'image/png'
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif image_path.lower().endswith('.webp'):
                mime_type = 'image/webp'
            # Add other types if needed (e.g., .bmp, .gif)

            files = {'image': (os.path.basename(image_path), f, mime_type)}
            # 'overwrite': 'true' prevents errors if the same filename is uploaded again
            # useful for re-running generations with the same intermediate files.
            data = {'overwrite': 'true', 'type': image_type}

            # Increased timeout for potentially large images or slow networks
            response = requests.post(upload_url, files=files, data=data, timeout=get_timeout('transfer'))
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()
        print(f"[StableGen]   Upload successful for '{os.path.basename(image_path)}'. Server response: {response_data}")

        # Crucial Validation
        if 'name' not in response_data:
             print(f"[StableGen]   Error: ComfyUI upload response for {os.path.basename(image_path)} missing 'name'. Response: {response_data}")
             return None
        # End Validation

        return response_data # Should contain 'name', often 'subfolder', 'type'

    except requests.exceptions.Timeout:
        print(f"[StableGen]   Error: Timeout uploading image {os.path.basename(image_path)} to {upload_url}.")
    except requests.exceptions.ConnectionError:
        print(f"[StableGen]   Error: Connection failed when uploading image {os.path.basename(image_path)} to {upload_url}. Is ComfyUI running and accessible?")
    except requests.exceptions.HTTPError as e:
         print(f"[StableGen]   Error: HTTP Error {e.response.status_code} uploading image {os.path.basename(image_path)} to {upload_url}.")
         print(f"[StableGen]   Server response content: {e.response.text}") # Show response body on error
    except requests.exceptions.RequestException as e:
        print(f"[StableGen]   Error uploading image {os.path.basename(image_path)} to {upload_url}: {e}")
    except json.JSONDecodeError:
        print(f"[StableGen]   Error decoding ComfyUI response after uploading {os.path.basename(image_path)}. Response text: {response.text}")
    except Exception as e:
        print(f"[StableGen]   An unexpected error occurred during image upload of {os.path.basename(image_path)}: {e}")
        traceback.print_exc() # Print full traceback for unexpected errors

    return None