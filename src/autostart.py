"""Enable/disable launching gamohud automatically when the user logs in.

Each OS has its own mechanism:

* Linux: an XDG autostart ``.desktop`` file in ``~/.config/autostart``.
* Windows: a value under ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``.
* macOS: a ``LaunchAgent`` plist in ``~/Library/LaunchAgents``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .platform_utils import IS_MACOS, IS_WINDOWS, config_dir

APP_NAME = "gamohud"
LINUX_AUTOSTART = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "autostart"
MACOS_AGENTS = Path.home() / "Library" / "LaunchAgents"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> list[str]:
    """Best-effort command that starts the GUI, suitable for autostart entries."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    app_py = Path(__file__).resolve().parent / "app.py"
    return [sys.executable, str(app_py)]


def _linux_entry_path() -> Path:
    return LINUX_AUTOSTART / f"{APP_NAME}.desktop"


def _macos_entry_path() -> Path:
    return MACOS_AGENTS / f"org.{APP_NAME}.plist"


def is_enabled() -> bool:
    if IS_WINDOWS:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except Exception:
            return False
    if IS_MACOS:
        return _macos_entry_path().exists()
    return _linux_entry_path().exists()


def _quote(cmd: list[str]) -> str:
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


def enable() -> Path | str:
    """Create the autostart entry; returns the created path (or registry value)."""
    if IS_WINDOWS:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _quote(launch_command()))
        return WINDOWS_RUN_KEY
    if IS_MACOS:
        path = _macos_entry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        args = "".join(f"<string>{c}</string>" for c in launch_command())
        path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key><string>org.{APP_NAME}</string>\n"
            "  <key>ProgramArguments</key>\n"
            f"  <array>{args}</array>\n"
            "  <key>RunAtLoad</key><true/>\n"
            "</dict>\n</plist>\n",
            encoding="utf-8",
        )
        return path
    path = _linux_entry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Overlay performance monitor\n"
        f"Exec={_quote(launch_command())}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n",
        encoding="utf-8",
    )
    return path


def disable() -> bool:
    """Remove the autostart entry; returns True if something was removed."""
    if IS_WINDOWS:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, APP_NAME)
            return True
        except Exception:
            return False
    if IS_MACOS:
        path = _macos_entry_path()
    else:
        path = _linux_entry_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
