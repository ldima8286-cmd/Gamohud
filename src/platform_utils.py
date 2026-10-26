"""Small cross-platform helpers shared across gamohud."""
from __future__ import annotations

import os
import shlex
import sys
import tempfile
from pathlib import Path

IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"

# Avoid flashing a console window for helper processes on Windows.
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


def config_dir(app: str = "gamohud") -> Path:
    """Per-user configuration directory, following each OS convention."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif IS_MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / app


def runtime_dir() -> Path:
    """A writable per-user runtime/temp directory."""
    if not IS_WINDOWS:
        xdg = os.environ.get("XDG_RUNTIME_DIR")
        if xdg:
            return Path(xdg)
    return Path(tempfile.gettempdir())


def app_dbus_name(suffix: str = "Gamohud") -> str:
    """A session-bus name the app is allowed to own.

    Flatpak only permits names below the app ID; outside a sandbox a name
    below org.gamohud is used instead.
    """
    app_id = os.environ.get("FLATPAK_ID")
    if app_id:
        return f"{app_id}.{suffix}"
    return f"org.gamohud.{suffix}"


OVERLAY_DBUS_PATH = "/Overlay"
OVERLAY_DBUS_INTERFACE = "org.gamohud.Overlay"


def split_args(text: str) -> list[str]:
    """Split a command/argument string respecting the host shell quoting rules."""
    if not text:
        return []
    if IS_WINDOWS:
        parts = shlex.split(text, posix=False)
        cleaned = []
        for p in parts:
            if len(p) >= 2 and p[0] == p[-1] and p[0] in ("'", '"'):
                p = p[1:-1]
            cleaned.append(p)
        return cleaned
    return shlex.split(text)


def which(name: str) -> str | None:
    import shutil
    return shutil.which(name)


def open_uri_command(uri: str) -> list[str]:
    """Command list that opens a URI with the default handler on this OS."""
    if IS_WINDOWS:
        return ["cmd", "/c", "start", "", uri]
    if IS_MACOS:
        return ["open", uri]
    return ["xdg-open", uri]
