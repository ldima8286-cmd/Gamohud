"""Match running processes to application profiles (for overlay auto-switch)."""
from __future__ import annotations

import fnmatch
import os
import subprocess

from .model import AppProfile


def match_name(name: str, patterns: list[str]) -> bool:
    if not name:
        return False
    low = name.lower()
    for pat in patterns:
        if not pat:
            continue
        if fnmatch.fnmatch(low, pat.lower()):
            return True
    return False


def find_profile(profiles: list[AppProfile], process_names: list[str]) -> AppProfile | None:
    """Return the first profile whose patterns match any running process name."""
    best = None
    best_specificity = -1
    for profile in profiles:
        if not profile.match:
            continue
        for proc in process_names:
            if match_name(proc, profile.match):
                specificity = max(len(p) for p in profile.match)
                if specificity > best_specificity:
                    best = profile
                    best_specificity = specificity
                break
    return best


def running_process_names(limit: int = 400) -> list[str]:
    try:
        import psutil
    except Exception:
        return []
    names = []
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name")
            if name:
                names.append(name)
        except Exception:
            continue
        if len(names) >= limit:
            break
    return names


def _run(cmd: list[str], timeout: float = 1.5) -> str:
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
        return (out.stdout or "").strip()
    except Exception:
        return ""


def _kwin_caption() -> str | None:
    """Active window caption via KWin's D-Bus interface (KDE Plasma)."""
    uuid = ""
    for tool in ("gdbus", "qdbus6", "qdbus"):
        if tool == "gdbus":
            cmd = [tool, "call", "--session", "--dest", "org.kde.KWin",
                   "--object-path", "/KWin", "--method", "org.kde.KWin.activeWindow"]
        else:
            cmd = [tool, "org.kde.KWin", "/KWin", "org.kde.KWin.activeWindow"]
        uuid = _run(cmd, timeout=1.0)
        if uuid:
            break
    if not uuid:
        return None
    uuid = uuid.strip().strip("'\"() ")
    if not uuid:
        return None
    for tool in ("gdbus", "qdbus6", "qdbus"):
        if tool == "gdbus":
            cmd = [tool, "call", "--session", "--dest", "org.kde.KWin",
                   "--object-path", "/KWin", "--method", "org.kde.KWin.getWindowInfo", uuid]
        else:
            cmd = [tool, "org.kde.KWin", "/KWin", "org.kde.KWin.getWindowInfo", uuid]
        info = _run(cmd, timeout=1.0)
        if not info:
            continue
        for line in info.splitlines():
            line = line.strip().strip("',() ")
            for prefix in ("caption:", "resourceClass:"):
                if line.startswith(prefix):
                    value = line.split(":", 1)[1].strip().strip("<>'\"")
                    if value:
                        return value
    return None


def active_window_title() -> str | None:
    """Best-effort title of the currently focused window, cross-desktop."""
    caption = _kwin_caption()
    if caption:
        return caption
    for cmd in (
        ["xdotool", "getactivewindow", "getwindowname"],
        ["xdotool", "getactivewindow", "getwindowclassname"],
        ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
    ):
        value = _run(cmd)
        if value:
            return value
    tree = _run(["swaymsg", "-t", "get_tree"])
    if tree:
        import json
        try:
            data = json.loads(tree)
            nodes = [data]
            while nodes:
                node = nodes.pop()
                if node.get("focused") and node.get("name"):
                    return node["name"]
                nodes.extend(node.get("nodes", []) + node.get("floating_nodes", []))
        except Exception:
            pass
    return None


def find_profile_by_window(profiles: list[AppProfile], window_title: str | None) -> AppProfile | None:
    """Return the first profile whose patterns match the active window title."""
    if not window_title:
        return None
    best = None
    best_specificity = -1
    for profile in profiles:
        if not profile.match:
            continue
        if match_name(window_title, profile.match):
            specificity = max(len(p) for p in profile.match)
            if specificity > best_specificity:
                best = profile
                best_specificity = specificity
    return best

