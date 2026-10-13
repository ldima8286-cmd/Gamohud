from dataclasses import dataclass, asdict
from pathlib import Path
import os
import shutil
import subprocess
import yaml

PROFILES = Path.home() / ".config" / "mangohud-preset-manager" / "gamemode_profiles.yaml"


@dataclass
class GMProfile:
    name: str
    gamemode: bool = True
    kill: list = None  # list of process names/commands to kill before run
    restore: list = None  # list of commands to run after process ends
    env: dict = None  # extra env vars
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


def _sanitize_list(lst):
    if not lst:
        return []
    res = []
    for x in lst:
        if x is None:
            continue
        res.append(str(x))
    return res


def _sanitize_env(env):
    if not env:
        return {}
    res = {}
    for k, v in env.items():
        if v is None:
            continue
        res[str(k)] = str(v)
    return res


def find_gamemoderun():
    return shutil.which("gamemoderun")


def build_env(profile: GMProfile, base_env=None):
    env = dict(base_env) if base_env else dict(os.environ)
    penv = _sanitize_env(profile.env)
    env.update(penv)
    return env


def run_kill(profile: GMProfile):
    for cmd in _sanitize_list(profile.kill):
        try:
            subprocess.run(cmd, shell=True, check=False)
        except Exception:
            pass


def run_restore(profile: GMProfile):
    for cmd in _sanitize_list(profile.restore):
        try:
            subprocess.run(cmd, shell=True, check=False)
        except Exception:
            pass


def run_profile(profile: GMProfile, command, cwd=None, wait=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
    if not command:
        return None
    gm = find_gamemoderun() if profile.gamemode else None
    # build full command
    if isinstance(command, (list, tuple)):
        cmd_list = list(command)
    else:
        cmd_list = command

    if gm:
        if isinstance(cmd_list, str):
            full_cmd = f'"{gm}" {cmd_list}'
        else:
            full_cmd = [gm] + list(cmd_list)
    else:
        full_cmd = cmd_list

    env = build_env(profile)
    try:
        run_kill(profile)
        if wait:
            proc = subprocess.run(full_cmd, shell=isinstance(full_cmd, str), env=env, cwd=cwd, stdout=stdout, stderr=stderr)
            run_restore(profile)
            return proc
        else:
            proc = subprocess.Popen(full_cmd, shell=isinstance(full_cmd, str), env=env, cwd=cwd, stdout=stdout, stderr=stderr)
            return proc
    except Exception:
        run_restore(profile)
        return None
