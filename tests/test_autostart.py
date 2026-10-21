import sys

from src import autostart


def test_launch_command_is_list_of_strings():
    cmd = autostart.launch_command()
    assert isinstance(cmd, list) and cmd
    assert all(isinstance(c, str) for c in cmd)


def test_launch_command_source_points_to_app():
    if getattr(sys, "frozen", False):
        return
    cmd = autostart.launch_command()
    assert any("app.py" in c for c in cmd)


def test_enable_disable_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart, "LINUX_AUTOSTART", tmp_path)
    monkeypatch.setattr(autostart, "IS_WINDOWS", False)
    monkeypatch.setattr(autostart, "IS_MACOS", False)
    try:
        assert autostart.is_enabled() is False
        path = autostart.enable()
        assert autostart.is_enabled() is True
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "[Desktop Entry]" in text and "Exec=" in text
        assert autostart.disable() is True
        assert autostart.is_enabled() is False
        assert autostart.disable() is False
    finally:
        monkeypatch.undo()
