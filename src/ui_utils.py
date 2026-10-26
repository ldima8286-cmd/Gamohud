"""Small shared Qt widgets and helpers used by the gamohud tabs.

Everything here is deliberately theme-aware: colors are taken from the
application palette (Fusion dark/light, Windows, KDE, ...), so the GUI keeps
looking native instead of shipping a hard-coded theme.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.i18n import tr


def _color(role: QPalette.ColorRole) -> QColor:
    return QApplication.palette().color(role)


def muted_color() -> str:
    """Theme-aware color for secondary text."""
    return _color(QPalette.ColorRole.PlaceholderText).name()


def _border_color() -> str:
    return _color(QPalette.ColorRole.Mid).name()


def apply_app_style() -> None:
    """Comfortable padding for form controls and tabs (theme-neutral)."""
    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(
        """
        QLineEdit, QComboBox, QPlainTextEdit {
            padding: 4px 6px;
        }
        QPushButton {
            padding: 5px 12px;
        }
        QListWidget {
            padding: 4px;
        }
        QTabBar::tab {
            padding: 7px 16px;
        }
        QTabWidget::pane {
            border: none;
        }
        """
    )


def page_header(title: str, subtitle: str = "") -> QWidget:
    """Large tab title with an optional muted one-line description."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    heading = QLabel(title)
    font = heading.font()
    font.setPointSizeF(max(15.0, font.pointSizeF() * 1.5))
    font.setWeight(QFont.DemiBold)
    heading.setFont(font)
    layout.addWidget(heading)

    if subtitle:
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {muted_color()};")
        layout.addWidget(sub)
    return box


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setWeight(QFont.DemiBold)
    label.setFont(font)
    return label


def form_label(text: str) -> QLabel:
    """Right-aligned label for QGridLayout-based forms."""
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return label


def hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {muted_color()}; font-size: 90%;")
    return label


def group_box(title: str) -> QGroupBox:
    """QGroupBox with a visible rounded frame on dark Fusion themes."""
    box = QGroupBox(title)
    box.setStyleSheet(
        f"QGroupBox {{ border: 1px solid {_border_color()}; border-radius: 8px;"
        f" margin-top: 10px; padding-top: 6px; }}"
        f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}"
    )
    return box


class MetricTile(QFrame):
    """Compact label/value card used on the dashboard."""

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("metricTile")
        self.setMinimumHeight(62)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            f"QFrame#metricTile {{ background: {_color(QPalette.ColorRole.AlternateBase).name()};"
            f" border: 1px solid {_border_color()}; border-radius: 9px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(2)

        self.name = QLabel(label)
        name_font = self.name.font()
        name_font.setPointSizeF(max(8.0, name_font.pointSizeF() * 0.9))
        name_font.setWeight(QFont.Medium)
        self.name.setFont(name_font)
        self.name.setStyleSheet(f"color: {muted_color()};")

        self.value = QLabel("--")
        value_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        value_font.setPointSizeF(max(13.0, value_font.pointSizeF() * 1.25))
        value_font.setWeight(QFont.DemiBold)
        self.value.setFont(value_font)
        self.value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(self.name)
        layout.addWidget(self.value, 1)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class StatusBanner(QFrame):
    """Inline warning with an action button (used for unavailable FPS)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("statusBanner")
        self.setStyleSheet(
            "QFrame#statusBanner { background: rgba(229, 165, 10, 32);"
            " border: 1px solid rgba(229, 165, 10, 120); border-radius: 8px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)

        self.icon = QLabel("\u26a0")
        self.text = QLabel("")
        self.text.setWordWrap(True)
        self.button = QPushButton(tr("Open Settings"))
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.text, 1)
        layout.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hide()

    def set_message(self, message: str) -> None:
        self.text.setText(message)
        self.show()


def color_swatch(value: str) -> QIcon:
    color = QColor(value if value else "#000000")
    if not color.isValid():
        color = QColor("#000000")
    pixmap = QPixmap(14, 14)
    pixmap.fill(color)
    painter = QPainter(pixmap)
    painter.setPen(QColor(120, 120, 120, 200))
    painter.drawRect(0, 0, 13, 13)
    painter.end()
    return QIcon(pixmap)


def color_button(initial: str, parent: QWidget | None = None) -> QPushButton:
    """Button that shows the current colour and opens QColorDialog."""
    btn = QPushButton(parent)
    btn.setMinimumWidth(96)
    btn.setIconSize(QSize(14, 14))

    def apply(value: str) -> None:
        color = QColor(value if value else "#000000")
        if not color.isValid():
            color = QColor("#000000")
        btn._value = color.name()
        btn.setText(color.name())
        btn.setIcon(color_swatch(color.name()))
        btn.setToolTip(tr("Pick a color"))

    def pick() -> None:
        chosen = QColorDialog.getColor(QColor(btn._value), btn, tr("Pick a color"))
        if chosen.isValid():
            apply(chosen.name())

    btn._set_value = apply  # type: ignore[attr-defined]
    btn.clicked.connect(pick)
    apply(initial)
    return btn
