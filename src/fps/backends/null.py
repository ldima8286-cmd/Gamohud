from __future__ import annotations

from ..base import BackendStatus, FPSBackend


class NullBackend(FPSBackend):
    name = "null"
    label = "Disabled"
    description = "No FPS measurement. Shows system metrics only."

    def available(self) -> BackendStatus:
        return BackendStatus(True)
