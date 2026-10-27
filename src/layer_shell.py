"""Optional wlr-layer-shell support for the overlay.

KWin places ordinary ``keepAbove`` windows below an *active* fullscreen
window.  A layer-shell surface on the ``overlay`` layer is above it, which is
what an FPS overlay needs.  Qt has no public layer-shell API, but KDE ships
``layer-shell-qt``; we call its small C++ interface through ctypes.

This module is intentionally usable only by the small host helper process: it
needs a PySide6 build whose Qt version matches the installed layer-shell-qt
library.  The GUI itself falls back to the normal Qt window when the helper is
not available.
"""
from __future__ import annotations

import ctypes
import ctypes.util

# LayerShellQt::Window::Anchor
ANCHOR_TOP = 1
ANCHOR_BOTTOM = 2
ANCHOR_LEFT = 4
ANCHOR_RIGHT = 8

# LayerShellQt::Window::Layer
LAYER_BACKGROUND = 0
LAYER_BOTTOM = 1
LAYER_TOP = 2
LAYER_OVERLAY = 3

# LayerShellQt::Window::KeyboardInteractivity
KEYBOARD_NONE = 0


class QMargins(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_int),
        ("top", ctypes.c_int),
        ("right", ctypes.c_int),
        ("bottom", ctypes.c_int),
    ]


class QSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int), ("height", ctypes.c_int)]


def _symbol(lib, name):
    try:
        return getattr(lib, name)
    except AttributeError as exc:  # pragma: no cover - version specific
        raise RuntimeError(f"layer-shell-qt symbol missing: {name}") from exc


class LayerShellController:
    """Attach a QWidget's QWindow to the Wayland overlay layer."""

    def __init__(self, window):
        library = ctypes.util.find_library("LayerShellQtInterface")
        if not library:
            raise RuntimeError("libLayerShellQtInterface is not installed")
        self.lib = ctypes.CDLL(library)

        # QWidget creates its native QWindow lazily; force it to exist before
        # LayerShellQt installs its shell integration.
        window.winId()
        qwindow = window.windowHandle()
        if qwindow is None:
            raise RuntimeError("the overlay QWindow is not available")

        import shiboken6

        pointers = shiboken6.getCppPointer(qwindow)
        if not pointers:
            raise RuntimeError("could not get the native QWindow pointer")
        self._qwindow = ctypes.c_void_p(int(pointers[0]))

        self._get = _symbol(self.lib, "_ZN12LayerShellQt6Window3getEP7QWindow")
        self._set_layer = _symbol(
            self.lib, "_ZN12LayerShellQt6Window8setLayerENS0_5LayerE"
        )
        self._set_anchors = _symbol(
            self.lib,
            "_ZN12LayerShellQt6Window10setAnchorsE6QFlagsINS0_6AnchorEE",
        )
        self._set_margins = _symbol(
            self.lib, "_ZN12LayerShellQt6Window10setMarginsERK8QMargins"
        )
        self._set_desired_size = _symbol(
            self.lib, "_ZN12LayerShellQt6Window14setDesiredSizeERK5QSize"
        )
        self._set_keyboard = _symbol(
            self.lib,
            "_ZN12LayerShellQt6Window24setKeyboardInteractivityENS0_21KeyboardInteractivityE",
        )
        self._set_exclusive_zone = _symbol(
            self.lib, "_ZN12LayerShellQt6Window16setExclusiveZoneEi"
        )
        self._set_activate_on_show = _symbol(
            self.lib, "_ZN12LayerShellQt6Window17setActivateOnShowEb"
        )
        self._set_close_on_dismissed = _symbol(
            self.lib, "_ZN12LayerShellQt6Window19setCloseOnDismissedEb"
        )

        self._get.argtypes = [ctypes.c_void_p]
        self._get.restype = ctypes.c_void_p
        for func, arg in (
            (self._set_layer, ctypes.c_int),
            (self._set_anchors, ctypes.c_int),
            (self._set_keyboard, ctypes.c_int),
            (self._set_exclusive_zone, ctypes.c_int),
            (self._set_activate_on_show, ctypes.c_bool),
            (self._set_close_on_dismissed, ctypes.c_bool),
        ):
            func.argtypes = [ctypes.c_void_p, arg]
            func.restype = None
        self._set_margins.argtypes = [ctypes.c_void_p, ctypes.POINTER(QMargins)]
        self._set_margins.restype = None
        self._set_desired_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(QSize)]
        self._set_desired_size.restype = None

        self._window = self._get(self._qwindow)
        if not self._window:
            raise RuntimeError("LayerShellQt could not attach to the QWindow")

        self._set_layer(self._window, LAYER_OVERLAY)
        self._set_keyboard(self._window, KEYBOARD_NONE)
        self._set_exclusive_zone(self._window, 0)
        self._set_activate_on_show(self._window, False)
        self._set_close_on_dismissed(self._window, False)

    def apply(
        self,
        profile,
        width: int,
        height: int,
        screen_width: int = 0,
        screen_height: int = 0,
    ) -> None:
        """Update anchors, margins and desired size from the overlay profile."""
        width = max(1, int(width))
        height = max(1, int(height))
        anchors, margins = _anchors_and_margins(profile)
        if (getattr(profile, "position", "") or "").lower() == "custom":
            # A saved custom x/y may have been chosen for a narrower overlay.
            # Keep the whole surface on screen after a profile/metric change.
            if screen_width > 0:
                margins.left = min(margins.left, max(0, screen_width - width))
            if screen_height > 0:
                margins.top = min(margins.top, max(0, screen_height - height))
        self._set_anchors(self._window, anchors)
        self._set_margins(self._window, ctypes.byref(margins))
        size = QSize(width, height)
        self._set_desired_size(self._window, ctypes.byref(size))

    def set_layer(self, layer: int) -> None:
        self._set_layer(self._window, int(layer))


def _anchors_and_margins(profile) -> tuple[int, QMargins]:
    position = (getattr(profile, "position", "top-left") or "top-left").lower()
    margin = max(0, int(getattr(profile, "margin", 16)))
    if position == "custom":
        x = max(0, int(getattr(profile, "x", 0)))
        y = max(0, int(getattr(profile, "y", 0)))
        return ANCHOR_TOP | ANCHOR_LEFT, QMargins(x, y, 0, 0)

    vertical, _, horizontal = position.partition("-")
    anchors = 0
    left = top = right = bottom = 0
    if vertical == "top":
        anchors |= ANCHOR_TOP
        top = margin
    elif vertical == "bottom":
        anchors |= ANCHOR_BOTTOM
        bottom = margin
    if horizontal == "left":
        anchors |= ANCHOR_LEFT
        left = margin
    elif horizontal == "right":
        anchors |= ANCHOR_RIGHT
        right = margin
    # "center"/"middle" without an axis anchor is centered by the compositor.
    return anchors, QMargins(left, top, right, bottom)
