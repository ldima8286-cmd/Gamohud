"""Proxy that renders the overlay in a host layer-shell process.

KWin puts an active fullscreen window in a layer above ordinary ``keepAbove``
windows, so a normal Qt/KWin overlay disappears behind it.  A Wayland
``layer-shell`` surface on the overlay layer is above it.  The GUI's bundled
Qt may not match the system layer-shell-qt ABI, so we start a tiny helper with
the system Python/PySide6 and exchange state through JSON files.

If the helper cannot be used (X11, Qt mismatch, no layer-shell-qt), the GUI
keeps using ``OverlayWindow`` exactly as before.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QTimer

from src.platform_utils import (
    default_mangohud_log_dir,
    host_command,
    host_run,
)

_SYSTEM_PYTHON = Path("/usr/bin/python3")
_PROBE = """
import ctypes
import ctypes.util
import PySide6
lib = ctypes.util.find_library("LayerShellQtInterface")
if not lib:
    raise SystemExit("layer-shell-qt is not installed")
ctypes.CDLL(lib)
print(PySide6.__version__)
"""


def host_overlay_available(platform_name: str) -> str | None:
    """Return the host Python interpreter to use, or ``None``.

    The interpreter must have PySide6 built against the installed
    layer-shell-qt library; loading the library is the exact ABI check.
    """
    if os.environ.get("GAMOHUD_NO_LAYER_SHELL") or platform_name != "wayland":
        return None
    python = str(_SYSTEM_PYTHON) if _SYSTEM_PYTHON.exists() else "python3"
    try:
        result = host_run([python, "-c", _PROBE], timeout=8)
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return python


class HostOverlay:
    """Subset of ``OverlayWindow``'s API backed by the helper process."""

    def __init__(self, data_provider, python: str):
        self._data_provider = data_provider
        self._python = python
        self.profile = None
        self.on_position_changed = None
        self.external_position = True
        self._visible = False
        self._locked = True
        self._proc: subprocess.Popen | None = None
        self._log_file = None
        self._last_spawn = 0.0
        # ``/run/user`` inside a Flatpak is not the host runtime directory.
        # The data directory below is shared by both the GUI (even sandboxed)
        # and the host helper, just like the MangoHud logs.
        run_dir = default_mangohud_log_dir().parent / "runtime"
        self._state_path = run_dir / "overlay.json"
        self._position_path = run_dir / "overlay-position.json"
        self._log_path = run_dir / "overlay.log"
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)

    # -- OverlayWindow-compatible API ------------------------------------
    def start(self, profile):
        self.profile = profile
        self._visible = True
        self._ensure_process()
        self._timer.start()
        self._write_state()

    def show(self):
        self._visible = True
        self._ensure_process()
        self._timer.start()
        self._write_state()

    def hide(self):
        self._visible = False
        self._write_state()

    def isVisible(self) -> bool:  # noqa: N802 - Qt spelling used by the GUI
        return self._visible

    def windowTitle(self) -> str:  # noqa: N802
        return "gamohud-layer-shell"

    def raise_(self):
        # Layer-shell surfaces already sit above normal windows.
        return None

    def set_profile(self, profile):
        self.profile = profile
        self._ensure_process()
        self._timer.start()
        self._write_state()

    def set_locked(self, locked: bool):
        self._locked = bool(locked)
        self._write_state()

    def refresh(self):
        self._write_state()

    def stop(self):
        self._visible = False
        if self.window_exists():
            self._write_state()
        self._timer.stop()
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None
        for path in (self._state_path, self._position_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except Exception:
                pass

    def window_exists(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # -- state exchange ---------------------------------------------------
    def _tick(self):
        self._read_position()
        if self._visible and not self.window_exists():
            # A crashed helper should not kill the overlay silently.  Retry at
            # most once every few seconds; the log file explains why.
            if time.monotonic() - self._last_spawn > 5:
                self._ensure_process()
        self._write_state()

    def _ensure_process(self):
        if self.window_exists():
            return
        helper = Path(__file__).with_name("overlay_helper.py")
        if not helper.exists():
            return
        try:
            self._log_file = open(self._log_path, "ab", buffering=0)
        except Exception:
            self._log_file = subprocess.DEVNULL
        cmd = host_command(
            [
                self._python,
                str(helper),
                "--state",
                str(self._state_path),
                "--position",
                str(self._position_path),
            ]
        )
        env = os.environ.copy()
        # Do not leak the GUI venv's PySide6 into the host helper.
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env["QT_QPA_PLATFORM"] = "wayland"
        env["PYTHONNOUSERSITE"] = "1"
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=self._log_file,
                stderr=self._log_file,
                env=env,
                start_new_session=True,
            )
            self._last_spawn = time.monotonic()
        except Exception as exc:
            self._proc = None
            try:
                self._log_path.write_text(f"could not start overlay helper: {exc}\n")
            except Exception:
                pass

    def _write_state(self):
        if self.profile is None:
            return
        try:
            metrics = self._data_provider() or {}
        except Exception:
            metrics = {}
        state = {
            "ts": time.time(),
            "title": self.windowTitle(),
            "profile": self.profile.to_dict(),
            "metrics": metrics,
            "locked": bool(self._locked),
            "visible": bool(self._visible),
        }
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(state), encoding="utf-8")
            tmp.replace(self._state_path)
        except Exception:
            pass

    def _read_position(self):
        try:
            raw = self._position_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except FileNotFoundError:
            return
        except Exception:
            return
        try:
            self._position_path.unlink()
        except Exception:
            pass
        if self.profile is None or data.get("name") != self.profile.name:
            return
        try:
            x = max(0, int(data.get("x", 0)))
            y = max(0, int(data.get("y", 0)))
        except Exception:
            return
        self.profile.position = "custom"
        self.profile.x = x
        self.profile.y = y
        self._write_state()
        if callable(self.on_position_changed):
            self.on_position_changed()
