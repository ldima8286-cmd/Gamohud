import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.platform_utils import config_dir

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

@dataclass
class Game:
    name: str
    launcher: str
    exec: str = ""
    appid: str = ""
    preset: str = ""
    gamemode_profile: str = ""


def find_steam_games():
    games = []
    vdf_paths = []
    vdf_paths.append(Path.home() / ".steam" / "steam" / "config" / "libraryfolders.vdf")
    vdf_paths.append(Path.home() / ".steam" / "config" / "libraryfolders.vdf")
    vdf_paths.append(Path.home() / ".local" / "share" / "Steam" / "config" / "libraryfolders.vdf")
    for env_var in ("ProgramFiles(x86)", "ProgramFiles"):
        pf = os.environ.get(env_var)
        if pf:
            vdf_paths.append(Path(pf) / "Steam" / "config" / "libraryfolders.vdf")
            vdf_paths.append(Path(pf) / "Steam" / "steamapps" / "libraryfolders.vdf")
    for v in vdf_paths:
        if v.exists():
            try:
                text = v.read_text(encoding='utf-8', errors='replace')
                for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                    raw = m.group(1).replace("\\\\", "\\")
                    base = Path(raw).expanduser()
                    steamapps = base / "steamapps"
                    if not steamapps.exists():
                        continue
                    for af in steamapps.glob("appmanifest_*.acf"):
                        try:
                            t = af.read_text(encoding='utf-8', errors='replace')
                            name = re.search(r'"name"\s+"([^"]+)"', t)
                            appid = re.search(r'"appid"\s+"([^"]+)"', t)
                            if name:
                                games.append(Game(name=name.group(1), launcher='steam', appid=appid.group(1) if appid else af.stem.split('_')[-1], exec=""))
                        except Exception:
                            pass
            except Exception:
                pass
    seen = set()
    res = []
    for g in games:
        if g.appid and g.appid in seen:
            continue
        if g.appid:
            seen.add(g.appid)
        res.append(g)
    res.sort(key=lambda x: x.name.lower())
    return res


def find_lutris_games():
    games = []
    bases = []
    bases.append(Path.home() / ".config" / "lutris" / "games")
    bases.append(Path.home() / ".local" / "share" / "lutris" / "games")
    for b in bases:
        if not b.exists():
            continue
        for f in b.glob("*.yml"):
            try:
                if yaml is None:
                    continue
                data = yaml.safe_load(f.read_text(encoding='utf-8', errors='replace')) or {}
                name = data.get('name') or data.get('game', {}).get('name') or f.stem
                exe = data.get('exe') or data.get('game', {}).get('exe') or data.get('game', {}).get('working_dir')
                games.append(Game(name=str(name), launcher='lutris', exec=str(exe) if exe else "", appid=f.stem))
            except Exception:
                pass
        for f in b.glob("*.yaml"):
            try:
                if yaml is None:
                    continue
                data = yaml.safe_load(f.read_text(encoding='utf-8', errors='replace')) or {}
                name = data.get('name') or data.get('game', {}).get('name') or f.stem
                exe = data.get('exe') or data.get('game', {}).get('exe') or ""
                games.append(Game(name=str(name), launcher='lutris', exec=str(exe), appid=f.stem))
            except Exception:
                pass
    seen = set()
    res = []
    for g in games:
        key = f"lutris:{g.appid}"
        if key in seen:
            continue
        seen.add(key)
        res.append(g)
    res.sort(key=lambda x: x.name.lower())
    return res


def find_bottles_games():
    games = []
    # Bottles stores data in various places; simple scan
    bases = []
    bases.append(Path.home() / ".local" / "share" / "bottles")
    bases.append(Path.home() / ".config" / "bottles")
    for b in bases:
        if not b.exists():
            continue
        for f in b.rglob("*.json"):
            try:
                data = json.loads(f.read_text(encoding='utf-8', errors='replace'))
                name = data.get('name') or data.get('Game', {}).get('name') or data.get('title')
                if name:
                    games.append(Game(name=str(name), launcher='bottles', exec="", appid=f.stem))
            except Exception:
                pass
    seen = set()
    res = []
    for g in games:
        key = f"bottles:{g.name.lower()}"
        if key in seen:
            continue
        seen.add(key)
        res.append(g)
    res.sort(key=lambda x: x.name.lower())
    return res


def find_heroic_games():
    games = []
    bases = []
    bases.append(Path.home() / ".config" / "heroic" / "games")
    bases.append(Path.home() / ".config" / "heroic" / "library")
    bases.append(Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic" / "games")
    bases.append(Path.home() / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic" / "library")
    for b in bases:
        if not b.exists():
            continue
        for f in b.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding='utf-8', errors='replace'))
                name = data.get('title') or data.get('name') or data.get('appName')
                exe = data.get('executable') or data.get('install_path')
                if not name:
                    continue
                games.append(Game(name=str(name), launcher='heroic', exec=str(exe) if exe else "", appid=f.stem))
            except Exception:
                pass
    seen = set()
    res = []
    for g in games:
        key = f"heroic:{g.name.lower()}"
        if key in seen:
            continue
        seen.add(key)
        res.append(g)
    res.sort(key=lambda x: x.name.lower())
    return res


def all_games():
    g = []
    g.extend(find_steam_games())
    g.extend(find_lutris_games())
    g.extend(find_bottles_games())
    g.extend(find_heroic_games())
    g.extend(find_manual_games())
    return g


MANUAL_FILE = config_dir("gamohud") / "manual_games.json"


def load_manual_games():
    if MANUAL_FILE.exists():
        try:
            data = json.loads(MANUAL_FILE.read_text(encoding='utf-8', errors='replace'))
            res = []
            for d in data:
                res.append(Game(**d))
            return res
        except Exception:
            pass
    return []


def save_manual_game(name, exe, appid=""):
    games = load_manual_games()
    key = (name.lower(), exe)
    games = [g for g in games if (g.name.lower(), g.exec) != key]
    games.append(Game(name=str(name), launcher='manual', exec=str(exe), appid=str(appid) if appid else str(exe)))
    MANUAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANUAL_FILE.write_text(json.dumps([asdict(g) for g in games], indent=2))


def find_manual_games():
    return load_manual_games()
