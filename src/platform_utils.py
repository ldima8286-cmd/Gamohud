"""Small cross-platform helpers shared across gamohud."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
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
    return shutil.which(name)


def in_flatpak() -> bool:
    """True when gamohud itself runs inside a Flatpak sandbox."""
    return bool(os.environ.get("FLATPAK_ID") or os.path.exists("/.flatpak-info"))


def host_command(args: list[str]) -> list[str]:
    """Prefix *args* so they run on the host when inside a Flatpak.

    Tools such as MangoHud live on the host, outside the sandbox.  Outside a
    Flatpak this is a no-op, so callers can use it unconditionally.
    """
    if IS_LINUX and in_flatpak() and shutil.which("flatpak-spawn"):
        return ["flatpak-spawn", "--host", *args]
    return list(args)


_HOST_WHICH_CACHE: dict[str, str | None] = {}


def host_which(name: str) -> str | None:
    """Locate an executable on the host, even when running in a sandbox."""
    if name in _HOST_WHICH_CACHE:
        return _HOST_WHICH_CACHE[name]
    found = shutil.which(name)
    if found is None and IS_LINUX and in_flatpak() and shutil.which("flatpak-spawn"):
        try:
            r = subprocess.run(
                ["flatpak-spawn", "--host", "sh", "-c", f"command -v {shlex.quote(name)}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                found = r.stdout.strip().splitlines()[0]
        except Exception:
            found = None
    _HOST_WHICH_CACHE[name] = found
    return found


def host_run(args: list[str], timeout: float = 5.0, **kwargs) -> subprocess.CompletedProcess:
    """Run a host command with a short timeout (used for MangoHud control)."""
    return subprocess.run(
        host_command(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        **kwargs,
    )


def default_mangohud_log_dir() -> Path:
    """Host-visible folder for MangoHud CSV logs.

    ``XDG_DATA_HOME`` points inside the Flatpak private data directory, which
    host games cannot write to.  ``$HOME/.local/share`` is shared and also the
    conventional location outside Flatpak.
    """
    if IS_WINDOWS:
        return config_dir("gamohud") / "mangohud"
    return Path.home() / ".local" / "share" / "gamohud" / "mangohud"


def open_uri_command(uri: str) -> list[str]:
    """Command list that opens a URI with the default handler on this OS."""
    if IS_WINDOWS:
        return ["cmd", "/c", "start", "", uri]
    if IS_MACOS:
        return ["open", uri]
    return ["xdg-open", uri]
