from dataclasses import dataclass, asdict
from pathlib import Path
import json

BIND = Path.home() / ".config" / "mangohud-preset-manager" / "game_bindings.json"


@dataclass
class Binding:
    game_key: str  # appid or name
    launcher: str
    preset: str = ""
    gamemode_profile: str = ""


def load_bindings():
    if BIND.exists():
        try:
            data = json.loads(BIND.read_text())
            return [Binding(**d) for d in data]
        except Exception:
            pass
    return []


def save_bindings(binds):
    BIND.parent.mkdir(parents=True, exist_ok=True)
    BIND.write_text(json.dumps([asdict(b) for b in binds], indent=2))


def get_binding(game_key: str):
    for b in load_bindings():
        if b.game_key == game_key:
            return b
    return None
