"""Match running processes to application profiles (for overlay auto-switch)."""
from __future__ import annotations

import fnmatch

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
