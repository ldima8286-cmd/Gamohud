from __future__ import annotations

from .backends import all_backends
from .base import BackendStatus, FPSBackend


class FPSManager:
    """Owns the currently selected FPS backend and multiplexes its interface."""

    def __init__(self, name: str = "null"):
        self._backends = {b.name: b for b in all_backends()}
        self._backend = self._backends.get("null")
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
        return self._backend.read()

    def is_env_only(self) -> bool:
        return self._backend.env_only
