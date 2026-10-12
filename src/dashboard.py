from pathlib import Path

MANGOHUD_CONF = Path.home() / ".config" / "MangoHud" / "MangoHud.conf"


def read_active():
    if MANGOHUD_CONF.exists():
        try:
            return MANGOHUD_CONF.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
    return ""
