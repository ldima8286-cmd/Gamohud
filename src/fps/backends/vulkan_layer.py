"""Own Vulkan implicit-layer backend (placeholder / future work).

When our companion C layer (`libgamohud_layer.so` + `gamohud_layer.json`) is
installed, this backend injects it into Vulkan/DXVK/VKD3D applications and reads
frame statistics the layer publishes to `$XDG_RUNTIME_DIR/gamohud-fps.json`.

The C layer is not shipped yet, so `available()` reports False and the overlay
falls back to other backends. The read path is ready so dropping in the layer
later requires no further changes here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ..base import BackendStatus, FPSBackend

_LAYER_NAME = "VK_LAYER_GAMOHUD_overlay"


def _layer_dirs():
    xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return [
        Path(__file__).resolve().parents[3] / "assets" / "vulkan_layer",
        Path(xdg) / "vulkan" / "implicit_layer.d",
        Path("/usr/share/vulkan/implicit_layer.d"),
    ]


def _layer_json() -> Path | None:
    for d in _layer_dirs():
        candidate = d / "gamohud_layer.json"
        if candidate.exists():
            return candidate
    return None


class VulkanLayerBackend(FPSBackend):
    name = "vulkan_layer"
    label = "gamohud Vulkan layer"
    description = "Our own implicit Vulkan layer. Real FPS in Vulkan/DXVK/VKD3D apps."
    env_only = False

    def _runtime_file(self) -> Path:
        run = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
        return Path(run) / "gamohud-fps.json"

    def available(self) -> BackendStatus:
        if _layer_json() is None:
            return BackendStatus(False, "gamohud Vulkan layer not installed yet")
        return BackendStatus(True)

    def launch_env(self, profile=None) -> dict:
        manifest = _layer_json()
        if manifest is None:
            return {}
        return {
            "VK_INSTANCE_LAYERS": _LAYER_NAME,
            "VK_LAYER_PATH": str(manifest.parent),
            "GAMOHUD_FPS_FILE": str(self._runtime_file()),
        }

    def read(self) -> dict | None:
        p = self._runtime_file()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return None
        result = {}
        if "fps" in data:
            try:
                result["fps"] = round(float(data["fps"]), 1)
            except Exception:
                pass
        if "frametime" in data:
            try:
                result["frametime"] = round(float(data["frametime"]), 2)
            except Exception:
                pass
        return result or None
