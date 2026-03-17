"""cameras – camera placement, overlays, ordering, and camera operators."""

# -- geometry.py --------------------------------------------------------------
from .geometry import (                     # noqa: F401
    _SGCameraResolution,
    _get_camera_resolution,
    _store_per_camera_resolution,
)

# -- overlays.py --------------------------------------------------------------
from .overlays import (                     # noqa: F401
    _sg_ensure_crop_overlay,
    _sg_remove_crop_overlay,
    _sg_ensure_label_overlay,
    _sg_remove_label_overlay,
    _sg_hide_label_overlay,
    _sg_restore_label_overlay,
    _sg_restore_square_display,
    _setup_square_camera_display,
)

# -- placement.py -------------------------------------------------------------
from .placement import AddCameras           # noqa: F401

# -- operators.py -------------------------------------------------------------
from .operators import (                    # noqa: F401
    switch_viewport_to_camera,
    CloneCamera,
    MirrorCamera,
    ToggleCameraLabels,
)

# -- prompts.py ---------------------------------------------------------------
from .prompts import (                      # noqa: F401
    CameraPromptItem,
    CameraOrderItem,
    SG_UL_CameraOrderList,
    SyncCameraOrder,
    MoveCameraOrder,
    ApplyCameraOrderPreset,
    CollectCameraPrompts,
)
