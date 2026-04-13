"""Geometry cleanup utilities for imported DAE meshes.

Addresses SketchUp-specific issues:
- Duplicate/overlapping faces from component boundaries
- Coincident vertices at joins
- Non-manifold geometry
- Inconsistent normals
- Excessive/conflicting materials
"""

import bpy      # pylint: disable=import-error
import bmesh     # pylint: disable=import-error
import mathutils # pylint: disable=import-error


def remove_exact_duplicate_faces(obj, precision=5):
    """Remove faces that share the exact same vertex positions.

    Uses high-precision coordinate rounding to detect true duplicates
    without affecting intentional nearby geometry. Also removes faces
    that share the same vertex objects (detected after merge-by-distance).
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    seen = {}
    duplicates = []

    for face in bm.faces:
        # Key 1: sorted vertex indices (catches faces sharing same verts after merge)
        vert_key = tuple(sorted(v.index for v in face.verts))
        # Key 2: sorted rounded positions (catches faces with coincident but separate verts)
        pos_key = tuple(sorted(
            (round(v.co.x, precision),
             round(v.co.y, precision),
             round(v.co.z, precision))
            for v in face.verts
        ))

        if vert_key in seen or pos_key in seen:
            duplicates.append(face)
        else:
            seen[vert_key] = face
            seen[pos_key] = face

    removed = len(duplicates)
    for f in duplicates:
        bm.faces.remove(f)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    return removed


def remove_coplanar_overlapping_faces(obj, distance_threshold=0.001, normal_threshold=0.95):
    """Remove overlapping coplanar faces from different SketchUp components.

    Detects overlapping faces by checking if any face's centroid lies
    very close to (and is coplanar with) another face. When two faces
    occupy the same space, the smaller one (or back-facing one) is removed.

    This catches overlapping geometry even when faces have different
    tessellation patterns.
    """
    bpy.context.view_layer.objects.active = obj

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    from mathutils.bvhtree import BVHTree

    bvh = BVHTree.FromBMesh(bm)

    to_remove = set()

    for face in bm.faces:
        if face.index in to_remove:
            continue

        center = face.calc_center_median()
        normal = face.normal

        # Cast a short ray forward and backward from the face center
        # to find very close parallel/anti-parallel faces
        for direction in (normal, -normal):
            origin = center + direction * 0.0001
            hit_loc, hit_normal, hit_idx, hit_dist = bvh.ray_cast(origin, direction, distance_threshold)

            if hit_loc is None or hit_idx is None:
                continue
            if hit_idx == face.index or hit_idx in to_remove:
                continue

            # Check if hit face is nearly coplanar (parallel or anti-parallel normal)
            hit_face = bm.faces[hit_idx]
            dot = normal.dot(hit_face.normal)

            if abs(dot) > normal_threshold:
                # Skip faces that share vertices — they are connected
                # geometry (e.g. window mullions), not true overlaps
                face_verts = set(v.index for v in face.verts)
                hit_verts = set(v.index for v in hit_face.verts)
                if face_verts & hit_verts:
                    continue

                # Faces are coplanar and very close — one is a duplicate
                # Remove the one with anti-parallel normal (back-face)
                # or the smaller one if normals are parallel
                if dot < 0:
                    # Anti-parallel normals — back face
                    to_remove.add(hit_idx)
                else:
                    # Parallel normals — keep the larger face
                    if face.calc_area() < hit_face.calc_area():
                        to_remove.add(face.index)
                    else:
                        to_remove.add(hit_idx)

    # Remove marked faces
    faces_to_remove = [bm.faces[i] for i in to_remove if i < len(bm.faces)]
    removed = len(faces_to_remove)

    for f in faces_to_remove:
        bm.faces.remove(f)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return removed


def merge_coincident_vertices(obj, threshold=0.0001):
    """Merge vertices that are essentially at the same position.

    Uses a very conservative threshold (0.1mm default) to avoid
    destroying any intentional detail. Also removes degenerate faces
    left behind after the merge.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=threshold)
    # Clean up degenerate geometry left after merge
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=threshold)
    bpy.ops.object.mode_set(mode='OBJECT')


def remove_loose_geometry(obj):
    """Remove loose vertices and edges (no faces attached)."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Remove wire edges (edges with no connected faces) via bmesh
    # — select_loose won't catch these if their vertices are shared
    # with faced edges
    bm = bmesh.from_edit_mesh(obj.data)
    wire_edges = [e for e in bm.edges if not e.link_faces]
    if wire_edges:
        bmesh.ops.delete(bm, geom=wire_edges, context='EDGES')
        bmesh.update_edit_mesh(obj.data)

    # Remove truly loose verts (no edges at all)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_loose()
    bpy.ops.mesh.delete(type='VERT')

    bpy.ops.object.mode_set(mode='OBJECT')


def fix_normals(obj):
    """Recalculate normals to face consistently outward."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def remove_interior_faces(obj, ray_samples=14):
    """Remove faces that are fully enclosed inside the mesh.

    Casts rays outward from face centers in multiple directions;
    if all rays hit another face of the same mesh, the face is
    considered interior (internal wall/partition).
    """
    bpy.context.view_layer.objects.active = obj

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    from mathutils.bvhtree import BVHTree

    bvh = BVHTree.FromBMesh(bm)

    # Generate ray directions: 6 axis-aligned + 8 diagonal corners
    directions = [
        mathutils.Vector((1, 0, 0)),
        mathutils.Vector((-1, 0, 0)),
        mathutils.Vector((0, 1, 0)),
        mathutils.Vector((0, -1, 0)),
        mathutils.Vector((0, 0, 1)),
        mathutils.Vector((0, 0, -1)),
        mathutils.Vector((1, 1, 1)).normalized(),
        mathutils.Vector((-1, 1, 1)).normalized(),
        mathutils.Vector((1, -1, 1)).normalized(),
        mathutils.Vector((-1, -1, 1)).normalized(),
        mathutils.Vector((1, 1, -1)).normalized(),
        mathutils.Vector((-1, 1, -1)).normalized(),
        mathutils.Vector((1, -1, -1)).normalized(),
        mathutils.Vector((-1, -1, -1)).normalized(),
    ]

    # Find candidate faces where all rays are blocked (no distance limit)
    candidate_indices = set()
    for face in bm.faces:
        center = face.calc_center_median()
        normal = face.normal
        all_blocked = True

        for d in directions:
            # Offset origin slightly along face normal to avoid self-hit
            origin = center + normal * 0.001
            hit_loc, hit_normal, hit_idx, hit_dist = bvh.ray_cast(origin, d)
            if hit_loc is None:
                all_blocked = False
                break

        if all_blocked:
            candidate_indices.add(face.index)

    if not candidate_indices:
        bm.free()
        return 0

    # Group candidates into edge-connected clusters.
    # Interior partitions form large contiguous surfaces while window
    # glass panes are small isolated patches. Only remove large clusters.
    visited = set()
    clusters = []
    for start_idx in candidate_indices:
        if start_idx in visited:
            continue
        cluster = []
        queue = [start_idx]
        while queue:
            idx = queue.pop()
            if idx in visited or idx not in candidate_indices:
                continue
            visited.add(idx)
            cluster.append(idx)
            for edge in bm.faces[idx].edges:
                for linked_face in edge.link_faces:
                    if linked_face.index not in visited and linked_face.index in candidate_indices:
                        queue.append(linked_face.index)
        clusters.append(cluster)

    # Only remove clusters whose total area exceeds 2% of the full mesh area
    total_area = sum(f.calc_area() for f in bm.faces)
    min_cluster_area = total_area * 0.02

    interior = []
    for cluster in clusters:
        cluster_area = sum(bm.faces[idx].calc_area() for idx in cluster)
        if cluster_area >= min_cluster_area:
            interior.extend(bm.faces[idx] for idx in cluster)

    removed = len(interior)
    for f in interior:
        bm.faces.remove(f)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return removed


def strip_materials_and_apply_clean(obj):
    """Remove all materials and assign a single clean Principled BSDF.

    This ensures compatibility with StableGen's projection/baking system.
    """
    # Clear all material slots
    obj.data.materials.clear()

    # Create a clean material
    mat = bpy.data.materials.new(name="SG_DAE_Material")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    nodes.clear()

    # Create Principled BSDF + Output
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    obj.data.materials.append(mat)


def join_all_meshes(context):
    """Join all mesh objects in the scene into a single object.

    Returns the resulting joined object, or None if no meshes found.
    """
    meshes = [obj for obj in context.scene.objects if obj.type == 'MESH']
    if not meshes:
        return None

    # Deselect all, then select only mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    context.view_layer.objects.active = meshes[0]

    if len(meshes) > 1:
        bpy.ops.object.join()

    return context.view_layer.objects.active


def remove_edge_only_objects(context):
    """Delete objects that have no faces (edge/vertex only geometry)."""
    removed = 0
    for obj in list(context.scene.objects):
        if obj.type == 'MESH' and len(obj.data.polygons) == 0:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def auto_smooth_shading(obj, angle=30.0):
    """Apply smooth shading with auto-smooth angle."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    # Blender 4.x+: use auto smooth via modifier or mesh attribute
    import math
    try:
        # Blender 4.1+
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(angle)
    except AttributeError:
        pass
