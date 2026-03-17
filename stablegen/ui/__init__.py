"""UI components for the StableGen addon."""

# -- presets.py ---------------------------------------------------------------
from .presets import (                      # noqa: F401
    PRESETS,
    GEN_PARAMETERS,
    get_preset_items,
    update_parameters,
    ResetQwenPrompt,
    ApplyPreset,
    SwitchToMeshGeneration,
    SavePreset,
    DeletePreset,
)

# -- panel.py -----------------------------------------------------------------
from .panel import StableGenPanel           # noqa: F401

# -- queue.py -----------------------------------------------------------------
from .queue import (                        # noqa: F401
    SceneQueueItem,
    _sg_queue_load_handler,
    _sg_queue_save,
    _sg_queue_load,
    SG_UL_SceneQueueList,
    SceneQueueAdd,
    SceneQueueRemove,
    SceneQueueClear,
    SceneQueueMoveUp,
    SceneQueueMoveDown,
    SceneQueueOpenResult,
    SceneQueueInvalidate,
    SceneQueueProcess,
    _resume_queue,
    _queue_tick,
    _persist_queue,
    _tag_redraw,
)
