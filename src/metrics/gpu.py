"""GPU metrics, cross-platform.

NVIDIA is queried through `nvidia-smi` (works on Windows and Linux).
AMD/Intel on Linux is read from sysfs/hwmon. On Windows a best-effort path reads
LibreHardwareMonitor's WMI namespace when it is running.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.platform_utils import CREATE_NO_WINDOW


IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = os.name == "nt"

_SYS = Path("/sys")

_NVIDIA_QUERY = (
    "name,utilization.gpu,utilization.memory,memory.used,memory.total,"
    "temperature.gpu,power.draw,power.limit,fan.speed,clocks.sm,clocks.mem"
)

EMPTY = {
    "gpu_vendor": None, "gpu_name": None, "gpu_usage": None,
    "gpu_mem_used": None, "gpu_mem_total": None, "gpu_mem_usage": None,
    "gpu_temp": None, "gpu_power": None, "gpu_power_limit": None,
    "gpu_fan": None, "gpu_freq": None, "gpu_mem_freq": None,
}

_LAST_VENDOR = {"value": None}


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


# --------------------------------------------------------------- NVIDIA
def nvidia_smi() -> dict | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, f"--query-gpu={_NVIDIA_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
            creationflags=CREATE_NO_WINDOW,
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

    _LAST_VENDOR["value"] = "nvidia"
    return {
        "gpu_vendor": "nvidia",
        "gpu_name": fields[0],
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


# ----------------------------------------------------------------- Linux
def _hwmon_dirs_for(device: Path):
    return sorted(device.glob("hwmon/hwmon*"))


def _hwmon_value(d: Path, pattern: str, scale: float = 1.0):
    for f in sorted(d.glob(pattern)):
        v = _read_int(f)
        if v is not None:
            return v / scale
    return None


def _drm_cards():
    base = _SYS / "class" / "drm"
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.name.startswith("card") and "-" not in p.name)


def _linux_amdgpu(card: Path) -> dict:
    dev = card / "device"
    usage = _read_int(dev / "gpu_busy_percent")
    vram_used_b = _read_int(dev / "mem_info_vram_used")
    vram_total_b = _read_int(dev / "mem_info_vram_total")
    temp = power = fan = freq = None
    for h in _hwmon_dirs_for(dev):
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


def _linux_intel(card: Path) -> dict:
    dev = card / "device"
    temp = power = freq = None
    for h in _hwmon_dirs_for(dev):
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


def linux_gpu() -> dict:
    for card in _drm_cards():
        dev = card / "device"
        hwmons = _hwmon_dirs_for(dev)
        names = " ".join(_read_text(h / "name").lower() for h in hwmons)
        blob = f"{_read_text(dev / 'uevent').lower()} {names}"
        if "amdgpu" in blob or "radeon" in blob:
            _LAST_VENDOR["value"] = "amd"
            return _linux_amdgpu(card)
        if "i915" in blob or "xe" in blob or "intel" in blob:
            _LAST_VENDOR["value"] = "intel"
            return _linux_intel(card)
    return dict(EMPTY)


# --------------------------------------------------------------- Windows
def _windows_gpu_name() -> str | None:
    if shutil.which("powershell"):
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController | Select-Object -First 1).Name"],
                capture_output=True, text=True, timeout=5,
                creationflags=CREATE_NO_WINDOW,
            )
            name = out.stdout.strip().splitlines()
            if name and name[0].strip():
                return name[0].strip()
        except Exception:
            pass
    if shutil.which("wmic"):
        try:
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True, text=True, timeout=5,
                creationflags=CREATE_NO_WINDOW,
            )
            lines = [l.strip() for l in out.stdout.splitlines() if l.strip()]
            if len(lines) > 1:
                return lines[1]
        except Exception:
            pass
    return None


def windows_gpu() -> dict:
    data = dict(EMPTY)
    data["gpu_name"] = _windows_gpu_name()
    try:
        import wmi  # type: ignore
    except Exception:
        return data
    try:
        c = wmi.WMI(namespace="root\\LibreHardwareMonitor")
    except Exception:
        return data
    vendor = None
    sensors = {}
    try:
        for s in c.Sensor():
            name = (s.Name or "").lower()
            if "gpu" not in name:
                continue
            stype = s.SensorType
            try:
                value = float(s.Value)
            except Exception:
                continue
            if stype == "Load" and "core" in name and data["gpu_usage"] is None:
                data["gpu_usage"] = value
            elif stype == "Temperature" and "core" in name and data["gpu_temp"] is None:
                data["gpu_temp"] = value
            elif stype == "Power" and data["gpu_power"] is None:
                data["gpu_power"] = value
            elif stype == "Fan" and data["gpu_fan"] is None:
                data["gpu_fan"] = value
            elif stype == "Clock" and data["gpu_freq"] is None:
                data["gpu_freq"] = value
            elif stype == "SmallData" and "memory used" in name:
                data["gpu_mem_used"] = round(value, 2)
            elif stype == "SmallData" and "memory total" in name:
                data["gpu_mem_total"] = round(value, 2)
    except Exception:
        pass
    if data["gpu_mem_used"] and data["gpu_mem_total"]:
        data["gpu_mem_usage"] = round(data["gpu_mem_used"] / data["gpu_mem_total"] * 100.0, 1)
    name = (data.get("gpu_name") or "").lower()
    if "amd" in name or "radeon" in name:
        vendor = "amd"
    elif "intel" in name:
        vendor = "intel"
    data["gpu_vendor"] = vendor
    _LAST_VENDOR["value"] = vendor
    return data


# ------------------------------------------------------------------ public
def collect() -> dict:
    data = nvidia_smi()
    if data:
        return data
    if IS_LINUX:
        return linux_gpu()
    if IS_WINDOWS:
        return windows_gpu()
    return dict(EMPTY)


def collect_all() -> list[dict]:
    return [collect()]
