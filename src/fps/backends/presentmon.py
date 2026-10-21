"""PresentMon FPS backend (Windows).

Launches Intel's PresentMon (https://github.com/GameTechDev/PresentMon) as a
detached helper that captures present events over ETW and writes FPS/frametime
to the same ``gamohud-fps.json`` the overlay already reads.

Unlike the Vulkan layer this covers **DirectX 9/10/11/12 and OpenGL** as well
as Vulkan, so it is the backend to use for non-Vulkan Windows games.

PresentMon is MIT-licensed (c) Intel and is *not* bundled with gamohud. Fetch
it with ``python tools/fetch_presentmon.py`` or point ``GAMOHUD_PRESENTMON`` at
an existing copy. Capturing requires the user to be an administrator or a
member of the "Performance Log Users" group.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from src.platform_utils import IS_WINDOWS, runtime_dir

from ..base import BackendStatus, FPSBackend
from ..presentmon_common import FPS_FILENAME, find_presentmon, target_process_name

# DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
_CREATE_FLAGS = 0x00000008 | 0x00000200 | 0x08000000


def _helper_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "presentmon-helper"]
    helper = Path(__file__).resolve().parents[1] / "presentmon_helper.py"
    return [sys.executable, str(helper)]


class PresentMonBackend(FPSBackend):
    name = "presentmon"
    label = "PresentMon (DirectX/OpenGL/Vulkan)"
    description = (
        "Intel PresentMon ETW capture. Covers DirectX 9/10/11/12, OpenGL and "
        "Vulkan. Windows only; needs admin or Performance Log Users."
    )
    env_only = False

    def __init__(self):
        self._proc: subprocess.Popen | None = None

    def _out_file(self) -> Path:
        return runtime_dir() / FPS_FILENAME

    def available(self) -> BackendStatus:
        if not IS_WINDOWS:
            return BackendStatus(False, "Windows only")
        if find_presentmon() is None:
            return BackendStatus(
                False,
                "PresentMon.exe not found (run tools/fetch_presentmon.py or set GAMOHUD_PRESENTMON)",
            )
        return BackendStatus(True)

    def start(self, command=None, profile=None) -> None:
        self.stop()
        exe = find_presentmon()
        if exe is None:
            return
        target = target_process_name(command, profile)
        out = self._out_file()
        try:
            out.unlink()
        except OSError:
            pass

        cmd = _helper_command() + ["--exe", str(exe), "--out", str(out)]
        if target:
            cmd += ["--target", target]
        if os.environ.get("GAMOHUD_PRESENTMON_ADMIN"):
            cmd.append("--admin")

        kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        if IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_FLAGS
        try:
            self._proc = subprocess.Popen(cmd, **kwargs)
        except OSError:
            self._proc = None

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            self._out_file().unlink()
        except OSError:
            pass

    def read(self) -> dict | None:
        path = self._out_file()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return None
        result = {}
        if isinstance(data.get("fps"), (int, float)):
            result["fps"] = round(float(data["fps"]), 1)
        if isinstance(data.get("frametime"), (int, float)):
            result["frametime"] = round(float(data["frametime"]), 2)
        return result or None
