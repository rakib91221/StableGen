import bpy
import os

from .projection import get_or_load_image


def _clone_color_tree_for_pbr(nodes, links, source_node, cam_tex_to_pbr,
                               channel, y_offset):
    """Recursively clone the colour mix-tree, sharing *Fac* connections and
    swapping Image Texture leaves for their PBR counterparts.

    Args:
        nodes / links: ``mat.node_tree.nodes / links``.
        source_node: current node being cloned (walk from BSDF backwards).
        cam_tex_to_pbr: ``{color_tex_node: pbr_tex_node}``.
        channel: PBR channel name (for default values).
        y_offset: vertical pixel shift for cloned nodes.

    Returns:
        Output socket of the cloned sub-tree, or *None*.
    """
    # ── Leaf: Image Texture → swap for PBR variant ────────────────────
    if source_node.type == 'TEX_IMAGE':
        pbr_node = cam_tex_to_pbr.get(source_node)
        return pbr_node.outputs[0] if pbr_node else None

    # ── Resolve input names: ShaderNodeMixRGB vs ShaderNodeMix ────────
    #    Blender 4.0+ may use "A"/"B"/"Factor" instead of legacy names.
    fac_name, c1_name, c2_name = "Fac", "Color1", "Color2"
    if "Factor" in source_node.inputs and "A" in source_node.inputs:
        fac_name, c1_name, c2_name = "Factor", "A", "B"

    # ── MixRGB / Mix node → clone with same Fac ──────────────────────
    is_mix = (source_node.type in ('MIX_RGB', 'MIX')
              or (hasattr(source_node, 'bl_idname')
                  and source_node.bl_idname in (
                      'ShaderNodeMixRGB', 'ShaderNodeMix'))
              or (c1_name in source_node.inputs
                  and c2_name in source_node.inputs
                  and fac_name in source_node.inputs))
    if is_mix:
        c1_link = source_node.inputs[c1_name].links
        c2_link = source_node.inputs[c2_name].links
        c1_src = c1_link[0].from_node if c1_link else None
        c2_src = c2_link[0].from_node if c2_link else None

        c1_pbr = (_clone_color_tree_for_pbr(
            nodes, links, c1_src, cam_tex_to_pbr, channel, y_offset)
            if c1_src else None)
        c2_pbr = (_clone_color_tree_for_pbr(
            nodes, links, c2_src, cam_tex_to_pbr, channel, y_offset)
            if c2_src else None)

        if c1_pbr is None and c2_pbr is None:
            return None

        new_mix = nodes.new("ShaderNodeMixRGB")
        new_mix.location = (source_node.location[0],
                            source_node.location[1] + y_offset)
        new_mix.label = f"PBR_{channel}"

        # Share the Fac (visibility weight) connection
        fac_links = source_node.inputs[fac_name].links
        if fac_links:
            links.new(fac_links[0].from_socket, new_mix.inputs["Fac"])
        else:
            new_mix.inputs["Fac"].default_value = (
                source_node.inputs[fac_name].default_value)

        # Connect children
        if c1_pbr:
            links.new(c1_pbr, new_mix.inputs["Color1"])
        else:
            # Sensible defaults for uncovered areas
            defaults = {
                'roughness': (0.5, 0.5, 0.5, 1.0),
                'metallic':  (0.0, 0.0, 0.0, 1.0),
                'albedo':    (0.5, 0.5, 0.5, 1.0),
                'residual':  (0.0, 0.0, 0.0, 1.0),
                'shading':   (0.5, 0.5, 0.5, 1.0),
            }
            new_mix.inputs["Color1"].default_value = defaults.get(
                channel, (0.0, 0.0, 0.0, 1.0))

        if c2_pbr:
            links.new(c2_pbr, new_mix.inputs["Color2"])
        else:
            # For Color2 (the "fallback" side of the mix) we inherit the
            # original node's default so that areas not covered by any
            # camera projection keep the scene's fallback colour.  Only
            # data channels (roughness, metallic, …) use a hardcoded
            # neutral, because the original tree's fallback colour would
            # be nonsensical for those channels.
            defaults = {
                'roughness': (0.5, 0.5, 0.5, 1.0),
                'metallic':  (0.0, 0.0, 0.0, 1.0),
                'residual':  (0.0, 0.0, 0.0, 1.0),
                'shading':   (0.5, 0.5, 0.5, 1.0),
            }
            new_mix.inputs["Color2"].default_value = defaults.get(
                channel, source_node.inputs[c2_name].default_value)

        return new_mix.outputs[0]

    # ── Unknown node → follow first connected input ───────────────────
    for inp in source_node.inputs:
        if inp.links:
            result = _clone_color_tree_for_pbr(
                nodes, links, inp.links[0].from_node,
                cam_tex_to_pbr, channel, y_offset)
            if result:
                return result
    return None


def project_pbr_to_bsdf(context, to_texture, pbr_maps, material_id=None):
    """Project PBR decomposition maps through the same camera UV projections
    as the colour texture and wire them to the Principled BSDF.

    This function is called **after** ``project_image()`` has finished
    building the full colour projection material (including UV Project
    attributes and the visibility-weighted mix tree).

    For each PBR channel it:

    1. Creates Image Texture nodes that re-use the per-camera UV attributes
       already baked by ``project_image()``.
    2. Clones the colour MixRGB binary tree, sharing the **Fac** (weight)
       connections so visibility blending is identical.
    3. Wires the cloned tree's output to the corresponding Principled BSDF
       input (Roughness, Metallic, Base Color, etc.).

    Args:
        context: Blender context.
        to_texture: List of mesh objects that were textured.
        pbr_maps: ``{camera_idx: {map_name: file_path}, …}``.
        material_id: Material slot index used during generation.
    """
    scene = context.scene

    if not pbr_maps:
        return

    # Build channel → BSDF input map from enabled per-map toggles
    channel_wiring = {}   # map_name → BSDF input name
    special_wiring = {}   # map_name → special handler ('normal' | 'displacement')

    if getattr(scene, 'pbr_replace_color_with_albedo', True) and getattr(scene, 'pbr_map_albedo', True):
        channel_wiring['albedo'] = 'Base Color'
    if getattr(scene, 'pbr_map_roughness', True):
        channel_wiring['roughness'] = 'Roughness'
    if getattr(scene, 'pbr_map_metallic', True):
        channel_wiring['metallic'] = 'Metallic'
    if getattr(scene, 'pbr_map_normal', True):
        special_wiring['normal'] = 'normal'
    if getattr(scene, 'pbr_map_height', False):
        special_wiring['height'] = 'displacement'
    if getattr(scene, 'pbr_map_emission', False):
        special_wiring['emission'] = 'emission'
    processed_materials = set()

    for obj in to_texture:
        if not hasattr(obj, 'active_material') or not obj.active_material:
            continue
        mat = obj.active_material
        if mat.name in processed_materials:
            continue
        if not mat.use_nodes:
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # ── Find or create the Principled BSDF ────────────────────────────
        principled = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        if principled is None:
            # No BSDF exists yet.  Create one and rewire the existing
            # colour output through it so that PBR channels have
            # somewhere to connect.
            output_node = None
            for node in nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    output_node = node
                    break
            if output_node is None:
                continue

            principled = nodes.new("ShaderNodeBsdfPrincipled")
            principled.inputs["Roughness"].default_value = 1.0

            # Rewire: existing surface source → BSDF Base Color → Output
            surface_links = output_node.inputs["Surface"].links
            if surface_links:
                old_source = surface_links[0].from_socket
                # Position BSDF between old source and output
                principled.location = (
                    output_node.location[0] - 300,
                    output_node.location[1])
                links.new(old_source, principled.inputs["Base Color"])
            else:
                principled.location = (
                    output_node.location[0] - 300,
                    output_node.location[1])

            links.new(principled.outputs[0],
                      output_node.inputs["Surface"])

        # ── Discover existing camera Image Texture nodes ──────────────
        # Labels follow the pattern "{cam_idx}-{mat_id}" set by
        # project_image().
        camera_tex_nodes = {}  # cam_idx → tex_node
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.label and '-' in node.label:
                parts = node.label.split('-')
                try:
                    cam_idx = int(parts[0])
                    camera_tex_nodes[cam_idx] = node
                except ValueError:
                    continue

        if not camera_tex_nodes:
            continue

        # ── Find the root of the colour mix tree ─────────────────────
        color_root = None
        if principled.inputs["Base Color"].links:
            color_root = principled.inputs["Base Color"].links[0].from_node

        # ── For each PBR channel, create textures and clone the tree ──
        channel_idx = 0
        for channel, bsdf_input in channel_wiring.items():
            if bsdf_input not in principled.inputs:
                continue

            # Build mapping: colour_tex_node → PBR_tex_node
            cam_tex_to_pbr = {}
            for cam_idx, color_tex in camera_tex_nodes.items():
                if cam_idx not in pbr_maps:
                    continue
                cam_pbr = pbr_maps[cam_idx]
                if channel not in cam_pbr:
                    continue

                pbr_path = cam_pbr[channel]
                if not os.path.exists(pbr_path):
                    continue

                pbr_img = get_or_load_image(pbr_path, force_reload=True)
                if not pbr_img:
                    continue

                # Colorspace: roughness/metallic are always linear data.
                # Albedo from IID-Lighting is also linear; IID-Appearance
                # albedo is sRGB (Blender's default for PNG), so leave it.
                if channel in ('roughness', 'metallic'):
                    pbr_img.colorspace_settings.name = 'Non-Color'
                elif (channel == 'albedo'
                      and getattr(scene, 'pbr_albedo_source', 'marigold') == 'lighting'):
                    pbr_img.colorspace_settings.name = 'Non-Color'

                pbr_tex = nodes.new("ShaderNodeTexImage")
                pbr_tex.image = pbr_img
                pbr_tex.extension = 'CLIP'
                pbr_tex.label = (
                    f"PBR_{channel}_{cam_idx}_{material_id}")
                pbr_tex.location = (
                    color_tex.location[0],
                    color_tex.location[1]
                    - 200 * (1 + channel_idx) * len(camera_tex_nodes))

                # Re-use the same camera UV attribute
                if color_tex.inputs["Vector"].links:
                    uv_socket = (
                        color_tex.inputs["Vector"].links[0].from_socket)
                    links.new(uv_socket, pbr_tex.inputs["Vector"])

                cam_tex_to_pbr[color_tex] = pbr_tex

            if not cam_tex_to_pbr:
                continue

            # Clone the colour mix tree (or fall back to direct connection)
            pbr_final_output = None
            if color_root:
                y_off = -500 * (1 + channel_idx)
                pbr_output = _clone_color_tree_for_pbr(
                    nodes, links, color_root, cam_tex_to_pbr,
                    channel, y_off)
                if pbr_output:
                    pbr_final_output = pbr_output
            else:
                # No colour tree exists; connect first PBR texture directly
                first_pbr = next(iter(cam_tex_to_pbr.values()))
                pbr_final_output = first_pbr.outputs["Color"]

            if pbr_final_output:
                links.new(pbr_final_output,
                          principled.inputs[bsdf_input])

            channel_idx += 1

        # ── Special wiring: Normal Map + Displacement ─────────────────
        for sp_channel, sp_type in special_wiring.items():
            # Build PBR texture nodes for this special channel
            sp_tex_map = {}  # color_tex_node → pbr_tex_node
            for cam_idx, color_tex in camera_tex_nodes.items():
                if cam_idx not in pbr_maps:
                    continue
                cam_pbr = pbr_maps[cam_idx]
                if sp_channel not in cam_pbr:
                    continue
                sp_path = cam_pbr[sp_channel]
                if not os.path.exists(sp_path):
                    continue
                sp_img = get_or_load_image(sp_path, force_reload=True)
                if not sp_img:
                    continue
                sp_img.colorspace_settings.name = 'Non-Color'

                sp_tex = nodes.new("ShaderNodeTexImage")
                sp_tex.image = sp_img
                sp_tex.extension = 'CLIP'
                sp_tex.label = f"PBR_{sp_channel}_{cam_idx}_{material_id}"
                sp_tex.location = (
                    color_tex.location[0],
                    color_tex.location[1]
                    - 200 * (2 + channel_idx) * len(camera_tex_nodes))
                if color_tex.inputs["Vector"].links:
                    uv_socket = color_tex.inputs["Vector"].links[0].from_socket
                    links.new(uv_socket, sp_tex.inputs["Vector"])
                sp_tex_map[color_tex] = sp_tex

            if not sp_tex_map:
                continue

            # Clone the colour tree for this special channel
            sp_output = None
            if color_root:
                y_off = -500 * (2 + channel_idx)
                sp_output = _clone_color_tree_for_pbr(
                    nodes, links, color_root, sp_tex_map,
                    sp_channel, y_off)
            else:
                first_sp = next(iter(sp_tex_map.values()))
                sp_output = first_sp.outputs["Color"]

            if sp_output is None:
                continue

            if sp_type == 'normal':
                normal_strength = getattr(scene, 'pbr_normal_strength', 0.5)

                # World-space Normal Map — camera-space normals were
                # already converted in _convert_normals_cam_to_world().
                # Using WORLD space avoids tangent-frame dependency,
                # so it works on voxel-remeshed geometry.
                normal_map_node = nodes.new("ShaderNodeNormalMap")
                normal_map_node.space = 'WORLD'
                normal_map_node.location = (
                    principled.location[0] - 300,
                    principled.location[1] - 400)
                normal_map_node.label = "PBR Normal Map (World)"
                normal_map_node.inputs["Strength"].default_value = (
                    normal_strength)
                links.new(sp_output, normal_map_node.inputs["Color"])
                if "Normal" in principled.inputs:
                    links.new(normal_map_node.outputs["Normal"],
                              principled.inputs["Normal"])

            elif sp_type == 'displacement':
                # ── Displacement / Height Map ─────────────────────
                height_scale = getattr(scene, 'pbr_height_scale', 0.1)
                output_node = None
                for node in nodes:
                    if node.type == 'OUTPUT_MATERIAL':
                        output_node = node
                        break
                if output_node and "Displacement" in output_node.inputs:
                    disp_node = nodes.new("ShaderNodeDisplacement")
                    disp_node.location = (
                        output_node.location[0] - 300,
                        output_node.location[1] - 200)
                    disp_node.label = "PBR Displacement"
                    disp_node.inputs["Scale"].default_value = height_scale
                    disp_node.inputs["Midlevel"].default_value = 0.5
                    links.new(sp_output, disp_node.inputs["Height"])
                    links.new(disp_node.outputs["Displacement"],
                              output_node.inputs["Displacement"])

            elif sp_type == 'emission':
                # ── Emission Map ──────────────────────────────────
                emission_strength = getattr(
                    scene, 'pbr_emission_strength', 5.0)
                if "Emission Color" in principled.inputs:
                    links.new(sp_output,
                              principled.inputs["Emission Color"])
                    principled.inputs[
                        "Emission Strength"].default_value = emission_strength
                elif "Emission" in principled.inputs:
                    # Older Blender versions use "Emission" not "Emission Color"
                    links.new(sp_output,
                              principled.inputs["Emission"])
                    if "Emission Strength" in principled.inputs:
                        principled.inputs[
                            "Emission Strength"].default_value = emission_strength

            channel_idx += 1

        # ── Set BSDF default values ───────────────────────────────────
        if 'roughness' in channel_wiring:
            principled.inputs["Roughness"].default_value = 1.0
        if 'metallic' in channel_wiring:
            principled.inputs["Metallic"].default_value = 0.0

        processed_materials.add(mat.name)

    # ── AO Bake (geometry-based, per-object) ──────────────────────────
    if getattr(scene, 'pbr_map_ao', False):
        _bake_ao_for_objects(context, to_texture, scene)


def _bake_ao_for_objects(context, to_texture, scene):
    """Add shader-based Ambient Occlusion to materials.

    Inserts a Blender ``Ambient Occlusion`` shader node into each
    material and multiplies it with the Base Color input of the
    Principled BSDF.  This is evaluated at render time — zero bake
    time and works with any poly count.
    """
    ao_samples = getattr(scene, 'pbr_ao_samples', 16)
    ao_distance = getattr(scene, 'pbr_ao_distance', 0.0)

    print(f"[StableGen] Adding shader-based AO "
          f"({ao_samples} samples, distance={ao_distance})…")

    processed = set()
    for oi, obj in enumerate(to_texture):
        if not hasattr(obj, 'active_material') or not obj.active_material:
            continue
        mat = obj.active_material
        if mat.name in processed:
            continue
        if not mat.use_nodes:
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Find Principled BSDF
        principled = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        if principled is None:
            continue

        print(f"[StableGen]     Adding AO node to {mat.name} "
              f"({oi+1}/{len(to_texture)})…")

        # Create Ambient Occlusion shader node
        ao_node = nodes.new("ShaderNodeAmbientOcclusion")
        ao_node.samples = ao_samples
        ao_node.label = "PBR AO"
        ao_node.location = (
            principled.location[0] - 500,
            principled.location[1] + 350)
        if ao_distance > 0:
            ao_node.inputs["Distance"].default_value = ao_distance

        # Wire AO into the material:
        # Intercept Base Color → Principled BSDF with a Multiply mix.
        base_input = principled.inputs.get("Base Color")
        if base_input and base_input.links:
            old_source = base_input.links[0].from_socket

            mix_node = nodes.new("ShaderNodeMix")
            mix_node.data_type = 'RGBA'
            mix_node.blend_type = 'MULTIPLY'
            mix_node.inputs["Factor"].default_value = 1.0
            mix_node.location = (
                principled.location[0] - 200,
                principled.location[1] + 200)
            mix_node.label = "AO Multiply"

            links.new(old_source, mix_node.inputs[6])        # A (base colour)
            links.new(ao_node.outputs["AO"], mix_node.inputs[7])  # B (AO)
            links.new(mix_node.outputs[2], base_input)        # Result → Base Color
        else:
            # No existing link — just plug AO colour directly
            links.new(ao_node.outputs["Color"], base_input)

        processed.add(mat.name)

    print(f"[StableGen] AO shader nodes added "
          f"({len(processed)} material(s))")

