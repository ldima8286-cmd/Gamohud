import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict

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
    # libraryfolders.vdf locations
    vdf_paths = []
    vdf_paths.append(Path.home() / ".steam" / "steam" / "config" / "libraryfolders.vdf")
    vdf_paths.append(Path.home() / ".steam" / "config" / "libraryfolders.vdf")
    vdf_paths.append(Path.home() / ".local" / "share" / "Steam" / "config" / "libraryfolders.vdf")
    # scan all vdf
    for v in vdf_paths:
        if v.exists():
            try:
                text = v.read_text(encoding='utf-8', errors='replace')
                # find paths
                for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                    base = Path(m.group(1)).expanduser()
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
    # dedupe by appid
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
