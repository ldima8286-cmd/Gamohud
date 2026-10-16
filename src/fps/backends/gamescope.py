"""gamescope backend.

Wraps the launched application with `gamescope` so the nested compositor owns
frame timing. gamescope has no stable public FPS API, so reading the numbers
back is experimental: if a stats dump path is configured (profile or env) we
parse the newest numeric frame rate from it, otherwise we report nothing.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from src.platform_utils import IS_LINUX
from ..base import BackendStatus, FPSBackend


class GamescopeBackend(FPSBackend):
    name = "gamescope"
    label = "gamescope"
    description = "Run the app inside gamescope (nested compositor). Experimental stats."
    env_only = False

    def __init__(self):
        self._stats_path = None
        self._last = None

    def available(self) -> BackendStatus:
        if not IS_LINUX:
            return BackendStatus(False, "gamescope is Linux-only")
        if shutil.which("gamescope"):
            return BackendStatus(True)
        return BackendStatus(False, "gamescope not installed")

    def command_prefix(self, profile=None) -> list:
        prefix = ["gamescope", "-f", "--"]
        if profile is not None:
            prefix = getattr(profile, "gamescope_args", None) or prefix
        self._stats_path = (
            getattr(profile, "gamescope_stats_path", None)
            if profile is not None else None
        ) or os.environ.get("GAMESCOPE_STATS_PATH")
        return list(prefix)

    def read(self) -> dict | None:
        if not self._stats_path:
            return None
        p = Path(self._stats_path)
        if not p.exists():
            return None
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
        for token in reversed(text.replace("\n", " ").split()):
            try:
                value = float(token)
            except ValueError:
                continue
            if 0 < value < 2000:
                self._last = value
                return {"fps": round(value, 1)}
        return None
