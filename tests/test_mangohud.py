"""Tests for the MangoHud CSV-log FPS backend."""
from __future__ import annotations

import os
import time

from src.fps.backends.mangohud import (
    MangoHudLogBackend,
    mangohud_logging_enabled,
    set_mangohud_logging,
)


def _write_log(path, rows):
    lines = [
        "os,cpu,gpu,ram,kernel,driver,cpuscheduler",
        "Bazzite,CPU,GPU,16000,6.0,,powersave",
        "fps,frametime,cpu_load,gpu_load",
    ]
    lines += [",".join(str(value) for value in row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_reads_fps_and_frametime_from_newest_row(tmp_path):
    log = tmp_path / "game_2026-01-01_00-00-00.csv"
    _write_log(log, [(60.0, 16.6, 12, 20), (144.5, 6.92, 14, 30)])
    backend = MangoHudLogBackend(tmp_path)

    data = backend.read()

    assert data is not None
    assert data["fps"] == 144.5
    assert data["frametime"] == 6.92


def test_read_uses_newest_csv_when_several_exist(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write_log(old, [(30.0, 33.3, 1, 2)])
    time.sleep(0.02)
    _write_log(new, [(90.0, 11.1, 1, 2)])
    backend = MangoHudLogBackend(tmp_path)

    data = backend.read()

    assert data is not None
    assert data["fps"] == 90.0


def test_ignores_stale_log(tmp_path):
    log = tmp_path / "game.csv"
    _write_log(log, [(60.0, 16.6, 1, 2)])
    old = time.time() - 60
    os.utime(log, (old, old))
    backend = MangoHudLogBackend(tmp_path)

    assert backend.read() is None


def test_start_ignores_old_file_and_accepts_new_file(tmp_path):
    old = tmp_path / "old.csv"
    _write_log(old, [(30.0, 33.3, 1, 2)])
    old_time = time.time() - 30
    os.utime(old, (old_time, old_time))
    backend = MangoHudLogBackend(tmp_path)
    backend.start()

    assert backend.read() is None

    new = tmp_path / "new.csv"
    _write_log(new, [(120.0, 8.3, 1, 2)])
    data = backend.read()
    assert data is not None
    assert data["fps"] == 120.0


def test_launch_env_enables_logging(tmp_path, monkeypatch):
    monkeypatch.delenv("MANGOHUD_CONFIG", raising=False)
    backend = MangoHudLogBackend(tmp_path)

    env = backend.launch_env()

    assert env["MANGOHUD"] == "1"
    config = env["MANGOHUD_CONFIG"]
    assert f"output_folder={tmp_path}" in config
    assert "autostart_log=1" in config
    assert "log_interval=100" in config


def test_launch_env_preserves_unrelated_options(tmp_path, monkeypatch):
    monkeypatch.setenv("MANGOHUD_CONFIG", "fps_limit=60,gpu_temp")
    backend = MangoHudLogBackend(tmp_path)

    config = backend.launch_env()["MANGOHUD_CONFIG"]

    assert "fps_limit=60" in config
    assert "gpu_temp" in config
    assert f"output_folder={tmp_path}" in config


def test_managed_mangohud_logging_block(tmp_path):
    config = tmp_path / "MangoHud.conf"
    config.write_text("fps\nfps_limit=60\n", encoding="utf-8")
    log_dir = tmp_path / "logs"

    set_mangohud_logging(True, log_dir, config)
    text = config.read_text(encoding="utf-8")
    assert "fps_limit=60" in text
    assert f"output_folder={log_dir}" in text
    assert mangohud_logging_enabled(log_dir, config)

    set_mangohud_logging(False, log_dir, config)
    text = config.read_text(encoding="utf-8")
    assert "fps_limit=60" in text
    assert "gamohud fps log" not in text
    assert not mangohud_logging_enabled(log_dir, config)


def test_available_uses_host_mangohud(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.fps.backends.mangohud.host_which",
        lambda name: "/usr/bin/mangohud" if name == "mangohud" else None,
    )
    backend = MangoHudLogBackend(tmp_path)
    assert backend.available().available


def test_command_prefix_uses_mangohud_wrapper(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.fps.backends.mangohud.host_which",
        lambda name: "/usr/bin/mangohud" if name == "mangohud" else None,
    )
    monkeypatch.setattr("src.fps.backends.mangohud.in_flatpak", lambda: False)
    backend = MangoHudLogBackend(tmp_path)

    assert backend.command_prefix() == ["mangohud"]


def test_store_roundtrips_mangohud_settings(tmp_path):
    from src.profiles.store import ProfileStore

    path = tmp_path / "profiles.yaml"
    store = ProfileStore(path)
    store.mangohud_log_dir = str(tmp_path / "logs")
    store.mangohud_logging = True
    store.hide_mangohud_hud = False
    store.save()

    reloaded = ProfileStore(path)
    assert reloaded.mangohud_log_dir == str(tmp_path / "logs")
    assert reloaded.mangohud_logging is True
    assert reloaded.hide_mangohud_hud is False


def test_fallback_skips_unavailable_and_env_only_backends():
    from src.fps.base import BackendStatus
    from src.fps.manager import FPSManager

    class FakeBackend:
        env_only = False

        def __init__(self, available):
            self._available = available

        def available(self):
            return BackendStatus(self._available)

    manager = FPSManager("null")
    manager._backends = {
        "mangohud_log": FakeBackend(False),
        "vulkan_layer": FakeBackend(False),
        "presentmon": FakeBackend(True),
        "gamescope": FakeBackend(True),
        "mesa_gallium": FakeBackend(True),
    }
    assert manager.fallback_backend() == "presentmon"

    manager._backends["presentmon"]._available = False
    env_only = FakeBackend(True)
    env_only.env_only = True
    manager._backends["gamescope"] = env_only
    assert manager.fallback_backend() is None
