from __future__ import annotations

from .gamescope import GamescopeBackend
from .mesa_gallium import MesaGalliumBackend
from .null import NullBackend
from .presentmon import PresentMonBackend
from .vulkan_layer import VulkanLayerBackend


def all_backends():
    return [
        NullBackend(),
        VulkanLayerBackend(),
        PresentMonBackend(),
        GamescopeBackend(),
        MesaGalliumBackend(),
    ]


__all__ = [
    "NullBackend",
    "VulkanLayerBackend",
    "PresentMonBackend",
    "GamescopeBackend",
    "MesaGalliumBackend",
    "all_backends",
]
