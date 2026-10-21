"""Own Vulkan implicit-layer backend.

The companion C layer (`libgamohud_layer.so` / `gamohud_layer.dll` plus a
`gamohud_layer.json` manifest) intercepts `vkQueuePresentKHR`, computes FPS and
frametime, and writes them to a JSON file the overlay reads. Build the layer
with `layer/build_layer.sh` (Unix) or `layer/build_layer.bat` (Windows).

When the layer is not installed, `available()` reports False with a reason and
the overlay simply falls back to other backends.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.platform_utils import IS_WINDOWS, config_dir, runtime_dir

from ..base import BackendStatus, FPSBackend

_LAYER_NAME = "VK_LAYER_GAMOHUD_overlay"


def _layer_dirs():
    root = Path(__file__).resolve().parents[3]
    dirs = [root / "layer" / "build", root / "assets" / "vulkan_layer"]
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "Vulkan" / "implicit_layer.d")
        dirs.append(config_dir("gamohud") / "vulkan_layer")
    else:
        xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        dirs.append(Path(xdg) / "vulkan" / "implicit_layer.d")
        dirs.append(Path("/usr/share/vulkan/implicit_layer.d"))
    return dirs


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
        return runtime_dir() / "gamohud-fps.json"

    def available(self) -> BackendStatus:
        manifest = _layer_json()
        if manifest is None:
            return BackendStatus(False, "gamohud Vulkan layer not built/installed")
        lib = manifest.parent / ("gamohud_layer.dll" if IS_WINDOWS else "libgamohud_layer.so")
        if not lib.exists():
            return BackendStatus(False, f"layer library missing next to {manifest.name}")
        return BackendStatus(True)

    def launch_env(self, profile=None) -> dict:
        manifest = _layer_json()
        if manifest is None:
            return {}
        return {
            "VK_INSTANCE_LAYERS": _LAYER_NAME,
            "VK_LAYER_PATH": str(manifest.parent),
            "GAMOHUD_ENABLE": "1",
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
