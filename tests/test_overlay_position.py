from PySide6.QtCore import QRect

from src.overlay import overlay_position
from src.profiles import OverlayProfile

SCREEN = QRect(0, 0, 1920, 1080)


def test_predefined_top_left_uses_margin():
    profile = OverlayProfile(position="top-left", margin=16)
    assert overlay_position(profile, 300, 200, SCREEN) == (16, 16)


def test_center_is_really_centered():
    profile = OverlayProfile(position="center", margin=16)
    x, y = overlay_position(profile, 300, 200, SCREEN)
    assert 780 <= x <= 820
    assert 420 <= y <= 460
    assert x > 16 and y > 16


def test_custom_garbage_coordinates_fall_back_to_margin():
    profile = OverlayProfile(position="custom", x=10000, y=10000, margin=16)
    assert overlay_position(profile, 300, 200, SCREEN) == (16, 16)


def test_custom_partially_offscreen_is_clamped():
    profile = OverlayProfile(position="custom", x=1900, y=1000, margin=16)
    assert overlay_position(profile, 300, 200, SCREEN) == (1620, 880)


def test_custom_negative_is_clamped():
    profile = OverlayProfile(position="custom", x=-50, y=-60, margin=16)
    assert overlay_position(profile, 300, 200, SCREEN) == (0, 0)


def test_unknown_position_and_bad_margin_are_safe():
    profile = OverlayProfile(position="nonsense", margin=-20)
    assert overlay_position(profile, 300, 200, SCREEN) == (0, 0)
