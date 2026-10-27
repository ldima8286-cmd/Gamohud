from types import SimpleNamespace

from src.layer_shell import (
    ANCHOR_LEFT,
    ANCHOR_RIGHT,
    ANCHOR_TOP,
    _anchors_and_margins,
)


def profile(**kwargs):
    values = {"position": "top-right", "margin": 16, "x": 0, "y": 0}
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_top_right_uses_right_and_top_anchors():
    anchors, margins = _anchors_and_margins(profile())
    assert anchors == ANCHOR_TOP | ANCHOR_RIGHT
    assert (margins.top, margins.right) == (16, 16)
    assert (margins.left, margins.bottom) == (0, 0)


def test_custom_position_uses_top_left_margins():
    anchors, margins = _anchors_and_margins(
        profile(position="custom", x=123, y=45)
    )
    assert anchors == ANCHOR_TOP | ANCHOR_LEFT
    assert (margins.left, margins.top) == (123, 45)


def test_center_has_no_anchors():
    anchors, margins = _anchors_and_margins(profile(position="center"))
    assert anchors == 0
    assert (margins.left, margins.top, margins.right, margins.bottom) == (0, 0, 0, 0)
