import os
import shutil
import subprocess
import psutil


def get_gpu_stats():
    gpu_load = None
    gpu_temp = None
    vram_used = None
    vram_total = None
    try:
        nv = shutil.which("nvidia-smi")
        if nv:
            out = subprocess.check_output(
                [nv, "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=2,
            )
            # take first line
            line = out.strip().splitlines()[0].replace(" ", "")
            parts = line.split(",")
            if len(parts) >= 4:
                gpu_load = float(parts[0]) if parts[0] not in ("", "N/A") else None
                gpu_temp = float(parts[1]) if parts[1] not in ("", "N/A") else None
                vram_used = round(float(parts[2]) / 1024.0, 2) if parts[2] not in ("", "N/A") else None
                vram_total = round(float(parts[3]) / 1024.0, 2) if parts[3] not in ("", "N/A") else None
                return {
                    "gpu_load": gpu_load,
                    "gpu_temp": gpu_temp,
                    "vram_used": vram_used,
                    "vram_total": vram_total,
                }
    except Exception:
        pass
    try:
        rocm = shutil.which("rocm-smi")
        if rocm:
            out = subprocess.check_output([rocm, "--showuse", "--showtemp"], stderr=subprocess.STDOUT, text=True, timeout=2)
            # very rough parse; leave None if not found
    except Exception:
        pass
    return {
        "gpu_load": None,
        "gpu_temp": None,
        "vram_used": None,
        "vram_total": None,
    }


def get_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    temp = None
    try:
        temps = psutil.sensors_temperatures()
        for k in temps:
            for t in temps[k]:
                if 'cpu' in k.lower() or 'core' in t.label.lower() or t.label == '':
                    temp = t.current
                    break
            if temp is not None:
                break
    except Exception:
        temp = None
    g = get_gpu_stats()
    try:
        with open("/proc/loadavg") as f:
            load1 = float(f.read().split()[0])
    except Exception:
        load1 = None
    return {
        'cpu': cpu,
        'load1': load1,
        'ram_used': round(mem.used / 1024**3, 2),
        'ram_total': round(mem.total / 1024**3, 2),
        'ram_percent': mem.percent,
        'swap_percent': swap.percent,
        'temp': temp,
        **g,
    }
