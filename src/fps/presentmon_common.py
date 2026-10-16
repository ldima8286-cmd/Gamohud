"""Shared PresentMon helpers: binary discovery, CSV parsing and aggregation.

Dependency-free so it can be imported both by the GUI/backend and by the
standalone ``presentmon_helper`` process (including under PyInstaller).
"""
from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict, deque
from pathlib import Path

FPS_FILENAME = "gamohud-fps.json"

# Names that are launchers/prefixes rather than the actual game executable.
_LAUNCHER_NAMES = {
    "steam",
    "steam.exe",
    "steamwebhelper.exe",
    "lutris",
    "heroic",
    "heroic.exe",
    "bottles",
    "bottles-cli",
    "epic",
    "epicgameslauncher.exe",
    "galaxyclient.exe",
    "gog",
    "wine",
    "wine64",
    "gamemoderun",
    "cmd",
    "cmd.exe",
    "flatpak",
}


def find_presentmon() -> Path | None:
    """Locate a PresentMon executable, or return None."""
    env = os.environ.get("GAMOHUD_PRESENTMON")
    if env:
        p = Path(env)
        if p.is_file():
            return p
        if p.is_dir():
            for name in ("PresentMon.exe", "PresentMon"):
                if (p / name).is_file():
                    return p / name

    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if base:
            roots.append(Path(base))
        roots.append(Path(sys.executable).resolve().parent)
    here = Path(__file__).resolve()
    # src/fps/presentmon_common.py -> repository root
    if len(here.parents) >= 3:
        roots.append(here.parents[2])

    candidates: list[Path] = []
    for r in roots:
        candidates += [
            r / "PresentMon.exe",
            r / "PresentMon",
            r / "tools" / "presentmon" / "PresentMon.exe",
            r / "tools" / "PresentMon.exe",
            r / "vendor" / "presentmon" / "PresentMon.exe",
        ]
    try:
        from ..platform_utils import config_dir

        candidates.append(config_dir("gamohud") / "presentmon" / "PresentMon.exe")
    except Exception:
        pass

    for c in candidates:
        if c.is_file():
            return c

    for name in ("PresentMon.exe", "PresentMon"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def exe_basename(value: str | None) -> str | None:
    """Return the executable file name from a command line / path string."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    token = text.split()[0]
    name = os.path.basename(token.replace("\\", "/"))
    return name or None


def target_process_name(command, profile) -> str | None:
    """Best-effort exe name to hand to PresentMon's ``--process_name``.

    Falls back to None (capture all processes) when the command is a launcher
    (Steam, Lutris, ...) whose real game process we cannot name up front. The
    ``GAMOHUD_PROCESS_NAME`` environment variable overrides everything.
    """
    env = os.environ.get("GAMOHUD_PROCESS_NAME")
    if env:
        return env

    candidates: list[str | None] = []
    if profile is not None:
        candidates.append(getattr(profile, "executable", None))
    if command:
        candidates.extend(reversed([str(c) for c in command]))

    for cand in candidates:
        name = exe_basename(cand)
        if not name or not name.lower().endswith(".exe"):
            continue
        if name.lower() in _LAUNCHER_NAMES:
            continue
        return name
    return None


_HEADER_MARKERS = ("MsBetweenPresents", "ProcessID", "CPUStartTime", "Application")


def looks_like_header(columns) -> bool:
    return any(m in columns for m in _HEADER_MARKERS)


def _column_index(header, name: str) -> int | None:
    for i, col in enumerate(header):
        if col.strip().lower() == name.lower():
            return i
    return None


def header_index(header) -> int | None:
    return _column_index(header, "MsBetweenPresents")


def pid_index(header) -> int | None:
    return _column_index(header, "ProcessID")


def parse_pid(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_ms(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "N/A", "NAN"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


class FrameTracker:
    """Aggregates per-process frame intervals from PresentMon CSV rows."""

    def __init__(self, window: int = 30):
        self.window = max(2, int(window))
        self._samples: dict[int, deque] = defaultdict(lambda: deque(maxlen=self.window))
        self._order: dict[int, int] = defaultdict(int)
        self._seq = 0

    def feed(self, pid: int, ms_between_presents: float | None) -> None:
        if pid is None or ms_between_presents is None or ms_between_presents <= 0:
            return
        self._samples[pid].append(ms_between_presents)
        self._seq += 1
        self._order[pid] = self._seq

    def active_pid(self) -> int | None:
        best = None
        best_order = -1
        for pid, samples in self._samples.items():
            if len(samples) < 2:
                continue
            if self._order[pid] > best_order:
                best = pid
                best_order = self._order[pid]
        return best

    def stats(self) -> dict | None:
        pid = self.active_pid()
        if pid is None:
            return None
        samples = list(self._samples[pid])
        mean_ms = sum(samples) / len(samples)
        if mean_ms <= 0:
            return None
        return {
            "fps": round(1000.0 / mean_ms, 1),
            "frametime": round(mean_ms, 2),
        }


def _selftest() -> None:
    header = [
        "Application",
        "ProcessID",
        "SwapChainAddress",
        "MsBetweenPresents",
        "MsBetweenDisplayChange",
    ]
    assert looks_like_header(header)
    assert header_index(header) == 3
    assert pid_index(header) == 1

    tracker = FrameTracker(window=10)
    for ms in (10.0, 11.0, 9.0, 10.0, 12.0, 10.0, 11.0, 10.0):
        tracker.feed(1234, ms)
    tracker.feed(999, 40.0)
    tracker.feed(999, 40.0)
    stats = tracker.stats()
    assert tracker.active_pid() == 999, tracker.active_pid()
    assert abs(stats["fps"] - 25.0) < 0.5, stats
    assert abs(stats["frametime"] - 40.0) < 0.1, stats

    # A single new frame must not immediately steal the "active" slot.
    tracker.feed(1234, 10.0)
    assert tracker.active_pid() == 1234, tracker.active_pid()

    assert parse_ms("NA") is None
    assert parse_ms("6.9") == 6.9
    assert parse_pid("12") == 12
    assert parse_pid("x") is None

    assert exe_basename("C:" + "\\" + "Games" + "\\" + "foo.exe --map x") == "foo.exe"
    assert exe_basename("steam steam://rungameid/1") == "steam"
    assert exe_basename(None) is None

    class _P:
        executable = "steam steam://rungameid/1"

    assert target_process_name(["steam", "steam://rungameid/1"], _P()) is None
    assert target_process_name(["C:\\Games\\game.exe"], None) == "game.exe"

    print("presentmon_common selftest OK")


if __name__ == "__main__":
    _selftest()
