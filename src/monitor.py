import psutil
import time

def get_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    net = psutil.net_io_counters()
    temp = None
    try:
        temps = psutil.sensors_temperatures()
        # common keys
        for k in temps:
            for t in temps[k]:
                if 'cpu' in k.lower() or 'core' in t.label.lower() or t.label == '':
                    temp = t.current
                    break
            if temp is not None:
                break
    except Exception:
        temp = None
    return {
        'cpu': cpu,
        'ram_used': round(mem.used / 1024**3, 2),
        'ram_total': round(mem.total / 1024**3, 2),
        'ram_percent': mem.percent,
        'swap_percent': swap.percent,
        'temp': temp,
    }
