from dataclasses import dataclass, asdict
from pathlib import Path
import yaml

PROFILES = Path.home() / ".config" / "mangohud-preset-manager" / "gamemode_profiles.yaml"


@dataclass
class GMProfile:
    name: str
    gamemode: bool = True
    kill: list = None
    restore: list = None
    env: dict = None
    preset: str = ""


def load_profiles():
    if not PROFILES.exists():
        return []
    try:
        data = yaml.safe_load(PROFILES.read_text()) or []
        return [GMProfile(**d) for d in data]
    except Exception:
        return []


def save_profiles(profiles):
    PROFILES.parent.mkdir(parents=True, exist_ok=True)
    PROFILES.write_text(yaml.safe_dump([asdict(p) for p in profiles], allow_unicode=True))
