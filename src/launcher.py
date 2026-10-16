"""Build and run application profiles with the selected FPS backend / Game Mode."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess

from src.profiles import AppProfile, ProfileStore


def build_invocation(profile: AppProfile, store: ProfileStore, fps_manager):
    """Return (command list, environment dict) for an application profile."""
    env = dict(os.environ)
    backend = profile.fps_backend or store.global_fps_backend
    fps_manager.set_backend(backend)

    env.update(fps_manager.launch_env(profile))
    for key, value in (profile.env or {}).items():
        env[str(key)] = str(value)

    command: list[str] = []
    command += [str(x) for x in (profile.command_prefix or [])]
    command += [str(x) for x in fps_manager.command_prefix(profile)]

    if profile.gamemode and shutil.which("gamemoderun"):
        command.insert(0, "gamemoderun")

    if profile.executable:
        command += shlex.split(profile.executable)
    if profile.args:
        command += shlex.split(profile.args)

    return command, env


def launch(profile: AppProfile, store: ProfileStore, fps_manager):
    command, env = build_invocation(profile, store, fps_manager)
    if not command:
        raise ValueError("profile has no executable/command")
    cwd = profile.cwd or None
    fps_manager.start(command, profile)
    proc = subprocess.Popen(
        command, env=env, cwd=cwd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return proc, command
