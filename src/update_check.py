"""Check GitHub Releases for a newer gamohud version.

The GUI calls :func:`latest_release` on a background thread and, if the remote
tag is newer than the running version, offers the user a link to it.
"""
from __future__ import annotations

import json
import urllib.request

REPO = "ldima8286-cmd/Gamohud"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 6.0


def parse_version(text: str) -> tuple[int, ...]:
    """Turn a tag like ``v0.2.0`` into a comparable tuple ``(0, 2, 0)``."""
    if not text:
        return ()
    cleaned = text.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in cleaned.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits == "":
            break
        parts.append(int(digits))
    return tuple(parts)


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def latest_release(include_prerelease: bool = False) -> dict | None:
    """Fetch the newest release metadata, or None on any failure."""
    url = API if not include_prerelease else f"https://api.github.com/repos/{REPO}/releases"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gamohud"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None
    if isinstance(data, list):
        data = next(iter(data), None)
    if not isinstance(data, dict):
        return None
    return {
        "tag": data.get("tag_name", ""),
        "name": data.get("name") or data.get("tag_name", ""),
        "url": data.get("html_url") or RELEASES_PAGE,
        "notes": data.get("body", ""),
    }
