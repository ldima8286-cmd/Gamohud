from __future__ import annotations

from .gamescope import GamescopeBackend
from .mesa_gallium import MesaGalliumBackend
from .null import NullBackend
from .vulkan_layer import VulkanLayerBackend


def all_backends():
    return [
        NullBackend(),
        VulkanLayerBackend(),
        GamescopeBackend(),
        MesaGalliumBackend(),
    ]


__all__ = [
    "NullBackend",
    "VulkanLayerBackend",
    "GamescopeBackend",
    "MesaGalliumBackend",
    "all_backends",
]
