import os
from pathlib import Path


_last_size = 0
_last_fps = None


def _parse_last_line(line: str):
    parts = [p.strip() for p in line.split(",")]
    for p in parts:
        try:
            v = float(p)
            if 0 <= v < 2000:
                return v
        except Exception:
            continue
    if parts:
        try:
            return float(parts[0])
        except Exception:
            return None
    return None


def read_log_fps(log_path):
    global _last_size, _last_fps
    p = Path(log_path)
    if not p.exists():
        return None
    try:
        size = p.stat().st_size
        if size == _last_size and _last_fps is not None:
            return _last_fps
        with p.open("r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        _last_size = size
        lines = [ln for ln in data.splitlines() if ln.strip()]
        if not lines:
            return None
        header = lines[0].lower()
        rows = lines[1:] if ("fps" in header or "frametime" in header) else lines
        if not rows:
            return None
        fps_idx = 0
        if "fps" in header:
            cols = [c.strip() for c in lines[0].split(",")]
            for i, c in enumerate(cols):
                if c == "fps":
                    fps_idx = i
                    break
        last = rows[-1]
        cols = [c.strip() for c in last.split(",")]
        if fps_idx < len(cols):
            try:
                _last_fps = float(cols[fps_idx])
                return _last_fps
            except Exception:
                pass
        _last_fps = _parse_last_line(last)
        return _last_fps
    except Exception:
        return None


def get_fps(settings):
    try:
        if getattr(settings, "mangohud_logging", False):
            v = read_log_fps(settings.fps_log)
            if v is not None:
                return round(v, 1)
    except Exception:
        pass
    return None
