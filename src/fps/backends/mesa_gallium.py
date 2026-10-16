"""Mesa GALLIUM_HUD backend.

Environment-only: Mesa draws its own on-screen HUD for OpenGL (and some Vulkan)
applications on free drivers (AMD/Intel). We cannot read those numbers back, so
this backend simply wires up the environment variables and does not feed FPS
into the overlay.
"""
from __future__ import annotations

from pathlib import Path

from ..base import BackendStatus, FPSBackend


def _has_amdgpu() -> bool:
    drm = Path("/sys/class/drm")
    if not drm.exists():
        return False
    for card in drm.glob("card[0-9]"):
        uevent = ""
        try:
            uevent = (card / "device" / "uevent").read_text(errors="replace")
        except Exception:
            pass
        if "amdgpu" in uevent or "radeon" in uevent:
            return True
    return False


class MesaGalliumBackend(FPSBackend):
    name = "mesa_gallium"
    label = "Mesa GALLIUM_HUD"
    description = "Draws Mesa's own HUD (AMD/Intel OpenGL). Env only; not shown in overlay."
    env_only = True

    def __init__(self):
        self._hud = "fps:frametime"

    def available(self) -> BackendStatus:
        if _has_amdgpu():
            return BackendStatus(True)
        return BackendStatus(False, "no AMD/Intel free-driver GPU detected")

    def launch_env(self, profile=None) -> dict:
        hud = self._hud
        if profile is not None:
            hud = getattr(profile, "gallium_hud", None) or hud
        return {"GALLIUM_HUD": hud}
