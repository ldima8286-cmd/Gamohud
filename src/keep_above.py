"""Best-effort "always on top" for KDE/KWin on Wayland.

Qt's ``WindowStaysOnTopHint`` is honoured on X11 and Windows but ignored by
KWin on Wayland, so the overlay can end up behind other windows. The only way
to force it above without a ``wlr-layer-shell`` surface is to ask KWin itself:
we load a tiny KWin script (over D-Bus) that sets ``keepAbove`` on our overlay
window. The overlay is identified by its window title ("gamohud-overlay"), so
the main window is left untouched.

All of this is best-effort: if the session bus / KWin is not reachable (e.g.
inside a Flatpak sandbox, or on X11/Windows) every call degrades to a no-op and
the caller can report it.
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
        if (isOverlay(w)) {
            w.keepAbove = true;
            w.skipTaskbar = true;
            w.skipSwitcher = true;
        }
    } catch (e) {}
}
try {
    if (typeof workspace !== "undefined") {
        if (workspace.windowList) {            // KWin 5.21+ / KWin 6
            workspace.windowList().forEach(apply);
            workspace.windowAdded.connect(apply);
        } else if (workspace.clientList) {     // older KWin 5
            workspace.clientList().forEach(apply);
            workspace.clientAdded.connect(apply);
        }
    }
} catch (e) {}
'''.replace("%TITLE%", _TITLE_PREFIX)


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

    @property
    def available(self) -> bool:
        return self._tool is not None

    def enable(self) -> tuple[bool, str]:
        """Write and load the KWin script. Returns (ok, message)."""
        if not IS_LINUX:
            return (False, "not Linux")
        if self._tool is None:
            return (False, "qdbus not found")
        path = config_dir("gamohud") / "keep_above.js"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_SCRIPT, encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            return (False, f"could not write script: {exc}")

        out = _call(
            self._tool,
            "/Scripting",
            "org.kde.kwin.Scripting.loadScript",
            str(path),
        )
        if out is None:
            return (False, "KWin D-Bus unavailable")
        self._id = "".join(ch for ch in out if ch.isdigit()) or None
        if self._id:
            _call(self._tool, f"/Scripting/Script{self._id}", "org.kde.kwin.Script.run")
        else:
            _call(self._tool, "/Scripting", "org.kde.kwin.Scripting.start")
        return (True, f"loaded (id={self._id})")

    def reapply(self) -> None:
        """Re-run the script so a freshly (re)mapped overlay is caught again."""
        if self._tool is None or self._id is None:
            return
        _call(self._tool, f"/Scripting/Script{self._id}", "org.kde.kwin.Script.run")
