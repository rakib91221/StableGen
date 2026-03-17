"""Architecture-mode and server-address callbacks.

Property ``update=`` callbacks that react to architecture / mode changes
and the server address preference.  Extracted from the original
``__init__.py`` to keep it slim.
"""

import bpy  # pylint: disable=import-error
from urllib.parse import urlparse

from ..ui.presets import update_parameters
from . import ADDON_PKG
from .state import (
    _cached_checkpoint_list,
    _cached_lora_list,
    _run_async,
)
from .server_api import (
    check_pbr_available,
    check_server_availability,
    check_trellis2_available,
)
from ..timeout_config import get_timeout


# ── Architecture-mode helpers ──────────────────────────────────────────────

def update_architecture_mode(self, context):
    """Called when the user changes the architecture_mode dropdown."""
    scene = context.scene
    mode = scene.architecture_mode

    if mode != 'trellis2':
        if scene.model_architecture != mode:
            scene.model_architecture = mode          # triggers update_combined
    else:
        _sync_trellis2_backbone(scene)

    update_parameters(self, context)


def _sync_trellis2_backbone(scene):
    """Pick the right diffusion backbone for the current TRELLIS.2 state."""
    tex_mode = getattr(scene, 'trellis2_texture_mode', 'native')
    if tex_mode in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein'):
        target = tex_mode
    elif getattr(scene, 'trellis2_generate_from', 'image') == 'prompt':
        target = getattr(scene, 'trellis2_initial_image_arch', 'sdxl')
    else:
        return
    if scene.model_architecture != target:
        scene.model_architecture = target


def update_trellis2_texture_mode(self, context):
    """Called when the user changes the texture generation mode inside TRELLIS.2."""
    scene = context.scene
    if getattr(scene, 'architecture_mode', '') != 'trellis2':
        return

    tex_mode = scene.trellis2_texture_mode
    scene.trellis2_skip_texture = (tex_mode != 'native')

    _sync_trellis2_backbone(scene)
    update_parameters(self, context)


def update_trellis2_initial_image_arch(self, context):
    """Called when the user changes the initial-image architecture for TRELLIS.2."""
    scene = context.scene
    if getattr(scene, 'architecture_mode', '') != 'trellis2':
        return
    _sync_trellis2_backbone(scene)
    update_parameters(self, context)


def update_trellis2_generate_from(self, context):
    """Called when the user switches between Image and Prompt input mode."""
    scene = context.scene
    if getattr(scene, 'architecture_mode', '') != 'trellis2':
        return

    if scene.trellis2_generate_from == 'prompt':
        _sync_trellis2_backbone(scene)

    update_parameters(self, context)


# ── Server-address change callback ────────────────────────────────────────

def update_combined(self, context):
    """Master callback for server_address changes — pings server, refreshes models."""
    # Import lazily to avoid circular ref at module level
    from .load_handlers import load_handler

    prefs = context.preferences.addons[ADDON_PKG].preferences
    raw_address = prefs.server_address

    if raw_address:
        if not raw_address.startswith(('http://', 'https://')):
            parsed_url = urlparse(f"http://{raw_address}")
        else:
            parsed_url = urlparse(raw_address)

        clean_address = parsed_url.netloc

        if clean_address and raw_address != clean_address:
            prefs.server_address = clean_address
            return None

    server_address = prefs.server_address

    if not server_address:
        prefs.server_online = False
        # Must mutate the lists in-place to keep existing references valid
        import stablegen.core.state as _state
        _state._cached_checkpoint_list = [("NO_SERVER", "Set Server Address", "...")]
        _state._cached_lora_list = [("NO_SERVER", "Set Server Address", "...")]
        return None

    print("[StableGen] Server address changed, checking asynchronously...")

    def _bg_work():
        result = {}
        result['online'] = check_server_availability(server_address, timeout=get_timeout('ping'))
        if result['online']:
            result['trellis2'] = check_trellis2_available(server_address, timeout=get_timeout('api'))
            result['pbr'] = check_pbr_available(server_address, timeout=get_timeout('api'))
        else:
            result['trellis2'] = False
            result['pbr'] = False
        return result

    def _on_done(result):
        if result is None:
            return
        _prefs = bpy.context.preferences.addons[ADDON_PKG].preferences
        _prefs.server_online = result.get('online', False)

        if hasattr(bpy.context, 'scene') and bpy.context.scene:
            bpy.context.scene.trellis2_available = result.get('trellis2', False)
            bpy.context.scene.pbr_nodes_available = result.get('pbr', False)

        if not result.get('online', False):
            print("[StableGen] ComfyUI server is not reachable.")
            return

        update_parameters(None, bpy.context)
        load_handler(None)

        def _deferred_refresh():
            try:
                bpy.ops.stablegen.refresh_checkpoint_list('INVOKE_DEFAULT')
                bpy.ops.stablegen.refresh_lora_list('INVOKE_DEFAULT')
                bpy.ops.stablegen.refresh_controlnet_mappings('INVOKE_DEFAULT')
            except Exception as e:
                print(f"[StableGen] Error during deferred refresh: {e}")
            return None
        bpy.app.timers.register(_deferred_refresh, first_interval=0.1)

    _run_async(_bg_work, _on_done, track_generation=True)

    update_parameters(self, context)
    load_handler(None)

    return None
