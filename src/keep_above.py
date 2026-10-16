"""Best-effort "always on top" + position restore for KDE/KWin on Wayland.

Qt's ``WindowStaysOnTopHint`` is honoured on X11 and Windows but ignored by
KWin on Wayland, and a normal Wayland toplevel cannot position itself
(``move()`` is a no-op). So the only way to keep the overlay above everything
*and* restore its saved position is to ask KWin itself: we load a small KWin
script (over D-Bus) that

  * sets ``keepAbove`` / ``skipTaskbar`` on our overlay, and
  * (optionally) moves the overlay to the saved global position.

The overlay is identified by its window title ("gamohud-overlay"). The position
is baked into the generated script on every load, so no file reads are needed
inside KWin.

Everything here is best-effort: if the session bus / KWin is not reachable
(e.g. inside a Flatpak sandbox, or on X11/Windows) every call degrades to a
no-op and the caller can report it.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from src.platform_utils import IS_LINUX, config_dir

_TITLE_PREFIX = "gamohud-overlay"

_SCRIPT = r'''
function isOverlay(w) {
    try {
        var t = "" + (w && w.caption ? w.caption : "");
        return t.indexOf("%TITLE%") === 0;
    } catch (e) { return false; }
}
function apply(w) {
    try {
        if (!w || !isOverlay(w)) return;
        try { w.keepAbove = true; } catch (e) {}
        try { w.skipTaskbar = true; } catch (e) {}
        try { w.skipSwitcher = true; } catch (e) {}
%RESTORE%
    } catch (e) {}
}
function applyAll() {
    try {
        if (typeof workspace === "undefined") return;
        if (workspace.windowList) {            // KWin 5.21+ / KWin 6
            workspace.windowList().forEach(apply);
            workspace.windowAdded.connect(apply);
        } else if (workspace.clientList) {     // older KWin 5
            workspace.clientList().forEach(apply);
            workspace.clientAdded.connect(apply);
        }
    } catch (e) {}
}
applyAll();
'''

_RESTORE_BLOCK = """        try {
            if (w.moveable) {
                var g = w.geometry;
                if (g.x !== %X% || g.y !== %Y%) {
                    w.geometry.x = %X%;
                    w.geometry.y = %Y%;
                }
            }
        } catch (e) {}"""


def _qdbus() -> str | None:
    for name in ("qdbus6", "qdbus", "qdbus-qt6"):
        p = shutil.which(name)
        if p:
            return p
    for p in (
        "/usr/bin/qdbus6",
        "/usr/bin/qdbus",
        "/run/host/usr/bin/qdbus6",
        "/run/host/usr/bin/qdbus",
    ):
        if os.path.exists(p):
            return p
    return None


def _call(tool: str, *args: str) -> str | None:
    try:
        r = subprocess.run(
            [tool, "org.kde.KWin", *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


class KeepAbove:
    def __init__(self) -> None:
        self._id: str | None = None
        self._tool: str | None = _qdbus() if IS_LINUX else None
        self._provider = None

    @property
    def available(self) -> bool:
        return self._tool is not None

    def set_position_provider(self, fn) -> None:
        """``fn()`` -> (x, y) global ints for the overlay, or None."""
        self._provider = fn

    def _script_text(self) -> str:
        restore = ""
        if self._provider is not None:
            xy = self._provider()
            if xy:
                x, y = int(xy[0]), int(xy[1])
                restore = _RESTORE_BLOCK.replace("%X%", str(x)).replace("%Y%", str(y))
        return _SCRIPT.replace("%TITLE%", _TITLE_PREFIX).replace("%RESTORE%", restore)

    def _write(self) -> str:
        path = config_dir("gamohud") / "keep_above.js"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._script_text(), encoding="utf-8")
        return str(path)

    def enable(self) -> tuple[bool, str]:
        """Write, load and run the KWin script. Returns (ok, message)."""
        if not IS_LINUX:
            return (False, "not Linux")
        if self._tool is None:
            return (False, "qdbus not found")
        try:
            path = self._write()
        except Exception as exc:  # pragma: no cover
            return (False, f"could not write script: {exc}")

        out = _call(
            self._tool,
            "/Scripting",
            "org.kde.kwin.Scripting.loadScript",
            path,
        )
        if out is None:
            return (False, "KWin D-Bus unavailable")
        self._id = "".join(ch for ch in out if ch.isdigit()) or None
        self._run()
        return (True, f"loaded (id={self._id})")

    def _run(self) -> None:
        if self._tool is None:
            return
        if self._id:
            _call(self._tool, f"/Scripting/Script{self._id}", "org.kde.kwin.Script.run")
        else:
            _call(self._tool, "/Scripting", "org.kde.kwin.Scripting.start")

    def reapply(self) -> None:
        """Regenerate the script (fresh position) and reload + re-run it.

        Called after the overlay is re-mapped (lock toggle) or moved, because a
        re-mapped Wayland window triggers windowAdded and must be re-placed.
        """
        if self._tool is None or self._id is None:
            return
        try:
            path = self._write()
        except Exception:
            return
        _call(self._tool, "/Scripting", "org.kde.kwin.Scripting.unloadScript", path)
        out = _call(self._tool, "/Scripting", "org.kde.kwin.Scripting.loadScript", path)
        if out is not None:
            self._id = "".join(ch for ch in out if ch.isdigit()) or self._id
        self._run()
