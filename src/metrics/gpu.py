"""GPU metrics for NVIDIA (nvidia-smi), AMD/Intel (sysfs + hwmon) without external libs."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


_SYS = Path("/sys")

_NVIDIA_QUERY = (
    "name,utilization.gpu,utilization.memory,memory.used,memory.total,"
    "temperature.gpu,power.draw,power.limit,fan.speed,clocks.sm,clocks.mem"
)


def _read_text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _read_int(path, default=None):
    v = _read_text(path)
    try:
        return int(v)
    except Exception:
        return default


def _hwmon_dirs_for(device: Path):
    return sorted(device.glob("hwmon/hwmon*"))


def _hwmon_value(d: Path, pattern: str, scale: float = 1.0):
    for f in sorted(d.glob(pattern)):
        v = _read_int(f)
        if v is not None:
            return v / scale
    return None


def _nvidia_smi() -> dict | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, f"--query-gpu={_NVIDIA_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
    except Exception:
        return None

    fields = out.stdout.strip().splitlines()[0].split(", ")
    if len(fields) < 11:
        return None

    def num(s):
        try:
            return float(s)
        except Exception:
            return None

    name = fields[0]
    return {
        "gpu_vendor": "nvidia",
        "gpu_name": name,
        "gpu_usage": num(fields[1]),
        "gpu_mem_usage": num(fields[2]),
        "gpu_mem_used": round(num(fields[3]) / 1024.0, 2) if num(fields[3]) is not None else None,
        "gpu_mem_total": round(num(fields[4]) / 1024.0, 2) if num(fields[4]) is not None else None,
        "gpu_temp": num(fields[5]),
        "gpu_power": num(fields[6]),
        "gpu_power_limit": num(fields[7]),
        "gpu_fan": num(fields[8]),
        "gpu_freq": num(fields[9]),
        "gpu_mem_freq": num(fields[10]),
    }


def _drm_cards():
    base = _SYS / "class" / "drm"
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.name.startswith("card") and "-" not in p.name)


def _amdgpu(card: Path) -> dict:
    dev = card / "device"
    usage = _read_int(dev / "gpu_busy_percent")
    vram_used_b = _read_int(dev / "mem_info_vram_used")
    vram_total_b = _read_int(dev / "mem_info_vram_total")
    hwmons = _hwmon_dirs_for(dev)
    temp = power = fan = freq = None
    for h in hwmons:
        temp = temp if temp is not None else _hwmon_value(h, "temp1_input", 1000.0)
        power = power if power is not None else _hwmon_value(h, "power1_average", 1_000_000.0)
        fan = fan if fan is not None else _hwmon_value(h, "fan1_input")
        freq = freq if freq is not None else _hwmon_value(h, "freq1_input", 1_000_000.0)
    return {
        "gpu_vendor": "amd",
        "gpu_name": "AMD GPU",
        "gpu_usage": float(usage) if usage is not None else None,
        "gpu_mem_used": round(vram_used_b / 1024 ** 3, 2) if vram_used_b else None,
        "gpu_mem_total": round(vram_total_b / 1024 ** 3, 2) if vram_total_b else None,
        "gpu_mem_usage": round(vram_used_b / vram_total_b * 100.0, 1) if vram_used_b and vram_total_b else None,
        "gpu_temp": round(temp, 1) if temp is not None else None,
        "gpu_power": round(power, 1) if power is not None else None,
        "gpu_power_limit": None,
        "gpu_fan": fan,
        "gpu_freq": round(freq, 0) if freq is not None else None,
        "gpu_mem_freq": None,
    }


def _intel(card: Path) -> dict:
    dev = card / "device"
    hwmons = _hwmon_dirs_for(dev)
    temp = power = freq = None
    for h in hwmons:
        temp = temp if temp is not None else _hwmon_value(h, "temp1_input", 1000.0)
        power = power if power is not None else _hwmon_value(h, "power1_average", 1_000_000.0)
        freq = freq if freq is not None else _hwmon_value(h, "freq1_input", 1_000_000.0)
    return {
        "gpu_vendor": "intel",
        "gpu_name": "Intel GPU",
        "gpu_usage": None,
        "gpu_mem_used": None,
        "gpu_mem_total": None,
        "gpu_mem_usage": None,
        "gpu_temp": round(temp, 1) if temp is not None else None,
        "gpu_power": round(power, 1) if power is not None else None,
        "gpu_power_limit": None,
        "gpu_fan": None,
        "gpu_freq": round(freq, 0) if freq is not None else None,
        "gpu_mem_freq": None,
    }


EMPTY = {
    "gpu_vendor": None, "gpu_name": None, "gpu_usage": None,
    "gpu_mem_used": None, "gpu_mem_total": None, "gpu_mem_usage": None,
    "gpu_temp": None, "gpu_power": None, "gpu_power_limit": None,
    "gpu_fan": None, "gpu_freq": None, "gpu_mem_freq": None,
}


def collect() -> dict:
    data = _nvidia_smi()
    if data:
        return data
    for card in _drm_cards():
        dev = card / "device"
        driver = _read_text(dev / "uevent")
        hwmons = _hwmon_dirs_for(dev)
        names = " ".join(_read_text(h / "name").lower() for h in hwmons)
        blob = f"{driver} {names}"
        if "amdgpu" in blob or "amdgpu" in _read_text(card / "device" / "uevent").lower():
            return _amdgpu(card)
        if "i915" in blob or "xe" in blob or "intel" in blob:
            return _intel(card)
    return dict(EMPTY)


def collect_all() -> list[dict]:
    return [collect()]
