"""GUI import and localization smoke tests."""
from __future__ import annotations

import importlib

import pytest

from src.i18n import system_language


def test_profiles_exports_needed_by_the_gui():
    """The GUI imports these helpers from the package root."""
    from src.profiles import active_window_title, find_profile, find_profile_by_window

    assert callable(active_window_title)
    assert callable(find_profile_by_window)
    assert callable(find_profile)


def test_gui_imports():
    """Catch missing package exports before the app fails at startup.

    PySide6 can be installed without the system libraries a desktop needs
    (for example on a headless CI runner), so skip when Qt itself is not
    importable.  The profiles export test above still runs in that case.
    """
    try:
        import PySide6.QtWidgets  # noqa: F401
    except ImportError:
        pytest.skip("PySide6 needs desktop libraries that the runner lacks")
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
