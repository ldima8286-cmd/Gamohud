from dataclasses import dataclass, asdict, field
from pathlib import Path
import json

CFG = Path.home() / ".config" / "gamohud" / "settings.json"


@dataclass
class Settings:
    overlay_enabled: bool = False
    position: str = "top-right"
    margin: int = 16
    opacity: float = 0.85
    font_size: int = 12
    font_color: str = "#f2f2f2"
    accent_color: str = "#4ec9b0"
    bg_color: str = "#101014"
    show_cpu: bool = True
    show_gpu: bool = True
    show_vram: bool = True
    show_ram: bool = True
    show_temp: bool = True
    show_fps: bool = True
    refresh_ms: int = 500
    click_through: bool = False
    fps_log: str = str(Path.home() / ".config" / "MangoHud" / "gamohud_fps.csv")
    mangohud_logging: bool = False

    def save(self):
        CFG.parent.mkdir(parents=True, exist_ok=True)
        CFG.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls):
        if CFG.exists():
            try:
                data = json.loads(CFG.read_text())
                known = {f.name for f in cls.__dataclass_fields__.values()}
                data = {k: v for k, v in data.items() if k in known}
                return cls(**data)
            except Exception:
                pass
        return cls()


def mangohud_conf_path():
    return Path.home() / ".config" / "MangoHud" / "MangoHud.conf"


def set_mangohud_logging(on: bool, log_path: str):
    p = mangohud_conf_path()
    lines = []
    if p.exists():
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if not on and (s.startswith("output_file") or s.startswith("log_duration") or s.startswith("autostart_log")):
            continue
        out.append(ln)
    if on:
        out.append(f"output_file={log_path}")
        out.append("log_duration=0")
        out.append("autostart_log=1")
        out.append("fps_only=0")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out).strip() + "\n", encoding="utf-8")
