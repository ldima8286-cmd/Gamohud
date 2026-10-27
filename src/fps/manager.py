from __future__ import annotations

from .backends import all_backends
from .base import BackendStatus, FPSBackend
from .stats import FPSStats


class FPSManager:
    """Owns the currently selected FPS backend and multiplexes its interface."""

    def __init__(self, name: str = "null"):
        self._backends = {b.name: b for b in all_backends()}
        self._backend = self._backends.get("null")
        self._stats = FPSStats()
        self.set_backend(name)

    def backends(self) -> list[FPSBackend]:
        return list(self._backends.values())

    def statuses(self) -> list[tuple[FPSBackend, BackendStatus]]:
        return [(b, b.available()) for b in self._backends.values()]

    @property
    def name(self) -> str:
        return self._backend.name

    @property
    def backend(self) -> FPSBackend:
        return self._backend

    def set_backend(self, name: str) -> bool:
        backend = self._backends.get(name)
        if backend is None:
            backend = self._backends["null"]
        if backend is self._backend:
            return True
        if self._backend is not None:
            try:
                self._backend.stop()
            except Exception:
                pass
        self._backend = backend
        self._stats.reset()
        return True

    def available(self, name: str) -> BackendStatus:
        b = self._backends.get(name)
        if b is None:
            return BackendStatus(False, "unknown backend")
        return b.available()

    def launch_env(self, profile=None) -> dict:
        return self._backend.launch_env(profile)

    def command_prefix(self, profile=None) -> list:
        return self._backend.command_prefix(profile)

    def start(self, command=None, profile=None) -> None:
        self._backend.start(command, profile)

    def stop(self) -> None:
        self._backend.stop()

    def read(self) -> dict | None:
        data = self._backend.read()
        if data and data.get("fps") is not None:
            self._stats.add(data.get("fps"))
        summary = self._stats.summary()
        if data is None:
            return summary or None
        data.update(summary)
        return data

    def reset_stats(self) -> None:
        self._stats.reset()

    def is_env_only(self) -> bool:
        return self._backend.env_only

    def set_mangohud_log_dir(self, path: str | None) -> None:
        backend = self._backends.get("mangohud_log")
        if backend is not None and hasattr(backend, "set_log_dir"):
            backend.set_log_dir(path)

    def set_mangohud_hide_hud(self, hide: bool) -> None:
        backend = self._backends.get("mangohud_log")
        if backend is not None and hasattr(backend, "set_hide_hud"):
            backend.set_hide_hud(hide)

    def fallback_backend(self, preferred: list[str] | None = None) -> str | None:
        """Return the first usable measurement backend, or ``None``.

        ``mesa_gallium`` is intentionally skipped: it draws Mesa's own HUD but
        cannot feed numbers back into our overlay.
        """
        order = preferred or [
            "mangohud_log",
            "vulkan_layer",
            "presentmon",
            "gamescope",
        ]
        for name in order:
            backend = self._backends.get(name)
            if backend is None or backend.env_only:
                continue
            if backend.available().available:
                return name
        return None
