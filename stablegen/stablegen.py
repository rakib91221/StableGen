""" This file contains the operators and panels for the StableGen addon """
# disable import-error because pylint doesn't recognize the blenders internal modules
import os
import sys
import bpy  # pylint: disable=import-error
import mathutils  # pylint: disable=import-error
import math  # pylint: disable=import-error
from .utils import sg_modal_active


def _is_refreshing():
    """Return True while async model-list refreshes are in-flight.

    If the counter has been stuck for longer than ``_REFRESH_TIMEOUT``
    seconds (e.g. due to a lost timer), force-reset it to 0 so the UI
    is not permanently blocked.
    """
    import time as _time
    pkg = sys.modules.get(__package__)
    count = getattr(pkg, '_pending_refreshes', 0)
    if count <= 0:
        return False
    started = getattr(pkg, '_refresh_started_at', 0.0)
    if started > 0 and (_time.monotonic() - started) > getattr(pkg, '_REFRESH_TIMEOUT', 30.0):
        # Safety net: force-clear a stuck counter
        print(f"[StableGen] Refreshing model lists stuck for >{getattr(pkg, '_REFRESH_TIMEOUT', 30.0):.0f}s – resetting.")
        pkg._pending_refreshes = 0
        pkg._refresh_started_at = 0.0
        return False
    return True

# Stock presets
PRESETS = {
    "DEFAULT": {"description": "Default settings for general purpose generation", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)),  "discard_factor": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "hm-mvgd-hm", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.15, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "MODEL IS IMPORTANT": {"description": "Same as default, but is more guided by the model", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.15, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.75, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "CHARACTERS": {"description": "Optimized settings for character generation", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.1, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "CHARACTERS (ALTERNATIVE MASKING)": {"description": "Optimized for character generation. Uses alternative masking parameters to be more consistent between images, but may produce more artifacts. Try if \"Characters\" fails.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.5, "sequential_factor_smooth": 0.3499999940395355, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 10, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "QUICK DRAFT": {"description": "Optimized for speed", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 4, "cfg": 1.0, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "grid", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.7, "sequential_factor_smooth": 0.1, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 2, "blur_mask_sigma": 1.0, "grow_mask_by": 2, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Hyper-SDXL-4steps-lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "UV INPAINTING": {"description": "Recommended UV Inpainting setup. It is recommended to bake texutures manually before running the generation to fine-tune unwrapping and avoid lag when generating.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 10, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "uv_inpaint", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "3,0,1,2", "sequential_factor": 0.6000000238418579, "sequential_factor_smooth": 0.11000001430511475, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]}, # No ControlNet for UV Inpainting by default
    "ARCHITECTURE": {"description": "Prioritizes only the most straight-on camera for each point. This means details generated on flat surfaces will not get blurred by getting generated differently from two or more viewpoints. Does not use visibility masking. Each picture will get generated as new, consistency depends on IPAdapter + geometry.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "weight_exponent": 10.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "separate", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": False, "sequential_custom_camera_order": "", "sequential_factor": 0.75, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "ipadapter_weight_type": "style", "ipadapter_strength": 0.800000011920929, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": False, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "QWEN PRECISE": {"description": "Precise detail when camera overlap is good. Relies on context renders plus the prompt, so sparse coverage can still introduce artifacts.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit","qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN SAFE": {"description": "Safer fallback when coverage is limited. Uses the previous view (recent mode) instead of context renders to keep global look coherent, at the cost of some fine-detail persistence.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 6.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN ALT": {"description": "Balanced option that mixes additional context renders with sequential references to smooth out coverage while keeping detail reasonable.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "recent", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "ADDITIONAL", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "early_priority": True, "early_priority_strength": 0.5, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},     
    "QWEN VORONOI": {"description": "Voronoi projection mode with exponent 1000 for hard camera segmentation during generation, then resets to 15 for softer blending. Each surface point is dominated by its closest camera. Based on Qwen Precise.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 1000.0, "weight_exponent_generation_only": True, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": True, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN PRECISE (NUNCHAKU)": {"description": "Precise detail using Nunchaku. Meant to be used with the Nunchaku model which has the 4-step Lightning LoRA included. Requires Nunchaku nodes.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "QWEN SAFE (NUNCHAKU)": {"description": "Safer fallback using Nunchaku. Meant to be used with the Nunchaku model which has the 4-step Lightning LoRA included. Requires Nunchaku nodes.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 6.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "QWEN ALT (NUNCHAKU)": {"description": "Balanced option using Nunchaku. Meant to be used with the Nunchaku model which has the 4-step Lightning LoRA included. Requires Nunchaku nodes.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "recent", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "ADDITIONAL", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "early_priority": True, "early_priority_strength": 0.5, "pbr_decomposition": False, "lora_units": []},
    "QWEN VORONOI (NUNCHAKU)": {"description": "Voronoi projection mode using Nunchaku. Exponent 1000 for hard camera segmentation during generation, then resets to 15 for softer blending. Requires Nunchaku nodes.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 1000.0, "weight_exponent_generation_only": True, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": True, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "KLEIN PRECISE": {"description": "FLUX.2 Klein with precise detail when camera overlap is good. Uses depth reference images with CFGGuider (cfg=1). Best for well-covered geometry.", "control_after_generate": "fixed", "model_architecture": "flux2_klein", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour.", "qwen_custom_prompt_seq_none": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour, adopting the visual style from image 2.", "qwen_custom_prompt_seq_replace": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray.", "qwen_custom_prompt_seq_additional": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray. Image 3 represents the overall style.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "KLEIN SAFE": {"description": "FLUX.2 Klein safer fallback when coverage is limited. Uses the previous view instead of context renders with depth references and CFGGuider (cfg=1).", "control_after_generate": "fixed", "model_architecture": "flux2_klein", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 6.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour.", "qwen_custom_prompt_seq_none": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour, adopting the visual style from image 2.", "qwen_custom_prompt_seq_replace": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray.", "qwen_custom_prompt_seq_additional": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray. Image 3 represents the overall style.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "KLEIN ALT": {"description": "FLUX.2 Klein balanced option that mixes additional context renders with sequential references. Uses depth references and CFGGuider (cfg=1).", "control_after_generate": "fixed", "model_architecture": "flux2_klein", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": False, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "recent", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "ADDITIONAL", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour.", "qwen_custom_prompt_seq_none": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour, adopting the visual style from image 2.", "qwen_custom_prompt_seq_replace": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray.", "qwen_custom_prompt_seq_additional": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray. Image 3 represents the overall style.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "early_priority": True, "early_priority_strength": 0.5, "pbr_decomposition": False, "lora_units": []},
    "KLEIN VORONOI": {"description": "FLUX.2 Klein voronoi projection mode. Exponent 1000 for hard camera segmentation during generation, then resets to 15 for softer blending. Uses depth references and CFGGuider (cfg=1).", "control_after_generate": "fixed", "model_architecture": "flux2_klein", "qwen_generation_method": "generate", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 1000.0, "weight_exponent_generation_only": True, "weight_exponent_after_generation": 15.0, "qwen_voronoi_mode": True, "clip_skip": 1, "auto_rescale": True, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.8, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour.", "qwen_custom_prompt_seq_none": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour, adopting the visual style from image 2.", "qwen_custom_prompt_seq_replace": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray.", "qwen_custom_prompt_seq_additional": "Reskin this into {main_prompt}{camera_suffix}, while preserve identity keep likeness replica contour. In image 2, replace all solid magenta areas with content that continues the surrounding style. Replace the background with solid gray. Image 3 represents the overall style.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "pbr_decomposition": False, "lora_units": []},
    "LOCAL REFINE": {"description": "Uses the SDXL local edit mode to improve detail / refine specific areas. Use new set of cameras or a single camera pointed at the area you want to refine.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "local_edit", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.10000000149011612, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "original_render", "sequential_desaturate_factor": 0.10000000149011612, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": True, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 5.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05, "visibility_vignette": True, "visibility_vignette_width": 0.3, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "pbr_decomposition": False, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.5, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "LOCAL EDIT (QWEN)": {"description": "Uses Qwen to make targeted edits to specific areas. Point cameras at what you want to change — you can alter colors, style, rewrite text, add details, and more. Untouched areas are preserved.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "local_edit", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": False, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": False, "refine_angle_ramp_active": False, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05, "visibility_vignette": True, "visibility_vignette_width": 0.1, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6, "refine_edge_feather_projection": True, "refine_edge_feather_width": 15, "refine_edge_feather_softness": 1.0, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "REFINE (QWEN)": {"description": "Uses Qwen to restyle or globally modify the entire existing texture. Applies changes uniformly across all camera views — ideal for changing the overall color scheme, art style, or surface appearance.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "qwen_generation_method": "refine", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 1.0, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": False, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": False, "pbr_decomposition": False, "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "DEFAULT (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and SDXL to generate a textured mesh. Optimized for general object generation. May not work ideally for the cases which have their specialized presets.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 75.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 85.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.10000000149011612, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "trellis2_input", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 5.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "sdxl", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 10, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": False, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": False, "trellis2_max_elevation": 1.2216999530792236, "trellis2_min_elevation": -1.0471975803375244, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": False, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "TRELLIS.2 (MESH ONLY)": {"description": "Uses TRELLIS.2 to generate a mesh without texturing. Useful when you only need geometry or plan to texture manually.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 75.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 85.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.10000000149011612, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "trellis2_input", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 5.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "none", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 10, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": False, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": False, "trellis2_max_elevation": 1.2216999530792236, "trellis2_min_elevation": -1.0471975803375244, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": False, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "CHARACTERS (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and SDXL to generate a textured mesh. Optimized settings for generating characters. Will not texture bottom facing faces.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 75.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 85.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.10000000149011612, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "trellis2_input", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 5.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "sdxl", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": True, "trellis2_max_elevation": 0.8726646259971648, "trellis2_min_elevation": -0.8726646259971648, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": False, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "ARCHITECTURE (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and SDXL to generate a textured mesh. Optimized settings for architecture, and other models with flat walls and sharp angles.", "control_after_generate": "fixed", "model_architecture": "sdxl", "steps": 8, "cfg": 1.5, "sampler": "dpmpp_2s_ancestral", "scheduler": "sgm_uniform", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 80.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 85.0, "weight_exponent": 10.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "separate", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": False, "sequential_custom_camera_order": "", "sequential_factor": 0.75, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": True, "sequential_ipadapter_mode": "trellis2_input", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 0.800000011920929, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": False, "blur_mask": True, "blur_mask_radius": 3, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 5.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "sdxl", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": False, "trellis2_max_elevation": 1.2216999530792236, "trellis2_min_elevation": -1.0471975803375244, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": False, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'sdxl_lightning_8step_lora.safetensors', 'model_strength': 1.0, 'clip_strength': 1.0}]},
    "QWEN PRECISE (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and Qwen Image Edit to generate a textured mesh. Precise detail when camera overlap is good. Relies on context renders plus the prompt.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "sg_silhouette_margin": 3, "sg_silhouette_depth": 0.05000000074505806, "sg_silhouette_rays": "4", "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "qwen_image_edit", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_seed": 0, "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": True, "trellis2_max_elevation": 0.8726646259971648, "trellis2_min_elevation": -0.8726646259971648, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": True, "qwen_trellis2_style_initial_only": True, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN SAFE (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and Qwen Image Edit to generate a textured mesh. Safer fallback when coverage is limited. Uses TRELLIS.2 input image as sequential style reference for global coherence.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 6.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "NONE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "sg_silhouette_margin": 3, "sg_silhouette_depth": 0.05000000074505806, "sg_silhouette_rays": "4", "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "qwen_image_edit", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_seed": 0, "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": True, "trellis2_max_elevation": 0.8726646259971648, "trellis2_min_elevation": -0.8726646259971648, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": True, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN ALT (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and Qwen Image Edit to generate a textured mesh. Uses ADDITIONAL context renders with TRELLIS.2 style transfer for consistency. Good general-purpose Qwen pipeline.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 3.0, "weight_exponent_generation_only": False, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.10000000149011612, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": True, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": False, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "ADDITIONAL", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "sg_silhouette_margin": 3, "sg_silhouette_depth": 0.05000000074505806, "sg_silhouette_rays": "4", "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "qwen_image_edit", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_seed": 0, "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": True, "trellis2_max_elevation": 0.8726646259971648, "trellis2_min_elevation": -0.8726646259971648, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": True, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
    "QWEN VORONOI (MESH + TEXTURE)": {"description": "Uses TRELLIS.2 and Qwen Image Edit to generate a textured mesh. Voronoi projection with exponent 1000 for hard camera segmentation during generation, then resets to 15 for softer blending.", "control_after_generate": "fixed", "model_architecture": "qwen_image_edit", "steps": 4, "cfg": 1.0, "sampler": "euler", "scheduler": "simple", "fallback_color": mathutils.Color((0.0, 0.0, 0.0)), "discard_factor": 70.0, "discard_factor_generation_only": True, "discard_factor_after_generation": 90.0, "weight_exponent": 1000.0, "weight_exponent_generation_only": True, "weight_exponent_after_generation": 15.0, "view_blend_use_color_match": False, "view_blend_color_match_method": "reinhard", "view_blend_color_match_strength": 1.0, "clip_skip": 1, "auto_rescale": True, "auto_rescale_target_mp": 1.0, "overwrite_material": True, "generation_method": "sequential", "refine_images": False, "refine_steps": 8, "refine_sampler": "dpmpp_2s_ancestral", "refine_scheduler": "sgm_uniform", "denoise": 0.800000011920929, "refine_cfg": 1.5, "refine_prompt": "", "refine_upscale_method": "lanczos", "sequential_smooth": True, "sequential_custom_camera_order": "", "sequential_factor": 0.699999988079071, "sequential_factor_smooth": 0.15000000596046448, "sequential_factor_smooth_2": 1.0, "sequential_ipadapter": False, "sequential_ipadapter_mode": "first", "sequential_desaturate_factor": 0.0, "sequential_contrast_factor": 0.0, "sequential_ipadapter_regenerate": False, "ipadapter_weight_type": "style", "ipadapter_strength": 1.0, "ipadapter_start": 0.0, "ipadapter_end": 1.0, "early_priority": False, "early_priority_strength": 0.5, "differential_diffusion": True, "differential_noise": True, "blur_mask": True, "blur_mask_radius": 1, "blur_mask_sigma": 1.0, "grow_mask_by": 3, "canny_threshold_low": 0, "canny_threshold_high": 80, "qwen_guidance_map_type": "depth", "qwen_voronoi_mode": True, "qwen_use_external_style_image": False, "qwen_external_style_image": "", "qwen_context_render_mode": "REPLACE_STYLE", "qwen_external_style_initial_only": False, "qwen_use_custom_prompts": False, "qwen_custom_prompt_initial": "Change the format of image 1 to '{main_prompt}'", "qwen_custom_prompt_seq_none": "Change and transfer the format of '{main_prompt}' in image 1 to the style from image 2", "qwen_custom_prompt_seq_replace": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas.", "qwen_custom_prompt_seq_additional": "Change and transfer the format of image 1 to '{main_prompt}'. Replace all solid magenta areas in image 2. Replace the background with solid gray. The style from image 2 should smoothly continue into the previously magenta areas. Image 3 represents the overall style of the object.", "qwen_guidance_fallback_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_guidance_background_color": mathutils.Color((1.0, 0.0, 1.0)), "qwen_context_cleanup": False, "qwen_context_cleanup_hue_tolerance": 0.0, "qwen_context_cleanup_value_adjust": 0.0, "qwen_context_fallback_dilation": 1, "qwen_prompt_gray_background": True, "qwen_rescale_alignment": True, "qwen_generation_method": "generate", "qwen_refine_use_prev_ref": False, "qwen_refine_use_depth": False, "qwen_timestep_zero_ref": False, "refine_angle_ramp_active": True, "refine_angle_ramp_pos_0": 0.0, "refine_angle_ramp_pos_1": 0.05000000074505806, "visibility_vignette": True, "visibility_vignette_width": 0.15000000596046448, "visibility_vignette_softness": 1.0, "visibility_vignette_blur": False, "sg_silhouette_margin": 3, "sg_silhouette_depth": 0.05000000074505806, "sg_silhouette_rays": "4", "refine_feather_ramp_pos_0": 0.0, "refine_feather_ramp_pos_1": 0.6000000238418579, "refine_edge_feather_projection": True, "refine_edge_feather_width": 30, "refine_edge_feather_softness": 1.0, "trellis2_texture_mode": "qwen_image_edit", "trellis2_initial_image_arch": "sdxl", "trellis2_camera_count": 8, "trellis2_placement_mode": "normal_weighted", "trellis2_auto_prompts": True, "trellis2_exclude_bottom": True, "trellis2_exclude_bottom_angle": 1.5533000230789185, "trellis2_auto_aspect": "per_camera", "trellis2_occlusion_mode": "none", "trellis2_consider_existing": False, "trellis2_delete_cameras": False, "trellis2_coverage_target": 0.949999988079071, "trellis2_max_auto_cameras": 12, "trellis2_fan_angle": 90.0, "trellis2_resolution": "1024_cascade", "trellis2_vram_mode": "disk_offload", "trellis2_attn_backend": "flash_attn", "trellis2_seed": 0, "trellis2_ss_guidance": 7.5, "trellis2_ss_steps": 12, "trellis2_shape_guidance": 7.5, "trellis2_shape_steps": 12, "trellis2_tex_guidance": 7.5, "trellis2_tex_steps": 12, "trellis2_max_tokens": 32768, "trellis2_texture_size": 4096, "trellis2_decimation": 1000000, "trellis2_remesh": True, "trellis2_post_processing_enabled": True, "trellis2_bg_removal": "auto", "trellis2_background_color": "black", "trellis2_import_scale": 2.0, "trellis2_clamp_elevation": True, "trellis2_max_elevation": 0.8726646259971648, "trellis2_min_elevation": -0.8726646259971648, "trellis2_auto_lighting": True, "use_ipadapter": False, "sequential_ipadapter_regenerate_wo_controlnet": False, "allow_modify_existing_textures": False, "ask_object_prompts": True, "weight_exponent_mask": False, "mask_blocky": False, "architecture_mode": "trellis2", "use_camera_prompts": True, "sg_use_custom_camera_order": False, "pbr_decomposition": False, "generation_mode": "standard", "texture_objects": "all", "use_flux_lora": True, "qwen_use_trellis2_style": True, "qwen_trellis2_style_initial_only": False, "trellis2_skip_texture": True, "controlnet_units": [{'unit_type': 'depth', 'model_name': 'controlnet_depth_sdxl.safetensors', 'strength': 0.6000000238418579, 'start_percent': 0.0, 'end_percent': 1.0, 'is_union': False, 'use_union_type': True}], "lora_units": [{'model_name': 'Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors', 'model_strength': 1.0, 'clip_strength': 0.0}]},
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
    "discard_factor_generation_only",
    "discard_factor_after_generation",
    "weight_exponent",
    "weight_exponent_generation_only",
    "weight_exponent_after_generation",
    "view_blend_use_color_match",
    "view_blend_color_match_method",
    "view_blend_color_match_strength",
    "clip_skip",
    "auto_rescale",
    "auto_rescale_target_mp",
    "overwrite_material",
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
    "sequential_desaturate_factor",
    "sequential_contrast_factor",
    "sequential_ipadapter_regenerate",
    "ipadapter_weight_type",
    "ipadapter_strength",
    "ipadapter_start",
    "ipadapter_end",
    "early_priority",
    "early_priority_strength",
    "differential_diffusion",
    "differential_noise",
    "blur_mask",
    "blur_mask_radius",
    "blur_mask_sigma",
    "grow_mask_by",
    "canny_threshold_low",
    "canny_threshold_high",
    "qwen_guidance_map_type",
    "qwen_voronoi_mode",
    "qwen_use_external_style_image",
    "qwen_external_style_image",
    "qwen_context_render_mode",
    "qwen_external_style_initial_only",
    "qwen_use_custom_prompts",
    "qwen_custom_prompt_initial",
    "qwen_custom_prompt_seq_none",
    "qwen_custom_prompt_seq_replace",
    "qwen_custom_prompt_seq_additional",
    "qwen_guidance_fallback_color",
    "qwen_guidance_background_color",
    "qwen_context_cleanup",
    "qwen_context_cleanup_hue_tolerance",
    "qwen_context_cleanup_value_adjust",
    "qwen_context_fallback_dilation",
    "qwen_prompt_gray_background",
    "qwen_rescale_alignment",
    "qwen_generation_method",
    "qwen_refine_use_prev_ref",
    "qwen_refine_use_depth",
    "qwen_timestep_zero_ref",
    "refine_angle_ramp_active",
    "refine_angle_ramp_pos_0",
    "refine_angle_ramp_pos_1",
    "visibility_vignette",
    "visibility_vignette_width",
    "visibility_vignette_softness",
    "visibility_vignette_blur",
    "sg_silhouette_margin",
    "sg_silhouette_depth",
    "sg_silhouette_rays",
    "refine_feather_ramp_pos_0",
    "refine_feather_ramp_pos_1",
    "refine_edge_feather_projection",
    "refine_edge_feather_width",
    "refine_edge_feather_softness",
    # --- TRELLIS.2 ---
    "trellis2_texture_mode",
    "trellis2_initial_image_arch",
    "trellis2_camera_count",
    "trellis2_placement_mode",
    "trellis2_auto_prompts",
    "trellis2_exclude_bottom",
    "trellis2_exclude_bottom_angle",
    "trellis2_auto_aspect",
    "trellis2_occlusion_mode",
    "trellis2_consider_existing",
    "trellis2_delete_cameras",
    "trellis2_coverage_target",
    "trellis2_max_auto_cameras",
    "trellis2_fan_angle",
    "trellis2_resolution",
    "trellis2_vram_mode",
    "trellis2_attn_backend",
    "trellis2_seed",
    "trellis2_ss_guidance",
    "trellis2_ss_steps",
    "trellis2_shape_guidance",
    "trellis2_shape_steps",
    "trellis2_tex_guidance",
    "trellis2_tex_steps",
    "trellis2_max_tokens",
    "trellis2_texture_size",
    "trellis2_decimation",
    "trellis2_remesh",
    "trellis2_post_processing_enabled",

    "trellis2_bg_removal",
    "trellis2_background_color",
    "trellis2_import_scale",
    "trellis2_clamp_elevation",
    "trellis2_max_elevation",
    "trellis2_min_elevation",
    "trellis2_auto_lighting",

    # --- General workflow settings (not prompt/seed/model/paths) ---
    "use_ipadapter",
    "sequential_ipadapter_regenerate_wo_controlnet",
    "allow_modify_existing_textures",
    "ask_object_prompts",
    "weight_exponent_mask",
    "mask_blocky",
    "architecture_mode",
    "use_camera_prompts",
    "sg_use_custom_camera_order",
    "generation_mode",
    "texture_objects",
    "use_flux_lora",
    "qwen_use_trellis2_style",
    "qwen_trellis2_style_initial_only",
    "trellis2_skip_texture",
    "pbr_decomposition",
    "pbr_albedo_saturation_mode",
]

# ── Preset diff preview helpers ──────────────────────────────────────────

# Parameters shown first in the diff preview (most user-visible settings).
_PRESET_DIFF_CORE = [
    'architecture_mode', 'model_architecture', 'steps', 'cfg',
    'sampler', 'scheduler', 'generation_method', 'denoise',
    'generation_mode', 'pbr_decomposition',
]

# Known enum values that need specific casing in diff labels.
_DISPLAY_NAMES = {
    'sdxl': 'SDXL',
    'flux1': 'FLUX.1',
    'qwen_image_edit': 'Qwen',
    'flux2_klein': 'FLUX.2 Klein',
    'trellis2': 'TRELLIS.2',
    'standard': 'Standard',
}

def _fmt_diff_val(v):
    """Format a property value for compact display in the diff preview."""
    if isinstance(v, bool):
        return 'On' if v else 'Off'
    if isinstance(v, float):
        # Strip trailing zeros: 1.50 → "1.5", 8.00 → "8"
        return f'{v:.2f}'.rstrip('0').rstrip('.')
    if isinstance(v, str):
        if v in _DISPLAY_NAMES:
            return _DISPLAY_NAMES[v]
        s = v.replace('_', ' ').title()
        return s[:20] + '…' if len(s) > 22 else s
    return str(v)


def _preset_diff(context):
    """Return list of (param, current_formatted, preset_formatted) for
    parameters that differ between the scene and the selected preset.
    Core parameters are listed first."""
    scene = context.scene
    preset_key = scene.stablegen_preset
    if preset_key not in PRESETS:
        return []
    preset = PRESETS[preset_key]
    core_diffs = []
    other_diffs = []
    core_set = set(_PRESET_DIFF_CORE)
    for key in GEN_PARAMETERS:
        if key not in preset or not hasattr(scene, key):
            continue
        current = getattr(scene, key)
        target = preset[key]
        try:
            if isinstance(current, (int, float)) and isinstance(target, (int, float)):
                if math.isclose(float(current), float(target), rel_tol=1e-7, abs_tol=0.0):
                    continue
            elif current == target:
                continue
        except Exception:
            continue
        entry = (key, _fmt_diff_val(current), _fmt_diff_val(target))
        if key in core_set:
            core_diffs.append(entry)
        else:
            other_diffs.append(entry)
    # Sort core diffs in the defined display order
    core_order = {k: i for i, k in enumerate(_PRESET_DIFF_CORE)}
    core_diffs.sort(key=lambda x: core_order.get(x[0], 999))
    return core_diffs + other_diffs


def get_preset_items(self, context):
    # Group presets by architecture for easier navigation.
    _ARCH_GROUP_ORDER = [
        ('sdxl',            'SDXL / FLUX.1'),
        ('qwen_image_edit', 'Qwen Image Edit'),
        ('flux2_klein',     'FLUX.2 Klein'),
        ('trellis2',        'TRELLIS.2 Pipeline'),
    ]
    _known_groups = {k for k, _ in _ARCH_GROUP_ORDER}

    # Classify each preset into its architecture group.
    groups = {}  # group_key -> list of (identifier, name, description)
    for key, preset in PRESETS.items():
        if preset.get('architecture_mode') == 'trellis2':
            grp = 'trellis2'
        else:
            grp = preset.get('model_architecture', 'sdxl')
        groups.setdefault(grp, []).append(
            (key, key.title(), preset.get('description', f'Preset {key}'))
        )

    items = []
    first_group = True
    for grp_key, _label in _ARCH_GROUP_ORDER:
        if grp_key not in groups:
            continue
        if not first_group:
            items.append(('', '', ''))          # horizontal separator
        # Section header: empty identifier + label name renders as header
        # in Blender 4.x enum popup menus.
        items.append(('', _label, ''))
        first_group = False
        items.extend(groups[grp_key])

    # Any architectures not explicitly listed above (future-proofing).
    for grp_key, grp_items in groups.items():
        if grp_key not in _known_groups:
            items.append(('', '', ''))
            items.append(('', grp_key.replace('_', ' ').title(), ''))
            items.extend(grp_items)

    items.append(('', '', ''))                  # separator before Custom
    items.append(('CUSTOM', 'Custom', 'Custom configuration'))
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
            units_match = True

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

        # Compute properties that differ from the pending (unapplied) preset.
        # Used to highlight affected fields inline with alert coloring.
        # Dict maps param name → formatted target value for "→ X" labels.
        _diff_props = {}
        if (hasattr(scene, 'active_preset')
                and scene.stablegen_preset != 'CUSTOM'
                and getattr(scene, 'active_preset', '') != scene.stablegen_preset):
            _diff_props = {d[0]: d[2] for d in _preset_diff(context)}

         # --- Action Buttons & Progress ---
        cam_tools_row = layout.row()
        cam_tools_row.operator("object.add_cameras", text="Add Cameras", icon="CAMERA_DATA")
        if width_mode == 'narrow':
            cam_tools_row = layout.row() 
        cam_tools_row.operator("object.collect_camera_prompts", text="Collect Camera Prompts", icon="FILE_TEXT")

        cam_extra_row = layout.row(align=True)
        cam_extra_row.operator("object.clone_camera", text="Clone Camera", icon="DUPLICATE")
        cam_extra_row.operator("object.mirror_camera", text="Mirror", icon="MOD_MIRROR")
        cam_extra_row.operator("object.toggle_camera_labels", text="Labels", icon="FONT_DATA")
        

        addon_prefs = context.preferences.addons[__package__].preferences
        config_error_message = None

        if not os.path.exists(addon_prefs.output_dir):
            config_error_message = "Output Path Invalid"
        elif not addon_prefs.server_address:
            config_error_message = "Server Address Missing"
        elif not addon_prefs.server_online:
            config_error_message = "Cannot reach server"

        # Determine if we are in TRELLIS.2 mode (used by generate button & later sections)
        _arch_mode = getattr(scene, 'architecture_mode', 'sdxl')
        _is_trellis2_mode = (_arch_mode == 'trellis2')

        # ── Prerequisite warnings (shown inline before the Generate button) ──
        if not _is_trellis2_mode and not config_error_message:
            has_cameras = any(obj.type == 'CAMERA' for obj in scene.objects)
            has_meshes = any(obj.type == 'MESH' for obj in context.view_layer.objects if not obj.hide_get())
            if not has_meshes:
                warn_box = layout.box()
                warn_row = warn_box.row()
                warn_row.alert = True
                warn_row.label(text="No visible mesh objects", icon='ERROR')
                warn_row.operator("stablegen.switch_to_mesh_generation",
                                  text="Mesh Generation", icon='MESH_DATA')
            if not has_cameras:
                warn_box = layout.box()
                warn_row = warn_box.row()
                warn_row.alert = True
                warn_row.label(text="No cameras in the scene", icon='ERROR')
                warn_row.operator("object.add_cameras", text="Add Cameras", icon='CAMERA_DATA')

        action_row = layout.row()
        action_row.scale_y = 2.0 # Scale the row vertically

        # Show a "Refreshing…" indicator while async model fetches are in-flight
        if _is_refreshing():
            refresh_row = layout.row()
            refresh_row.alignment = 'CENTER'
            refresh_row.label(text="Refreshing model lists...", icon="SORTTIME")

        if _is_trellis2_mode:
            # --- TRELLIS.2 Generate Button ---
            trellis2_op = next(
                (op for win in context.window_manager.windows
                 for op in win.modal_operators
                 if op.bl_idname == 'OBJECT_OT_trellis2_generate'),
                None
            )
            # Also look for ComfyUIGenerate running as the texturing phase
            comfy_tex_op = next(
                (op for win in context.window_manager.windows
                 for op in win.modal_operators
                 if op.bl_idname == 'OBJECT_OT_test_stable'),
                None
            ) if not trellis2_op else None

            if config_error_message:
                if config_error_message == "Cannot reach server":
                    split = action_row.split(factor=0.85, align=True)
                    split.operator("object.trellis2_generate", text="Cannot generate: " + config_error_message, icon="ERROR")
                    split.operator("stablegen.check_server_status", text="", icon='FILE_REFRESH')
                else:
                    action_row.operator("object.trellis2_generate", text="Cannot generate: " + config_error_message, icon="ERROR")
                    action_row.enabled = False

            elif trellis2_op:
                # ── Phases 1 & 2: Trellis2Generate is alive ──
                action_row.operator("object.trellis2_generate", text="Cancel TRELLIS.2", icon="CANCEL")
                progress_col = layout.column()

                # Bar 1 — Overall
                overall_pct = getattr(trellis2_op, '_overall_progress', 0)
                overall_label = getattr(trellis2_op, '_overall_stage', 'Initializing')
                progress_col.progress(
                    text=f"{overall_label} ({overall_pct:.0f}%)",
                    factor=max(0.0, min(overall_pct / 100.0, 1.0))
                )

                # Bar 2 — Phase
                phase_pct = getattr(trellis2_op, '_phase_progress', 0)
                phase_label = getattr(trellis2_op, '_phase_stage', '')
                if phase_label:
                    progress_col.progress(
                        text=f"{phase_label} ({phase_pct:.0f}%)",
                        factor=max(0.0, min(phase_pct / 100.0, 1.0))
                    )

                # Bar 3 — Detail (only when there's actual sampler progress)
                detail_pct = getattr(trellis2_op, '_detail_progress', 0)
                detail_label = getattr(trellis2_op, '_detail_stage', '')
                if detail_label and detail_pct > 0:
                    progress_col.progress(
                        text=f"{detail_label} ({detail_pct:.0f}%)",
                        factor=max(0.0, min(detail_pct / 100.0, 1.0))
                    )

            elif comfy_tex_op and getattr(scene, 'trellis2_pipeline_active', False):
                # ── Phase 3: Texturing via ComfyUIGenerate ──
                action_row.operator("object.test_stable", text="Cancel Texturing", icon="CANCEL")
                progress_col = layout.column()

                pbr_active = getattr(comfy_tex_op, '_pbr_active', False)
                if pbr_active:
                    # PBR decomposition sub-phase — 3 bars:
                    # Bar 1 (top): overall pipeline progress
                    # Bar 2: current PBR model (camera progress)
                    # Bar 3: PBR step N/M
                    pbr_step = getattr(comfy_tex_op, '_pbr_step', 0)
                    pbr_total = max(getattr(comfy_tex_op, '_pbr_total_steps', 1), 1)
                    pbr_cam = getattr(comfy_tex_op, '_pbr_cam', 0)
                    pbr_cam_total = max(getattr(comfy_tex_op, '_pbr_cam_total', 1), 1)
                    cam_frac = pbr_cam / pbr_cam_total
                    stage_text = getattr(comfy_tex_op, '_stage', 'PBR Decomposition')

                    # Overall: texturing is done, PBR owns the upper slice of Phase 3
                    phase_start = getattr(scene, 'trellis2_pipeline_phase_start_pct', 65.0)
                    phase_weight = 100.0 - phase_start
                    tex_portion = phase_weight * 0.6  # first 60% of phase = texturing
                    pbr_portion = phase_weight * 0.4  # last 40% = PBR
                    pbr_frac = max(0.0, min(((pbr_step - 1) + cam_frac) / pbr_total, 1.0))
                    overall_pct = phase_start + tex_portion + pbr_portion * pbr_frac
                    overall_pct = max(0.0, min(overall_pct, 100.0))
                    total_phases = getattr(scene, 'trellis2_pipeline_total_phases', 3)

                    # Bar 1 — Overall pipeline
                    progress_col.progress(
                        text=f"Phase {total_phases}/{total_phases}: PBR Decomposition ({overall_pct:.0f}%)",
                        factor=max(0.0, min(overall_pct / 100.0, 1.0))
                    )
                    # Bar 2 — Current model (camera progress)
                    progress_col.progress(text=stage_text, factor=max(0.0, min(cam_frac, 1.0)))
                    # Bar 3 — PBR step N/M
                    progress_col.progress(text=f"PBR: Step {pbr_step}/{pbr_total}", factor=pbr_frac)
                else:
                    # Normal texturing progress
                    # Compute overall from scene pipeline props + ComfyUI progress
                    phase_start = getattr(scene, 'trellis2_pipeline_phase_start_pct', 65.0)
                    phase_weight = 100.0 - phase_start
                    comfy_progress = getattr(comfy_tex_op, '_progress', 0) / 100.0
                    total_imgs = getattr(comfy_tex_op, '_total_images', 0)
                    cur_img_idx = getattr(comfy_tex_op, '_current_image', 0)
                    if total_imgs > 1:
                        comfy_overall = (cur_img_idx + comfy_progress) / total_imgs
                    else:
                        comfy_overall = comfy_progress
                    overall_pct = phase_start + comfy_overall * phase_weight
                    overall_pct = max(0.0, min(overall_pct, 100.0))

                    total_phases = getattr(scene, 'trellis2_pipeline_total_phases', 3)
                    # Bar 1 — Overall
                    progress_col.progress(
                        text=f"Phase {total_phases}/{total_phases}: Texturing ({overall_pct:.0f}%)",
                        factor=max(0.0, min(overall_pct / 100.0, 1.0))
                    )

                    # Bar 2 — Per-image (same as normal ComfyUI bar)
                    stage = getattr(comfy_tex_op, '_stage', 'Generating')
                    img_pct = getattr(comfy_tex_op, '_progress', 0)
                    progress_col.progress(
                        text=f"{stage} ({img_pct:.0f}%)",
                        factor=max(0.0, min(img_pct / 100.0, 1.0))
                    )

                    # Bar 3 — Image N/M (same as normal ComfyUI overall bar)
                    if total_imgs > 1:
                        cur_img = min(cur_img_idx + 1, total_imgs)
                        img_overall = max(0.0, min(comfy_overall, 1.0))
                        progress_col.progress(
                            text=f"Overall: Image {cur_img}/{total_imgs}",
                            factor=img_overall
                        )

            elif comfy_tex_op and scene.generation_status == 'running':
                # Standalone ComfyUIGenerate (e.g. Reproject with PBR)
                # outside the TRELLIS.2 pipeline.
                action_row.operator("object.test_stable", text="Cancel Generation", icon="CANCEL")
                progress_col = layout.column()
                raw_progress = getattr(comfy_tex_op, '_progress', 0) / 100.0
                pbr_active = getattr(comfy_tex_op, '_pbr_active', False)

                if pbr_active:
                    pbr_step = getattr(comfy_tex_op, '_pbr_step', 0)
                    pbr_total = max(getattr(comfy_tex_op, '_pbr_total_steps', 1), 1)
                    pbr_cam = getattr(comfy_tex_op, '_pbr_cam', 0)
                    pbr_cam_total = max(getattr(comfy_tex_op, '_pbr_cam_total', 1), 1)
                    cam_frac = pbr_cam / pbr_cam_total
                    stage_text = getattr(comfy_tex_op, '_stage', 'PBR Decomposition')
                    progress_col.progress(text=stage_text, factor=max(0.0, min(cam_frac, 1.0)))
                    pbr_factor = max(0.0, min(((pbr_step - 1) + cam_frac) / pbr_total, 1.0))
                    progress_col.progress(text=f"PBR: Step {pbr_step}/{pbr_total}", factor=pbr_factor)
                else:
                    progress_text = f"{getattr(comfy_tex_op, '_stage', 'Generating')} ({getattr(comfy_tex_op, '_progress', 0):.0f}%)"
                    progress_col.progress(text=progress_text, factor=max(0.0, min(raw_progress, 1.0)))
                    total_images = getattr(comfy_tex_op, '_total_images', 0)
                    if total_images > 1:
                        current_image_idx = getattr(comfy_tex_op, '_current_image', 0)
                        overall_progress = (current_image_idx + max(0.0, min(raw_progress, 1.0))) / total_images if total_images > 0 else 0
                        cur_img = min(current_image_idx + 1, total_images)
                        progress_col.progress(text=f"Overall: Image {cur_img}/{total_images}", factor=max(0.0, min(overall_progress, 1.0)))

            elif scene.trellis2_generate_from == 'image' and not scene.trellis2_input_image:
                action_row.operator("object.trellis2_generate", text="Select an image first", icon="ERROR")
                action_row.enabled = False
            elif not getattr(scene, 'trellis2_available', False):
                split = action_row.split(factor=0.8)
                err_sub = split.row()
                err_sub.operator("object.trellis2_generate", text="TRELLIS.2 nodes not found", icon="ERROR")
                err_sub.enabled = False
                split.operator("stablegen.check_server_status", text="", icon="FILE_REFRESH")
            else:
                action_row.operator("object.trellis2_generate", text="Generate 3D Mesh", icon="MESH_ICOSPHERE")
        else:
            # --- Standard Diffusion Generate Button ---
            if config_error_message:
                # Split the row to have the error message/disabled button and the refresh button
                if config_error_message == "Cannot reach server":
                    split = action_row.split(factor=0.85, align=True) # Adjust factor as needed
                    split.operator("object.test_stable", text="Cannot generate: " + config_error_message, icon="ERROR") # Use ERROR icon
                    # Use the operator from __init__.py
                    split.operator("stablegen.check_server_status", text="", icon='FILE_REFRESH')
                else:
                    action_row.operator("object.test_stable", text="Cannot generate: " + config_error_message, icon="ERROR")
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
                    # Check if any cameras are selected and if there is existing output
                    selected_cameras = [obj for obj in context.selected_objects if obj.type == 'CAMERA']
                    if not selected_cameras or scene.get("output_timestamp") == "":
                        action_row.operator("object.test_stable", text="Generate", icon="PLAY")
                    else:
                        # Use the regenerate operator
                        action_row.operator("object.stablegen_regenerate", text="Regenerate Selected Views", icon="PLAY")
                elif scene.generation_status == 'running':
                    action_row.operator("object.test_stable", text="Cancel Generation", icon="CANCEL")

                    operator_instance = next((op for win in context.window_manager.windows for op in win.modal_operators if op.bl_idname == 'OBJECT_OT_test_stable'), None)
                    if operator_instance:
                        progress_col = layout.column()
                        raw_progress = getattr(operator_instance, '_progress', 0) / 100.0
                        pbr_active = getattr(operator_instance, '_pbr_active', False)

                        if pbr_active:
                            # During PBR: top bar shows camera progress within
                            # the current model step (no raw ComfyUI jitter).
                            pbr_step = getattr(operator_instance, '_pbr_step', 0)
                            pbr_total = max(getattr(operator_instance, '_pbr_total_steps', 1), 1)
                            pbr_cam = getattr(operator_instance, '_pbr_cam', 0)
                            pbr_cam_total = max(getattr(operator_instance, '_pbr_cam_total', 1), 1)

                            # Top bar: camera X out of N within this step
                            cam_frac = pbr_cam / pbr_cam_total
                            stage_text = getattr(operator_instance, '_stage', 'PBR Decomposition')
                            progress_col.progress(
                                text=stage_text,
                                factor=max(0.0, min(cam_frac, 1.0))
                            )
                            # Bottom bar: overall PBR progress
                            pbr_factor = max(0.0, min(
                                ((pbr_step - 1) + cam_frac) / pbr_total, 1.0))
                            progress_col.progress(
                                text=f"PBR: Step {pbr_step}/{pbr_total}",
                                factor=pbr_factor
                            )
                        else:
                            # Normal generation progress
                            progress_text = f"{getattr(operator_instance, '_stage', 'Generating')} ({getattr(operator_instance, '_progress', 0):.0f}%)"
                            progress_col.progress(text=progress_text, factor=max(0.0, min(raw_progress, 1.0)))

                            total_images = getattr(operator_instance, '_total_images', 0)
                            if total_images > 1:
                                current_image_idx = getattr(operator_instance, '_current_image', 0)
                                current_image_decimal_progress = max(0.0, min(raw_progress, 1.0))
                                
                                # Ensure total_images is not zero to prevent division by zero
                                overall_progress_factor = (current_image_idx + current_image_decimal_progress) / total_images if total_images > 0 else 0
                                overall_progress_factor_clamped = max(0.0, min(overall_progress_factor, 1.0))

                                current_img = min(current_image_idx + 1, total_images)  # Clamp to total_images

                                progress_col.progress(
                                    text=f"Overall: Image {current_img}/{total_images}",
                                    factor=overall_progress_factor_clamped # Ensure factor is <= 1.0 (logic maintained)
                                )
                            
                elif context.scene.generation_status == 'waiting':
                    action_row.operator("object.test_stable", text="Waiting for Cancellation", icon="TIME")
                else:
                    action_row.operator("object.test_stable", text="Fix Issues to Generate", icon="ERROR")
                    action_row.enabled = False
        
        bake_row = layout.row()
        if config_error_message:
            bake_row.operator("object.bake_textures", text="Cannot Bake: " + config_error_message, icon="ERROR")
            bake_row.enabled = False
        else:
            bake_row.operator("object.bake_textures", text="Bake Textures", icon="RENDER_STILL")
            bake_row.enabled = True
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

        export_row = layout.row()
        export_row.operator("object.export_game_engine",
                            text="Export for Game Engine",
                            icon="EXPORT")

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

        # --- Scene Queue ---
        queue_box = layout.box()
        queue_col = queue_box.column()
        wm = context.window_manager
        show_queue = getattr(wm, 'sg_show_queue', False)
        queue_header = queue_col.row()
        queue_header.prop(wm, "sg_show_queue",
                          text=f"Scene Queue ({len(wm.sg_scene_queue)})",
                          icon="TRIA_DOWN" if show_queue else "TRIA_RIGHT",
                          emboss=False)
        if _queue_processing:
            status_text = "Exporting GIF..." if _queue_phase == 'exporting_gif' else "Processing..."
            queue_header.label(text=status_text, icon="SORTTIME")

        if show_queue:
            queue_content = queue_col.box()
            row = queue_content.row()
            row.template_list("SG_UL_SceneQueueList", "",
                              wm, "sg_scene_queue",
                              wm, "sg_scene_queue_index",
                              rows=3)
            col = row.column(align=True)
            col.operator("stablegen.queue_move_up", text="", icon="TRIA_UP")
            col.operator("stablegen.queue_move_down", text="", icon="TRIA_DOWN")
            col.separator()
            col.operator("stablegen.queue_remove", text="", icon="REMOVE")

            btn_row = queue_content.row(align=True)
            btn_row.operator("stablegen.queue_add", text="Add Scene", icon="ADD")
            btn_row.operator("stablegen.queue_open_result", text="Open", icon="FILE_BLEND")
            btn_row2 = queue_content.row(align=True)
            btn_row2.operator("stablegen.queue_invalidate", text="Reset", icon="LOOP_BACK")
            btn_row2.operator("stablegen.queue_clear", text="Clear", icon="TRASH")

            process_row = queue_content.row()
            if _queue_processing:
                process_row.alert = True
                process_row.operator("stablegen.queue_process", text="Cancel Queue", icon="CANCEL")
            else:
                process_row.operator("stablegen.queue_process", text="Process Queue", icon="PLAY")
                process_row.enabled = len(wm.sg_scene_queue) > 0

            # ── GIF Export settings ──
            gif_box = queue_content.box()
            gif_row = gif_box.row()
            gif_row.prop(wm, "sg_queue_gif_export", text="Export Orbit GIF/MP4")
            if getattr(wm, 'sg_queue_gif_export', False):
                gif_col = gif_box.column(align=True)
                row = gif_col.row(align=True)
                row.prop(wm, "sg_queue_gif_duration")
                row.prop(wm, "sg_queue_gif_fps")
                row = gif_col.row(align=True)
                row.prop(wm, "sg_queue_gif_resolution")
                row.prop(wm, "sg_queue_gif_samples")
                gif_col.prop(wm, "sg_queue_gif_engine")
                gif_col.prop(wm, "sg_queue_gif_interpolation")
                gif_col.separator()
                gif_col.prop(wm, "sg_queue_gif_use_hdri")
                if getattr(wm, 'sg_queue_gif_use_hdri', False):
                    gif_col.prop(wm, "sg_queue_gif_hdri_path")
                    gif_col.prop(wm, "sg_queue_gif_hdri_strength")
                    gif_col.prop(wm, "sg_queue_gif_hdri_rotation")
                    gif_col.prop(wm, "sg_queue_gif_env_mode")
                gif_col.prop(wm, "sg_queue_gif_denoiser")
                if bpy.app.version >= (5, 1, 0) and getattr(wm, 'sg_queue_gif_engine', 'CYCLES') == 'CYCLES':
                    gif_col.prop(wm, "sg_queue_gif_use_gpu")
                gif_col.prop(wm, "sg_queue_gif_also_no_pbr")

        # --- Main Parameters section ---
        if not hasattr(scene, 'show_generation_params'): 
            scene.show_generation_params = True

        is_trellis2 = getattr(scene, 'architecture_mode', 'sdxl') == 'trellis2'
        trellis2_tex_mode = getattr(scene, 'trellis2_texture_mode', 'native')
        trellis2_diffusion_texturing = is_trellis2 and trellis2_tex_mode in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein')
            
        main_params_box = layout.box()
        main_params_col = main_params_box.column()
        main_params_col.prop(scene, "show_generation_params", text="Main Parameters", icon="TRIA_DOWN" if scene.show_generation_params else "TRIA_RIGHT", emboss=False)
        if scene.show_generation_params:
            params_container = main_params_col.box()
            # Split for prompt
            split = params_container.split(factor=0.25)
            split.label(text="Prompt:")
            prompt_row = split.row(align=True)
            prompt_row.prop(scene, "comfyui_prompt", text="")
            # Hide texture prompt toggle when texture mode is none/native (no separate texture pipeline)
            if not (is_trellis2 and trellis2_tex_mode in ('none', 'native')):
                prompt_row.prop(scene, "use_separate_texture_prompt", text="",
                               icon='BRUSH_DATA',
                               icon_only=True)
            if scene.use_separate_texture_prompt and not (is_trellis2 and trellis2_tex_mode in ('none', 'native')):
                split = params_container.split(factor=0.25)
                split.label(text="Texture Prompt:")
                split.prop(scene, "texture_prompt", text="")

            # Architecture selector (architecture_mode — includes TRELLIS.2)
            # Alert when either architecture_mode or model_architecture changes.
            _arch_diff = 'architecture_mode' in _diff_props or 'model_architecture' in _diff_props
            split = params_container.split(factor=0.5)
            if _arch_diff:
                split.alert = True
            split.label(text="Architecture:")
            split.prop(scene, "architecture_mode", text="")
            if _arch_diff:
                _has_mode = 'architecture_mode' in _diff_props
                _has_model = 'model_architecture' in _diff_props
                if _has_mode:
                    # architecture_mode differs — always show model in parens.
                    # Use the preset's model_architecture even if it didn't change.
                    _preset_key = scene.stablegen_preset
                    _preset_data = PRESETS.get(_preset_key, {})
                    _model_display = _fmt_diff_val(_preset_data.get(
                        'model_architecture', scene.model_architecture))
                    split.label(text="→ " + _diff_props['architecture_mode']
                                + " (" + _model_display + ")")
                else:
                    # Only model_architecture differs (e.g. SDXL → Qwen).
                    split.label(text="→ " + _diff_props['model_architecture'])

            if is_trellis2:
                # --- TRELLIS.2 specific layout ---
                # Warning if TRELLIS.2 nodes not detected
                if not getattr(scene, 'trellis2_available', False):
                    warn_row = params_container.row()
                    warn_row.alert = True
                    warn_split = warn_row.split(factor=0.9)
                    warn_split.label(text="TRELLIS.2 nodes not detected on server", icon="ERROR")
                    warn_split.operator("stablegen.check_server_status", text="", icon="FILE_REFRESH")

                # Generate From toggle (Image / Prompt)
                split = params_container.split(factor=0.5)
                split.label(text="Generate From:")
                split.prop(scene, "trellis2_generate_from", text="")

                # Input image picker (only when generate_from = image)
                if scene.trellis2_generate_from == 'image':
                    split = params_container.split(factor=0.25)
                    split.label(text="Input Image:")
                    split.prop(scene, "trellis2_input_image", text="")

                # Preview gallery (only when generate_from = prompt)
                if scene.trellis2_generate_from == 'prompt':
                    row = params_container.row(align=True)
                    row.prop(scene, "trellis2_preview_gallery_enabled", text="Preview Gallery", toggle=True, icon="IMAGE_REFERENCE")
                    sub = row.row(align=True)
                    sub.enabled = scene.trellis2_preview_gallery_enabled
                    sub.prop(scene, "trellis2_preview_gallery_count", text="Count")

                # Texture Generation Mode
                split = params_container.split(factor=0.5)
                split.label(text="Texture Mode:")
                split.prop(scene, "trellis2_texture_mode", text="")

                # Mesh shading mode
                split = params_container.split(factor=0.5)
                split.label(text="Shading:")
                split.prop(scene, "trellis2_shade_mode", text="")

                # Prompt + native/none: show initial-image architecture & checkpoint
                _prompt_needs_initial = (
                    scene.trellis2_generate_from == 'prompt'
                    and trellis2_tex_mode in ('native', 'none')
                )
                if _prompt_needs_initial:
                    split = params_container.split(factor=0.5)
                    split.label(text="Initial Image Arch:")
                    split.prop(scene, "trellis2_initial_image_arch", text="")

                    split = params_container.split(factor=0.25)
                    split.label(text="Checkpoint:")
                    row = split.row(align=True)
                    row.prop(scene, "model_name", text="")
                    row.operator("stablegen.refresh_checkpoint_list", text="", icon='FILE_REFRESH')

                # When diffusion texturing: show checkpoint, generation mode, camera count
                if trellis2_diffusion_texturing:
                    split = params_container.split(factor=0.25)
                    split.label(text="Checkpoint:")
                    row = split.row(align=True)
                    row.prop(scene, "model_name", text="")
                    row.operator("stablegen.refresh_checkpoint_list", text="", icon='FILE_REFRESH')

                    split = params_container.split(factor=0.5)
                    if 'generation_method' in _diff_props or 'qwen_generation_method' in _diff_props:
                        split.alert = True
                    split.label(text="Generation Mode:")
                    if scene.model_architecture.startswith("qwen"):
                        split.prop(scene, "qwen_generation_method", text="")
                    else:
                        split.prop(scene, "generation_method", text="")
                    _lbl = ''.join(f'→{_diff_props[k]} ' for k in ('generation_method', 'qwen_generation_method') if k in _diff_props)
                    if _lbl:
                        split.label(text=_lbl.strip())
            else:
                # --- Standard diffusion layout ---
                # Split for model name
                split = params_container.split(factor=0.25)
                split.label(text="Checkpoint:")
                row = split.row(align=True)
                row.prop(scene, "model_name", text="")
                row.operator("stablegen.refresh_checkpoint_list", text="", icon='FILE_REFRESH')

                # Split for generation method
                split = params_container.split(factor=0.5)
                if 'generation_method' in _diff_props or 'qwen_generation_method' in _diff_props:
                    split.alert = True
                split.label(text="Generation Mode:")
                if scene.model_architecture.startswith("qwen"):
                    split.prop(scene, "qwen_generation_method", text="")
                else:
                    split.prop(scene, "generation_method", text="")
                _lbl = ''.join(f'→{_diff_props[k]} ' for k in ('generation_method', 'qwen_generation_method') if k in _diff_props)
                if _lbl:
                    split.label(text=_lbl.strip())

                # Split for object selection
                split = params_container.split(factor=0.5)
                split.label(text="Target Objects:")
                split.prop(scene, "texture_objects", text="")

        # Helper to create collapsible sections
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
            "show_core_settings", "show_lora_settings", "show_camera_options",
            "show_scene_understanding_settings", 
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

            # --- TRELLIS.2: Mesh Generation Settings ---
            if is_trellis2:
                content_box = draw_collapsible_section(advanced_params_box, "show_trellis2_mesh_settings", "Mesh Generation Settings", icon="MESH_DATA")
                if content_box:
                    # Core mesh params
                    row = content_box.row()
                    row.prop(scene, "trellis2_seed", text="Seed")

                    content_box.separator()

                    # Post-processing (ComfyUI-side decimation + remesh)
                    content_box.label(text="Post-Processing:", icon="OUTLINER_OB_MESH")
                    row = content_box.row()
                    row.prop(scene, "trellis2_post_processing_enabled", text="Enable Post-Processing", toggle=True, icon="MOD_DECIM")

                    if scene.trellis2_post_processing_enabled:
                        row = content_box.row()
                        row.prop(scene, "trellis2_decimation", text="Decimation Target")
                        row = content_box.row()
                        row.prop(scene, "trellis2_remesh", text="Remesh", toggle=True, icon="MOD_REMESH")

                    content_box.separator()

                    # Model settings
                    content_box.label(text="Model:", icon="SETTINGS")
                    split = content_box.split(factor=0.5)
                    split.label(text="Resolution:")
                    split.prop(scene, "trellis2_resolution", text="")

                    split = content_box.split(factor=0.5)
                    split.label(text="VRAM Mode:")
                    split.prop(scene, "trellis2_vram_mode", text="")

                    split = content_box.split(factor=0.5)
                    split.label(text="Attention:")
                    split.prop(scene, "trellis2_attn_backend", text="")

                    content_box.separator()

                    # Shape generation
                    content_box.label(text="Shape Generation:", icon="MESH_ICOSPHERE")
                    row = content_box.row(align=True)
                    row.prop(scene, "trellis2_ss_guidance", text="SS Guidance")
                    row.prop(scene, "trellis2_ss_steps", text="SS Steps")
                    row = content_box.row(align=True)
                    row.prop(scene, "trellis2_shape_guidance", text="Shape Guidance")
                    row.prop(scene, "trellis2_shape_steps", text="Shape Steps")
                    row = content_box.row()
                    row.prop(scene, "trellis2_max_tokens", text="Max Tokens (VRAM)")

                    content_box.separator()

                    # Conditioning
                    content_box.label(text="Conditioning:", icon="IMAGE_DATA")
                    split = content_box.split(factor=0.5)
                    split.label(text="Background:")
                    split.prop(scene, "trellis2_background_color", text="")
                    content_box.separator()

                    # Misc
                    content_box.label(text="Misc:", icon="PREFERENCES")
                    split = content_box.split(factor=0.5)
                    split.label(text="BG Removal:")
                    split.prop(scene, "trellis2_bg_removal", text="")
                    content_box.separator()

            # --- TRELLIS.2: Native Texture Settings ---
            if is_trellis2 and trellis2_tex_mode == 'native':
                content_box = draw_collapsible_section(advanced_params_box, "show_trellis2_texture_settings", "Texture Settings (TRELLIS.2 Native)", icon="TEXTURE")
                if content_box:
                    row = content_box.row(align=True)
                    row.prop(scene, "trellis2_tex_guidance", text="Tex Guidance")
                    row.prop(scene, "trellis2_tex_steps", text="Tex Steps")
                    row = content_box.row()
                    row.prop(scene, "trellis2_texture_size", text="Texture Size")

                    content_box.separator()
                    row = content_box.row()
                    row.prop(scene, "trellis2_auto_lighting", text="Studio Lighting", icon="LIGHT_AREA")

            # --- TRELLIS.2: Camera Placement Settings (diffusion texturing) ---
            if is_trellis2 and trellis2_diffusion_texturing:
                content_box = draw_collapsible_section(advanced_params_box, "show_trellis2_camera_settings", "Camera Placement (TRELLIS.2)", icon="CAMERA_DATA")
                if content_box:
                    _t2_pm = getattr(scene, 'trellis2_placement_mode', 'normal_weighted')

                    row = content_box.row()
                    row.prop(scene, "trellis2_import_scale", text="Import Scale (BU)")

                    content_box.separator()

                    split = content_box.split(factor=0.4)
                    split.label(text="Placement:")
                    split.prop(scene, "trellis2_placement_mode", text="")

                    # Camera count (not used by greedy)
                    if _t2_pm != 'greedy_coverage':
                        row = content_box.row()
                        row.prop(scene, "trellis2_camera_count", text="Camera Count")

                    # Greedy-specific
                    if _t2_pm == 'greedy_coverage':
                        row = content_box.row(align=True)
                        row.prop(scene, "trellis2_coverage_target", text="Coverage Target")
                        row.prop(scene, "trellis2_max_auto_cameras", text="Max Cameras")

                    # Fan-specific
                    if _t2_pm == 'fan_from_camera':
                        row = content_box.row()
                        row.prop(scene, "trellis2_fan_angle", text="Fan Angle")

                    content_box.separator()

                    row = content_box.row()
                    row.prop(scene, "trellis2_auto_prompts", text="Auto View Prompts", toggle=True, icon="OUTLINER_OB_CAMERA")

                    split = content_box.split(factor=0.4)
                    split.label(text="Auto Aspect:")
                    split.prop(scene, "trellis2_auto_aspect", text="")

                    split = content_box.split(factor=0.4)
                    split.label(text="Occlusion:")
                    split.prop(scene, "trellis2_occlusion_mode", text="")

                    row = content_box.row()
                    row.prop(scene, "trellis2_exclude_bottom", text="Exclude Bottom Faces", toggle=True, icon="TRIA_DOWN_BAR")
                    if scene.trellis2_exclude_bottom:
                        row = content_box.row()
                        row.prop(scene, "trellis2_exclude_bottom_angle", text="Bottom Angle")

                    row = content_box.row()
                    row.prop(scene, "trellis2_consider_existing", text="Consider Existing Cameras", toggle=True)

                    row = content_box.row()
                    row.prop(scene, "trellis2_delete_cameras", text="Delete Cameras After", toggle=True, icon="TRASH")

                    content_box.separator()

                    row = content_box.row()
                    row.prop(scene, "trellis2_clamp_elevation", text="Clamp Elevation", toggle=True, icon="CON_ROTLIMIT")
                    if scene.trellis2_clamp_elevation:
                        row = content_box.row(align=True)
                        row.prop(scene, "trellis2_min_elevation", text="Min")
                        row.prop(scene, "trellis2_max_elevation", text="Max")

            # --- Diffusion-based advanced sections ---
            # Each is individually guarded: shown for standard arches or TRELLIS.2 with diffusion texturing
            _show_diffusion_sections = not is_trellis2 or trellis2_diffusion_texturing
            # Mesh-only + prompt mode still needs initial-image pipeline settings
            _show_initial_image_settings = (
                is_trellis2 and trellis2_tex_mode == 'none'
                and getattr(scene, 'trellis2_generate_from', 'image') == 'prompt'
            )

            # --- Core Generation Settings ---
            
            if _show_diffusion_sections or _show_initial_image_settings:
                content_box = draw_collapsible_section(advanced_params_box, "show_core_settings", "Core Generation Settings", icon="SETTINGS")
            else:
                content_box = None
            if content_box:
                row = content_box.row()
                row.prop(scene, "seed", text="Seed")
                if width_mode == 'narrow':
                    row = content_box.row()
                sub = row.row()
                if 'steps' in _diff_props:
                    sub.alert = True
                sub.prop(scene, "steps", text="Steps")
                if 'steps' in _diff_props:
                    sub.label(text="→" + _diff_props['steps'])
                if width_mode == 'narrow':
                    row = content_box.row()
                sub = row.row()
                if 'cfg' in _diff_props:
                    sub.alert = True
                sub.prop(scene, "cfg", text="CFG")
                if 'cfg' in _diff_props:
                    sub.label(text="→" + _diff_props['cfg'])

                split = content_box.split(factor=0.5)
                split.label(text="Negative Prompt:")
                split.prop(scene, "comfyui_negative_prompt", text="")
                
                split = content_box.split(factor=0.5)
                split.label(text="Control After Generate:")
                split.prop(scene, "control_after_generate", text="")

                split = content_box.split(factor=0.5)
                if 'sampler' in _diff_props:
                    split.alert = True
                split.label(text="Sampler:")
                split.prop(scene, "sampler", text="")
                if 'sampler' in _diff_props:
                    split.label(text="→ " + _diff_props['sampler'])

                split = content_box.split(factor=0.5)
                if 'scheduler' in _diff_props:
                    split.alert = True
                split.label(text="Scheduler:")
                split.prop(scene, "scheduler", text="")
                if 'scheduler' in _diff_props:
                    split.label(text="→ " + _diff_props['scheduler'])
                
                row = content_box.row()
                row.prop(scene, "clip_skip", text="Clip Skip")

           # --- LoRA Settings ---
            if _show_diffusion_sections or _show_initial_image_settings:
                content_box = draw_collapsible_section(advanced_params_box, "show_lora_settings", "LoRA Management", icon="MODIFIER")
            else:
                content_box = None
            if content_box:
                row = content_box.row()
                row.alignment = 'CENTER'
                row.label(text="LoRA Units", icon="BRUSHES_ALL") # Using decimate icon for LoRA

                if scene.lora_units:
                    for i, lora_unit in enumerate(scene.lora_units):
                        is_selected_lora = (scene.lora_units_index == i)
                        unit_box = content_box.box()
                        row = unit_box.row()
                        row.prop(lora_unit, "model_name", text=f"LoRA {i+1}") # Shows selected model
                        
                        sub_row = unit_box.row(align=True)
                        sub_row.prop(lora_unit, "model_strength", text="Model Strength")
                        if not scene.model_architecture.startswith("qwen") and scene.model_architecture != 'flux2_klein': # Qwen/Klein use model only loras
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
                    
                    # Draw the operator with the dynamically determined text
                    btn_row_lora.operator("stablegen.add_lora_unit", text=button_text, icon="ADD")
                    # The enabled state (greying out) will be handled by AddLoRAUnit.poll()
                else:
                    # Multiple buttons if LoRA units exist
                    btn_row_lora.operator("stablegen.add_lora_unit", text="Add Another LoRA", icon="ADD")
                    btn_row_lora.operator("stablegen.remove_lora_unit", text="Remove Selected", icon="REMOVE")

            # --- Camera Options ---
            if _show_diffusion_sections:
                content_box = draw_collapsible_section(advanced_params_box, "show_camera_options", "Camera Settings", icon="CAMERA_DATA")
            else:
                content_box = None
            if content_box:
                row = content_box.row(align=True)
                row.prop(scene, "use_camera_prompts", text="Use Camera Prompts", toggle=True, icon="OUTLINER_OB_CAMERA")

                # ── Camera Generation Order ──
                row = content_box.row(align=True)
                row.prop(scene, "sg_use_custom_camera_order",
                         text="Custom Generation Order", toggle=True, icon="SORTALPHA")
                if scene.sg_use_custom_camera_order:
                    order_box = content_box.box()
                    # Preset strategy selector + sync
                    row = order_box.row(align=True)
                    row.operator_menu_enum(
                        "stablegen.apply_camera_order_preset", "strategy",
                        text="Sort Preset", icon="PRESET")
                    row.operator("stablegen.sync_camera_order",
                                 text="", icon="FILE_REFRESH")

                    # UIList with move buttons
                    row = order_box.row()
                    row.template_list(
                        "SG_UL_CameraOrderList", "",
                        scene, "sg_camera_order",
                        scene, "sg_camera_order_index",
                        rows=4, maxrows=8)
                    col = row.column(align=True)
                    op = col.operator("stablegen.move_camera_order",
                                      text="", icon="TRIA_UP")
                    op.direction = 'UP'
                    op = col.operator("stablegen.move_camera_order",
                                      text="", icon="TRIA_DOWN")
                    op.direction = 'DOWN'

            # --- Viewpoint Blending Settings ---
            if _show_diffusion_sections:
                content_box = draw_collapsible_section(advanced_params_box, "show_scene_understanding_settings", "Viewpoint Blending Settings", icon="ZOOM_IN")
            else:
                content_box = None
            if content_box:
                # Row 1: Discard-Over Angle | Weight Exponent
                split = content_box.split(factor=0.5, align=True)
                sub = split.row()
                if 'discard_factor' in _diff_props:
                    sub.alert = True
                sub.prop(scene, "discard_factor", text="Discard Angle")
                if 'discard_factor' in _diff_props:
                    sub.label(text="→" + _diff_props['discard_factor'])
                sub = split.row()
                if 'weight_exponent' in _diff_props:
                    sub.alert = True
                sub.prop(scene, "weight_exponent", text="Exponent")
                if 'weight_exponent' in _diff_props:
                    sub.label(text="→" + _diff_props['weight_exponent'])

                # Row 2 & 3: Reset toggles and values (only for sequential / qwen)
                if scene.generation_method == 'sequential' or scene.model_architecture in ('qwen_image_edit', 'flux2_klein'):
                    split = content_box.split(factor=0.5, align=True)
                    split.prop(scene, "discard_factor_generation_only", text="Reset Angle", toggle=True)
                    split.prop(scene, "weight_exponent_generation_only", text="Reset Exponent", toggle=True)

                    if scene.discard_factor_generation_only or scene.weight_exponent_generation_only:
                        split = content_box.split(factor=0.5, align=True)
                        if scene.discard_factor_generation_only:
                            split.prop(scene, "discard_factor_after_generation", text="Angle After")
                        else:
                            split.label(text="")
                        if scene.weight_exponent_generation_only:
                            split.prop(scene, "weight_exponent_after_generation", text="Exp. After")
                        else:
                            split.label(text="")

                row = content_box.row()
                row.prop(scene, "early_priority", text="Prioritize Initial Views", toggle=True, icon="REW")
                if scene.early_priority:
                    row = content_box.row()
                    row.prop(scene, "early_priority_strength", text="Priority Strength")

                row = content_box.row()
                row.prop(scene, "bake_visibility_weights", text="Bake Visibility (Transform-Stable)", toggle=True, icon="MESH_DATA")

                row = content_box.row()
                row.prop(scene, "sg_silhouette_margin", text="Silhouette Margin (px)")

                row = content_box.row()
                row.prop(scene, "sg_silhouette_depth", text="Silhouette Depth Threshold")

                row = content_box.row()
                row.prop(scene, "sg_silhouette_rays", text="Silhouette Rays")

            # --- Output & Material Settings ---
            if _show_diffusion_sections:
                content_box = draw_collapsible_section(advanced_params_box, "show_output_material_settings", "Output & Material Settings", icon="MATERIAL")
            else:
                content_box = None
            if content_box:
                # ── PBR Decomposition ──
                row = content_box.row()
                if 'pbr_decomposition' in _diff_props:
                    row.alert = True
                row.prop(scene, "pbr_decomposition", text="PBR Decomposition", toggle=True, icon="NODE_MATERIAL")
                if 'pbr_decomposition' in _diff_props:
                    row.label(text="→ " + _diff_props['pbr_decomposition'])
                if scene.pbr_decomposition:
                    # Warning if PBR decomposition nodes not detected
                    if not getattr(scene, 'pbr_nodes_available', False):
                        warn_row = content_box.row()
                        warn_row.alert = True
                        warn_split = warn_row.split(factor=0.9)
                        warn_split.label(text="PBR nodes not detected on server", icon="ERROR")
                        warn_split.operator("stablegen.check_server_status", text="", icon="FILE_REFRESH")
                    sub = content_box.box()
                    sub.label(text="PBR Decomposition", icon="NODE_MATERIAL")
                    # ── Map toggles ──
                    sub.label(text="Maps to Extract:", icon="IMAGE_DATA")
                    grid = sub.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
                    grid.prop(scene, "pbr_map_albedo", toggle=True, icon="SHADING_SOLID")
                    grid.prop(scene, "pbr_map_roughness", toggle=True, icon="MATFLUID")
                    grid.prop(scene, "pbr_map_metallic", toggle=True, icon="META_BALL")
                    grid.prop(scene, "pbr_map_normal", toggle=True, icon="NORMALS_FACE")
                    grid.prop(scene, "pbr_map_height", toggle=True, icon="MOD_DISPLACE")
                    grid.prop(scene, "pbr_map_ao", toggle=True, icon="SHADING_RENDERED")
                    grid.prop(scene, "pbr_map_emission", toggle=True, icon="LIGHT_POINT")
                    # ── Per-map adjustment controls ──
                    if scene.pbr_map_normal:
                        adj_row = sub.row()
                        adj_row.prop(scene, "pbr_normal_strength", text="Normal Strength", slider=True)
                    if scene.pbr_map_height:
                        adj_row = sub.row()
                        adj_row.prop(scene, "pbr_height_scale", text="Height Scale", slider=True)
                    if scene.pbr_map_ao:
                        ao_row = sub.row(align=True)
                        ao_row.prop(scene, "pbr_ao_samples", text="AO Samples")
                        ao_row.prop(scene, "pbr_ao_distance", text="AO Distance")
                    if scene.pbr_map_emission:
                        adj_row = sub.row()
                        adj_row.prop(scene, "pbr_emission_method", text="Method")
                        adj_row = sub.row()
                        adj_row.prop(scene, "pbr_emission_threshold", text="Threshold", slider=True)
                        adj_row = sub.row()
                        adj_row.prop(scene, "pbr_emission_strength", text="Emission Strength", slider=True)
                        if scene.pbr_emission_method == 'hsv':
                            hsv_row = sub.row(align=True)
                            hsv_row.prop(scene, "pbr_emission_saturation_min", text="Sat Min", slider=True)
                            hsv_row.prop(scene, "pbr_emission_value_min", text="Val Min", slider=True)
                            hsv_row = sub.row()
                            hsv_row.prop(scene, "pbr_emission_bloom", text="Bloom Radius", slider=True)
                    # ── Albedo source selector (only when albedo enabled) ──
                    if scene.pbr_map_albedo:
                        sub.separator()
                        row = sub.row()
                        row.prop(scene, "pbr_albedo_source", text="Albedo Source")
                        if scene.pbr_albedo_source == 'delight':
                            adj_row = sub.row()
                            adj_row.prop(scene, "pbr_delight_strength", text="Delight Strength", slider=True)
                        adj_row = sub.row(align=True)
                        adj_row.prop(scene, "pbr_albedo_auto_saturation", text="Correct Albedo Saturation", toggle=True, icon="BRUSHES_ALL")
                        if scene.pbr_albedo_auto_saturation:
                            adj_row.prop(scene, "pbr_albedo_saturation_mode", text="")
                    sub.separator()
                    # ── Quality settings ──
                    row = sub.row(align=True)
                    row.prop(scene, "pbr_use_native_resolution", text="Native Resolution", toggle=True, icon="FULLSCREEN_ENTER")
                    row.prop(scene, "pbr_tiling", text="")
                    if scene.pbr_tiling != 'off':
                        row = sub.row(align=True)
                        row.prop(scene, "pbr_tile_grid", text="Tile Grid (N\u00d7N)")
                        row.prop(scene, "pbr_tile_superres", text="Super Res", toggle=True, icon="IMAGE_PLANE")
                    if scene.pbr_tiling == 'custom':
                        row = sub.row(align=True)
                        row.prop(scene, "pbr_tile_albedo", text="Albedo", toggle=True)
                        row.prop(scene, "pbr_tile_material", text="Material", toggle=True)
                        row.prop(scene, "pbr_tile_normal", text="Normal", toggle=True)
                        row.prop(scene, "pbr_tile_height", text="Height", toggle=True)
                        row.prop(scene, "pbr_tile_emission", text="Emission", toggle=True)
                    if not scene.pbr_use_native_resolution:
                        row = sub.row()
                        row.prop(scene, "pbr_processing_resolution", text="Processing Resolution")
                    row = sub.row(align=True)
                    row.prop(scene, "pbr_denoise_steps", text="Denoise Steps")
                    row.prop(scene, "pbr_ensemble_size", text="Ensemble Size")
                    sub.separator()
                    row = sub.row()
                    row.prop(scene, "pbr_replace_color_with_albedo", text="Use Albedo as Base Color", toggle=True, icon="SHADING_SOLID")
                    row = sub.row()
                    row.prop(scene, "pbr_auto_lighting", text="Studio Lighting", toggle=True, icon="LIGHT_AREA")

                content_box.separator()
                split = content_box.split(factor=0.5)
                split.label(text="Fallback Color:")
                split.prop(scene, "fallback_color", text="")

                row = content_box.row()
                row.prop(scene, "auto_rescale", text="Auto Rescale Resolution", toggle=True, icon="ARROW_LEFTRIGHT")
                if scene.auto_rescale:
                    sub_box_rescale = content_box.box()
                    row = sub_box_rescale.row()
                    row.prop(scene, "auto_rescale_target_mp", text="Target Megapixels")
                    if scene.model_architecture.startswith('qwen'):
                        row = sub_box_rescale.row()
                        row.prop(scene, "qwen_rescale_alignment", text="Qwen VL-Aligned Rescale (112px)", toggle=True, icon="SNAP_INCREMENT")
                row = content_box.row()
                if 'overwrite_material' in _diff_props:
                    row.alert = True
                row.prop(scene, "overwrite_material", text="Overwrite Material", toggle=True, icon="FILE_REFRESH")
                if 'overwrite_material' in _diff_props:
                    row.label(text="→ " + _diff_props['overwrite_material'])

            # --- Image Guidance (IPAdapter & ControlNet) ---
            if _show_diffusion_sections:
                if scene.model_architecture in ['sdxl', 'flux1']:
                    content_box = draw_collapsible_section(advanced_params_box, "show_image_guidance_settings", "Image Guidance (IPAdapter & ControlNet)", icon="MODIFIER")
                elif scene.model_architecture == 'flux2_klein':
                    content_box = draw_collapsible_section(advanced_params_box, "show_image_guidance_settings", "FLUX.2 Klein Guidance", icon="MODIFIER")
                else: # Qwen Image Edit
                    content_box = draw_collapsible_section(advanced_params_box, "show_image_guidance_settings", "Qwen-Image-Edit Guidance", icon="MODIFIER")
            else:
                content_box = None
            if content_box:
                if scene.model_architecture in ('qwen_image_edit', 'flux2_klein'):
                    if scene.model_architecture == 'flux2_klein' or scene.qwen_generation_method == 'generate':
                        split = content_box.split(factor=0.5)
                        split.label(text="Guidance Map:")
                        split.prop(scene, "qwen_guidance_map_type", text="")

                        row = content_box.row()
                        row.prop(scene, "qwen_use_external_style_image", text="Use External Image as Style", toggle=True, icon="FILE_IMAGE")

                        # TRELLIS.2 input as style (only in trellis2 architecture mode)
                        if getattr(scene, 'architecture_mode', '') == 'trellis2':
                            row = content_box.row()
                            row.prop(scene, "qwen_use_trellis2_style", text="Use TRELLIS.2 Input as Style", toggle=True, icon="MESH_MONKEY")

                        if scene.qwen_use_external_style_image:
                            style_box = content_box.box()
                            row = style_box.row()
                            row.prop(scene, "qwen_external_style_image", text="Style Image")
                            row = style_box.row()
                            row.prop(scene, "qwen_external_style_initial_only", text="External for Initial Only", toggle=True)

                        if scene.qwen_use_external_style_image and scene.qwen_external_style_initial_only:
                            subsequent_box = style_box.box()
                            split = subsequent_box.split(factor=0.5)
                            split.label(text="Subsequent mode:")
                            split.prop(scene, "sequential_ipadapter_mode", text="")
                            if scene.sequential_ipadapter_mode == 'recent':
                                subsequent_box.prop(scene, "sequential_desaturate_factor", text="Desaturate")
                                subsequent_box.prop(scene, "sequential_contrast_factor", text="Reduce Contrast")

                        if getattr(scene, 'architecture_mode', '') == 'trellis2' and scene.qwen_use_trellis2_style:
                            t2_style_box = content_box.box()
                            row = t2_style_box.row()
                            row.prop(scene, "qwen_trellis2_style_initial_only", text="TRELLIS.2 Style for Initial Only", toggle=True)
                            if scene.qwen_trellis2_style_initial_only:
                                subsequent_box = t2_style_box.box()
                                split = subsequent_box.split(factor=0.5)
                                split.label(text="Subsequent mode:")
                                split.prop(scene, "sequential_ipadapter_mode", text="")
                                if scene.sequential_ipadapter_mode == 'recent':
                                    subsequent_box.prop(scene, "sequential_desaturate_factor", text="Desaturate")
                                    subsequent_box.prop(scene, "sequential_contrast_factor", text="Reduce Contrast")

                        if not scene.qwen_use_external_style_image and scene.generation_method in ['sequential', 'separate']:
                            row = content_box.row()
                            row.prop(scene, "sequential_ipadapter", text="Use Previous Image as Style", toggle=True, icon="MODIFIER")
                            if scene.sequential_ipadapter:
                                sub_ip_box = content_box.box()
                                split = sub_ip_box.split(factor=0.5)
                                split.label(text="Mode:")
                                split.prop(scene, "sequential_ipadapter_mode", text="")
                                if scene.sequential_ipadapter_mode == 'recent':
                                    sub_ip_box.prop(scene, "sequential_desaturate_factor", text="Desaturate")
                                    sub_ip_box.prop(scene, "sequential_contrast_factor", text="Reduce Contrast")

                        if scene.generation_method == 'sequential':
                            split = content_box.split(factor=0.5)
                            split.label(text="Context Render:")
                            split.prop(scene, "qwen_context_render_mode", text="")

                            row = content_box.row()
                            row.prop(scene, "qwen_voronoi_mode", text="Voronoi Projection", toggle=True, icon="MESH_GRID")
                    
                    elif scene.qwen_generation_method in ('refine', 'local_edit'):
                        row = content_box.row()
                        row.prop(scene, "qwen_refine_use_prev_ref", text="Use Previous Refined View", toggle=True)
                        
                        row = content_box.row()
                        row.prop(scene, "qwen_refine_use_depth", text="Use Depth Map", toggle=True, icon="MODIFIER")
                        
                        row = content_box.row()
                        row.prop(scene, "qwen_use_external_style_image", text="Use External Image as Style", toggle=True, icon="FILE_IMAGE")

                        # TRELLIS.2 input as style (only in trellis2 architecture mode)
                        if getattr(scene, 'architecture_mode', '') == 'trellis2':
                            row = content_box.row()
                            row.prop(scene, "qwen_use_trellis2_style", text="Use TRELLIS.2 Input as Style", toggle=True, icon="MESH_MONKEY")

                        if scene.qwen_use_external_style_image:
                            style_box = content_box.box()
                            row = style_box.row()
                            row.prop(scene, "qwen_external_style_image", text="Style Image")
                    
                    # Timestep-zero reference method — shared across all Qwen modes
                    row = content_box.row()
                    row.prop(scene, "qwen_timestep_zero_ref", text="Timestep-Zero References (color shift fix)", toggle=True, icon="COLORSET_08_VEC")

                    row = content_box.row()
                    row.prop(scene, "qwen_use_custom_prompts", text="Custom Guidance Prompts", toggle=True, icon="TEXT")
                    if scene.qwen_use_custom_prompts:
                        custom_prompt_box = content_box.box()
                        
                        # Initial Image Prompt
                        col = custom_prompt_box.column()
                        col.label(text="Initial Image Prompt:")
                        row = col.row(align=True)
                        row.prop(scene, "qwen_custom_prompt_initial", text="")
                        op = row.operator("stablegen.reset_qwen_prompt", text="", icon='FILE_REFRESH')
                        op.prompt_type = 'initial'

                        # Subsequent Images Prompt (conditional)
                        if scene.generation_method == 'sequential' or (scene.qwen_generation_method in ('refine', 'local_edit') and scene.qwen_refine_mode == 'sequential'):
                            col = custom_prompt_box.column()
                            col.label(text="Subsequent Images Prompt:")
                            row = col.row(align=True)
                            
                            if scene.qwen_context_render_mode == 'NONE' and scene.qwen_generation_method == 'generate':
                                row.prop(scene, "qwen_custom_prompt_seq_none", text="")
                                op_prop = 'seq_none'
                            elif scene.qwen_context_render_mode == 'REPLACE_STYLE' and scene.qwen_generation_method == 'generate':
                                row.prop(scene, "qwen_custom_prompt_seq_replace", text="")
                                op_prop = 'seq_replace'
                            elif scene.qwen_context_render_mode == 'ADDITIONAL' and scene.qwen_generation_method == 'generate':
                                row.prop(scene, "qwen_custom_prompt_seq_additional", text="")
                                op_prop = 'seq_additional'
                            else: # Refine mode or other
                                row.prop(scene, "qwen_custom_prompt_seq_none", text="")
                                op_prop = 'seq_none'
                            
                            op = row.operator("stablegen.reset_qwen_prompt", text="", icon='FILE_REFRESH')
                            op.prompt_type = op_prop

                    if (scene.generation_method == 'sequential' and scene.qwen_generation_method == 'generate' and
                            scene.qwen_context_render_mode in {'REPLACE_STYLE', 'ADDITIONAL'}):
                        context_box = content_box.box()
                        context_box.label(text="Context Render Options")

                        row = context_box.row()
                        row.prop(scene, "qwen_prompt_gray_background", text="Prompt: Gray Background", toggle=True)

                        if scene.qwen_use_custom_prompts:
                            colors_box = context_box.box()
                            colors_box.label(text="Context Render Colors")
                            row = colors_box.row()
                            row.prop(scene, "qwen_guidance_background_color", text="Background")
                            row = colors_box.row()
                            row.prop(scene, "qwen_guidance_fallback_color", text="Fallback")

                        dilation_row = context_box.row()
                        dilation_row.prop(scene, "qwen_context_fallback_dilation", text="Fallback Dilate (px)")

                        cleanup_row = context_box.row()
                        cleanup_row.prop(scene, "qwen_context_cleanup", text="Apply Cleanup", toggle=True, icon="BRUSH_DATA")
                        if scene.qwen_context_cleanup:
                            row = context_box.row()
                            row.prop(scene, "qwen_context_cleanup_hue_tolerance", text="Hue Tol (°)")
                            row = context_box.row()
                            row.prop(scene, "qwen_context_cleanup_value_adjust", text="Value Adjust")

                elif scene.model_architecture == 'sdxl' or scene.model_architecture == 'flux1':
                    # IPAdapter Parameters
                    if not scene.generation_method == 'uv_inpaint':
                        ipadapter_main_box = content_box.box() # Group IPAdapter settings together
                        if scene.model_architecture == 'flux1':
                            row = ipadapter_main_box.row()
                            row.prop(scene, "use_flux_lora", text="Use Flux Depth LoRA", toggle=True, icon="MODIFIER")
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
                            if context.scene.model_architecture == 'sdxl':
                                split.label(text="Weight Type:")
                                split.prop(scene, "ipadapter_weight_type", text="")
                    
                    content_box.separator() # Separator between IPAdapter and ControlNet if both are shown
                    # ControlNet Parameters
                    if not (scene.model_architecture == 'flux1' and scene.use_flux_lora):
                        cn_box = content_box.box()
                        row = cn_box.row()
                        row.alignment = 'CENTER'
                        row.label(text="ControlNet Units", icon="NODETREE")
                        for i, unit in enumerate(scene.controlnet_units): 
                            sub_unit_box = cn_box.box() # Each unit gets its own box
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
                        
                        btn_row = cn_box.row(align=True) 
                        if width_mode == 'wide':
                            btn_row.operator("stablegen.add_controlnet_unit", text="Add Unit", icon="ADD")
                            btn_row.operator("stablegen.remove_controlnet_unit", text="Remove Unit", icon="REMOVE")
                        else:
                            cn_box.operator("stablegen.add_controlnet_unit", text="Add ControlNet Unit", icon="ADD")
                            cn_box.operator("stablegen.remove_controlnet_unit", text="Remove Last ControlNet Unit", icon="REMOVE")

            if _show_diffusion_sections and scene.model_architecture not in ('qwen_image_edit', 'flux2_klein'):
                # --- Inpainting Options (Conditional) ---
                if scene.generation_method == 'uv_inpaint' or scene.generation_method == 'sequential':
                    content_box = draw_collapsible_section(advanced_params_box, "show_masking_inpainting_settings", "Inpainting Options", icon="MOD_MASK")
                    if content_box: # content_box is the container for these settings
                        row = content_box.row()
                        if 'differential_diffusion' in _diff_props:
                            row.alert = True
                        row.prop(scene, "differential_diffusion", text="Use Differential Diffusion", toggle=True, icon="SMOOTHCURVE")
                        if 'differential_diffusion' in _diff_props:
                            row.label(text="→ " + _diff_props['differential_diffusion'])
                        
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
            if _show_diffusion_sections:
                mode_specific_outer_box = draw_collapsible_section(advanced_params_box, "show_mode_specific_settings", "Generation Mode Specifics", icon="OPTIONS")
            else:
                mode_specific_outer_box = None
            if mode_specific_outer_box: # This is the box where all mode-specific UIs should go
                
                # Qwen Local Edit Mode Parameters
                if scene.model_architecture.startswith('qwen') and scene.qwen_generation_method == 'local_edit':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Qwen Local Edit Parameters", icon='BRUSH_DATA')
                    row = mode_specific_outer_box.row()
                    if 'denoise' in _diff_props:
                        row.alert = True
                    row.prop(scene, "denoise", text="Denoise")
                    if 'denoise' in _diff_props:
                        row.label(text="→ " + _diff_props['denoise'])
                    
                    # Angle Ramp Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "refine_angle_ramp_active", text="Use Angle-Based Blending", icon="DRIVER")
                    if scene.refine_angle_ramp_active:
                        row = box.row()
                        row.prop(scene, "refine_angle_ramp_pos_0", text="Black Point")
                        row.prop(scene, "refine_angle_ramp_pos_1", text="White Point")
                    
                    # Feather Ramp Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "visibility_vignette", text="Use Vignette Blending", icon="DRIVER")
                    if scene.visibility_vignette:
                        row = box.row()
                        row.prop(scene, "refine_feather_ramp_pos_0", text="Black Point")
                        row.prop(scene, "refine_feather_ramp_pos_1", text="White Point")
                        row = box.row()
                        row.prop(scene, "visibility_vignette_width", text="Feather Width")
                        if width_mode == 'narrow':
                            row = box.row()
                        row.prop(scene, "visibility_vignette_softness", text="Feather Softness")
                        row = box.row()
                        row.prop(scene, "visibility_vignette_blur", text="Blur Mask", icon="SURFACE_NSPHERE")

                    # Edge Feather Projection Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "refine_edge_feather_projection", text="Edge Feather (Projection)", icon="MOD_EDGESPLIT")
                    if scene.refine_edge_feather_projection:
                        row = box.row()
                        row.prop(scene, "refine_edge_feather_width", text="Feather Width (px)")
                        row = box.row()
                        row.prop(scene, "refine_edge_feather_softness", text="Feather Softness")

                    # Color Matching
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "view_blend_use_color_match", text="Match Colors to Viewport", toggle=True, icon="COLOR")
                    if scene.view_blend_use_color_match:
                        row = box.row(align=True)
                        row.prop(scene, "view_blend_color_match_method", text="Method")
                        row = box.row()
                        row.prop(scene, "view_blend_color_match_strength", text="Strength")

                # Qwen Refine Mode Parameters
                elif scene.model_architecture.startswith('qwen') and scene.qwen_generation_method == 'refine':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Qwen Refine Parameters", icon='SHADERFX')
                    row = mode_specific_outer_box.row()
                    if 'denoise' in _diff_props:
                        row.alert = True
                    row.prop(scene, "denoise", text="Denoise")
                    if 'denoise' in _diff_props:
                        row.label(text="→ " + _diff_props['denoise'])

                # Grid Mode Parameters
                elif scene.generation_method == 'grid':
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
                        if 'denoise' in _diff_props:
                            row.alert = True
                        row.prop(scene, "denoise", text="Denoise")
                        if 'denoise' in _diff_props:
                            row.label(text="→ " + _diff_props['denoise'])
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
                elif scene.generation_method == 'separate':
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

                        if scene.sequential_ipadapter_mode == 'recent':
                            sub_ip_box_separate.prop(scene, "sequential_desaturate_factor", text="Desaturate")
                            sub_ip_box_separate.prop(scene, "sequential_contrast_factor", text="Reduce Contrast")

                        if context.scene.model_architecture not in ('qwen_image_edit', 'flux2_klein'):
                            split = sub_ip_box_separate.split(factor=0.5) 
                            if context.scene.model_architecture == 'sdxl':
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
                    if 'denoise' in _diff_props:
                        row.alert = True
                    row.prop(scene, "denoise", text="Denoise")
                    if 'denoise' in _diff_props:
                        row.label(text="→ " + _diff_props['denoise'])
                    row = mode_specific_outer_box.row() 
                    row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Refine Mode", toggle=True, icon="MODIFIER")
                    if scene.sequential_ipadapter: 
                        sub_ip_box_separate = mode_specific_outer_box.box()
                        
                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Mode:")
                        split.prop(scene, "sequential_ipadapter_mode", text="") 

                        split = sub_ip_box_separate.split(factor=0.5) 
                        if context.scene.model_architecture == 'sdxl':
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

                # Local Edit Mode Parameters
                elif scene.generation_method == 'local_edit':
                    row = mode_specific_outer_box.row()
                    row.alignment = 'CENTER'
                    row.label(text="Local Edit Parameters", icon='BRUSH_DATA')
                    row = mode_specific_outer_box.row()
                    if 'denoise' in _diff_props:
                        row.alert = True
                    row.prop(scene, "denoise", text="Denoise")
                    if 'denoise' in _diff_props:
                        row.label(text="→ " + _diff_props['denoise'])
                    
                    # Angle Ramp Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "refine_angle_ramp_active", text="Use Angle-Based Blending", icon="DRIVER")
                    if scene.refine_angle_ramp_active:
                        row = box.row()
                        row.prop(scene, "refine_angle_ramp_pos_0", text="Black Point")
                        row.prop(scene, "refine_angle_ramp_pos_1", text="White Point")
                    
                    # Feather Ramp Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "visibility_vignette", text="Use Vignette Blending", icon="DRIVER")
                    if scene.visibility_vignette:
                        row = box.row()
                        row.prop(scene, "refine_feather_ramp_pos_0", text="Black Point")
                        row.prop(scene, "refine_feather_ramp_pos_1", text="White Point")
                        row = box.row()
                        row.prop(scene, "visibility_vignette_width", text="Feather Width")
                        if width_mode == 'narrow':
                            row = box.row()
                        row.prop(scene, "visibility_vignette_softness", text="Feather Softness")
                        row = box.row()
                        row.prop(scene, "visibility_vignette_blur", text="Blur Mask", icon="SURFACE_NSPHERE")

                    # Edge Feather Projection Controls
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "refine_edge_feather_projection", text="Edge Feather (Projection)", icon="MOD_EDGESPLIT")
                    if scene.refine_edge_feather_projection:
                        row = box.row()
                        row.prop(scene, "refine_edge_feather_width", text="Feather Width (px)")
                        row = box.row()
                        row.prop(scene, "refine_edge_feather_softness", text="Feather Softness")

                    # Color Matching
                    box = mode_specific_outer_box.box()
                    row = box.row()
                    row.prop(scene, "view_blend_use_color_match", text="Match Colors to Viewport", toggle=True, icon="COLOR")
                    if scene.view_blend_use_color_match:
                        row = box.row(align=True)
                        row.prop(scene, "view_blend_color_match_method", text="Method")
                        row = box.row()
                        row.prop(scene, "view_blend_color_match_strength", text="Strength")

                    row = mode_specific_outer_box.row() 
                    row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Local Edit", toggle=True, icon="MODIFIER")
                    if scene.sequential_ipadapter: 
                        sub_ip_box_separate = mode_specific_outer_box.box()
                        
                        split = sub_ip_box_separate.split(factor=0.5) 
                        split.label(text="Mode:")
                        split.prop(scene, "sequential_ipadapter_mode", text="") 

                        split = sub_ip_box_separate.split(factor=0.5) 
                        if context.scene.model_architecture == 'sdxl':
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
                    
                    if not (scene.differential_diffusion and not scene.differential_noise): 
                        row = mode_specific_outer_box.row()
                        if 'sequential_smooth' in _diff_props:
                            row.alert = True
                        row.prop(scene, "sequential_smooth", text="Use Smooth Visibility Map", toggle=True, icon="MOD_SMOOTH")
                        if 'sequential_smooth' in _diff_props:
                            row.label(text="→ " + _diff_props['sequential_smooth'])
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
                    
                    row = mode_specific_outer_box.row()
                    row.prop(scene, "sequential_ipadapter", text="Use IPAdapter for Sequential Mode", toggle=True, icon="MODIFIER")
                    if scene.sequential_ipadapter:
                        sub_ip_seq_box = mode_specific_outer_box.box()
                        
                        split = sub_ip_seq_box.split(factor=0.5)
                        split.label(text="Mode:")
                        split.prop(scene, "sequential_ipadapter_mode", text="")

                        if scene.sequential_ipadapter_mode == 'recent':
                            sub_ip_seq_box.prop(scene, "sequential_desaturate_factor", text="Desaturate")
                            sub_ip_seq_box.prop(scene, "sequential_contrast_factor", text="Reduce Contrast")

                        if context.scene.model_architecture not in ('qwen_image_edit', 'flux2_klein'):
                            split = sub_ip_seq_box.split(factor=0.5)
                            if context.scene.model_architecture == 'sdxl':
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
        if config_error_message:
            row.enabled = False
            row.operator("object.export_orbit_gif", text=f"Cannot Export: {config_error_message}", icon="ERROR")
        else:
            row.enabled = True
            row.operator("object.export_orbit_gif", text="Export Orbit GIF/MP4", icon="RENDER_ANIMATION")

        if width_mode == 'narrow':
            row = tools_box.row()
        row.operator("object.stablegen_reproject", text="Reproject Textures", icon="FILE_REFRESH")

        row = tools_box.row()
        row.operator("object.stablegen_mirror_reproject", text="Mirror Last Projection", icon="MOD_MIRROR")

        # --- Debug Tools ---
        prefs = context.preferences.addons.get(__package__)
        if prefs and prefs.preferences.enable_debug:
            layout.separator()
            debug_box = layout.box()
            row = debug_box.row()
            row.alignment = 'CENTER'
            row.label(text="Debug / Diagnostics", icon="GHOST_ENABLED")

            row = debug_box.row()
            row.operator("stablegen.debug_solid_colors", text="Draw Solid Colors", icon="COLOR")
            if width_mode == 'narrow':
                row = debug_box.row()
            row.operator("stablegen.debug_grid_pattern", text="Grid Pattern", icon="MESH_GRID")

            row = debug_box.row()
            row.operator("stablegen.debug_coverage_heatmap", text="Coverage Heatmap", icon="AREA_SWAP")
            if width_mode == 'narrow':
                row = debug_box.row()
            row.operator("stablegen.debug_visibility_material", text="Visibility Material", icon="HIDE_OFF")

            row = debug_box.row()
            row.operator("stablegen.debug_uv_seam_viz", text="UV Seam Visualizer", icon="UV")
            if width_mode == 'narrow':
                row = debug_box.row()
            row.operator("stablegen.debug_restore_material", text="Remove Debug Mats", icon="TRASH")

            row = debug_box.row()
            op = row.operator("stablegen.debug_per_camera_weight", text="Per-Camera Weight", icon="CAMERA_DATA")
            if width_mode == 'narrow':
                row = debug_box.row()
            op2 = row.operator("stablegen.debug_feather_preview", text="Feather Preview", icon="MOD_SMOOTH")

        # --- Narrow panel hint ---
        if width_mode == 'narrow':
            hint_row = layout.row()
            hint_row.alignment = 'CENTER'
            hint_row.label(text="Widen panel for side-by-side layout", icon="INFO")

        layout.separator()
          

class ResetQwenPrompt(bpy.types.Operator):
    """Resets a guidance prompt to its default value"""
    bl_idname = "stablegen.reset_qwen_prompt"
    bl_label = "Reset Qwen Prompt"
    bl_description = "Reset this prompt to its default value based on the current settings"

    prompt_type: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return not sg_modal_active(context)

    def execute(self, context):
        from .workflows import WorkflowManager
        # We need an operator instance to call the helper, a bit of a workaround
        # This doesn't run generation, just gives us access to the method
        wm = WorkflowManager(self) 

        # Choose the correct default prompt builder for the active architecture
        is_klein = getattr(context.scene, 'model_architecture', '') == 'flux2_klein'
        get_defaults = wm._get_klein_default_prompts if is_klein else wm._get_qwen_default_prompts

        # Determine which prompt to reset
        if self.prompt_type == 'initial':
            default_prompt = get_defaults(context, is_initial_image=True)
            context.scene.qwen_custom_prompt_initial = default_prompt
        elif self.prompt_type == 'seq_none':
            default_prompt = get_defaults(context, is_initial_image=False)
            context.scene.qwen_custom_prompt_seq_none = default_prompt
        elif self.prompt_type == 'seq_replace':
            default_prompt = get_defaults(context, is_initial_image=False)
            context.scene.qwen_custom_prompt_seq_replace = default_prompt
        elif self.prompt_type == 'seq_additional':
            default_prompt = get_defaults(context, is_initial_image=False)
            context.scene.qwen_custom_prompt_seq_additional = default_prompt
        
        self.report({'INFO'}, "Prompt reset to default.")
        return {'FINISHED'}

class ApplyPreset(bpy.types.Operator):
    """Apply selected preset values to parameters"""
    bl_idname = "stablegen.apply_preset"
    bl_label = "Apply Preset"
    bl_description = "Set multiple parameters based on selected preset for easier configuration"

    @classmethod
    def poll(cls, context):
        return not sg_modal_active(context)

    def execute(self, context):
        preset = context.scene.stablegen_preset
        if preset in PRESETS:
            values = PRESETS[preset]
            
            # Apply architecture_mode first so dynamic enums that
            # depend on it (e.g. sequential_ipadapter_mode) are valid
            # when their values are set in the main loop.
            if "architecture_mode" in values and hasattr(context.scene, "architecture_mode"):
                try:
                    setattr(context.scene, "architecture_mode", values["architecture_mode"])
                except (TypeError, AttributeError):
                    pass

            # Apply regular parameters
            skipped = []
            for key, value in values.items():
                if key not in ["controlnet_units", "lora_units", "description"] and hasattr(context.scene, key):
                    try:
                        setattr(context.scene, key, value)
                    except (TypeError, AttributeError):
                        # Dynamic enum values (e.g. trellis2_input) may not
                        # exist when the current architecture differs.
                        skipped.append(key)
            
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
                        
            # Reverse-sync: if the preset set model_architecture but didn't
            # include architecture_mode, update the visible dropdown to match.
            if "architecture_mode" not in values:
                arch = context.scene.model_architecture
                if arch in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein'):
                    context.scene.architecture_mode = arch

            if skipped:
                self.report({'WARNING'}, f"Preset '{preset}' applied (skipped {len(skipped)} incompatible setting(s)).")
            else:
                self.report({'INFO'}, f"Preset '{preset}' applied.")
        else:
            self.report({'INFO'}, "Custom preset active.")
        
        # Force update to ensure preset detection is correct after list changes
        update_parameters(self, context)

        return {'FINISHED'}

class SwitchToMeshGeneration(bpy.types.Operator):
    """Switch to mesh generation mode using TRELLIS.2"""
    bl_idname = "stablegen.switch_to_mesh_generation"
    bl_label = "Switch to Mesh Generation"
    bl_description = "Apply the TRELLIS.2 (Mesh Only) preset to generate 3D meshes"

    @classmethod
    def poll(cls, context):
        return (not sg_modal_active(context)
                and "TRELLIS.2 (MESH ONLY)" in PRESETS
                and getattr(context.scene, 'trellis2_available', False))

    def execute(self, context):
        context.scene.stablegen_preset = "TRELLIS.2 (MESH ONLY)"
        bpy.ops.stablegen.apply_preset()
        return {'FINISHED'}


class SavePreset(bpy.types.Operator):
    """Save the current parameter values as a custom preset"""
    bl_idname = "stablegen.save_preset"
    bl_label = "Save Custom Preset"

    @classmethod
    def poll(cls, context):
        return not sg_modal_active(context)

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

        # Print LoRA units in a compact format if included
        if self.include_loras:
            print(f'"lora_units": {lora_units_data},', end="")
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

    @classmethod
    def poll(cls, context):
        return not sg_modal_active(context)

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


# =====================================================================
# Scene Queue System
# =====================================================================
# Allows users to queue multiple Blender scenes for unattended batch
# processing.  Each queued scene is processed in order — the manager
# switches to the scene, invokes the appropriate generation operator
# (TRELLIS.2 or standard texturing), waits for completion, optionally
# saves a .blend copy, then advances to the next item.

_queue_timer = None          # Reference to the active timer callback
_queue_processing = False    # Global flag: queue is being processed
_queue_current_idx = 0       # Index of the currently-processing item
_queue_phase = 'idle'        # 'idle' | 'switching' | 'running' | 'settling' | 'waiting_texturing' | 'exporting_gif'
_queue_settle_deadline = 0.0 # monotonic time after which 'settling' may finish
_queue_force_reload = False  # Force re-open of the .blend on next idle tick (for retries)
_queue_texturing_seen = False  # Set True once generation_status='running' is observed during settling
_queue_refresh_deadline = 0.0  # monotonic deadline while waiting for model-list refresh
_queue_original_pbr = False    # stored pbr_decomposition before no-PBR reproject
_queue_original_gen_method = 'sequential'  # stored generation_method before reproject
_queue_original_overwrite = True  # stored overwrite_material before reproject
_QUEUE_MAX_RETRIES = 3       # how many times a failed item is retried


class SG_UL_SceneQueueList(bpy.types.UIList):
    """UIList for the scene generation queue."""
    bl_idname = "SG_UL_SceneQueueList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Label (or scene name as fallback)
            display = item.label if item.label else item.scene_name
            row.label(text=display, icon='SCENE_DATA')

            # Status icon + retry indicator
            if item.status == 'done':
                row.label(text="", icon='CHECKMARK')
            elif item.status == 'error':
                retry_txt = f"x{item.retries}" if item.retries else ""
                if item.error_reason:
                    reason_short = item.error_reason[:28] + "…" if len(item.error_reason) > 30 else item.error_reason
                    row.label(text=f"{reason_short} {retry_txt}".strip(), icon='ERROR')
                else:
                    row.label(text=retry_txt, icon='ERROR')
            elif item.status == 'processing':
                retry_txt = f"#{item.retries + 1}" if item.retries else ""
                row.label(text=retry_txt, icon='SORTTIME')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            display = item.label if item.label else item.scene_name
            layout.label(text=display, icon='SCENE_DATA')


def _persist_queue():
    """Write the queue + processing state to a JSON file on disk."""
    try:
        from . import _sg_queue_save
        _sg_queue_save(
            processing=_queue_processing,
            current_idx=_queue_current_idx,
            phase=_queue_phase,
        )
    except Exception:
        pass


def _resume_queue(idx):
    """Resume queue processing from *idx* (called after a .blend switch).

    This is invoked by ``_sg_queue_load()`` in ``__init__.py`` when the
    JSON file indicates that processing was active.
    """
    global _queue_processing, _queue_current_idx, _queue_phase, _queue_timer

    _queue_processing = True
    _queue_current_idx = idx
    _queue_phase = 'idle'

    # Avoid duplicate timers
    if _queue_timer is not None:
        try:
            bpy.app.timers.unregister(_queue_tick)
        except Exception:
            pass

    _queue_timer = bpy.app.timers.register(_queue_tick, first_interval=1.5)
    print(f"[Queue] Resumed processing from item {idx}")
    _tag_redraw()


class SceneQueueAdd(bpy.types.Operator):
    """Add the current scene to the generation queue.

    Saves a *copy* of the current .blend into ``<output_dir>/queue_jobs/``.
    The queue item points at that copy so the original file is never
    modified by queue processing.
    """
    bl_idname = "stablegen.queue_add"
    bl_label = "Add to Queue"
    bl_description = "Snapshot the current .blend and add the scene to the batch queue"
    bl_options = {'REGISTER', 'UNDO'}

    item_label: bpy.props.StringProperty(
        name="Name",
        description="A short label for this queue entry",
        default="",
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return not _queue_processing and not sg_modal_active(context)

    def invoke(self, context, event):
        scene = context.scene
        cur_prompt = getattr(scene, 'comfyui_prompt', '')
        # Pre-fill with a truncated prompt
        self.item_label = (cur_prompt[:40]) if cur_prompt else scene.name
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "item_label")

    def execute(self, context):
        import time

        wm = context.window_manager
        scene = context.scene
        scene_name = scene.name
        cur_prompt = getattr(scene, 'comfyui_prompt', '')
        cur_neg = getattr(scene, 'comfyui_negative_prompt', '')
        label = self.item_label.strip() or scene_name

        # Determine queue_jobs directory
        prefs = context.preferences.addons.get(__package__)
        output_dir = ''
        if prefs:
            output_dir = bpy.path.abspath(prefs.preferences.output_dir or '')
        if not output_dir or not os.path.isdir(output_dir):
            self.report({'ERROR'}, "Set an Output Directory in StableGen preferences first.")
            return {'CANCELLED'}

        jobs_dir = os.path.join(output_dir, "queue_jobs")
        os.makedirs(jobs_dir, exist_ok=True)

        # Build filename from the user-provided label
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_label = label.replace(" ", "_").replace("/", "_").replace("\\", "_")
        # Truncate to keep filenames reasonable
        safe_label = safe_label[:60]
        copy_name = f"{safe_label}_{timestamp}.blend"
        copy_path = os.path.join(jobs_dir, copy_name)

        # Save a copy — current file stays active & untouched
        # Snapshot the model_name into the plain-string backup property
        # BEFORE saving so the copy carries the correct value even if
        # the dynamic Enum resolves wrong on re-open (stale item cache).
        scene.sg_model_name_backup = scene.model_name
        try:
            bpy.ops.wm.save_as_mainfile(filepath=copy_path, copy=True)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save queue snapshot: {e}")
            return {'CANCELLED'}

        new_item = wm.sg_scene_queue.add()
        new_item.label = label
        new_item.scene_name = scene_name
        new_item.blend_file = copy_path
        new_item.prompt = cur_prompt
        new_item.negative_prompt = cur_neg
        new_item.status = 'pending'
        wm.sg_scene_queue_index = len(wm.sg_scene_queue) - 1
        _persist_queue()

        self.report({'INFO'}, f"Queued '{label}' ({copy_name})")
        return {'FINISHED'}


class SceneQueueRemove(bpy.types.Operator):
    """Remove the selected scene from the queue"""
    bl_idname = "stablegen.queue_remove"
    bl_label = "Remove from Queue"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return not _queue_processing and len(wm.sg_scene_queue) > 0 and not sg_modal_active(context)

    def invoke(self, context, event):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        if 0 <= idx < len(wm.sg_scene_queue):
            item = wm.sg_scene_queue[idx]
            display = item.label or item.scene_name
            # Show a confirmation popup
            return context.window_manager.invoke_confirm(self, event,
                message=f"Remove '{display}' from queue?",
                confirm_text="Remove")
        return {'CANCELLED'}

    def execute(self, context):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        if 0 <= idx < len(wm.sg_scene_queue):
            item = wm.sg_scene_queue[idx]
            display = item.label or item.scene_name
            # Delete the snapshot .blend if the item hasn't been processed
            if item.status != 'done' and item.blend_file:
                try:
                    blend_path = item.blend_file
                    if os.path.isfile(blend_path):
                        os.remove(blend_path)
                        print(f"[Queue] Deleted snapshot: {blend_path}")
                except Exception as e:
                    print(f"[Queue] Could not delete snapshot: {e}")
            wm.sg_scene_queue.remove(idx)
            wm.sg_scene_queue_index = min(idx, len(wm.sg_scene_queue) - 1)
            _persist_queue()
            self.report({'INFO'}, f"Removed '{display}' from queue.")
        return {'FINISHED'}


class SceneQueueClear(bpy.types.Operator):
    """Clear the entire queue"""
    bl_idname = "stablegen.queue_clear"
    bl_label = "Clear Queue"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return not _queue_processing and len(wm.sg_scene_queue) > 0 and not sg_modal_active(context)

    def invoke(self, context, event):
        wm = context.window_manager
        count = len(wm.sg_scene_queue)
        return context.window_manager.invoke_confirm(self, event,
            message=f"Clear all {count} item(s) from queue?",
            confirm_text="Clear All")

    def execute(self, context):
        wm = context.window_manager
        # Delete snapshot .blends for unprocessed items
        for item in wm.sg_scene_queue:
            if item.status != 'done' and item.blend_file:
                try:
                    if os.path.isfile(item.blend_file):
                        os.remove(item.blend_file)
                        print(f"[Queue] Deleted snapshot: {item.blend_file}")
                except Exception as e:
                    print(f"[Queue] Could not delete snapshot: {e}")
        wm.sg_scene_queue.clear()
        wm.sg_scene_queue_index = 0
        _persist_queue()
        self.report({'INFO'}, "Queue cleared.")
        return {'FINISHED'}


class SceneQueueMoveUp(bpy.types.Operator):
    """Move the selected queue item up"""
    bl_idname = "stablegen.queue_move_up"
    bl_label = "Move Up"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return not _queue_processing and wm.sg_scene_queue_index > 0 and not sg_modal_active(context)

    def execute(self, context):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        wm.sg_scene_queue.move(idx, idx - 1)
        wm.sg_scene_queue_index -= 1
        return {'FINISHED'}


class SceneQueueMoveDown(bpy.types.Operator):
    """Move the selected queue item down"""
    bl_idname = "stablegen.queue_move_down"
    bl_label = "Move Down"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return (not _queue_processing
                and wm.sg_scene_queue_index < len(wm.sg_scene_queue) - 1
                and not sg_modal_active(context))

    def execute(self, context):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        wm.sg_scene_queue.move(idx, idx + 1)
        wm.sg_scene_queue_index += 1
        return {'FINISHED'}


class SceneQueueOpenResult(bpy.types.Operator):
    """Open the .blend snapshot for the selected queue item"""
    bl_idname = "stablegen.queue_open_result"
    bl_label = "Open"
    bl_description = "Open the .blend snapshot of the selected queue item"

    @classmethod
    def poll(cls, context):
        if sg_modal_active(context):
            return False
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        if idx < 0 or idx >= len(wm.sg_scene_queue):
            return False
        item = wm.sg_scene_queue[idx]
        return bool(item.blend_file) and os.path.isfile(item.blend_file)

    def execute(self, context):
        wm = context.window_manager
        item = wm.sg_scene_queue[wm.sg_scene_queue_index]
        filepath = item.blend_file
        try:
            bpy.ops.wm.open_mainfile(filepath=filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open file: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


class SceneQueueInvalidate(bpy.types.Operator):
    """Reset a processed queue item back to pending and clear its scene"""
    bl_idname = "stablegen.queue_invalidate"
    bl_label = "Reset to Pending"
    bl_description = (
        "Reset the selected item to unprocessed, "
        "removing generated meshes and cameras from its snapshot "
        "so it can be re-processed"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        if _queue_processing:
            cls.poll_message_set("Queue is currently processing")
            return False
        if sg_modal_active(context):
            cls.poll_message_set("Another operation is in progress")
            return False
        if idx < 0 or idx >= len(wm.sg_scene_queue):
            cls.poll_message_set("No queue item selected")
            return False
        item = wm.sg_scene_queue[idx]
        if item.status not in ('done', 'error'):
            cls.poll_message_set("Only completed or failed items can be reset")
            return False
        if not item.blend_file or not os.path.isfile(item.blend_file):
            cls.poll_message_set("Snapshot .blend file not found")
            return False
        return True

    def invoke(self, context, event):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        item = wm.sg_scene_queue[idx]
        display = item.label or item.scene_name
        return context.window_manager.invoke_confirm(
            self, event,
            message=f"Reset '{display}'?\nThis will remove generated meshes and cameras from its snapshot and mark it as unprocessed.",
            confirm_text="Reset",
        )

    def execute(self, context):
        wm = context.window_manager
        idx = wm.sg_scene_queue_index
        item = wm.sg_scene_queue[idx]
        blend_path = item.blend_file
        display = item.label or item.scene_name

        # Open the processed .blend, clean it, save, then re-open current
        current_file = bpy.data.filepath

        try:
            bpy.ops.wm.open_mainfile(filepath=blend_path)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open snapshot: {e}")
            return {'CANCELLED'}

        # Remove all mesh objects and cameras from the scene
        scene = bpy.context.scene
        to_remove = [obj for obj in scene.objects if obj.type in {'MESH', 'CAMERA', 'EMPTY'}]
        for obj in to_remove:
            bpy.data.objects.remove(obj, do_unlink=True)

        # Purge orphaned data
        for block_attr in ('meshes', 'cameras', 'materials', 'images'):
            collection = getattr(bpy.data, block_attr, None)
            if collection is None:
                continue
            orphans = [b for b in collection if b.users == 0]
            for orphan in orphans:
                collection.remove(orphan)

        # Save the cleaned .blend in place
        try:
            bpy.ops.wm.save_mainfile()
            print(f"[Queue] Invalidated and saved: {blend_path}")
        except Exception as e:
            print(f"[Queue] Save warning during invalidate: {e}")

        # Mark the item as pending directly in the queue JSON file.
        # After open_mainfile the in-memory queue collection is empty
        # (it's restored 0.3 s later by the deferred load handler), so
        # patching the JSON is the only reliable approach.
        try:
            from . import _sg_queue_filepath
            fp = _sg_queue_filepath()
            if os.path.isfile(fp):
                import json as _json
                with open(fp, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                items_list = data.get("items", data) if isinstance(data, dict) else data
                if isinstance(items_list, list) and idx < len(items_list):
                    items_list[idx]["status"] = "pending"
                    items_list[idx]["retries"] = 0
                    items_list[idx]["error_reason"] = ""
                with open(fp, 'w', encoding='utf-8') as f:
                    _json.dump(data, f)
                print(f"[Queue] Marked item {idx} as pending in queue JSON")
        except Exception as e:
            print(f"[Queue] Warning: could not update queue JSON: {e}")

        # Re-open the original file (if we had one)
        if current_file and os.path.isfile(current_file):
            try:
                bpy.ops.wm.open_mainfile(filepath=current_file)
            except Exception:
                pass

        self.report({'INFO'}, f"Reset '{display}' — ready for re-processing")
        return {'FINISHED'}


class SceneQueueProcess(bpy.types.Operator):
    """Start or cancel batch processing of the scene queue"""
    bl_idname = "stablegen.queue_process"
    bl_label = "Process Queue"
    bl_description = "Process all queued scenes sequentially"

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        if _queue_processing:
            return True  # Allow clicking to cancel
        if len(wm.sg_scene_queue) == 0:
            cls.poll_message_set("Queue is empty — add scenes first")
            return False
        if sg_modal_active(context):
            cls.poll_message_set("Another operation is in progress")
            return False
        return True

    def execute(self, context):
        global _queue_processing, _queue_timer, _queue_current_idx, _queue_phase

        if _queue_processing:
            # Cancel
            _queue_processing = False
            _queue_phase = 'idle'
            _persist_queue()  # Save stopped state so load_post won't auto-resume
            print("[Queue] Cancelled by user.")
            self.report({'WARNING'}, "Queue processing cancelled.")
            return {'FINISHED'}

        # Reset statuses
        wm = context.window_manager
        for item in wm.sg_scene_queue:
            if item.status != 'done':
                item.status = 'pending'

        _queue_processing = True
        _queue_current_idx = 0
        _queue_phase = 'idle'

        # Find first pending item
        while _queue_current_idx < len(wm.sg_scene_queue):
            if wm.sg_scene_queue[_queue_current_idx].status == 'pending':
                break
            _queue_current_idx += 1

        if _queue_current_idx >= len(wm.sg_scene_queue):
            _queue_processing = False
            self.report({'INFO'}, "No pending items in queue.")
            return {'FINISHED'}

        # Start the timer-based queue driver
        _queue_timer = bpy.app.timers.register(_queue_tick, first_interval=0.5)
        self.report({'INFO'}, f"Queue processing started ({len(wm.sg_scene_queue)} items).")
        return {'FINISHED'}


def _queue_tick():
    """Timer callback that drives queue advancement.

    Returns:
        float: Seconds until next tick, or None to stop.
    """
    import time as _time
    global _queue_processing, _queue_current_idx, _queue_phase, _queue_timer
    global _queue_settle_deadline, _queue_force_reload, _queue_texturing_seen
    global _queue_refresh_deadline

    if not _queue_processing:
        _queue_phase = 'idle'
        _queue_timer = None
        _tag_redraw()
        return None  # Stop timer

    wm = bpy.context.window_manager
    queue = wm.sg_scene_queue

    if _queue_current_idx >= len(queue):
        # All done
        _queue_processing = False
        _queue_phase = 'idle'
        _queue_timer = None
        print("[Queue] All items processed.")
        _tag_redraw()
        return None

    item = queue[_queue_current_idx]

    # ── Phase: IDLE → switch to the next scene and start ──
    if _queue_phase == 'idle':
        # Verify the item belongs to the currently-open .blend
        current_blend = bpy.data.filepath or "<unsaved>"
        need_open = (item.blend_file and item.blend_file != current_blend)

        # On retry, always re-open the .blend to restore clean state
        is_retry_reload = False
        if _queue_force_reload and item.blend_file:
            need_open = True
            is_retry_reload = True
            _queue_force_reload = False

        if need_open:
            # Need to open a different .blend file
            target = item.blend_file
            if not os.path.isfile(target):
                print(f"[Queue] Blend file not found: {target} — skipping.")
                item.status = 'error'
                item.error_reason = "Blend file not found"
                _queue_current_idx += 1
                _persist_queue()
                _tag_redraw()
                return 0.5

            # Save current file first so nothing is lost — BUT skip save
            # on retry reloads; we want to discard dirty state and revert
            # to the original clean copy.
            if bpy.data.filepath and not is_retry_reload:
                try:
                    bpy.ops.wm.save_mainfile()
                except Exception as e:
                    print(f"[Queue] Warning: could not save current file: {e}")

            # Persist state so the load_post handler can resume after
            # the new file is opened.
            _persist_queue()
            print(f"[Queue] Opening '{os.path.basename(target)}' for item "
                  f"'{item.scene_name}'...")

            # Open the target file.  After this call the current WM
            # data (and our timer) are gone — the load_post handler
            # will restore the queue and call _resume_queue().
            try:
                bpy.ops.wm.open_mainfile(filepath=target)
            except Exception as e:
                print(f"[Queue] Failed to open '{target}': {e}")
                # Can't recover gracefully — stop processing
                _queue_processing = False
                _queue_phase = 'idle'
                _queue_timer = None
                _persist_queue()
                _tag_redraw()
            return None  # Stop timer — load_post will restart it

        scene_ref = bpy.data.scenes.get(item.scene_name)
        if not scene_ref:
            print(f"[Queue] Scene '{item.scene_name}' not found — skipping.")
            item.status = 'error'
            item.error_reason = "Scene not found"
            _queue_current_idx += 1
            _tag_redraw()
            return 0.5  # Try next immediately

        # Switch to the target scene
        bpy.context.window.scene = scene_ref
        item.status = 'processing'
        _queue_phase = 'switching'
        print(f"[Queue] Switched to scene '{item.scene_name}'")
        _tag_redraw()
        return 1.0  # Give Blender a moment to digest

    # ── Phase: SWITCHING → invoke the generation operator ──
    if _queue_phase == 'switching':
        scene_ref = bpy.context.scene
        arch_mode = getattr(scene_ref, 'architecture_mode', 'sdxl')

        # Wait for any in-flight checkpoint / LoRA refreshes to finish so
        # ``model_name`` resolves to the correct value.  The load_post
        # handler triggers an async refresh when the cached architecture
        # doesn't match the file that was just opened.
        from . import _pending_refreshes
        if _pending_refreshes > 0:
            if _queue_refresh_deadline == 0.0:
                _queue_refresh_deadline = _time.monotonic() + 15.0
            if _time.monotonic() < _queue_refresh_deadline:
                return 1.0  # Re-check on next tick
            else:
                print("[Queue] Model-list refresh timed out — proceeding anyway")
        _queue_refresh_deadline = 0.0  # Reset for next item

        # Clear the error flag before invoking
        scene_ref.sg_last_gen_error = False

        # Disable interactive elements for unattended batch
        if arch_mode == 'trellis2':
            scene_ref.trellis2_preview_gallery_enabled = False

        try:
            if arch_mode == 'trellis2':
                bpy.ops.object.trellis2_generate('INVOKE_DEFAULT')
                print(f"[Queue] Invoked trellis2_generate for '{item.scene_name}'")
            else:
                # Standard texturing — select all cameras first
                bpy.ops.object.select_all(action='DESELECT')
                for obj in scene_ref.objects:
                    if obj.type == 'CAMERA':
                        obj.select_set(True)
                bpy.ops.object.test_stable('INVOKE_DEFAULT')
                print(f"[Queue] Invoked test_stable for '{item.scene_name}'")
            _queue_phase = 'running'
        except Exception as e:
            print(f"[Queue] Failed to invoke operator for '{item.scene_name}': {e}")
            _queue_handle_failure(item, str(e))
        _tag_redraw()
        return 1.5

    # ── Phase: RUNNING → poll for completion ──
    if _queue_phase == 'running':
        from .generator import Trellis2Generate, ComfyUIGenerate
        scene_ref = bpy.context.scene
        arch_mode = getattr(scene_ref, 'architecture_mode', 'sdxl')

        if arch_mode == 'trellis2':
            trellis_running = Trellis2Generate._is_running
            gen_err = getattr(scene_ref, 'sg_last_gen_error', False)
            tex_mode = getattr(scene_ref, 'trellis2_texture_mode', 'native')
            pipe_active = getattr(scene_ref, 'trellis2_pipeline_active', False)
            gen_status = getattr(scene_ref, 'generation_status', 'idle')
            # TRELLIS.2: wait for the operator to finish
            if trellis_running:
                return 1.0  # Still running

            # Check if Trellis2 itself failed
            if gen_err:
                print(f"[Queue] TRELLIS.2 generation failed for '{item.scene_name}'")
                _queue_handle_failure(item, "TRELLIS.2 generation failed")
                return 0.5

            # Trellis2Generate finished — enter settling phase to wait for
            # _schedule_texture_generation / _deferred_generate to fire.
            if tex_mode in ('sdxl', 'flux1', 'qwen_image_edit', 'flux2_klein'):
                _queue_phase = 'settling'
                _queue_settle_deadline = _time.monotonic() + 15.0  # generous: server may need VRAM flush
                _queue_texturing_seen = False
                print(f"[Queue] TRELLIS.2 mesh done, entering settling (tex_mode='{tex_mode}'), "
                      f"waiting for texturing to start (up to 15 s)...")
            else:
                # Native texture mode — mesh only, done
                print(f"[Queue] tex_mode='{tex_mode}' — no diffusion texturing, finishing item")
                _queue_finish_item(item)
            return 1.0
        else:
            # Standard texturing
            gen_status = getattr(scene_ref, 'generation_status', 'idle')
            if gen_status in ('idle', 'waiting'):
                if getattr(scene_ref, 'sg_last_gen_error', False):
                    _queue_handle_failure(item, "Generation failed")
                    return 0.5
                _queue_finish_item(item)
                return 0.5
            return 1.0  # Still running

    # ── Phase: SETTLING → wait for TRELLIS.2 chained texturing to start ──
    if _queue_phase == 'settling':
        scene_ref = bpy.context.scene
        pipeline_active = getattr(scene_ref, 'trellis2_pipeline_active', False)
        gen_status = getattr(scene_ref, 'generation_status', 'idle')
        if pipeline_active or gen_status == 'running':
            _queue_texturing_seen = True

        if _queue_texturing_seen:
            if gen_status == 'running' or pipeline_active:
                # Texturing is actively running — transition
                _queue_phase = 'waiting_texturing'
                print(f"[Queue] Texturing confirmed running, waiting for completion...")
                return 1.0
            else:
                # Texturing already completed (fast finish during settling)
                if getattr(scene_ref, 'sg_last_gen_error', False):
                    _queue_handle_failure(item, "Texturing failed")
                else:
                    _queue_finish_item(item)
                return 0.5

        # Texturing hasn't appeared yet — wait until deadline
        if _time.monotonic() >= _queue_settle_deadline:
            print(f"[Queue] Texturing never started for '{item.scene_name}' (timeout)")
            _queue_handle_failure(item, "Diffusion texturing failed to start")
            return 0.5

        return 1.0  # Still settling

    # ── Phase: WAITING_TEXTURING → poll chained ComfyUIGenerate ──
    if _queue_phase == 'waiting_texturing':
        scene_ref = bpy.context.scene
        gen_status = getattr(scene_ref, 'generation_status', 'idle')
        pipeline_active = getattr(scene_ref, 'trellis2_pipeline_active', False)
        gen_err = getattr(scene_ref, 'sg_last_gen_error', False)

        if gen_status in ('idle', 'waiting') and not pipeline_active:
            if getattr(scene_ref, 'sg_last_gen_error', False):
                _queue_handle_failure(item, "Texturing failed")
                return 0.5
            _queue_finish_item(item)
            return 0.5
        return 1.0  # Still running

    # ── Phase: EXPORTING_GIF → poll ExportOrbitGIF completion ──
    if _queue_phase == 'exporting_gif':
        from .render_tools import ExportOrbitGIF
        if ExportOrbitGIF._rendering:
            return 1.0  # Still rendering frames
        # First GIF export finished
        print("[Queue] GIF export completed")

        # Check whether a second (no-PBR) export is needed
        wm = bpy.context.window_manager
        scene_ref = bpy.context.scene
        if (getattr(wm, 'sg_queue_gif_also_no_pbr', False)
                and getattr(scene_ref, 'pbr_decomposition', False)):
            # Start the no-PBR reproject → second GIF pipeline
            if _queue_start_no_pbr_reproject():
                _queue_phase = 'reprojecting_no_pbr'
                print("[Queue] Starting no-PBR reproject for second GIF")
                _tag_redraw()
                return 1.0
            else:
                print("[Queue] No-PBR reproject failed to start — skipping second GIF")

        _queue_save_and_advance(item)
        return 0.5

    # ── Phase: REPROJECTING_NO_PBR → wait for ComfyUIGenerate to finish ──
    if _queue_phase == 'reprojecting_no_pbr':
        from .generator import ComfyUIGenerate
        if ComfyUIGenerate._is_running:
            return 1.0
        # Reproject done — start second GIF with 1 sample + suffix
        print("[Queue] No-PBR reproject finished — starting second GIF export")
        if _queue_start_gif_export(samples_override=1, suffix='_no_pbr'):
            _queue_phase = 'exporting_gif_no_pbr'
            _tag_redraw()
            return 1.0
        else:
            print("[Queue] Second GIF export failed to start — restoring PBR")
            _queue_restore_pbr()
            _queue_save_and_advance(item)
            return 0.5

    # ── Phase: EXPORTING_GIF_NO_PBR → poll second GIF completion ──
    if _queue_phase == 'exporting_gif_no_pbr':
        from .render_tools import ExportOrbitGIF
        if ExportOrbitGIF._rendering:
            return 1.0
        print("[Queue] Second (no-PBR) GIF export completed")
        _queue_restore_pbr()
        _queue_save_and_advance(item)
        return 0.5

    return 1.0


def _queue_handle_failure(item, reason):
    """Handle a failed queue item — retry if under the limit, else mark as error."""
    global _queue_current_idx, _queue_phase, _queue_processing, _queue_timer
    global _queue_force_reload

    item.retries += 1
    if item.retries < _QUEUE_MAX_RETRIES:
        item.status = 'pending'
        _queue_phase = 'idle'  # Will re-attempt on next tick
        _queue_force_reload = True  # Force re-open to restore clean .blend state
        print(f"[Queue] Retrying '{item.label or item.scene_name}' "
              f"(attempt {item.retries + 1}/{_QUEUE_MAX_RETRIES}): {reason}")
    else:
        item.status = 'error'
        item.error_reason = reason
        print(f"[Queue] '{item.label or item.scene_name}' failed after "
              f"{_QUEUE_MAX_RETRIES} attempts: {reason}")
        _queue_current_idx += 1
        # Find next pending
        wm = bpy.context.window_manager
        while _queue_current_idx < len(wm.sg_scene_queue):
            if wm.sg_scene_queue[_queue_current_idx].status == 'pending':
                break
            _queue_current_idx += 1
        if _queue_current_idx >= len(wm.sg_scene_queue):
            _queue_processing = False
            _queue_phase = 'idle'
            _queue_timer = None
            print("[Queue] All queue items processed.")
        else:
            _queue_phase = 'idle'
    _persist_queue()
    _tag_redraw()


def _queue_finish_item(item):
    """Mark the current queue item as done and advance to the next.

    If GIF export is enabled, starts the orbit GIF export first and
    defers the save+advance to the ``exporting_gif`` phase handler.
    """
    global _queue_current_idx, _queue_phase, _queue_processing, _queue_timer

    item.status = 'done'
    print(f"[Queue] Finished '{item.scene_name}'")

    # ── Optional GIF export before saving ──
    wm = bpy.context.window_manager
    if getattr(wm, 'sg_queue_gif_export', False):
        if _queue_start_gif_export():
            _queue_phase = 'exporting_gif'
            print("[Queue] GIF export started — deferring save until export finishes")
            _tag_redraw()
            return  # save + advance will happen in the 'exporting_gif' handler

    # No GIF (or export failed to start) — save and advance immediately
    _queue_save_and_advance(item)


def _queue_start_gif_export(samples_override=None, suffix=''):
    """Try to invoke ExportOrbitGIF with current WM settings.

    Args:
        samples_override: If set, use this sample count instead of the WM setting.
        suffix: Appended to orbit filenames (e.g. '_no_pbr' → orbit_no_pbr.gif).

    Returns True if the operator was successfully started.
    """
    from .render_tools import ExportOrbitGIF

    scene = bpy.context.scene

    # ── Always use the first camera (Camera_0 or lowest-numbered) ──
    cameras = sorted(
        [o for o in scene.objects if o.type == 'CAMERA'],
        key=lambda c: c.name,
    )
    if not cameras:
        print("[Queue] No cameras in scene — skipping GIF export")
        return False
    scene.camera = cameras[0]
    print(f"[Queue] GIF export: using camera '{cameras[0].name}'")

    # ── Ensure an active mesh/empty exists (poll requirement) ──
    vl = bpy.context.view_layer
    active = vl.objects.active
    if not active or active.type not in {'MESH', 'EMPTY'}:
        for obj in scene.objects:
            if obj.type == 'MESH':
                vl.objects.active = obj
                obj.select_set(True)
                print(f"[Queue] GIF export: activated mesh '{obj.name}'")
                break
        else:
            print("[Queue] No mesh in scene — skipping GIF export")
            return False

    wm = bpy.context.window_manager

    # ── Explicitly apply HDRI from the queue's file path (if set) ──
    hdri_path = getattr(wm, 'sg_queue_gif_hdri_path', '')
    hdri_strength = getattr(wm, 'sg_queue_gif_hdri_strength', 1.0)
    use_hdri = getattr(wm, 'sg_queue_gif_use_hdri', False)

    if use_hdri and hdri_path:
        import os as _os
        resolved = bpy.path.abspath(hdri_path)
        if _os.path.isfile(resolved):
            try:
                bpy.ops.object.add_hdri(hdri_path=resolved,
                                        strength=hdri_strength)
                print(f"[Queue] Applied HDRI: {resolved}  "
                      f"(strength={hdri_strength:.2f})")
            except Exception as e:
                print(f"[Queue] AddHDRI failed: {e}  — continuing anyway")
        else:
            print(f"[Queue] HDRI file not found: {resolved}  — skipping HDRI")

    kwargs = {
        'duration':                getattr(wm, 'sg_queue_gif_duration', 5.0),
        'frame_rate':              getattr(wm, 'sg_queue_gif_fps', 24),
        'resolution_percentage':   getattr(wm, 'sg_queue_gif_resolution', 50),
        'samples':                 samples_override if samples_override is not None else getattr(wm, 'sg_queue_gif_samples', 32),
        'engine':                  getattr(wm, 'sg_queue_gif_engine', 'CYCLES'),
        'interpolation':           getattr(wm, 'sg_queue_gif_interpolation', 'LINEAR'),
        'use_hdri':                use_hdri,
        'hdri_rotation':           getattr(wm, 'sg_queue_gif_hdri_rotation', 0.0),
        'env_mode':                getattr(wm, 'sg_queue_gif_env_mode', 'FIXED'),
        'use_denoiser':            getattr(wm, 'sg_queue_gif_denoiser', True),
        'use_gpu':                 getattr(wm, 'sg_queue_gif_use_gpu', True),
        'filename_suffix':         suffix,
    }

    # Build a temp_override so the modal operator has a proper window
    window = bpy.context.window
    if not window:
        for w in wm.windows:
            window = w
            break
    if not window:
        print("[Queue] No window available — skipping GIF export")
        return False

    try:
        with bpy.context.temp_override(window=window):
            result = bpy.ops.object.export_orbit_gif('EXEC_DEFAULT', **kwargs)
        if 'RUNNING_MODAL' in result:
            print(f"[Queue] GIF export started successfully")
            return True
        print(f"[Queue] GIF export returned {result} — skipping")
        return False
    except Exception as e:
        print(f"[Queue] GIF export failed to start: {e}")
        import traceback; traceback.print_exc()
        return False


def _queue_start_no_pbr_reproject():
    """Disable PBR, then invoke a project-only reproject.

    Saves the original PBR / generation settings so they can be restored
    by ``_queue_restore_pbr()`` after the second GIF is done.

    Returns True if the reproject operator was successfully started.
    """
    global _queue_original_pbr, _queue_original_gen_method, _queue_original_overwrite

    scene = bpy.context.scene
    _queue_original_pbr = scene.pbr_decomposition
    _queue_original_gen_method = scene.generation_method
    _queue_original_overwrite = scene.overwrite_material

    scene.pbr_decomposition = False
    scene.generation_mode = 'project_only'
    scene.generation_method = 'separate'
    scene.overwrite_material = True

    # Select all cameras (required by ComfyUIGenerate)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in scene.objects:
        if obj.type == 'CAMERA':
            obj.select_set(True)

    window = bpy.context.window
    wm = bpy.context.window_manager
    if not window:
        for w in wm.windows:
            window = w
            break
    if not window:
        print("[Queue] No window available — cannot start reproject")
        return False

    try:
        with bpy.context.temp_override(window=window):
            bpy.ops.object.test_stable('INVOKE_DEFAULT')
        print("[Queue] No-PBR reproject invoked")
        return True
    except Exception as e:
        print(f"[Queue] Failed to invoke reproject: {e}")
        import traceback; traceback.print_exc()
        # Restore settings on failure
        scene.pbr_decomposition = _queue_original_pbr
        scene.generation_mode = 'standard'
        scene.generation_method = _queue_original_gen_method
        scene.overwrite_material = _queue_original_overwrite
        return False


def _queue_restore_pbr():
    """Restore PBR and generation settings saved by ``_queue_start_no_pbr_reproject``."""
    scene = bpy.context.scene
    scene.pbr_decomposition = _queue_original_pbr
    scene.generation_mode = 'standard'
    scene.generation_method = _queue_original_gen_method
    scene.overwrite_material = _queue_original_overwrite
    print(f"[Queue] Restored pbr_decomposition={_queue_original_pbr}")


def _queue_save_and_advance(item):
    """Save the current .blend and advance to the next queue item."""
    global _queue_current_idx, _queue_phase, _queue_processing, _queue_timer

    # Save the result in-place on the queue copy .blend
    if bpy.data.filepath:
        try:
            bpy.ops.wm.save_mainfile()
            print(f"[Queue] Saved result: {bpy.data.filepath}")
        except Exception as e:
            print(f"[Queue] Save warning: {e}")

    # Advance to next pending item
    _queue_current_idx += 1
    wm = bpy.context.window_manager
    while _queue_current_idx < len(wm.sg_scene_queue):
        if wm.sg_scene_queue[_queue_current_idx].status == 'pending':
            break
        _queue_current_idx += 1

    if _queue_current_idx >= len(wm.sg_scene_queue):
        _queue_processing = False
        _queue_phase = 'idle'
        _queue_timer = None
        print("[Queue] All queue items processed.")
    else:
        _queue_phase = 'idle'  # Will switch to next scene on next tick

    _persist_queue()
    _tag_redraw()


def _tag_redraw():
    """Redraw all 3D viewports so the queue UI updates."""
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception:
        pass
