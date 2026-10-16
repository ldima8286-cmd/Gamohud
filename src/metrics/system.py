"""System-wide metrics collected from /proc, /sys and psutil (no external tools)."""
from __future__ import annotations

import os
import time
from pathlib import Path


_SYS = Path("/sys")
_PREV_NET = {}
_PREV_DISK = {}
_PREV_TIME = {}


def _read_text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _read_int(path, default=None):
    v = _read_text(path)
    if v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default


def _hwmon_dirs() -> list[Path]:
    base = _SYS / "class" / "hwmon"
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir())


def _hwmon_name(d: Path) -> str:
    return _read_text(d / "name").lower()


def _hwmon_value(d: Path, pattern: str) -> float | None:
    for f in sorted(d.glob(pattern)):
        v = _read_int(f)
        if v is not None:
            return v
    return None


CPU_TEMP_NAMES = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz", "cpu")
GPU_TEMP_NAMES = ("amdgpu", "nouveau", "i915", "xe", "radeon")


def cpu_temperature() -> float | None:
    for d in _hwmon_dirs():
        name = _hwmon_name(d)
        if name in CPU_TEMP_NAMES:
            v = _hwmon_value(d, "temp*_input")
            if v is not None:
                return round(v / 1000.0, 1)
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        for key in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"):
            if key in temps and temps[key]:
                return float(temps[key][0].current)
    except Exception:
        pass
    return None


def cpu_fan() -> float | None:
    for d in _hwmon_dirs():
        name = _hwmon_name(d)
        if name in CPU_TEMP_NAMES:
            v = _hwmon_value(d, "fan*_input")
            if v is not None:
                return float(v)
    return None


def cpu_power() -> float | None:
    base = _SYS / "class" / "powercap"
    if not base.exists():
        return None
    total = 0.0
    found = False
    for dom in base.glob("*intel-rapl*"):
        uj = _read_int(dom / "energy_uj")
        max_range = _read_int(dom / "max_energy_range_uj")
        if uj is None:
            continue
        prev = _PREV_TIME.get(("rapl", str(dom)))
        now = time.monotonic()
        if prev is not None:
            p_uj, p_t = prev
            delta = uj - p_uj
            if delta < 0 and max_range:
                delta += max_range
            dt = now - p_t
            if dt > 0:
                total += (delta / 1_000_000.0) / dt
                found = True
        _PREV_TIME[("rapl", str(dom))] = (uj, now)
    return round(total, 1) if found else None


def cpu_frequency() -> float | None:
    base = _SYS / "devices" / "system" / "cpu"
    freqs = []
    if base.exists():
        for c in base.glob("cpu[0-9]*"):
            v = _read_int(c / "cpufreq" / "scaling_cur_freq")
            if v:
                freqs.append(v)
    if not freqs:
        return None
    return round(sum(freqs) / len(freqs) / 1000.0, 0)


def cpu_stats():
    import psutil
    freq = cpu_frequency()
    if freq is None:
        try:
            f = psutil.cpu_freq()
            freq = round(f.current, 0) if f else None
        except Exception:
            freq = None
    return {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "cpu_freq": freq,
        "cpu_temp": cpu_temperature(),
        "cpu_power": cpu_power(),
        "cpu_fan": cpu_fan(),
        "load1": _loadavg()[0],
    }


def _loadavg():
    try:
        parts = _read_text("/proc/loadavg").split()
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception:
        return (None, None, None)


def memory_stats():
    import psutil
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "ram_used": round(mem.used / 1024 ** 3, 2),
        "ram_total": round(mem.total / 1024 ** 3, 2),
        "ram_percent": mem.percent,
        "swap_percent": swap.percent,
    }


def net_stats():
    import psutil
    now = time.monotonic()
    counters = psutil.net_io_counters()
    sent, recv = counters.bytes_sent, counters.bytes_recv
    prev = _PREV_NET.get("all")
    up = down = None
    if prev is not None:
        p_sent, p_recv, p_t = prev
        dt = now - p_t
        if dt > 0:
            up = round((sent - p_sent) / dt / 1024.0, 1)
            down = round((recv - p_recv) / dt / 1024.0, 1)
    _PREV_NET["all"] = (sent, recv, now)
    return {"net_up": up, "net_down": down}


def disk_stats():
    import psutil
    now = time.monotonic()
    io = psutil.disk_io_counters()
    if io is None:
        return {"disk_read": None, "disk_write": None}
    prev = _PREV_DISK.get("all")
    read = write = None
    if prev is not None:
        p_r, p_w, p_t = prev
        dt = now - p_t
        if dt > 0:
            read = round((io.read_bytes - p_r) / dt / 1024 ** 2, 1)
            write = round((io.write_bytes - p_w) / dt / 1024 ** 2, 1)
    _PREV_DISK["all"] = (io.read_bytes, io.write_bytes, now)
    return {"disk_read": read, "disk_write": write}


def uptime():
    try:
        return int(float(_read_text("/proc/uptime").split()[0]))
    except Exception:
        return None


def collect():
    return {
        **cpu_stats(),
        **memory_stats(),
        **net_stats(),
        **disk_stats(),
        "uptime": uptime(),
    }
