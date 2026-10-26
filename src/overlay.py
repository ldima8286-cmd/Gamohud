"""Standalone, profile-driven always-on-top overlay window (no MangoHud)."""
from __future__ import annotations

import uuid
from collections import deque

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.metrics import format_metric, metric_label, metric_unit
from src.profiles import OverlayProfile


def _hex_to_rgb(value, default=(16, 16, 20)):
    v = (value or "").lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except Exception:
        return default


def _rgba(value, alpha, default=(16, 16, 20)) -> str:
    r, g, b = _hex_to_rgb(value, default)
    a = int(max(0.0, min(1.0, alpha)) * 255)
    return f"rgba({r},{g},{b},{a})"


def overlay_position(profile: OverlayProfile, width: int, height: int, geo) -> tuple[int, int]:
    """Return a safe global top-left for the overlay inside *geo*.

    The profile can contain stale/garbage custom coordinates (for example
    ``10000, 10000``), so custom positions are validated here.  A position that
    is nowhere near the screen falls back to the top-left margin; a partially
    off-screen one is clamped so at least the whole overlay stays reachable.
    """
    w = max(1, int(width))
    h = max(1, int(height))
    margin = max(0, int(getattr(profile, "margin", 0) or 0))
    pos = getattr(profile, "position", "top-left") or "top-left"

    if pos == "custom":
        raw_x = int(getattr(profile, "x", 0) or 0)
        raw_y = int(getattr(profile, "y", 0) or 0)
        # Saved coordinates are relative to the primary screen.  Reject values
        # that cannot possibly be on it instead of clamping to a far corner.
        if (
            raw_x < -w
            or raw_y < -h
            or raw_x > geo.width() + w
            or raw_y > geo.height() + h
        ):
            x, y = geo.left() + margin, geo.top() + margin
        else:
            x, y = geo.left() + raw_x, geo.top() + raw_y
    else:
        if pos == "center":
            vert, horiz = "middle", "center"
        else:
            vert, _, horiz = pos.partition("-")
            if not horiz:
                vert, horiz = "top", "left"
            if vert not in ("top", "middle", "bottom"):
                vert = "top"
            if horiz not in ("left", "center", "right"):
                horiz = "left"

        cols = {
            "left": geo.left() + margin,
            "center": geo.center().x() - w // 2,
            "right": geo.right() - w + 1 - margin,
        }
        rows = {
            "top": geo.top() + margin,
            "middle": geo.center().y() - h // 2,
            "bottom": geo.bottom() - h + 1 - margin,
        }
        x = cols[horiz]
        y = rows[vert]

    max_x = max(geo.left(), geo.right() - w + 1)
    max_y = max(geo.top(), geo.bottom() - h + 1)
    return min(max(x, geo.left()), max_x), min(max(y, geo.top()), max_y)


class Sparkline(QWidget):
    def __init__(self, points: int = 60, color: str = "#7CFC00", parent=None):
        super().__init__(parent)
        self._values = deque([0.0] * points, maxlen=points)
        self._color = color
        self.setMinimumHeight(28)

    def set_color(self, color: str):
        self._color = color
        self.update()

    def push(self, value):
        self._values.append(float(value or 0.0))
        self.update()

    def paintEvent(self, event):
        if not self._values:
            return
        w, h = self.width(), self.height()
        vmax = max(max(self._values), 60.0)
        n = len(self._values)
        poly = QPolygonF()
        for i, val in enumerate(self._values):
            x = w * i / max(1, n - 1)
            y = h - (val / vmax) * (h - 2) - 1
            poly.append(QPointF(x, y))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(self._color))
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.drawPolyline(poly)


class OverlayWindow(QWidget):
    def __init__(self, profile: OverlayProfile, data_provider, window_title: str | None = None):
        super().__init__(None)
        self._data_provider = data_provider
        self.profile = profile
        self._rows: dict[str, tuple[QLabel, QLabel]] = {}

        # A unique title prevents a KWin script left over from an earlier run
        # (or another instance) from matching and moving this window.
        self._overlay_title = window_title or f"gamohud-hud-{uuid.uuid4().hex[:12]}"
        self.setWindowTitle(self._overlay_title)

        # Locked == click-through (mouse passes to the game). Unlocked makes the
        # window interactive so it can be dragged with the mouse.
        self.locked = bool(getattr(profile, "click_through", True))
        self.on_position_changed = None
        self.external_position = False
        self._drag_offset = None
        self._system_moving = False
        self._programmatic_move = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._emit_position_changed)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._apply_window_flags()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 1)

        self.container = QWidget(self)
        self.container.setObjectName("hud")
        self.container.setGraphicsEffect(shadow)

        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(14, 10, 14, 10)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(3)

        self.spark = Sparkline(color=profile.accent_color)
        self.spark.setVisible(bool(profile.graph))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.container)

        self._build_rows()
        self._apply_style()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(max(100, int(profile.refresh_ms)))

    # -- window / wayland -------------------------------------------------
    def _desired_flags(self):
        """Window flags that must never change while the overlay is visible.

        Changing the window type or toggling ``Qt.Tool``/``Qt.Window`` via
        ``QWidget.setWindowFlags()`` re-maps the Wayland surface, and KWin then
        places it at its default position.  Locking/unlocking therefore used to
        reset a custom drag position.  Click-through is toggled separately on
        the existing QWindow, which only changes ``wl_surface.set_input_region``
        and keeps the surface (and its compositor-owned position) alive.
        """
        return (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
            | Qt.Window
        )

    def _apply_input_transparency(self):
        """Toggle click-through on the live window without re-mapping it."""
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.locked)
        handle = self.windowHandle()
        if handle is None:
            return
        currently_transparent = bool(handle.flags() & Qt.WindowTransparentForInput)
        if currently_transparent != self.locked:
            handle.setFlag(Qt.WindowTransparentForInput, self.locked)

    def _apply_window_flags(self):
        """Apply base flags once, then keep the native surface stable."""
        flags = self._desired_flags()
        if self.windowFlags() != flags:
            was_visible = self.isVisible()
            self.setWindowFlags(flags)
            if was_visible:
                self.show()
                self.raise_()
                self._restore_position()
        self._apply_input_transparency()

    def showEvent(self, event):
        super().showEvent(event)
        # The native QWindow exists only after the first show; apply the
        # click-through state now without re-creating the surface.
        self._apply_input_transparency()

    def _restore_position(self):
        """Re-apply the saved position after a rare window re-map."""
        if self._drag_offset is not None or self._system_moving:
            return
        self._reposition(force=True)

    def set_locked(self, locked: bool):
        """Lock (click-through, cannot be dragged) or unlock the overlay."""
        locked = bool(locked)
        changed = locked != self.locked
        self.locked = locked
        self._apply_window_flags()
        if changed:
            self._apply_style()
            self.setCursor(Qt.ArrowCursor if locked else Qt.SizeAllCursor)

    # -- mouse dragging ---------------------------------------------------
    def mousePressEvent(self, event):
        if not self.locked and event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._system_moving = False
            handle = self.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove"):
                try:
                    self._system_moving = bool(handle.startSystemMove())
                except Exception:
                    self._system_moving = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Manual fallback for platforms where startSystemMove() is unavailable.
        if (not self.locked and not self._system_moving
                and self._drag_offset is not None and event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (not self.locked and event.button() == Qt.LeftButton
                and (self._drag_offset is not None or self._system_moving)):
            self._drag_offset = None
            self._system_moving = False
            self._commit_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._programmatic_move or self.locked:
            return
        if self._drag_offset is None and not self._system_moving:
            return
        self._update_profile_position()
        self._save_timer.start()

    def _update_profile_position(self):
        if self.external_position:
            # Wayland does not expose the real window position to the client.
            # KWin reports the geometry over D-Bus instead; don't overwrite it
            # with Qt's 0/0 fallback on release.
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.profile.position = "custom"
        max_x = max(0, geo.width() - self.width())
        max_y = max(0, geo.height() - self.height())
        self.profile.x = min(max(self.x() - geo.left(), 0), max_x)
        self.profile.y = min(max(self.y() - geo.top(), 0), max_y)

    def _commit_position(self):
        self._update_profile_position()
        self._emit_position_changed()

    def _emit_position_changed(self):
        self._system_moving = False
        if callable(self.on_position_changed):
            self.on_position_changed()

    def _try_layer_shell(self) -> bool:
        """Best-effort: real always-on-top over fullscreen needs a layer-shell
        surface. PySide6 has no layer-shell binding, so we only succeed if a
        helper is present; otherwise the always-on-top window is the fallback."""
        return False

    # -- layout -----------------------------------------------------------
    def _build_rows(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None and w is not self.spark:
                w.setParent(None)
                w.deleteLater()
        self._rows.clear()

        self.grid.addWidget(self.spark, 0, 0, 1, 2)
        row = 1
        for key in self.profile.metrics:
            name = QLabel(metric_label(key))
            name.setTextFormat(Qt.PlainText)
            value = QLabel("--")
            value.setTextFormat(Qt.PlainText)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.grid.addWidget(name, row, 0)
            self.grid.addWidget(value, row, 1)
            self._rows[key] = (name, value)
            row += 1

    def _apply_style(self):
        p = self.profile
        weight = "700" if p.font_bold else "400"
        for _key, (name, value) in self._rows.items():
            name.setStyleSheet(
                f"color: {p.label_color}; font-size: {p.font_size}px; font-weight: {weight};"
                f" letter-spacing: 1px;"
            )
            value.setStyleSheet(
                f"color: {p.fg_color}; font-size: {p.font_size}px; font-weight: {weight};"
            )
        border = _rgba(p.bg_color, min(1.0, p.bg_opacity + 0.3))
        if not self.locked:
            border = p.accent_color
        self.container.setStyleSheet(
            f"#hud {{ background: {_rgba(p.bg_color, p.bg_opacity)};"
            f" border-radius: {p.border_radius}px;"
            f" border: {'2px dashed' if not self.locked else '1px solid'} {border}; }}"
        )
        f = QFont(p.font_family or "Monospace")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(max(7, int(p.font_size * 0.8)))
        self.container.setFont(f)
        self.spark.setVisible(bool(p.graph))
        self.spark.set_color(p.accent_color)
        self.adjustSize()

    # -- data -------------------------------------------------------------
    def refresh(self):
        try:
            data = self._data_provider() or {}
        except Exception:
            data = {}
        for key, (_name, value) in self._rows.items():
            text = format_metric(key, data.get(key))
            if text is None:
                value.setText("--")
            else:
                unit = metric_unit(key)
                value.setText(f"{text} {unit}".strip())
        if self.profile.graph:
            fps = data.get("fps")
            if fps is not None:
                self.spark.push(fps)
        self.adjustSize()
        if self._drag_offset is None and not self._system_moving:
            self._reposition()
        self.raise_()

    def _reposition(self, force: bool = False):
        if self._drag_offset is not None or self._system_moving:
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        if self.profile.position == "custom" and not force:
            # Wayland ignores move(): the compositor owns the position, so once
            # the user has dragged the overlay we must not fight it.
            return
        x, y = overlay_position(self.profile, self.width(), self.height(), geo)
        self._programmatic_move = True
        self.move(x, y)
        self._programmatic_move = False

    # -- public -----------------------------------------------------------
    def set_profile(self, profile: OverlayProfile):
        self.profile = profile
        self.timer.setInterval(max(100, int(profile.refresh_ms)))
        self._apply_window_flags()
        self._build_rows()
        self._apply_style()
        self.refresh()
        self._reposition(force=True)
        if not self.isVisible():
            self.show()
        self.raise_()

    def apply_profile(self, profile: OverlayProfile):
        self.set_profile(profile)
