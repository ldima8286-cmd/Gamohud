"""Best-effort "always on top" + position restore for KDE/KWin on Wayland.

Qt's ``WindowStaysOnTopHint`` is honoured on X11 and Windows but ignored by
KWin on Wayland, and a normal Wayland toplevel cannot position itself
(``move()`` is a no-op). So the only way to keep the overlay above everything
*and* restore its saved position is to ask KWin itself: we load a small KWin
script (over D-Bus) that

  * sets ``keepAbove`` / ``skipTaskbar`` on our overlay,
  * moves it to the saved global position (KWin 6 ``frameGeometry``), and
  * reports every geometry change back to the app over D-Bus, so a Wayland
    drag can be persisted accurately.

The overlay is identified by a unique window title generated for each app
session.  A script left loaded by an earlier run therefore cannot match (and
move) a new overlay.  The position is baked into the generated script when it
is loaded, so no file reads are needed inside KWin.

Everything here is best-effort: if the session bus / KWin is not reachable
(e.g. on X11/Windows) every call degrades to a no-op and the caller can report
it.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from src.platform_utils import (
    IS_LINUX,
    OVERLAY_DBUS_INTERFACE,
    OVERLAY_DBUS_PATH,
    config_dir,
)

_SCRIPT = r'''
function isOverlay(w) {
    try {
        var t = "" + (w && w.caption ? w.caption : "");
        return t.indexOf("%TITLE%") === 0;
    } catch (e) { return false; }
}
%REPORT_FUNCTION%
function apply(w) {
    try {
        if (!w || !isOverlay(w)) return;
        try { w.keepAbove = true; } catch (e) {}
        try { w.skipTaskbar = true; } catch (e) {}
        try { w.skipSwitcher = true; } catch (e) {}
%REPORT_HOOK%
%RESTORE%
%REPORT_CALL%
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
                if (w.x !== %X% || w.y !== %Y%) {
                    var geo = { x: %X%, y: %Y%, width: w.width, height: w.height };
                    try { w.frameGeometry = geo; } catch (e1) {
                        try { w.geometry = geo; } catch (e2) {}
                    }
                }
            }
        } catch (e) {}"""

_REPORT_FUNCTION = """function reportGeometry(w) {
    try {
        if (!w || !isOverlay(w)) return;
        callDBus("%SERVICE%", "%PATH%", "%INTERFACE%", "Geometry",
                 "%TITLE%", Math.round(w.x), Math.round(w.y),
                 Math.round(w.width), Math.round(w.height));
    } catch (e) {}
}"""

_REPORT_HOOK = """        try {
            if (!w._gamohudGeometryHooked) {
                w._gamohudGeometryHooked = true;
                if (w.frameGeometryChanged) {
                    w.frameGeometryChanged.connect(function () { reportGeometry(w); });
                } else if (w.geometryChanged) {
                    w.geometryChanged.connect(function () { reportGeometry(w); });
                }
            }
        } catch (e) {}"""

_REPORT_CALL = "        reportGeometry(w);"


def _qdbus() -> list[str] | None:
    # Inside a Flatpak sandbox /run/host/usr/bin/qdbus often cannot load its
    # Qt libraries.  flatpak-spawn executes the host's qdbus with the host's
    # session bus, which is what KWin needs.
    if shutil.which("flatpak-spawn") and (
        os.environ.get("FLATPAK_ID") or os.path.exists("/.flatpak-info")
    ):
        return ["flatpak-spawn", "--host", "qdbus"]
    for name in ("qdbus6", "qdbus", "qdbus-qt6"):
        p = shutil.which(name)
        if p:
            return [p]
    for p in (
        "/usr/bin/qdbus6",
        "/usr/bin/qdbus",
        "/run/host/usr/bin/qdbus6",
        "/run/host/usr/bin/qdbus",
    ):
        if os.path.exists(p):
            return [p]
    return None


def _call(tool: list[str], *args: str) -> str | None:
    try:
        r = subprocess.run(
            [*tool, "org.kde.KWin", *args],
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
        self._tool: list[str] | None = _qdbus() if IS_LINUX else None
        self._provider = None
        self._title: str | None = None
        self._geometry_service: str | None = None
        self._script_path = config_dir("gamohud") / "keep_above.js"

    @property
    def available(self) -> bool:
        return self._tool is not None

    def set_window_title(self, title: str) -> None:
        """Tie the generated KWin script to this specific overlay title."""
        title = str(title or "")
        if not title or title == self._title:
            return
        self._title = title
        safe = "".join(
            ch if ch.isalnum() or ch in "-_." else "_" for ch in title
        )[:80]
        self._script_path = config_dir("gamohud") / f"keep_above-{safe}.js"

    def set_position_provider(self, fn) -> None:
        """``fn()`` -> (x, y) global ints for the overlay, or None."""
        self._provider = fn

    def set_geometry_bus(self, service: str | None) -> None:
        """Where the KWin script should report the overlay geometry."""
        self._geometry_service = service or None

    def _script_text(self) -> str:
        if not self._title:
            return ""
        restore = ""
        if self._provider is not None:
            xy = self._provider()
            if xy:
                x, y = int(xy[0]), int(xy[1])
                restore = _RESTORE_BLOCK.replace("%X%", str(x)).replace("%Y%", str(y))

        title = self._title.replace("\\", "\\\\").replace('"', '\\"')
        report_function = ""
        report_hook = ""
        report_call = ""
        if self._geometry_service:
            report_function = (
                _REPORT_FUNCTION.replace("%SERVICE%", self._geometry_service)
                .replace("%PATH%", OVERLAY_DBUS_PATH)
                .replace("%INTERFACE%", OVERLAY_DBUS_INTERFACE)
                .replace("%TITLE%", title)
            )
            report_hook = _REPORT_HOOK
            report_call = _REPORT_CALL

        return (
            _SCRIPT.replace("%TITLE%", title)
            .replace("%REPORT_FUNCTION%", report_function)
            .replace("%REPORT_HOOK%", report_hook)
            .replace("%REPORT_CALL%", report_call)
            .replace("%RESTORE%", restore)
        )

    def _write(self) -> str:
        path = self._script_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._script_text(), encoding="utf-8")
        return str(path)

    def enable(self) -> tuple[bool, str]:
        """Write, load and run the KWin script. Returns (ok, message)."""
        if not IS_LINUX:
            return (False, "not Linux")
        if self._tool is None:
            return (False, "qdbus not found")
        if not self._title:
            return (False, "overlay title not set")
        try:
            path = self._write()
        except Exception as exc:  # pragma: no cover
            return (False, f"could not write script: {exc}")

        # Remove the persistent script used by older versions.  It matched every
        # window whose title started with "gamohud-overlay" and could keep
        # moving new overlays to stale coordinates.
        legacy = config_dir("gamohud") / "keep_above.js"
        if str(legacy) != path:
            _call(
                self._tool,
                "/Scripting",
                "org.kde.kwin.Scripting.unloadScript",
                str(legacy),
            )
        _call(
            self._tool,
            "/Scripting",
            "org.kde.kwin.Scripting.unloadScript",
            path,
        )
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

        Only called when the overlay is started or previewed, not on every
        lock/unlock: re-applying a stale position could move a window the user
        has just dragged.
        """
        if self._tool is None or self._id is None or not self._title:
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
