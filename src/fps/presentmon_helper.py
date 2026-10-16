"""Standalone helper that runs PresentMon and writes ``gamohud-fps.json``.

Invoked as a detached process by the ``presentmon`` FPS backend so the capture
keeps running even when ``gamohud-run`` exec()s the game. Dependency-free
except for :mod:`src.fps.presentmon_common`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.fps.presentmon_common import (  # noqa: E402
    FrameTracker,
    header_index,
    looks_like_header,
    parse_ms,
    parse_pid,
    pid_index,
)


def _write_json(path: Path, data: dict | None) -> None:
    if data is None:
        try:
            path.unlink()
        except OSError:
            pass
        return
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def run(presentmon: str, out_path: Path, target: str | None, interval: float, admin: bool) -> int:
    cmd = [presentmon, "--output_stdout", "--no_console_stats"]
    if target:
        cmd += ["--process_name", target, "--terminate_on_proc_exit"]
    if admin:
        cmd.append("--restart_as_admin")

    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        sys.stderr.write(f"gamohud-presentmon: cannot start {presentmon}: {exc}\n")
        return 1

    stderr_lines: list[str] = []

    def _drain_stderr() -> None:
        try:
            for line in proc.stderr:  # type: ignore[union-attr]
                stderr_lines.append(line)
        except Exception:
            pass

    err_thread = threading.Thread(target=_drain_stderr, daemon=True)
    err_thread.start()

    tracker = FrameTracker(window=30)
    ms_col: int | None = None
    pid_col: int | None = None
    last_write = 0.0
    wrote = False

    try:
        reader = csv.reader(proc.stdout)  # type: ignore[arg-type]
        for row in reader:
            if not row:
                continue
            if ms_col is None:
                if looks_like_header(row):
                    ms_col = header_index(row)
                    pid_col = pid_index(row)
                continue
            if ms_col is None or pid_col is None:
                continue
            if len(row) <= max(ms_col, pid_col):
                continue
            tracker.feed(parse_pid(row[pid_col]), parse_ms(row[ms_col]))
            now = time.monotonic()
            if now - last_write >= interval:
                stats = tracker.stats()
                _write_json(out_path, stats)
                wrote = wrote or stats is not None
                last_write = now
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        err_thread.join(timeout=1.0)

    if not wrote and stderr_lines:
        sys.stderr.write("".join(stderr_lines[-20:]))
    _write_json(out_path, None)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gamohud-presentmon")
    parser.add_argument("--exe", required=True, help="path to PresentMon executable")
    parser.add_argument("--out", required=True, help="path to write gamohud-fps.json")
    parser.add_argument("--target", default=None, help="target process exe name")
    parser.add_argument("--interval", type=float, default=0.4, help="JSON refresh interval")
    parser.add_argument("--admin", action="store_true", help="let PresentMon request elevation")
    args = parser.parse_args(argv)
    return run(args.exe, Path(args.out), args.target, args.interval, args.admin)


if __name__ == "__main__":
    raise SystemExit(main())
