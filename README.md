# StableGen: AI-Powered 3D Texturing in Blender ✨

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Blender Version](https://img.shields.io/badge/Blender-4.2%2B-orange.svg)](#system-requirements)

**Transform your 3D texturing workflow with the power of generative AI, directly within Blender!**

StableGen is an open-source Blender plugin designed to seamlessly integrate advanced diffusion models (SDXL, FLUX.1-dev) into your creative process. Generate complex, coherent, and controllable textures for your 3D models and entire scenes using a flexible ComfyUI backend.

---

## 🌟 Key Features

StableGen empowers 3D artists by bringing cutting-edge AI texturing capabilities into Blender:

* 🌍 **Scene-Wide Multi-Mesh Texturing:**
    * Don't just texture one mesh at a time! StableGen is designed to apply textures to **all mesh objects in your scene simultaneously** from your defined camera viewpoints. Alternatively, you can choose to texture only selected objects.
    * Achieve a cohesive look across entire environments or collections of assets in a single generation pass.
    * Ideal for concept art, look development for complex scenes, and batch-texturing asset libraries.
* 🎨 **Multi-View Consistency:**
    * **Sequential Mode:** Generates textures viewpoint by viewpoint on each mesh, using inpainting and visibility masks for high consistency across complex surfaces.
    * **Grid Mode:** Processes multiple viewpoints for all meshes simultaneously for faster previews. Includes an optional refinement pass.
    * Sophisticated weighted blending ensures smooth transitions between views.
* 📐 **Precise Geometric Control with ControlNet:**
    * Leverage multiple ControlNet units (Depth, Canny, Normal) simultaneously to ensure generated textures respect your model's geometry.
    * Fine-tune strength, start/end steps for each ControlNet unit.
    * Supports custom ControlNet model mapping.
* 🖌️ **Powerful Style Guidance with IPAdapter:**
    * Use external reference images to guide the style, mood, and content of your textures with IPAdapter.
    * Employ IPAdapter without an reference image for enhanced consistency in multi-view generation modes.
    * Control IPAdapter strength, weight type, and active steps.
* ⚙️ **Flexible ComfyUI Backend:**
    * Connects to your existing ComfyUI installation, allowing you to use your preferred SDXL checkpoints and custom LoRAs. Experimental support for FLUX.1-dev.
    * Offloads heavy computation to the ComfyUI server, keeping Blender mostly responsive.
* ✨ **Advanced Inpainting & Refinement:**
    * **Refine Mode (Img2Img):** Re-style, enhance, or add detail to existing textures (StableGen generated or otherwise) using an image-to-image process. Choose to preserve original textures for localized refinement.
    * **UV Inpaint Mode:** Intelligently fills untextured areas directly on your model's UV map using surrounding texture context.
* 🛠️ **Integrated Workflow Tools:**
    * **Camera Setup:** Quickly add and arrange multiple cameras around your subject.
    * **View-Specific Prompts:** Assign unique text prompts to individual camera viewpoints for targeted details.
    * **Texture Baking:** Convert complex procedural StableGen materials into standard UV image textures.
    * **HDRI Setup, Modifier Application, Curve Conversion, GIF/MP4 Export & Reproject.**
* 📋 **Preset System:**
    * Get started quickly with built-in presets for common scenarios (e.g., "Default", "Characters", "Quick Draft").
    * Save and manage your own custom parameter configurations for repeatable workflows.

---

## 🚀 Showcase Gallery

See what StableGen can do!

---

### Showcase 1: Head Model Stylization with IPAdapter

This showcase demonstrates how StableGen can texture the model using a standard prompt and then with style guidance from an IPAdapter image reference.

**3D Model Source:** "Brown" by ucupumar - Available at: [BlendSwap (Blend #15262)](https://www.blendswap.com/blend/15262)



| Untextured Model  | Generated | Generated  | Generated (with a reference image) |
| :------: | :---------: | :----------: | :-----------------: |
| <img src="docs/img/head_blank.gif" alt="Untextured Anime Head" width="200"> | <img src="docs/img/head_red.gif" alt="Anime head with red hair" width="200">  | <img src="docs/img/head_cyberpunk.gif" alt="Anime head with Cyberpunk style" width="200">   |  <img src="docs/img/head_starry.gif" alt="Anime head with Starry Night style" width="200">   | 
| *Base Untextured Model* | <small>Prompt: "anime girl head, red hair"</small>    |   <small>Prompt: "girl head, brown hair, cyberpunk style, realistic"</small>  |   <small>Prompt: "anime girl head, artistic style"<br><em>(Style guided by reference image shown below)</em></small>      |
<p align="left">
  <img src="docs/img/starry_night_small.jpg" alt="The Starry Night - IPAdapter Reference" width="250">
  <br>
  <small><em>Reference: "The Starry Night" by Vincent van Gogh (used to guide the "Artistic Style" variant)</em></small>
</p>


### Showcase 2: Car Asset Texturing

This showcase demonstrates how StableGen can texture a car model using different textual prompts implying various visual styles.

**3D Model Source:** "Pontiac GTO 67" by thecali - Available at: [BlendSwap (Blend #13575)](https://www.blendswap.com/blend/13575)

| Untextured Model  | Generated | Generated | Generated |
| :------: | :---------: | :----------: | :-----------------: |
| <img src="docs/img/car_blank.gif" alt="Untextured Car" width="200"> | <img src="docs/img/car_green.gif" alt="Green car" width="200">  | <img src="docs/img/car_steampunk.gif" alt="Steampunk style car" width="200">   |  <img src="docs/img/car_black.gif" alt="Stealth black car" width="200">   | 
| *Base Untextured Model* | <small>Prompt: "green car"</small>    |   <small>Prompt: "steampunk style car"</small>  |   <small>Prompt: "stealth black car"</small>      |


### Showcase 3: Subway Scene Asset Texturing

This showcase demonstrates how StableGen can texture a more complex scene consisting of many mesh objects.

**3D Model Source:** "Subway Station Entrance" by argonius - Available at: [BlendSwap (Blend #19305)](https://www.blendswap.com/blend/19305)

| Untextured Scene  | Generated | Generated | Generated |
| :------: | :---------: | :----------: | :-----------------: |
| <img src="docs/img/subway_blank.gif" alt="Untextured Subway Scene" width="200"> | <img src="docs/img/subway_default.gif" alt="Subway station" width="200">  | <img src="docs/img/subway_palace.gif" alt="Overgrown fantasy palace interior" width="200">   |  <img src="docs/img/subway_cyberpunk.gif" alt="Cyberpunk subway station" width="200">   | 
| *Base Untextured Scene* | <small>Prompt: "subway station"</small>    |   <small>Prompt: "an overgrown fantasy palace interior, gold elements"</small>  |   <small>Prompt: "subway station, cyberpunk style, neon lit"</small>      |

---

## 🛠️ How It Works (A Glimpse)

StableGen acts as an intuitive interface within Blender that communicates with a ComfyUI backend.
1.  You set up your scene and parameters in the StableGen panel.
2.  StableGen prepares necessary data (like ControlNet inputs from camera views).
3.  It constructs a workflow and sends it to your ComfyUI server.
4.  ComfyUI processes the request using your selected diffusion models.
5.  Generated images are sent back to Blender.
6.  StableGen applies these images as textures to your models using sophisticated projection and blending techniques.

---

## 💻 System Requirements

* **Blender:** Version 4.2 or newer.
* **Operating System:** Windows 10/11 or Linux.
* **GPU:** **NVIDIA GPU with CUDA is recommended** for ComfyUI. For further details, check ComfyUI's github page: [https://github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI).
* **ComfyUI:** A working installation of ComfyUI. StableGen uses this as its backend.
* **Python:** Version 3.x (usually comes with Blender, but Python 3 is needed for the `installer.py` script).
* **Git:** Required by the `installer.py` script.
* **Disk Space:** Significant free space for ComfyUI, AI models (10GB to 50GB+), and generated textures.

---

## ⚙️ Installation

Setting up StableGen involves installing ComfyUI, then StableGen's dependencies into ComfyUI using our installer script, and finally installing the StableGen plugin in Blender.

### Step 1: Install ComfyUI (If not already installed)

StableGen relies on a working ComfyUI installation as its backend.
1.  If you don't have ComfyUI, please follow the **official ComfyUI installation guide**: [https://github.com/comfyanonymous/ComfyUI#installing](https://github.com/comfyanonymous/ComfyUI#installing).
    * Install ComfyUI in a dedicated directory. We'll refer to this as `<YourComfyUIDirectory>`.
    * Ensure you can run ComfyUI and it's functioning correctly before proceeding.
    * Remote ComfyUI instances are not currently supported. This includes ComfyUI installations running on a different machine or in a virtual machine (including WSL).

### Step 2: Install Dependencies (Custom Nodes & AI Models) - Automated (Recommended)

The `installer.py` script (found in this repository) automates the download and placement of required ComfyUI custom nodes and core AI models into your `<YourComfyUIDirectory>`.

**Prerequisites for the installer:**
* Python 3.
* Git installed and accessible in your system's PATH.
* The path to your ComfyUI installation (`<YourComfyUIDirectory>`).
* Required Python packages for the script: `requests` and `tqdm`. Install them via pip:
    ```bash
    pip install requests tqdm
    ```

**Running the Installer:**
1.  **Download/Locate the Installer:** Get `installer.py` from this GitHub repository.
2.  **Execute the Script:**
    * Open your system's terminal or command prompt.
    * Navigate to the directory containing `installer.py`.
    * Run the script:
        ```bash
        python installer.py <YourComfyUIDirectory>
        ```
        Replace `<YourComfyUIDirectory>` with the actual path. If omitted, the script will prompt for it.
3.  **Follow On-Screen Instructions:**
    * The script will display a menu of installation packages (Minimal, Essential, Recommended, Complete SDXL). Choose one based on your needs.
    * It will download and place files into the correct subdirectories of `<YourComfyUIDirectory>`.
4.  **Restart ComfyUI:** If ComfyUI was running, restart it to load new custom nodes.

*(For manual dependency installation (and for installation of FLUX.1-dev and its dependecies), see `docs/MANUAL_INSTALLATION.md`.)*

### Step 3: Install StableGen Blender Plugin

1.  Go to the [**Releases** page](https://github.com/sakalond/stablegen/releases) of this repository.
2.  Download the latest `StableGen.zip` file.
3.  In Blender, go to `Edit > Preferences > Add-ons > Install...`.
4.  Navigate to and select the downloaded `StableGen.zip` file.
5.  Enable the "StableGen" addon (search for "StableGen" and check the box).

### Step 4: Configure StableGen Plugin in Blender

1.  In Blender, go to `Edit > Preferences > Add-ons`.
2.  Find "StableGen" and expand its preferences.
3.  Set the following paths:
    * **ComfyUI Directory:** Path to your ComfyUI installation (e.g., `<YourComfyUIDirectory>`).
    * **Output Directory:** Choose a folder where StableGen will save generated images.
    * **Server Address:** Ensure this matches your ComfyUI server (default `127.0.0.1:8188`).
    * Review **ControlNet Mapping** if using custom named ControlNet models.
    * **External Checkpoints / LoRAs Directory (Optional):** Path to your external checkpoint directory. Also has to be configured in ComfyUI.
4.  Enable online access in Blender if not enabled already. Select `Edit -> Preferences` from the topbar of Blender. Then navigate to `System -> Network` and check the box `Enable Online Access`. While StableGen does not require internet access, this is added to respect Blender add-on guidelines, as there are still network calls being made locally.

---

## 🚀 Quick Start Guide

Here’s how to get your first texture generated with StableGen:

1.  **Start ComfyUI Server:** Make sure it's running in the background.
2.  **Open Blender & Prepare Scene:**
    * Have a mesh object ready (e.g., the default Cube).
    * Ensure the StableGen addon is enabled and configured (see Step 4 above).
3.  **Access StableGen Panel:** Press `N` in the 3D Viewport, go to the "StableGen" tab.
4.  **Add Cameras (Recommended for Multi-View):**
    * Select your object.
    * In the StableGen panel, click "**Add Cameras**". Choose `Object` as center type. Adjust interactively if needed, then confirm.
5.  **Set Basic Parameters:**
    * **Prompt:** Type a description (e.g., "ancient stone wall with moss").
    * **Checkpoint:** Select a checkpoint (e.g., `sdxl_base_1.0`).
    * **Generation Mode:** `Sequential` is a good starting point for consistency.
6.  **Hit Generate!** Click the main "**Generate**" button.
7.  **Observe:** Watch the progress in the panel and the ComfyUI console. Your object should update with the new texture! Output files will be in your specified "Output Directory".
    * By default, the generated texture will only be visible in the Rendered viewport shading mode (CYCLES Render Engine).

---

## 📖 Usage & Parameters Overview

StableGen provides a comprehensive interface for controlling your AI texturing process, from initial setup to final output. Here's an overview of the main sections and tools available in the StableGen panel:

### Primary Actions & Scene Setup

These are the main operational buttons and initial setup tools, generally found near the top of the StableGen panel:

* **Generate / Cancel Generation (Main Button):** This is the primary button to start the AI texture generation process for meshe objects based on your current settings. It communicates with the ComfyUI backend. While processing, the button changes to "Cancel Generation," allowing you to stop the current task. Progress bars will appear below this button during generation.
* **Bake Textures:** Converts the dynamic, multi-projection material StableGen creates on your meshes into a single, standard UV-mapped image texture per object. This is essential for exporting or simplifying scenes. You can set the resolution and UV unwrapping method for the bake. This option is crucial for finalizing your AI-generated textures into a portable format.
* **Add Cameras:** Helps you quickly set up multiple viewpoints. It creates a circular array of Blender cameras around the active object (if "Object" center type is chosen) or the current 3D view center. You can specify the number of cameras and interactively adjust their positions before finalizing.
* **Collect Camera Prompts:** Cycles through all cameras in your scene, allowing you to type a specific descriptive text prompt for each viewpoint (e.g., "front view," "close-up on face"). These per-camera prompts are used in conjunction with the main prompt if `Use camera prompts` is enabled in `Viewpoint Blending Settings`.

### Preset Management

* Located prominently in the UI, this system allows you to:
    * **Select a Preset:** Choose from built-in configurations (e.g., `Default`, `Characters`, `Quick Draft`) for common scenarios or select `Custom` to use your current settings.
    * **Apply Preset:** If you modify a stock preset, this button applies its original values.
    * **Save Preset:** When your settings are `Custom`, this allows you to save your current configuration as a new named preset.
    * **Delete Preset:** Removes a selected custom preset.

### Main Parameters

These are your primary controls for defining the generation:

* **Prompt:** The main text description of the texture you want to generate.
* **Checkpoint:** Select the base SDXL checkpoint.
* **Architecture:** Choose between `SDXL` and `Flux 1` (experimental) model architectures.
* **Generation Mode:** Defines the core strategy for texturing:
    * `Generate Separately`: Each viewpoint generates independently.
    * `Generate Sequentially`: Viewpoints generate one by one, using inpainting from previous views for consistency.
    * `Generate Using Grid`: Combines all views into a grid for a single generation pass, with an optional refinement step.
    * `Refine/Restyle Texture (Img2Img)`: Uses the current texture as input for an image-to-image process.
    * `UV Inpaint Missing Areas`: Fills untextured areas on a UV map via inpainting.
* **Target Objects:** Choose whether to texture all visible mesh objects or only selected ones.

### Advanced Parameters (Collapsible Sections)

Click the arrow next to each title to expand and access detailed settings:

* **Core Generation Settings:** Control diffusion basics like Seed, Steps, CFG, Negative Prompt, Sampler, Scheduler and Clip Skip.
* **LoRA Management:** Add and configure LoRAs (Low-Rank Adaptation) for additional style or content guidance. You can set the model and clip strength for each LoRA.
* **Viewpoint Blending Settings:** Manage how textures from different camera views are combined, including camera-specific prompts, discard angles, and blending weight exponents.
* **Output & Material Settings:** Define fallback color, material properties (BSDF), automatic resolution scaling, and options for baking textures during generation which enables generating with more than 8 viewpoints.
* **Image Guidance (IPAdapter & ControlNet):** Configure IPAdapter for style transfer using external images and set up multiple ControlNet units (Depth, Canny, etc.) for precise structural control.
* **Inpainting Options:** Fine-tune masking and blending for `Sequential` and `UV Inpaint` modes (e.g., differential diffusion, mask blurring/growing).
* **Generation Mode Specifics:** Parameters unique to the selected Generation Mode, like refinement options for Grid mode or IPAdapter consistency settings for Sequential/Separate/Refine modes.

### Integrated Workflow Tools (Bottom Section)

A collection of utilities to further support your texturing workflow:

* **Switch Material:** For selected objects with multiple material slots, this tool allows you to quickly set a material at a specific index as the active one.
* **Add HDRI Light:** Prompts for an HDRI image file and sets it up as the world lighting, providing realistic illumination for your scene.
* **Apply All Modifiers:** Iterates through all mesh objects in the scene, applies their modifier stacks, and converts geometry instances (like particle systems or collection instances) into real mesh data. This helps prepare models for texturing.
* **Convert Curves to Mesh:** Converts any selected curve objects into mesh objects, which is necessary before StableGen can texture them.
* **Export  GIF/MP4:** Creates an animated GIF and MP4 video of the currently active object, with the camera ing around it. Useful for quickly showcasing your textured model. You can set duration, frame rate, and resolution.
* **Reproject Images:** This operator re-applies previously generated textures to your models using the latest `Viewpoint Blending Settings` (e.g., `Discard-Over Angle`, `Weight Exponent`). This allows you to tweak texture blending without full regeneration.

Experiment with these settings and tools to achieve a vast range of effects and control! Remember that the optimal parameters can vary greatly depending on the model, subject matter, and desired artistic style.

---

## 📁 Output Directory Structure

StableGen organizes the generated files within the `Output Directory` specified in your addon preferences. For each generation session, a new timestamped folder is created, helping you keep track of different iterations. The structure for each session (revision) is as follows:

* `<Output Directory>/`
    * `<SceneName>/` *(Based on your `.blend` file name, or scene name if unsaved)*
        * `<YYYY-MM-DDTHH-MM-SS>/` *(Timestamp of generation start - this is the main revision directory)*
            * `generated/` *(Main output textures from each camera/viewpoint before being applied or baked)*
            * `controlnet/` *(Intermediate ControlNet input images)*
                * `depth/` *(Depth pass renders)*
                * `canny/` *(Renders processed using Canny edge decetor)*
                * `normal/` *(Normal pass renders)*
            * `baked/` *(Textures baked onto UV maps using the standalone `Bake Textures` tool)*
            * `generated_baked/` *(Textures baked as part of the generation process if "Bake Textures While Generating" is enabled)*
            * `inpaint/` *(Files related to inpainting processes, e.g., for `Sequential mode`)*
                * `render/` *(Renders of previous state used as context for inpainting)*
                * `visibility/` *(Visibility masks used as masks during the inpainting)*
            * `uv_inpaint/` *(Files specific to the UV Inpaint mode)*
                * `uv_visibility/` *(Visibility masks generated on UVs for UV inpainting)*
            * `misc/` *(Other temporary or miscellaneous files, e.g., renders made for Canny edge detection input)*
            * `.gif` / `.mp4` *(If the `Export  GIF/MP4` tool is used, these files are saved directly into the timestamped revision directory)*
            * `prompt.json` *(The last generated workflow to be used in ComfyUI)*
         
---

## 🤔 Troubleshooting

Encountering issues? Here are some common fixes. Always check the **Blender System Console** (Window > Toggle System Console) AND the **ComfyUI server console** for error messages.

* **StableGen Panel Not Showing:** Ensure the addon is installed and enabled in Blender's preferences.
* **"Cannot generate..." on Generate Button:** Check Addon Preferences: `Model Directory`, `Output Directory`, and `Server Address` must be correctly set.
* **Connection Issues with ComfyUI:**
    * Make sure your ComfyUI server is running.
    * Verify the `Server Address` in StableGen preferences.
    * Check firewall settings.
* **Models Not Found (Error in ComfyUI Console):**
    * Run the `installer.py` script.
    * Manually ensure models are in the correct subfolders of `<YourComfyUIDirectory>/models/` (e.g., `checkpoints/`, `controlnet/`, `loras/`, `ipadapter/`, `clip_vision/`).
    * Restart ComfyUI after adding new models or custom nodes.
* **GPU Out Of Memory (OOM):**
    * Enable `Auto Rescale Resolution` in `Advanced Parameters` > `Output & Material Settings` if disabled.
    * Try lower bake resolutions if baking.
    * Close other GPU-intensive applications.
* **Textures not visible after generation completes:**
    * Switch to Rendered viewport shading (top right corner, fourth "sphere" icon)
* **Textures not affected by your lighting setup:**
    * Enable `Apply BSDF` in `Advanced Parameters > Output & Material Settings` and regenerate.
* **Poor Texture Quality/Artifacts:**
    * Try using the provided presets.
    * Adjust prompts and negative prompts.
    * Experiment with different Generation Modes. `Sequential` with IPAdapter is often good for consistency.
    * Ensure adequate camera coverage and appropriate `Discard-Over Angle`.
    * Fine-tune ControlNet strength. Too low might ignore geometry; too high might yield flat results.
    * For `Sequential` mode, check inpainting and visibility mask settings.
* **All Visible Meshes Textured:** StableGen textures all visible mesh objects by default. You can set `Target Objects` to `Selected` to only texture selected objects.

---

## 🤝 Contributing

We welcome contributions! Whether it's bug reports, feature suggestions, code contributions, or new presets, please feel free to open an issue or a pull request.

---

## 📜 License

StableGen is released under the **GNU General Public License v3.0**. See the `LICENSE` file for details.

---

## 🙏 Acknowledgements

StableGen builds upon the fantastic work of many individuals and communities. Our sincere thanks go to:

* **Academic Roots:** This plugin originated as a Bachelor's Thesis by Ondřej Sakala at the Czech Technical University in Prague (Faculty of Information Technology), supervised by Ing. Radek Richtr, Ph.D.
* **Core Technologies & Communities:**
    * **ComfyUI** by ComfyAnonymous ([GitHub](https://github.com/comfyanonymous/ComfyUI)) for the powerful and flexible backend.
    * The **Blender Foundation** and its community for the amazing open-source 3D creation suite.
* **Inspired by following Blender Addons:**
    * **Dream Textures** by Carson Katri et al. ([GitHub](https://github.com/carson-katri/dream-textures))
    * **Diffused Texture Addon** by Frederik Hasecke ([GitHub](https://github.com/FrederikHasecke/diffused-texture-addon))
* **Pioneering Research:** We are indebted to the researchers behind key advancements that power StableGen. The following list highlights some of the foundational and influential works in diffusion models, AI-driven control, and 3D texturing (links to arXiv pre-prints):
    * **Diffusion Models:**
        * Ho et al. (2020), Denoising Diffusion Probabilistic Models - [2006.11239](https://arxiv.org/abs/2006.11239)
        * Rombach et al. (2022), Latent Diffusion Models (Stable Diffusion) - [2112.10752](https://arxiv.org/abs/2112.10752)
    * **AI Control Mechanisms:**
        * Zhang et al. (2023), ControlNet - [2302.05543](https://arxiv.org/abs/2302.05543)
        * Ye et al. (2023), IP-Adapter - [2308.06721](https://arxiv.org/abs/2308.06721)
    * **Key 3D Texture Synthesis Papers:**
        * Chen et al. (2023), Text2Tex - [2303.11396](https://arxiv.org/abs/2303.11396)
        * Richardson et al. (2023), TEXTure - [2302.01721](https://arxiv.org/abs/2302.01721)
        * Zeng et al. (2023), Paint3D - [2312.13913](https://arxiv.org/abs/2312.13913)
        * Le et al. (2024), EucliDreamer - [2311.15573](https://arxiv.org/abs/2311.15573)
        * Ceylan et al. (2024), MatAtlas - [2404.02899](https://arxiv.org/abs/2404.02899)
    * **Other Influential Works:**
        * Siddiqui et al. (2022), Texturify - [2204.02411](https://arxiv.org/abs/2204.02411)
        * Bokhovkin et al. (2023), Mesh2Tex - [2304.05868](https://arxiv.org/abs/2304.05868)
        * Levin & Fried (2024), Differential Diffusion - [2306.00950](https://arxiv.org/abs/2306.00950)

The open spirit of the AI and open-source communities is what makes projects like StableGen possible.

---

## 💡 List of planned features

Here are some features we plan to implement in the future (in no particular order):
* **Advanced IPAdapter support:** Support for custom IPAdapter models, support for advanced IPAdapter parameters.
* **Upscaling:** Support for upscaling generated textures.
* **FLUX.1-dev Support:** Full support for the FLUX.1-dev, including IPAdapter, depth control LoRAs, and more.
* **SD 3.5 Support:** Support for the Stable Diffusion 3.5 architecture.
* **Remote ComfyUI Support:** Allow connecting to remote ComfyUI servers, enabling distributed processing.

If you have any suggestions, please feel free to open an issue!

---

## 📧 Contact

Ondřej Sakala
* Email: `sakalaondrej@gmail.com`
* X/Twitter: `@sakalond`

---
*Last Updated: May 24, 2025*
