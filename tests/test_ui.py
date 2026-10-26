"""GUI import and localization smoke tests."""
from __future__ import annotations

import importlib

from src.i18n import system_language


def test_gui_imports():
    """Catch missing package exports before the app fails at startup."""
    module = importlib.import_module("src.gui")
    assert hasattr(module, "MainWindow")


def test_system_language_prefers_supported_env(monkeypatch):
    monkeypatch.setattr("src.i18n.locale.getlocale", lambda: (None, None))
    monkeypatch.setenv("LANGUAGE", "de_DE.UTF-8")
    monkeypatch.setenv("LC_ALL", "ru_RU.UTF-8")
    monkeypatch.setenv("LC_MESSAGES", "")
    monkeypatch.setenv("LANG", "")
    assert system_language() == "ru"


def test_system_language_falls_back_to_locale(monkeypatch):
    monkeypatch.setattr("src.i18n.locale.getlocale", lambda: ("ru_RU", "UTF-8"))
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    assert system_language() == "ru"


def test_system_language_defaults_to_english(monkeypatch):
    monkeypatch.setattr("src.i18n.locale.getlocale", lambda: (None, None))
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    assert system_language() == "en"
