"""texturing – image-to-texture pipeline: exports, masks, baking, orbit GIF."""

# -- rendering.py ------------------------------------------------------------
from .rendering import (                    # noqa: F401
    purge_orphans,
    apply_vignette_to_mask,
    create_edge_feathered_mask,
    render_edge_feather_mask,
    apply_uv_inpaint_texture,
    flatten_projection_material_for_refine,
    export_emit_image,
    export_render,
    export_viewport,
    export_canny,
    expand_mask_to_blocks,
    export_visibility,
    SwitchMaterial,
    prepare_baking,
    unwrap,
    bake_texture,
    bake_pbr_channel,
    BakeTextures,
)

# -- orbit_export.py ---------------------------------------------------------
from .orbit_export import ExportOrbitGIF    # noqa: F401

# -- game_export.py ----------------------------------------------------------
from .game_export import ExportForGameEngine  # noqa: F401

# -- generator.py ------------------------------------------------------------
from .generator import (                    # noqa: F401
    ComfyUIGenerate,
    Regenerate,
    Reproject,
    MirrorReproject,
)

# -- pbr.py ------------------------------------------------------------------
from .pbr import _PBRMixin                  # noqa: F401

# -- gallery.py --------------------------------------------------------------
from .gallery import _PreviewGalleryOverlay  # noqa: F401

# -- projection.py -----------------------------------------------------------
from .projection import (                    # noqa: F401
    _SG_BUFFER_UV_NAME,
    _copy_uv_to_attribute,
    project_image,
    get_or_create_osl_text,
    get_or_load_image,
    reinstate_compare_nodes,
    create_native_raycast_visibility,
    create_native_feather,
)

# -- pbr_projection.py -------------------------------------------------------
from .pbr_projection import project_pbr_to_bsdf  # noqa: F401
