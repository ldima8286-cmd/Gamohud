"""Metric registry and aggregation for the standalone gamohud overlay."""
from __future__ import annotations

from . import gpu as _gpu
from . import system as _system

# key -> (label, unit, formatter)
METRICS = {
    "fps": ("FPS", "", lambda v: f"{v:.0f}"),
    "fps_avg": ("AVG FPS", "", lambda v: f"{v:.0f}"),
    "fps_1low": ("1% LOW", "", lambda v: f"{v:.0f}"),
    "fps_01low": ("0.1% LOW", "", lambda v: f"{v:.0f}"),
    "frametime": ("Frame", "ms", lambda v: f"{v:.1f}"),
    "cpu_usage": ("CPU", "%", lambda v: f"{v:.0f}"),
    "cpu_freq": ("CPU CLK", "MHz", lambda v: f"{v:.0f}"),
    "cpu_temp": ("CPU TEMP", "\u00b0C", lambda v: f"{v:.0f}"),
    "cpu_power": ("CPU PWR", "W", lambda v: f"{v:.1f}"),
    "cpu_fan": ("CPU FAN", "rpm", lambda v: f"{v:.0f}"),
    "gpu_usage": ("GPU", "%", lambda v: f"{v:.0f}"),
    "gpu_temp": ("GPU TEMP", "\u00b0C", lambda v: f"{v:.0f}"),
    "gpu_power": ("GPU PWR", "W", lambda v: f"{v:.1f}"),
    "gpu_freq": ("GPU CLK", "MHz", lambda v: f"{v:.0f}"),
    "gpu_fan": ("GPU FAN", "%", lambda v: f"{v:.0f}"),
    "gpu_mem_used": ("VRAM", "GB", lambda v: f"{v:.1f}"),
    "gpu_mem_usage": ("VRAM %", "%", lambda v: f"{v:.0f}"),
    "ram_used": ("RAM", "GB", lambda v: f"{v:.1f}"),
    "ram_percent": ("RAM %", "%", lambda v: f"{v:.0f}"),
    "swap_percent": ("SWAP", "%", lambda v: f"{v:.0f}"),
    "net_up": ("NET UP", "KB/s", lambda v: f"{v:.0f}"),
    "net_down": ("NET DN", "KB/s", lambda v: f"{v:.0f}"),
    "disk_read": ("DISK R", "MB/s", lambda v: f"{v:.1f}"),
    "disk_write": ("DISK W", "MB/s", lambda v: f"{v:.1f}"),
}

DEFAULT_METRICS = ["fps", "frametime", "cpu_usage", "gpu_usage", "gpu_temp", "ram_percent"]


# Layout presets: one-click metric sets for the overlay.
# key -> (label, description, metrics)
LAYOUT_PRESETS = {
    "compact": (
        "Compact",
        "Just FPS and the two loads",
        ["fps", "cpu_usage", "gpu_usage"],
    ),
    "detailed": (
        "Detailed",
        "FPS, frametime, loads, temperatures and memory",
        [
            "fps", "frametime", "cpu_usage", "cpu_temp",
            "gpu_usage", "gpu_temp", "gpu_mem_usage", "ram_percent",
        ],
    ),
    "power": (
        "Power",
        "Clocks, power draw and fan speeds",
        [
            "fps", "cpu_freq", "cpu_power", "cpu_fan",
            "gpu_freq", "gpu_power", "gpu_fan", "gpu_temp",
        ],
    ),
    "memory": (
        "Memory",
        "VRAM, RAM and swap",
        ["fps", "gpu_mem_used", "gpu_mem_usage", "ram_used", "ram_percent", "swap_percent"],
    ),
    "network": (
        "Network",
        "FPS, network and disk throughput",
        ["fps", "net_up", "net_down", "disk_read", "disk_write"],
    ),
    "smoothness": (
        "Smoothness",
        "FPS with 1% and 0.1% low frame rates",
        ["fps", "fps_avg", "fps_1low", "fps_01low", "frametime"],
    ),
}


def available_metric_keys() -> list[str]:
    return list(METRICS.keys())


def collect_system() -> dict:
    return _system.collect()


def collect_gpu() -> dict:
    return _gpu.collect()


def collect_all(fps: dict | None = None) -> dict:
    data = {}
    for collect in (_system.collect, _gpu.collect):
        try:
            data.update(collect() or {})
        except Exception:
            continue
    if fps:
        data.update(fps)
    return data


def format_metric(key: str, value) -> str | None:
    spec = METRICS.get(key)
    if spec is None or value is None:
        return None
    _, _, fmt = spec
    try:
        return fmt(value)
    except Exception:
        return str(value)


def metric_label(key: str) -> str:
    spec = METRICS.get(key)
    return spec[0] if spec else key


def metric_unit(key: str) -> str:
    spec = METRICS.get(key)
    return spec[1] if spec else ""
