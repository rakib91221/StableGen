"""Game engine export operator (glTF/FBX)."""

import os
import bpy  # pylint: disable=import-error
from ..utils import get_dir_path, sg_modal_active

_ADDON_PKG = __package__.rsplit('.', 1)[0]

class ExportForGameEngine(bpy.types.Operator):
    """Export textured objects for game engines with PBR textures.

    Wraps Blender's glTF / FBX exporters with game-engine-optimal settings
    and auto-saves to the StableGen output directory."""
    bl_idname = "object.export_game_engine"
    bl_label = "Export for Game Engine"
    bl_options = {'REGISTER'}

    export_format: bpy.props.EnumProperty(
        name="Format",
        description="Export file format",
        items=[
            ('GLB', 'glTF Binary (.glb)',
             'Single-file binary glTF — best for web, Unity, Godot'),
            ('GLTF_SEPARATE', 'glTF + Textures (.gltf)',
             'Separate .gltf, .bin and texture files'),
            ('FBX', 'FBX (.fbx)',
             'Autodesk FBX with embedded textures — Unreal Engine'),
        ],
        default='GLB'
    ) # type: ignore

    export_scope: bpy.props.EnumProperty(
        name="Objects",
        description="Which objects to export",
        items=[
            ('SELECTED', 'Selected', 'Export selected mesh objects'),
            ('ALL_MESH', 'All Mesh', 'Export all visible mesh objects'),
        ],
        default='SELECTED'
    ) # type: ignore

    apply_transforms: bpy.props.BoolProperty(
        name="Apply Transforms",
        description="Apply location, rotation and scale before export",
        default=True
    ) # type: ignore

    export_animations: bpy.props.BoolProperty(
        name="Export Animations",
        description="Include animations in the export",
        default=False
    ) # type: ignore

    @classmethod
    def poll(cls, context):
        addon_prefs = context.preferences.addons[_ADDON_PKG].preferences
        if not os.path.exists(addon_prefs.output_dir):
            cls.poll_message_set("Output directory not set or does not exist (check addon preferences)")
            return False
        if sg_modal_active(context):
            cls.poll_message_set("Another operation is in progress")
            return False
        return True

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_format")
        layout.prop(self, "export_scope")
        layout.prop(self, "apply_transforms")
        layout.prop(self, "export_animations")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # ── Prepare selection ─────────────────────────────────────────
        original_selection = list(context.selected_objects)
        original_active = context.view_layer.objects.active

        if self.export_scope == 'ALL_MESH':
            bpy.ops.object.select_all(action='DESELECT')
            meshes = [o for o in context.view_layer.objects
                      if o.type == 'MESH' and not o.hide_get()]
            for o in meshes:
                o.select_set(True)
            if meshes:
                context.view_layer.objects.active = meshes[0]
        else:
            meshes = [o for o in context.selected_objects
                      if o.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "No mesh objects selected.")
                return {'CANCELLED'}

        # ── Output path ───────────────────────────────────────────────
        output_base = get_dir_path(context, "baked")
        os.makedirs(output_base, exist_ok=True)

        # Build filename from first object name
        base_name = meshes[0].name if meshes else "export"

        if self.export_format == 'FBX':
            ext = ".fbx"
        elif self.export_format == 'GLTF_SEPARATE':
            ext = ".gltf"
        else:
            ext = ".glb"
        filepath = os.path.join(output_base, f"{base_name}{ext}")

        # ── Apply transforms if requested ─────────────────────────────
        if self.apply_transforms:
            for o in meshes:
                o.select_set(True)
            bpy.ops.object.transform_apply(
                location=True, rotation=True, scale=True)

        # ── Export ────────────────────────────────────────────────────
        try:
            if self.export_format in ('GLB', 'GLTF_SEPARATE'):
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    export_format=self.export_format,
                    use_selection=True,
                    export_materials='EXPORT',
                    export_image_format='AUTO',
                    export_tangents=True,
                    export_yup=True,
                    export_apply=False,
                    export_animations=self.export_animations,
                )
            else:  # FBX
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    apply_scale_options='FBX_SCALE_ALL',
                    path_mode='COPY',
                    embed_textures=True,
                    bake_anim=self.export_animations,
                    mesh_smooth_type='FACE',
                )

            self.report({'INFO'},
                        f"Exported to {filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            import traceback
            traceback.print_exc()

        # ── Restore selection ─────────────────────────────────────────
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selection:
            try:
                o.select_set(True)
            except ReferenceError:
                pass
        if original_active:
            try:
                context.view_layer.objects.active = original_active
            except ReferenceError:
                pass

        return {'FINISHED'}