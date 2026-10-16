"""Download the latest PresentMon console executable into tools/presentmon/.

PresentMon is MIT-licensed (c) Intel Corporation:
https://github.com/GameTechDev/PresentMon

Usage:
    python tools/fetch_presentmon.py [--version v2.3.1] [--arch x64]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fps.presentmon_common import download_presentmon  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="latest", help="release tag, or 'latest'")
    parser.add_argument("--arch", default="x64", choices=["x64", "x86", "arm64"])
    args = parser.parse_args(argv)

    try:
        path = download_presentmon(args.version, args.arch, log=lambda m: print(m, flush=True))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("PresentMon is MIT-licensed (c) Intel Corporation.")
    print(f"gamohud will use: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
