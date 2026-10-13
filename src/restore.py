import shutil
import threading
import time
from pathlib import Path

MANGOHUD_CONF = Path.home() / ".config" / "MangoHud" / "MangoHud.conf"
BACKUP = Path.home() / ".config" / "mangohud-preset-manager" / "MangoHud.conf.bak"


def has_backup():
    return BACKUP.exists()


def backup_conf():
    if not MANGOHUD_CONF.exists():
        return False
    # do not overwrite an existing restore point (e.g. leftover from a crash)
    if BACKUP.exists():
        return True
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(MANGOHUD_CONF, BACKUP)
        return True
    except Exception:
        return False


def restore_conf():
    if not BACKUP.exists():
        return False
    try:
        MANGOHUD_CONF.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BACKUP, MANGOHUD_CONF)
        return True
    except Exception:
        return False


def _read_environ(pid):
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            data = f.read()
    except Exception:
        return {}
    env = {}
    for entry in data.split(b"\x00"):
        if b"=" in entry:
            k, _, v = entry.partition(b"=")
            env[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
    return env


def steam_game_running(appid: str):
    appid = str(appid)
    try:
        import psutil
    except Exception:
        return False
    for proc in psutil.process_iter(["pid"]):
        pid = proc.pid
        env = _read_environ(pid)
        if env.get("SteamAppId") == appid or env.get("SteamGameId") == appid:
            return True
    return False


def watch_and_restore(appid, on_restore=None, poll=2.0, start_timeout=300.0, max_runtime=21600.0):
    """Wait for the given Steam appid to appear, then restore conf when it exits.

    Runs in a background thread. If the game never starts within start_timeout,
    restore anyway so we don't leave the preset applied forever.
    """
    def worker():
        started = False
        t0 = time.time()
        while True:
            running = steam_game_running(appid)
            now = time.time()
            if running:
                started = True
            elif started:
                break
            elif now - t0 > start_timeout:
                break
            if now - t0 > max_runtime:
                break
            time.sleep(poll)
        ok = restore_conf()
        if on_restore:
            try:
                on_restore(ok)
            except Exception:
                pass

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    return th
