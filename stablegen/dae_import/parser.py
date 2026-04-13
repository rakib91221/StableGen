"""XML-based COLLADA (.dae) parser.

Parses the subset of COLLADA 1.4/1.5 used by SketchUp exports:
- <library_geometries>: mesh positions, normals, texcoords, triangles
- <library_visual_scenes>: scene graph with transforms
- <library_nodes>: reusable component definitions (SketchUp components)
- <library_materials> / <library_effects>: basic diffuse colors
- Unit conversion (SketchUp uses inches)

Creates Blender mesh objects via the bmesh API with no dependency on
any deprecated Blender import operators.
"""

import xml.etree.ElementTree as ET
import math
from collections import defaultdict

try:
    import bpy          # pylint: disable=import-error
    import bmesh         # pylint: disable=import-error
    import mathutils     # pylint: disable=import-error
except ImportError:
    pass  # Allow importing outside Blender for testing

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


def _tag(name):
    """Return namespace-qualified tag."""
    return f"{{{NS['c']}}}{name}"


def _find(elem, path):
    return elem.find(path, NS)


def _findall(elem, path):
    return elem.findall(path, NS)


def _parse_float_array(text):
    """Parse a space-separated float string into a list of floats."""
    return [float(x) for x in text.split()]


def _parse_int_array(text):
    """Parse a space-separated int string into a list of ints."""
    return [int(x) for x in text.split()]


def _parse_matrix(text):
    """Parse a 16-float COLLADA matrix (row-major) into a mathutils.Matrix."""
    vals = _parse_float_array(text)
    if len(vals) != 16:
        return mathutils.Matrix.Identity(4)
    return mathutils.Matrix((
        vals[0:4],
        vals[4:8],
        vals[8:12],
        vals[12:16],
    ))


class _GeometryData:
    """Parsed geometry: vertex positions, normals, UVs, and face groups."""
    __slots__ = ("positions", "normals", "uvs", "face_groups")

    def __init__(self):
        self.positions = []   # list of (x, y, z)
        self.normals = []     # list of (nx, ny, nz)
        self.uvs = []         # list of (u, v)
        self.face_groups = [] # list of {material, faces: [(v_indices, uv_indices, n_indices)]}


class _MeshInstance:
    """A geometry placed in the scene with a world transform."""
    __slots__ = ("geo_id", "world_matrix", "material_map")

    def __init__(self, geo_id, world_matrix, material_map=None):
        self.geo_id = geo_id
        self.world_matrix = world_matrix
        self.material_map = material_map or {}


class ColladaParser:
    """Parse a COLLADA file and create Blender mesh objects."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()

        # Unit scale: COLLADA stores a <unit meter="X"> attribute
        self.unit_scale = 1.0
        self._parse_asset()

        # Lookup tables populated during parsing
        self.geometries = {}       # id -> _GeometryData
        self.library_nodes = {}    # id -> ET Element
        self.instances = []        # list of _MeshInstance

    def _parse_asset(self):
        """Extract unit scale and up-axis from <asset>."""
        asset = _find(self.root, "c:asset")
        if asset is not None:
            unit = _find(asset, "c:unit")
            if unit is not None:
                meter = unit.get("meter")
                if meter:
                    self.unit_scale = float(meter)

    # ------------------------------------------------------------------
    # Geometry parsing
    # ------------------------------------------------------------------

    def _parse_source(self, source_elem):
        """Parse a <source> element, return (data_list, stride)."""
        fa = _find(source_elem, "c:float_array")
        if fa is None or fa.text is None:
            return [], 3
        data = _parse_float_array(fa.text)
        accessor = _find(source_elem, "c:technique_common/c:accessor")
        stride = int(accessor.get("stride", "3")) if accessor is not None else 3
        return data, stride

    def _parse_geometry(self, geo_elem):
        """Parse a single <geometry> element into _GeometryData."""
        geo = _GeometryData()
        mesh_elem = _find(geo_elem, "c:mesh")
        if mesh_elem is None:
            return geo

        # Build source lookup: id -> (data, stride)
        sources = {}
        for src in _findall(mesh_elem, "c:source"):
            sid = src.get("id")
            data, stride = self._parse_source(src)
            sources[sid] = (data, stride)

        # Parse <vertices> to find position/normal source bindings
        vertices_elem = _find(mesh_elem, "c:vertices")
        vert_id = vertices_elem.get("id") if vertices_elem is not None else None
        pos_source_id = None
        norm_source_id = None

        if vertices_elem is not None:
            for inp in _findall(vertices_elem, "c:input"):
                semantic = inp.get("semantic")
                src_ref = inp.get("source", "").lstrip("#")
                if semantic == "POSITION":
                    pos_source_id = src_ref
                elif semantic == "NORMAL":
                    norm_source_id = src_ref

        # Extract positions
        if pos_source_id and pos_source_id in sources:
            data, stride = sources[pos_source_id]
            for i in range(0, len(data), stride):
                geo.positions.append(tuple(data[i:i + stride]))

        # Extract normals from vertices binding
        if norm_source_id and norm_source_id in sources:
            data, stride = sources[norm_source_id]
            for i in range(0, len(data), stride):
                geo.normals.append(tuple(data[i:i + stride]))

        # Parse <triangles> and <polylist> elements
        for prim_tag in ("c:triangles", "c:polylist"):
            for prim in _findall(mesh_elem, prim_tag):
                group = self._parse_primitive(prim, sources, vert_id,
                                              geo.positions, geo.normals, geo.uvs)
                if group and group["faces"]:
                    geo.face_groups.append(group)

        return geo

    def _parse_primitive(self, prim_elem, sources, vert_id, positions, normals, uvs):
        """Parse a <triangles> or <polylist> element into a face group."""
        count = int(prim_elem.get("count", "0"))
        material = prim_elem.get("material", "")
        if count == 0:
            return None

        # Determine input layout (which offsets map to which semantics)
        inputs = _findall(prim_elem, "c:input")
        max_offset = 0
        vertex_offset = None
        normal_offset = None
        texcoord_offset = None
        normal_source_id = None
        texcoord_source_id = None

        for inp in inputs:
            semantic = inp.get("semantic")
            offset = int(inp.get("offset", "0"))
            src_ref = inp.get("source", "").lstrip("#")
            max_offset = max(max_offset, offset)

            if semantic == "VERTEX":
                vertex_offset = offset
            elif semantic == "NORMAL":
                normal_offset = offset
                normal_source_id = src_ref
            elif semantic == "TEXCOORD":
                texcoord_offset = offset
                texcoord_source_id = src_ref

        stride = max_offset + 1  # number of indices per vertex in <p>

        # Parse normals from per-primitive source (if not in <vertices>)
        prim_normals = []
        if normal_source_id and normal_source_id in sources:
            data, ns = sources[normal_source_id]
            for i in range(0, len(data), ns):
                prim_normals.append(tuple(data[i:i + ns]))

        # Parse UVs
        prim_uvs = []
        if texcoord_source_id and texcoord_source_id in sources:
            data, us = sources[texcoord_source_id]
            for i in range(0, len(data), us):
                prim_uvs.append(tuple(data[i:i + min(us, 2)]))

        # Parse index array <p>
        p_elem = _find(prim_elem, "c:p")
        if p_elem is None or p_elem.text is None:
            return None
        p_data = _parse_int_array(p_elem.text)

        # Determine face sizes
        tag_local = prim_elem.tag.split("}")[-1] if "}" in prim_elem.tag else prim_elem.tag
        if tag_local == "triangles":
            vcount = [3] * count
        else:
            # <polylist> has a <vcount> element
            vc_elem = _find(prim_elem, "c:vcount")
            if vc_elem is None or vc_elem.text is None:
                return None
            vcount = _parse_int_array(vc_elem.text)

        faces = []
        idx = 0
        for nv in vcount:
            face_vert_indices = []
            face_norm_indices = []
            face_uv_indices = []
            for _ in range(nv):
                if idx + stride > len(p_data):
                    break
                if vertex_offset is not None:
                    face_vert_indices.append(p_data[idx + vertex_offset])
                if normal_offset is not None:
                    face_norm_indices.append(p_data[idx + normal_offset])
                if texcoord_offset is not None:
                    face_uv_indices.append(p_data[idx + texcoord_offset])
                idx += stride
            if len(face_vert_indices) >= 3:
                faces.append((face_vert_indices, face_norm_indices, face_uv_indices))

        return {"material": material, "faces": faces,
                "prim_normals": prim_normals, "prim_uvs": prim_uvs}

    # ------------------------------------------------------------------
    # Scene graph traversal
    # ------------------------------------------------------------------

    def _collect_library_nodes(self):
        """Build lookup for <library_nodes> definitions."""
        for node in _findall(self.root, ".//c:library_nodes/c:node"):
            nid = node.get("id")
            if nid:
                self.library_nodes[nid] = node

    def _traverse_node(self, node_elem, parent_matrix):
        """Recursively walk a <node>, collecting mesh instances."""
        # Compute this node's local transform
        local_matrix = mathutils.Matrix.Identity(4)
        mat_elem = _find(node_elem, "c:matrix")
        if mat_elem is not None and mat_elem.text:
            local_matrix = _parse_matrix(mat_elem.text)
        else:
            # Try decomposed transforms: translate, rotate, scale
            for translate in _findall(node_elem, "c:translate"):
                if translate.text:
                    vals = _parse_float_array(translate.text)
                    if len(vals) == 3:
                        t = mathutils.Matrix.Translation(vals)
                        local_matrix = local_matrix @ t
            for rotate in _findall(node_elem, "c:rotate"):
                if rotate.text:
                    vals = _parse_float_array(rotate.text)
                    if len(vals) == 4:
                        axis = mathutils.Vector(vals[:3])
                        angle = math.radians(vals[3])
                        r = mathutils.Matrix.Rotation(angle, 4, axis)
                        local_matrix = local_matrix @ r
            for scale_elem in _findall(node_elem, "c:scale"):
                if scale_elem.text:
                    vals = _parse_float_array(scale_elem.text)
                    if len(vals) == 3:
                        s = mathutils.Matrix.Diagonal((*vals, 1.0))
                        local_matrix = local_matrix @ s

        world_matrix = parent_matrix @ local_matrix

        # Collect instance_geometry references
        for ig in _findall(node_elem, "c:instance_geometry"):
            geo_url = ig.get("url", "").lstrip("#")
            if geo_url:
                # Parse material bindings
                mat_map = {}
                for im in _findall(ig, ".//c:instance_material"):
                    symbol = im.get("symbol", "")
                    target = im.get("target", "").lstrip("#")
                    if symbol and target:
                        mat_map[symbol] = target
                self.instances.append(_MeshInstance(geo_url, world_matrix, mat_map))

        # Resolve instance_node references (SketchUp components)
        for in_node in _findall(node_elem, "c:instance_node"):
            ref_url = in_node.get("url", "").lstrip("#")
            if ref_url and ref_url in self.library_nodes:
                self._traverse_node(self.library_nodes[ref_url], world_matrix)

        # Recurse into child <node> elements
        for child in _findall(node_elem, "c:node"):
            self._traverse_node(child, world_matrix)

    # ------------------------------------------------------------------
    # Blender object creation
    # ------------------------------------------------------------------

    def parse(self):
        """Parse the COLLADA file and populate internal data structures."""
        # Parse all geometries
        for geo_elem in _findall(self.root, ".//c:library_geometries/c:geometry"):
            gid = geo_elem.get("id")
            if gid:
                self.geometries[gid] = self._parse_geometry(geo_elem)

        # Build library_nodes lookup
        self._collect_library_nodes()

        # Walk visual scene
        for vs in _findall(self.root, ".//c:library_visual_scenes/c:visual_scene"):
            for node in _findall(vs, "c:node"):
                self._traverse_node(node, mathutils.Matrix.Identity(4))

    def create_blender_objects(self, context, name_prefix="DAE"):
        """Create Blender mesh objects from parsed COLLADA data.

        Returns list of created objects.
        """
        created = []
        collection = context.collection or context.scene.collection

        for i, inst in enumerate(self.instances):
            geo = self.geometries.get(inst.geo_id)
            if geo is None or not geo.positions or not geo.face_groups:
                continue

            mesh_name = f"{name_prefix}_{i:03d}"
            mesh = bpy.data.meshes.new(mesh_name)
            bm = bmesh.new()

            # Add vertices with unit scaling and world transform
            # Important: apply the world transform FIRST (in original units),
            # THEN scale to meters. The COLLADA matrix translations are in
            # the same unit system as the geometry positions.
            scale = self.unit_scale
            verts = []
            for pos in geo.positions:
                co = mathutils.Vector((pos[0], pos[1], pos[2]))
                co = inst.world_matrix @ co
                co = mathutils.Vector((co.x * scale, co.y * scale, co.z * scale))
                verts.append(bm.verts.new(co))
            bm.verts.ensure_lookup_table()
            bm.verts.index_update()

            # Collect all UVs from face groups
            has_any_uvs = any(
                grp.get("prim_uvs") and any(f[2] for f in grp["faces"])
                for grp in geo.face_groups
            )
            uv_layer = None
            if has_any_uvs:
                uv_layer = bm.loops.layers.uv.new("UVMap")

            # Add faces from each group
            for grp in geo.face_groups:
                prim_uvs = grp.get("prim_uvs", [])
                for face_data in grp["faces"]:
                    v_indices, _n_indices, uv_indices = face_data
                    # Validate indices
                    if any(vi >= len(verts) or vi < 0 for vi in v_indices):
                        continue
                    face_verts = [verts[vi] for vi in v_indices]
                    # Skip degenerate faces
                    if len(set(id(v) for v in face_verts)) < 3:
                        continue
                    try:
                        face = bm.faces.new(face_verts)
                    except ValueError:
                        # Face already exists (duplicate)
                        continue
                    # Assign UVs
                    if uv_layer and uv_indices and prim_uvs:
                        for loop, uv_idx in zip(face.loops, uv_indices):
                            if uv_idx < len(prim_uvs):
                                uv = prim_uvs[uv_idx]
                                loop[uv_layer].uv = (uv[0], uv[1]) if len(uv) >= 2 else (0, 0)

            if len(bm.faces) == 0:
                bm.free()
                continue

            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

            obj = bpy.data.objects.new(mesh_name, mesh)
            collection.objects.link(obj)
            created.append(obj)

        return created
