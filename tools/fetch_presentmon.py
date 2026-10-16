"""Download the latest PresentMon console executable into tools/presentmon/.

PresentMon is MIT-licensed (c) Intel Corporation:
https://github.com/GameTechDev/PresentMon

Usage:
    python tools/fetch_presentmon.py [--version v2.3.1] [--arch x64]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_API = "https://api.github.com/repos/GameTechDev/PresentMon/releases"
_DEST = Path(__file__).resolve().parent / "presentmon"


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gamohud-presentmon-fetch"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _pick_asset(release: dict, arch: str) -> dict | None:
    suffix = f"-{arch}.exe"
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("PresentMon-") and name.endswith(suffix):
            return asset
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="latest", help="release tag, or 'latest'")
    parser.add_argument("--arch", default="x64", choices=["x64", "x86", "arm64"])
    args = parser.parse_args(argv)

    url = f"{_API}/latest" if args.version == "latest" else f"{_API}/tags/{args.version}"
    try:
        release = json.loads(_fetch(url))
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot query GitHub releases: {exc}", file=sys.stderr)
        return 1

    asset = _pick_asset(release, args.arch)
    if asset is None:
        print(f"error: no PresentMon-*-{args.arch}.exe asset in release", file=sys.stderr)
        return 1

    _DEST.mkdir(parents=True, exist_ok=True)
    target = _DEST / "PresentMon.exe"
    print(f"Downloading {asset['name']} -> {target} ...")
    try:
        data = _fetch(asset["browser_download_url"])
    except Exception as exc:  # noqa: BLE001
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1
    target.write_bytes(data)
    print(f"Saved {target} ({len(data)} bytes)")
    print("PresentMon is MIT-licensed (c) Intel Corporation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
