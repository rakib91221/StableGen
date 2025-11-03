#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import requests
import shutil
from pathlib import Path
from typing import Dict, List, Set, Any

try:
    from tqdm.auto import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# --- Configuration: Dependencies Data ---
# Sizes are in MB.
DEPENDENCIES: Dict[str, Dict[str, Any]] = {
    # --- Custom Nodes ---
    "cn_ipadapter_plus": {
        "id": "cn_ipadapter_plus", "type": "node", "name": "ComfyUI IPAdapter Plus",
        "git_url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
        "target_dir_relative": "custom_nodes",
        "repo_name": "ComfyUI_IPAdapter_plus",
        "license": "GPL-3.0", "packages": ["core"]
    },
    # --- Models ---
    # Core Models
    "model_ipadapter_plus_sdxl_vit_h": {
        "id": "model_ipadapter_plus_sdxl_vit_h", "type": "model", "name": "IPAdapter Plus SDXL ViT-H",
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors?download=true",
        "target_path_relative": "models/ipadapter", "filename": "ip-adapter-plus_sdxl_vit-h.safetensors",
        "license": "Apache 2.0", "size_mb": 850, "packages": ["core"]
    },
    "model_clip_vision_h": {
        "id": "model_clip_vision_h", "type": "model", "name": "IPAdapter CLIP Vision ViT-H",
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors",
        "target_path_relative": "models/clip_vision", "filename": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
        "rename_from": "model.safetensors", "license": "Apache 2.0", "size_mb": 2500, "packages": ["core"]
    },
    "model_clip_vision_g": {
        "id": "model_clip_vision_g", "type": "model", "name": "IPAdapter CLIP Vision ViT-G",
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/image_encoder/model.safetensors",
        "target_path_relative": "models/clip_vision", "filename": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors",
        "rename_from": "model.safetensors", "license": "Apache 2.0", "size_mb": 3500, "packages": ["core"]
    },
    "lora_sdxl_lightning_8step": {
        "id": "lora_sdxl_lightning_8step", "type": "model", "name": "SDXL Lightning 8-Step LoRA",
        "url": "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_8step_lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "sdxl_lightning_8step_lora.safetensors",
        "license": "OpenRAIL++", "size_mb": 400, "packages": ["core"]
    },
    # Preset Essentials
    "controlnet_depth_sdxl_preset": {
        "id": "controlnet_depth_sdxl_preset", "type": "model", "name": "ControlNet Depth SDXL (for presets)",
        "url": "https://huggingface.co/xinsir/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors?download=true",
        "target_path_relative": "models/controlnet", "filename": "controlnet_depth_sdxl.safetensors",
        "rename_from": "diffusion_pytorch_model.safetensors", "license": "Apache 2.0", "size_mb": 2500, "packages": ["preset_essentials"]
    },
    # Extended SDXL Optional Models
    "lora_sdxl_lightning_4step": {
        "id": "lora_sdxl_lightning_4step", "type": "model", "name": "SDXL Lightning 4-Step LoRA",
        "url": "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_4step_lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "sdxl_lightning_4step_lora.safetensors",
        "license": "OpenRAIL++", "size_mb": 400, "packages": ["extended_optional"]
    },
    "lora_sdxl_lightning_2step": {
        "id": "lora_sdxl_lightning_2step", "type": "model", "name": "SDXL Lightning 2-Step LoRA",
        "url": "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_2step_lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "sdxl_lightning_2step_lora.safetensors",
        "license": "OpenRAIL++", "size_mb": 400, "packages": ["extended_optional"]
    },
    "lora_hyper_sdxl_8step": {
        "id": "lora_hyper_sdxl_8step", "type": "model", "name": "Hyper-SDXL 8-Steps LoRA",
        "url": "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-SDXL-8steps-lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Hyper-SDXL-8steps-lora.safetensors",
        "license": "Unknown (User to verify)", "size_mb": 800, "packages": ["extended_optional"]
    },
    "lora_hyper_sdxl_4step": {
        "id": "lora_hyper_sdxl_4step", "type": "model", "name": "Hyper-SDXL 4-Steps LoRA",
        "url": "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-SDXL-4steps-lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Hyper-SDXL-4steps-lora.safetensors",
        "license": "Unknown (User to verify)", "size_mb": 800, "packages": ["extended_optional"]
    },
    "lora_hyper_sdxl_1step": {
        "id": "lora_hyper_sdxl_1step", "type": "model", "name": "Hyper-SDXL 1-Step LoRA",
        "url": "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-SDXL-1step-lora.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Hyper-SDXL-1step-lora.safetensors",
        "license": "Unknown (User to verify)", "size_mb": 800, "packages": ["extended_optional"]
    },
    "controlnet_depth_sdxl_fp16_alt": {
        "id": "controlnet_depth_sdxl_fp16_alt", "type": "model", "name": "ControlNet Depth SDXL fp16 (alternative)",
        "url": "https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors?download=true",
        "target_path_relative": "models/controlnet", "filename": "diffusion_pytorch_model.fp16.safetensors",
        "license": "OpenRAIL++", "size_mb": 2500, "packages": ["extended_optional"]
    },
    "controlnet_union_promax": {
        "id": "controlnet_union_promax", "type": "model", "name": "ControlNet Union SDXL ProMax",
        "url": "https://huggingface.co/brad-twinkl/controlnet-union-sdxl-1.0-promax/resolve/main/diffusion_pytorch_model.safetensors?download=true",
        "target_path_relative": "models/controlnet", "filename": "sdxl_promax.safetensors",
        "rename_from": "diffusion_pytorch_model.safetensors", "license": "Apache 2.0", "size_mb": 2500, "packages": ["extended_optional"]
    },
    # Checkpoints
    "checkpoint_realvis_v5": {
        "id": "checkpoint_realvis_v5", "type": "model", "name": "RealVisXL V5.0 fp16 Checkpoint",
        "url": "https://huggingface.co/SG161222/RealVisXL_V5.0/resolve/main/RealVisXL_V5.0_fp16.safetensors?download=true",
        "target_path_relative": "models/checkpoints", "filename": "RealVisXL_V5.0_fp16.safetensors",
        "license": "OpenRAIL++", "size_mb": 6500, "packages": ["checkpoint_realvis"]
    },
    # Qwen Core
    "cn_comfyui_gguf": {
        "id": "cn_comfyui_gguf", "type": "node", "name": "ComfyUI GGUF Loader",
        "git_url": "https://github.com/city96/ComfyUI-GGUF.git",
        "target_dir_relative": "custom_nodes",
        "repo_name": "ComfyUI-GGUF",
        "license": "Apache 2.0", "packages": ["qwen_core"]
    },
    "model_qwen_unet_q3_k_m": {
        "id": "model_qwen_unet_q3_k_m", "type": "model", "name": "Qwen Image Edit 2509 UNet (Q3_K_M)",
        "url": "https://huggingface.co/QuantStack/Qwen-Image-Edit-2509-GGUF/resolve/main/Qwen-Image-Edit-2509-Q3_K_M.gguf?download=true",
        "target_path_relative": "models/unet", "filename": "Qwen-Image-Edit-2509-Q3_K_M.gguf",
        "license": "Apache 2.0", "size_mb": 9760, "packages": ["qwen_core"]
    },
    "model_qwen_vae": {
        "id": "model_qwen_vae", "type": "model", "name": "Qwen Image VAE",
        "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors?download=true",
        "target_path_relative": "models/vae", "filename": "qwen_image_vae.safetensors",
        "license": "Apache 2.0", "size_mb": 254, "packages": ["qwen_core"]
    },
    "model_qwen_text_encoder_fp8": {
        "id": "model_qwen_text_encoder_fp8", "type": "model", "name": "Qwen 2.5 VL 7B Text Encoder (FP8)",
        "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors?download=true",
        "target_path_relative": "models/clip", "filename": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "license": "Apache 2.0", "size_mb": 9380, "packages": ["qwen_core"]
    },
    "lora_qwen_lightning_4step_edit": {
        "id": "lora_qwen_lightning_4step_edit", "type": "model", "name": "Qwen Image Edit Lightning 4-Step LoRA (bf16)",
        "url": "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
        "license": "Apache 2.0", "size_mb": 850, "packages": ["qwen_core"]
    },
    # Qwen Extras
    "lora_qwen_lightning_8step": {
        "id": "lora_qwen_lightning_8step", "type": "model", "name": "Qwen Image Edit Lightning 8-Step LoRA (bf16)",
        "url": "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-8steps-V1.0-bf16.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Qwen-Image-Edit-2509-Lightning-8steps-V1.0-bf16.safetensors",
        "license": "Apache 2.0", "size_mb": 850, "packages": ["qwen_extras"]
    },
    "lora_qwen_lightning_4step": {
        "id": "lora_qwen_lightning_4step", "type": "model", "name": "Qwen Image Lightning 4-Step LoRA (bf16)",
        "url": "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0-bf16.safetensors?download=true",
        "target_path_relative": "models/loras", "filename": "Qwen-Image-Lightning-4steps-V1.0-bf16.safetensors",
        "license": "Apache 2.0", "size_mb": 850, "packages": ["qwen_extras"]
    },
}

# Define what items each menu option entails by listing package tags
# The script will collect all unique items based on the selected package tags.
MENU_PACKAGES: Dict[str, Dict[str, Any]] = {
    '1': {"name": "[MINIMAL CORE] Basic Requirements",
          "tags": ["core"],
          "size_gb": 7.3,
          "description_suffix": "*You will still need to manually download your own SDXL checkpoint(s) and all ControlNet models for full functionality and preset usage.*"},
    '2': {"name": "[ESSENTIAL] Core + Preset Essentials",
          "tags": ["core", "preset_essentials"],
          "size_gb": 9.8,
          "description_suffix": "*All models for preset functionality. You will still need to manually download your own SDXL checkpoint(s).*"},
    '3': {"name": "[RECOMMENDED] Full SDXL Setup (No Checkpoints)",
          "tags": ["core", "preset_essentials", "extended_optional"],
          "size_gb": 16.0,
          "description_suffix": "*Downloads optional ControlNet and LoRA models. You will still need to manually download your own SDXL checkpoint(s).*"},
    '4': {"name": "[COMPLETE SDXL] Full SDXL Setup + RealVisXL V5.0 Checkpoint",
          "tags": ["core", "preset_essentials", "extended_optional", "checkpoint_realvis"],
        "size_gb": 23.0,
        "description_suffix": ""},
    '5': {"name": "[QWEN CORE] Models + GGUF Node",
        "tags": ["qwen_core"],
        "size_gb": 20.3,
        "description_suffix": "*Installs Qwen Image Edit UNet, VAE, text encoder, core LoRA, and GGUF ComfyUI node.*"},
    '6': {"name": "[QWEN EXTRAS] Core + Lightning LoRAs",
        "tags": ["qwen_core", "qwen_extras"],
        "size_gb": 22.6,
        "description_suffix": "*Adds additional Qwen Lightning LoRAs on top of the Qwen core install.*"}
}

# --- Helper Functions ---
def print_header(title: str):
    print(f"\n{'='*10} {title} {'='*10}")

def print_separator(char='-', length=70):
    print(char * length)

def get_comfyui_path_from_args() -> Path:
    parser = argparse.ArgumentParser(description="StableGen Dependency Installer Script.")
    parser.add_argument("comfyuipath", nargs='?', default=None,
                        help="Full path to your ComfyUI installation directory. If not provided, will be prompted.")
    args = parser.parse_args()

    comfyui_path_str = args.comfyuipath
    while not comfyui_path_str:
        comfyui_path_str = input("Please enter the full path to your ComfyUI installation directory: ").strip()

    comfyui_path = Path(comfyui_path_str).resolve() # Get absolute path

    if not comfyui_path.is_dir():
        print(f"Error: ComfyUI path '{comfyui_path}' not found or not a directory.")
        sys.exit(1)
    if not (comfyui_path / "models").is_dir() or not (comfyui_path / "custom_nodes").is_dir():
        print(f"Error: '{comfyui_path}' does not look like a valid ComfyUI directory (missing 'models' or 'custom_nodes' subfolder).")
        sys.exit(1)
    return comfyui_path

def create_dir_if_not_exists(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def download_file(item_details: Dict[str, Any], comfyui_path: Path):
    url = item_details["url"]
    target_dir = comfyui_path / item_details["target_path_relative"]
    final_filename = item_details["filename"]
    final_filepath = target_dir / final_filename
    temp_filename = item_details.get("rename_from", final_filename)
    temp_filepath = target_dir / temp_filename

    if final_filepath.exists():
        print(f"INFO: File '{final_filename}' already exists at '{final_filepath}'. Skipping download.")
        print(f"      Please ensure this is the correct file as specified (License: {item_details['license']}).")
        return

    if item_details.get("rename_from") and temp_filepath.exists():
        # This case covers if a previous download was interrupted after download but before rename
        # or if user manually placed the file with the original name.
        print(f"INFO: File '{temp_filename}' (to be renamed to '{final_filename}') already exists at '{temp_filepath}'.")
        print(f"      Assuming it's the correct file. Renaming if necessary and skipping download.")
        print(f"      Please ensure this is the correct file (License: {item_details['license']}).")
        if temp_filepath != final_filepath: # Needs rename
            try:
                shutil.move(str(temp_filepath), str(final_filepath))
                print(f"      Successfully renamed '{temp_filename}' to '{final_filename}'.")
            except Exception as e:
                print(f"      ERROR: Could not rename '{temp_filename}' to '{final_filename}': {e}")
        return

    create_dir_if_not_exists(target_dir)
    size_mb = item_details.get("size_mb", "N/A")
    print(f"  Downloading: {item_details['name']} ({size_mb}MB) - License: {item_details['license']}")
    print(f"  From: {url}")
    print(f"  To:   {final_filepath}")
    if item_details.get("rename_from"):
        print(f"  (Will be downloaded as '{temp_filename}' and then renamed to '{final_filename}')")

    try:
        response = requests.get(url, stream=True, timeout=30) # Added timeout
        response.raise_for_status()  # Raise an exception for HTTP errors
        total_size = int(response.headers.get('content-length', 0))
        
        # Use temp_filepath for download, then rename to final_filepath
        download_target = temp_filepath if item_details.get("rename_from") else final_filepath
        # Ensure no partial file from previous attempt if not renaming
        if not item_details.get("rename_from") and download_target.exists():
             print(f"WARNING: '{download_target}' exists but was not caught by pre-check. This might be a partial file. Overwriting.")


        with open(download_target, 'wb') as f:
            if TQDM_AVAILABLE and total_size > 0:
                with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc=item_details['name'], ascii=True) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
            else:
                print(f"  Downloading {item_details['name']} (size: {total_size/1024/1024:.2f} MB)...")
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"  Download complete: {download_target}")

        if item_details.get("rename_from") and temp_filepath != final_filepath:
            if final_filepath.exists():
                print(f"WARNING: Target renamed file '{final_filepath}' already exists. Overwriting.")
                final_filepath.unlink()
            shutil.move(str(temp_filepath), str(final_filepath))
            print(f"  Successfully renamed to '{final_filename}'.")

    except requests.exceptions.RequestException as e:
        print(f"  ERROR downloading {item_details['name']}: {e}")
    except Exception as e:
        print(f"  An unexpected error occurred during download of {item_details['name']}: {e}")


def clone_git_repo(item_details: Dict[str, Any], comfyui_path: Path):
    git_url = item_details["git_url"]
    target_parent_dir = comfyui_path / item_details["target_dir_relative"]
    repo_name = item_details["repo_name"]
    final_repo_path = target_parent_dir / repo_name

    if final_repo_path.is_dir():
        print(f"INFO: Custom node directory '{repo_name}' already exists at '{final_repo_path}'. Skipping clone.")
        print(f"      Please ensure it's the correct repository and up-to-date if you encounter issues (License: {item_details['license']}).")
        return

    create_dir_if_not_exists(target_parent_dir)
    print(f"  Cloning: {item_details['name']} - License: {item_details['license']}")
    print(f"  From: {git_url}")
    print(f"  To:   {final_repo_path}")

    try:
        subprocess.run(['git', 'clone', git_url, str(final_repo_path)], check=True, cwd=str(target_parent_dir))
        print(f"  Successfully cloned '{repo_name}'.")
        print(f"  IMPORTANT: Restart ComfyUI if it was running to load this new custom node.")
    except subprocess.CalledProcessError as e:
        print(f"  ERROR cloning {item_details['name']}: Git command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"  Git stderr: {e.stderr.decode(errors='ignore')}")
        if e.stdout:
            print(f"  Git stdout: {e.stdout.decode(errors='ignore')}")

    except FileNotFoundError:
        print("  ERROR: Git command not found. Please ensure Git is installed and in your system's PATH.")
    except Exception as e:
        print(f"  An unexpected error occurred during git clone of {item_details['name']}: {e}")


def display_menu(comfyui_path: Path):
    print_header("StableGen Dependency Installer")
    print(f"Target ComfyUI Directory: {comfyui_path}")
    print_separator()
    print("This script helps download and set up essential and optional models for StableGen.")
    print("For FLUX.1 model setup (which requires manual download due to licensing),")
    print("please refer to the main README.md on our GitHub page: https://github.com/sakalond/stablegen")
    print_separator()
    print("Note: Download sizes are estimates. Actual sizes may vary slightly.")
    print()
    print("Upon entering a choice, the full list of components will be shown for approval before proceeding.")
    print_separator()
    print("Please choose an installation package:")
    print()

    for key, val in MENU_PACKAGES.items():
        print(f"\n{key}. {val['name']}")
        print_separator(char='.')
        # Dynamically list contents for clarity (optional, can make menu long)
        # items_in_package = get_items_for_package_tags(val['tags'])
        # for item_id in items_in_package:
        #     print(f"    - {DEPENDENCIES[item_id]['name']}")
        print(f"    *Approximate total download size: ~{val['size_gb']:.1f} GB*")
        if val.get("description_suffix"):
            print(f"    {val['description_suffix']}")
    print("\nq. Quit")
    print_separator()


def get_unique_item_ids_for_tags(selected_tags: List[str]) -> Set[str]:
    item_ids: Set[str] = set()
    for item_id, details in DEPENDENCIES.items():
        # An item is included if any of its 'packages' tags are in selected_tags
        if any(tag in details["packages"] for tag in selected_tags):
            item_ids.add(item_id)
    return item_ids

# --- Main Script Logic ---
def main():
    comfyui_base_path = get_comfyui_path_from_args()

    processed_during_this_session: Set[str] = set() # To avoid re-processing in same session if menu is re-shown

    while True:
        display_menu(comfyui_base_path)
        choice = input("Enter your choice (1-6, or q to quit): ").strip().lower()

        if choice == 'q':
            print("Exiting installer.")
            break

        selected_option = MENU_PACKAGES.get(choice)
        if not selected_option:
            print("Invalid choice. Please try again.")
            continue

        print_separator()
        print(f"You selected: {selected_option['name']}")
        print(f"Estimated download for this package (if items not present): ~{selected_option['size_gb']:.1f} GB")
        
        current_selection_item_ids = get_unique_item_ids_for_tags(selected_option["tags"])
        items_to_process_this_round: List[Dict[str, Any]] = []
        
        print("This package will check/install the following components:")
        for item_id in sorted(list(current_selection_item_ids)): # Sort for consistent display
            if item_id not in processed_during_this_session and item_id in DEPENDENCIES:
                print(f"  - {DEPENDENCIES[item_id]['name']}")
                items_to_process_this_round.append(DEPENDENCIES[item_id])
        
        if not items_to_process_this_round:
            print("All components for this selection appear to have been processed or are not defined. Nothing new to install for this choice.")
            print("If you expected installations, ensure the components are not already present from a previous run or selection.")
            print_separator()
            continue

        confirm_all = input("Proceed with checking/installing these components? (y/n, Enter for yes): ").strip().lower()
        if not (confirm_all == "" or confirm_all == 'y'):
            print("Installation of this package cancelled by user.")
            print_separator()
            continue
            
        print_separator(char='*')
        for item_details in items_to_process_this_round:
            if item_details["id"] in processed_during_this_session: # Should not happen if items_to_process_this_round is built correctly
                continue

            print_separator(char='.')
            print(f"Processing: {item_details['name']}")
            
            target_full_path: Path
            if item_details["type"] == "node":
                target_full_path = comfyui_base_path / item_details["target_dir_relative"] / item_details["repo_name"]
                clone_git_repo(item_details, comfyui_base_path)
            elif item_details["type"] == "model":
                target_full_path = comfyui_base_path / item_details["target_path_relative"] / item_details["filename"]
                download_file(item_details, comfyui_base_path)
            
            processed_during_this_session.add(item_details["id"])
        
        print_separator(char='*')
        print("Processing for selected package complete.")
        print("Please check messages above for status of each item.")
        if any(item["type"] == "node" for item in items_to_process_this_round):
             print("IMPORTANT: If any custom nodes were newly cloned, restart ComfyUI to load them.")
        print_separator()

if __name__ == "__main__":
    if not TQDM_AVAILABLE:
        print("NOTE: 'tqdm' library not found. Download progress will not be shown as a bar.")
        print("      You can install it with: pip install tqdm")
    main()