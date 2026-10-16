"""gamohud-run: transparent launcher that applies a profile's overlay/backend/env.

Usage:
  gamohud run --list
  gamohud run --profile NAME [-- extra args]
  gamohud run [--backend NAME] [--env K=V ...] [--gamemode] -- COMMAND [ARGS...]
"""
from __future__ import annotations

import os
import shutil
import sys

from src.fps import FPSManager
from src.profiles import ProfileStore


def _usage() -> int:
    print(__doc__.strip())
    return 2


def main(argv: list[str]) -> int:
    store = ProfileStore()
    manager = FPSManager(store.global_fps_backend)

    backend = None
    gamemode = False
    env_overrides = {}
    profile_name = None
    command: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--list":
            for p in store.app_profiles:
                print(f"{p.name}\tmatch={','.join(p.match)}\toverlay={p.overlay or '-'}")
            return 0
        if arg == "--profile" and i + 1 < len(argv):
            profile_name = argv[i + 1]
            i += 2
            continue
        if arg == "--backend" and i + 1 < len(argv):
            backend = argv[i + 1]
            i += 2
            continue
        if arg == "--env" and i + 1 < len(argv):
            if "=" in argv[i + 1]:
                k, v = argv[i + 1].split("=", 1)
                env_overrides[k] = v
            i += 2
            continue
        if arg == "--gamemode":
            gamemode = True
            i += 1
            continue
        if arg == "--":
            command = argv[i + 1:]
            break
        if arg.startswith("-") and not command:
            return _usage()
        command = argv[i:]
        break

    if profile_name:
        profile = next((p for p in store.app_profiles if p.name == profile_name), None)
        if profile is None:
            print(f"gamohud: unknown app profile '{profile_name}'", file=sys.stderr)
            return 1
        if backend:
            profile.fps_backend = backend
        if gamemode:
            profile.gamemode = True
        if command:
            profile.args = (profile.args + " " if profile.args else "") + " ".join(command)
        if env_overrides:
            profile.env = {**(profile.env or {}), **env_overrides}
        if not profile.executable:
            print(f"gamohud: profile '{profile_name}' has no executable", file=sys.stderr)
            return 1
        cmd, env = _invoke(profile, store, manager)
    else:
        if not command:
            return _usage()
        cmd = list(command)
        env = dict(os.environ)
        manager.set_backend(backend or store.global_fps_backend)
        env.update(manager.launch_env(None))
        if gamemode and shutil.which("gamemoderun"):
            cmd = ["gamemoderun"] + cmd
        env.update(env_overrides)

    if not cmd:
        return _usage()
    try:
        os.execvpe(cmd[0], cmd, env)
    except FileNotFoundError:
        print(f"gamohud: command not found: {cmd[0]}", file=sys.stderr)
        return 127


def _invoke(profile, store, manager):
    from src.launcher import build_invocation
    return build_invocation(profile, store, manager)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
