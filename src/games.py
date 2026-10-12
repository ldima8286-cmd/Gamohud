import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Game:
    name: str
    launcher: str  # steam/lutris/heroic/bottles/manual
    exec: str = ""
    appid: str = ""
    preset: str = ""  # preset filename
    gamemode_profile: str = ""


def find_steam_games():
    games = []
    # common paths
    paths = []
    paths.append(Path.home() / ".steam" / "steam" / "appcache" / "librarycache")
    paths.append(Path.home() / ".local" / "share" / "Steam" / "appcache" / "librarycache")
    for p in paths:
        if not p.exists():
            continue
        for f in p.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                name = data.get("name") or f.stem
                appid = data.get("appid") or data.get("appID") or ""
                games.append(Game(name=name, launcher="steam", appid=str(appid)))
            except Exception:
                pass
    return games


def find_lutris_games():
    games = []
    dbs = [
        Path.home() / ".local" / "share" / "lutris" / "pga.db",
        Path.home() / "Games" / "lutris" / "pga.db",
    ]
    # simple parse not needed now; return empty if not import sqlite3? skip heavy
    return games
