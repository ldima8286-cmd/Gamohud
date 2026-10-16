"""Pluggable FPS measurement backends.

Because no Linux compositor or GPU exposes a process' frame rate directly,
measuring real in-game FPS always needs one of:

* injecting into the application (a Vulkan implicit layer / OpenGL preload),
* running under a frame-owning compositor such as gamescope,
* or letting Mesa draw its own HUD (GALLIUM_HUD).

Every backend implements this small interface so the overlay and launcher can
treat them uniformly. A backend may also be *environment only* (it changes the
launch environment but does not feed FPS back into our overlay).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackendStatus:
    available: bool
    reason: str = ""


class FPSBackend:
    name = "null"
    label = "Disabled"
    description = ""
    env_only = False

    def available(self) -> BackendStatus:
        return BackendStatus(True)

    def launch_env(self, profile=None) -> dict:
        return {}

    def command_prefix(self, profile=None) -> list:
        return []

    def start(self, command=None, profile=None) -> None:
        pass

    def stop(self) -> None:
        pass

    def read(self) -> dict | None:
        return None
