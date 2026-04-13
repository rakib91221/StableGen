"""Topology improvement utilities for imported DAE meshes.

Addresses low-poly issues and bad topology from SketchUp:
- Voxel remesh for clean topology
- Planar decimation to simplify flat surfaces then subdivide
- Adaptive subdivision for large faces
- QuadriFlow remesh for high-quality quad topology
"""

import bpy    # pylint: disable=import-error
import bmesh   # pylint: disable=import-error
import math


def voxel_remesh(obj, voxel_size=0.02):
    """Apply voxel remesh to get clean, uniform topology.

    Args:
        obj: Blender mesh object.
        voxel_size: Size of voxels in Blender units. Smaller = more detail.
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Auto-calculate voxel size if not specified: ~1/100th of bounding box diagonal
    if voxel_size <= 0:
        bbox = obj.bound_box
        dims = obj.dimensions
        diagonal = math.sqrt(dims.x ** 2 + dims.y ** 2 + dims.z ** 2)
        voxel_size = diagonal / 100.0

    obj.data.remesh_voxel_size = voxel_size
    bpy.ops.object.voxel_remesh()


def subdivide_large_faces(obj, area_threshold=None, max_cuts=2):
    """Subdivide faces that are larger than a threshold.

    This addresses the low-poly problem where large flat faces cause
    texture distortion. Only large faces are subdivided, preserving
    detail in already-dense areas.

    Args:
        obj: Blender mesh object.
        area_threshold: Minimum face area to subdivide. If None, auto-calculated
                        as 4x the median face area.
        max_cuts: Number of subdivision cuts per large face.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    if not bm.faces:
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    # Auto-calculate threshold from median face area
    if area_threshold is None:
        areas = sorted(f.calc_area() for f in bm.faces)
        median_area = areas[len(areas) // 2]
        area_threshold = median_area * 4.0

    # Select only large faces
    bpy.ops.mesh.select_all(action='DESELECT')
    bm.faces.ensure_lookup_table()
    selected_count = 0
    for face in bm.faces:
        if face.calc_area() > area_threshold:
            face.select = True
            selected_count += 1

    bmesh.update_edit_mesh(obj.data)

    if selected_count > 0:
        bpy.ops.mesh.subdivide(number_cuts=max_cuts)

    bpy.ops.object.mode_set(mode='OBJECT')
    return selected_count


def fix_triangle_fans(obj, max_edge_ratio=2.5, equalize_iterations=4):
    """Fix triangle fan patterns by dissolving flat regions and retriangulating.

    SketchUp creates fans where edges radiate from corner vertices across
    entire walls. This function:
    1. Dissolves all edges between coplanar faces → wall polygons
    2. Retriangulates with BEAUTY (Delaunay-like, avoids star/fan shapes)
    3. Iteratively splits long edges to equalize triangle density
    4. Runs beautify_fill to flip remaining sub-optimal triangle edges

    Args:
        obj: Blender mesh object.
        max_edge_ratio: Edges longer than median * this ratio get split.
        equalize_iterations: Max rounds of edge-length equalization.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Step 1: Dissolve all edges between coplanar faces.
    # This completely removes the original fan topology, merging flat
    # triangles back into their underlying wall/roof polygons.
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(1.0))

    # Step 2: Retriangulate with BEAUTY.
    # BEAUTY uses a Delaunay-like algorithm that maximises minimum angles,
    # producing roughly-equilateral triangles instead of fans.
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

    # Step 3: Iteratively split edges that are much longer than the
    # median, then retriangulate.  Each pass halves the longest edges
    # and redistributes triangles via BEAUTY.
    for _ in range(equalize_iterations):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        lengths = sorted(e.calc_length() for e in bm.edges)
        if not lengths:
            break
        median_len = lengths[len(lengths) // 2]
        threshold = median_len * max_edge_ratio

        bpy.ops.mesh.select_all(action='DESELECT')
        bm.edges.ensure_lookup_table()
        long_count = 0
        for edge in bm.edges:
            if edge.calc_length() > threshold:
                edge.select = True
                long_count += 1
        bmesh.update_edit_mesh(obj.data)

        if long_count == 0:
            break

        # Subdivide only the long edges (adds midpoint vertices)
        bpy.ops.mesh.subdivide(number_cuts=1)

        # Retriangulate so BEAUTY can incorporate the new vertices
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')

    # Step 4: Final beautify pass — flips existing triangle edges to
    # maximize minimum angles.  This catches remaining fan-like
    # connections that quads_convert_to_tris doesn't touch.
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.beautify_fill(angle_limit=math.radians(5))

    bpy.ops.object.mode_set(mode='OBJECT')


def planar_decimate(obj, angle_limit=2.0):
    """Dissolve edges between coplanar faces to simplify flat regions.

    This is useful for SketchUp models where flat walls are unnecessarily
    triangulated. Merges coplanar triangles into larger N-gons.

    Uses a conservative angle limit (2°) to avoid dissolving edges at
    window frames, door frames, and other intentional angle breaks.

    Args:
        obj: Blender mesh object.
        angle_limit: Maximum angle (degrees) between face normals to consider
                     them coplanar.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(angle_limit))
    bpy.ops.object.mode_set(mode='OBJECT')


def apply_subdivision_modifier(obj, levels=1):
    """Add and apply a Subdivision Surface modifier.

    Args:
        obj: Blender mesh object.
        levels: Subdivision levels to apply.
    """
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new(name="DAE_Subdiv", type='SUBSURF')
    mod.levels = levels
    mod.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=mod.name)


def auto_improve_topology(obj, method='planar_subdivide'):
    """High-level topology improvement combining multiple strategies.

    Methods:
        'fix_fans': Only fix triangle fan patterns, keep rest of topology.
                    Best balance of quality and preservation.
        'planar_subdivide': Dissolve coplanar faces, then subdivide large ones.
                            Can create poor triangulation on large walls.
        'voxel': Voxel remesh at auto-calculated resolution. Gives clean uniform
                 topology but loses sharp edges. Good for organic shapes.
        'subdivide_only': Just subdivide large faces without topology changes.

    Args:
        obj: Blender mesh object.
        method: One of 'fix_fans', 'planar_subdivide', 'voxel', 'subdivide_only'.
    """
    if method == 'fix_fans':
        fix_triangle_fans(obj)
    elif method == 'planar_subdivide':
        planar_decimate(obj, angle_limit=2.0)
        subdivide_large_faces(obj, max_cuts=2)
    elif method == 'voxel':
        voxel_remesh(obj, voxel_size=0)  # auto-size
    elif method == 'subdivide_only':
        subdivide_large_faces(obj, max_cuts=2)
