from dataclasses import dataclass, asdict
from pathlib import Path
import json

CFG_PATH = Path.home() / ".config" / "mangohud-preset-manager" / "config.json"


@dataclass
class Config:
    last_dir: str = str(Path.home() / ".config" / "MangoHud")
    show_flatpak: bool = True

    def save(self):
        CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CFG_PATH.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls):
        if CFG_PATH.exists():
            try:
                data = json.loads(CFG_PATH.read_text())
                return cls(**data)
            except Exception:
                pass
        return cls()
