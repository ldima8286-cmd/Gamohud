"""Standalone, profile-driven always-on-top overlay window (no MangoHud)."""
from __future__ import annotations

import os
from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtCore import QPointF
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
    def __init__(self, profile: OverlayProfile, data_provider):
        super().__init__(None)
        self._data_provider = data_provider
        self.profile = profile
        self._rows: dict[str, tuple[QLabel, QLabel]] = {}

        # Locked == click-through (mouse passes to the game). Unlocked makes the
        # window interactive so it can be dragged with the mouse.
        self.locked = bool(getattr(profile, "click_through", True))
        self.on_position_changed = None
        self._drag_offset = None

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
        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        if self.locked:
            flags |= Qt.WindowTransparentForInput
        return flags

    def _apply_window_flags(self):
        """Only touch window flags when they actually change.

        Calling setWindowFlags() on a visible window hides and re-maps it; on
        Wayland the re-mapped surface can end up behind other windows, which is
        what made the overlay "disappear" after saving/switching a profile.
        """
        flags = self._desired_flags()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.locked)
        if self.windowFlags() == flags:
            return
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()
            self.raise_()

    def set_locked(self, locked: bool):
        """Lock (click-through, cannot be dragged) or unlock the overlay."""
        locked = bool(locked)
        if locked == self.locked:
            return
        self.locked = locked
        self._apply_window_flags()
        self._apply_style()
        self.setCursor(Qt.ArrowCursor if locked else Qt.SizeAllCursor)
        if not locked:
            self.show()
            self.raise_()

    # -- mouse dragging ---------------------------------------------------
    def mousePressEvent(self, event):
        if not self.locked and event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.locked and self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.locked and event.button() == Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            screen = QApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                self.profile.position = "custom"
                self.profile.x = self.x() - geo.left()
                self.profile.y = self.y() - geo.top()
            if callable(self.on_position_changed):
                self.on_position_changed()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

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
        for key, (name, value) in self._rows.items():
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
        self._reposition()
        self.raise_()

    def _reposition(self):
        if self._drag_offset is not None:
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        m = self.profile.margin
        pos = self.profile.position
        if pos == "custom":
            x, y = geo.left() + self.profile.x, geo.top() + self.profile.y
        else:
            cols = {
                "left": geo.left() + m,
                "center": geo.center().x() - w // 2,
                "right": geo.right() - w - m,
            }
            rows = {
                "top": geo.top() + m,
                "middle": geo.center().y() - h // 2,
                "bottom": geo.bottom() - h - m,
            }
            vert, _, horiz = pos.partition("-")
            x = cols.get(horiz or "left", cols["left"])
            y = rows.get(vert, rows["top"])
        self.move(x, y)

    # -- public -----------------------------------------------------------
    def set_profile(self, profile: OverlayProfile):
        self.profile = profile
        self.timer.setInterval(max(100, int(profile.refresh_ms)))
        self._apply_window_flags()
        self._build_rows()
        self._apply_style()
        self.refresh()
        if not self.isVisible():
            self.show()
        self.raise_()

    def apply_profile(self, profile: OverlayProfile):
        self.set_profile(profile)
