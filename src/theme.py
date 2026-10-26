"""Modern light/dark application theme.

The GUI intentionally uses one global stylesheet instead of native-looking
Fusion frames: flat cards, rounded inputs, a restrained accent colour and
crisp vector-like icons generated at runtime for the current palette.  The
palette is also applied to Qt so dialogs, menus and native controls stay in
sync with the stylesheet.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from string import Template

from PySide6.QtCore import QPointF, QStandardPaths, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication

THEME_MODES = ("dark", "light", "system")
THEME_LABELS = {
    "dark": "Dark",
    "light": "Light",
    "system": "System",
}


@dataclass(frozen=True)
class ThemeColors:
    window: str
    surface: str
    surface_hover: str
    base: str
    text: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    accent_text: str
    warning: str


DARK = ThemeColors(
    window="#16181d",
    surface="#1e2128",
    surface_hover="#262a33",
    base="#111317",
    text="#eef1f6",
    muted="#8b93a1",
    border="#2c313b",
    accent="#5b8cff",
    accent_hover="#709bff",
    accent_text="#ffffff",
    warning="#e5a50a",
)

LIGHT = ThemeColors(
    window="#f5f6f8",
    surface="#ffffff",
    surface_hover="#eef1f5",
    base="#ffffff",
    text="#1c2027",
    muted="#6b7280",
    border="#d9dde4",
    accent="#2f6fed",
    accent_hover="#1f5fe0",
    accent_text="#ffffff",
    warning="#b77900",
)


def resolved_theme(mode: str) -> str:
    """Return the concrete palette for a persisted theme mode."""
    if mode in ("dark", "light"):
        return mode
    if QGuiApplication.instance() is None:
        return "dark"
    hints = QGuiApplication.styleHints()
    try:
        scheme = hints.colorScheme()
    except AttributeError:  # pragma: no cover - old Qt
        scheme = Qt.ColorScheme.Unknown
    if scheme == Qt.ColorScheme.Light:
        return "light"
    return "dark"


def colors_for(mode: str) -> ThemeColors:
    return LIGHT if resolved_theme(mode) == "light" else DARK


def warning_color() -> str:
    """Accent colour for inline warnings in the currently applied theme."""
    app = QApplication.instance()
    concrete = app.property("gamohudTheme") if app is not None else None
    return LIGHT.warning if concrete == "light" else DARK.warning


def _font_family() -> str:
    """Pick a modern sans-serif that exists on the current machine."""
    preferred = (
        "Inter",
        "SF Pro Display",
        "Segoe UI Variable Display",
        "Segoe UI",
        "Noto Sans",
        "Carlito",
        "Ubuntu",
        "Cantarell",
        "Liberation Sans",
        "DejaVu Sans",
    )
    families = set(QFontDatabase.families())
    for name in preferred:
        if name in families:
            return name
    return QApplication.font().family()


def _palette(colors: ThemeColors) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors.window))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors.base))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.surface))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.surface))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors.surface))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.accent_text))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors.accent))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors.muted))
    palette.setColor(QPalette.ColorRole.Mid, QColor(colors.border))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(colors.surface_hover))
    palette.setColor(QPalette.ColorRole.Dark, QColor(colors.border))
    palette.setColor(QPalette.ColorRole.Light, QColor(colors.window))

    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(disabled, role, QColor(colors.muted))
    palette.setColor(disabled, QPalette.ColorRole.Base, QColor(colors.surface))
    palette.setColor(disabled, QPalette.ColorRole.Button, QColor(colors.surface))
    return palette


def _icon_dir() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.CacheLocation
    )
    root = Path(base) if base else Path(tempfile.gettempdir())
    path = root / "gamohud" / "theme"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:  # pragma: no cover - read-only cache
        path = Path(tempfile.gettempdir()) / "gamohud-theme"
        path.mkdir(parents=True, exist_ok=True)
    return path


def _draw_icon(path: Path, color: str, kind: str) -> str:
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(4.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    if kind == "check":
        painter.drawPolyline(
            [QPointF(11, 25), QPointF(20, 34), QPointF(37, 14)]
        )
    elif kind == "up":
        painter.drawPolyline(
            [QPointF(13, 29), QPointF(24, 18), QPointF(35, 29)]
        )
    else:
        painter.drawPolyline(
            [QPointF(13, 19), QPointF(24, 30), QPointF(35, 19)]
        )
    painter.end()
    pixmap.save(str(path), "PNG")
    return path.as_posix()


def _icons(colors: ThemeColors, concrete: str) -> dict[str, str]:
    root = _icon_dir()
    return {
        "down": _draw_icon(root / f"chevron-down-{concrete}.png", colors.muted, "down"),
        "up": _draw_icon(root / f"chevron-up-{concrete}.png", colors.muted, "up"),
        "check": _draw_icon(
            root / f"check-{concrete}.png", colors.accent_text, "check"
        ),
    }


_QSS = Template(
    """
    QWidget {
        color: $text;
    }
    QMainWindow, QDialog {
        background: $window;
    }
    QToolTip {
        color: $text;
        background: $surface;
        border: 1px solid $border;
        border-radius: 6px;
        padding: 4px 7px;
    }

    /* navigation */
    QTabWidget::pane {
        border: none;
        background: $window;
    }
    QTabBar {
        background: transparent;
    }
    QTabBar::tab {
        background: transparent;
        color: $muted;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 9px 16px;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        color: $text;
    }
    QTabBar::tab:selected {
        color: $text;
        border-bottom: 2px solid $accent;
    }

    /* cards */
    QGroupBox {
        background: $surface;
        border: 1px solid $border;
        border-radius: 12px;
        margin-top: 14px;
        padding-top: 5px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        background: $window;
        color: $text;
        font-weight: 600;
    }
    QFrame#metricTile {
        background: $surface;
        border: 1px solid $border;
        border-radius: 12px;
    }
    QFrame#statusBanner {
        border-radius: 10px;
    }

    /* form controls */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
        background: $base;
        border: 1px solid $border;
        border-radius: 8px;
        padding: 5px 8px;
        min-height: 20px;
        selection-background-color: $accent;
        selection-color: $accent_text;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus, QPlainTextEdit:focus {
        border: 1px solid $accent;
    }
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
    QDoubleSpinBox:disabled, QPlainTextEdit:disabled {
        color: $muted;
        background: $surface;
    }
    QLineEdit:hover, QPlainTextEdit:hover {
        border-color: $muted;
    }
    QComboBox {
        padding-right: 28px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 26px;
        border: none;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: url("$icon_down");
        width: 11px;
        height: 11px;
    }
    QComboBox QAbstractItemView {
        background: $surface;
        border: 1px solid $border;
        border-radius: 8px;
        padding: 4px;
        outline: 0;
        selection-background-color: $accent;
        selection-color: $accent_text;
    }
    QComboBox QAbstractItemView::item {
        min-height: 24px;
        padding: 2px 7px;
        border-radius: 5px;
    }
    QSpinBox, QDoubleSpinBox {
        padding-right: 24px;
    }
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border: none;
        border-left: 1px solid $border;
        border-top-right-radius: 8px;
        background: transparent;
    }
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border: none;
        border-left: 1px solid $border;
        border-bottom-right-radius: 8px;
        background: transparent;
    }
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background: $surface_hover;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: url("$icon_up");
        width: 8px;
        height: 8px;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: url("$icon_down");
        width: 8px;
        height: 8px;
    }

    /* buttons */
    QPushButton {
        background: $surface;
        color: $text;
        border: 1px solid $border;
        border-radius: 8px;
        padding: 6px 14px;
        min-height: 20px;
    }
    QPushButton:hover {
        background: $surface_hover;
        border-color: $muted;
    }
    QPushButton:pressed {
        background: $base;
    }
    QPushButton:disabled {
        color: $muted;
        background: $surface;
    }
    QPushButton:default {
        border: 1px solid $accent;
    }
    QPushButton#primary {
        background: $accent;
        color: $accent_text;
        border: 1px solid $accent;
        font-weight: 600;
    }
    QPushButton#primary:hover {
        background: $accent_hover;
        border-color: $accent_hover;
    }
    QPushButton#primary:pressed {
        background: $accent;
    }
    QPushButton:flat {
        background: transparent;
        border: none;
        color: $accent;
        padding: 4px 9px;
    }
    QPushButton:flat:hover {
        background: $surface_hover;
        border-radius: 7px;
    }

    /* checkboxes */
    QCheckBox {
        spacing: 8px;
        background: transparent;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid $border;
        border-radius: 4px;
        background: $base;
    }
    QCheckBox::indicator:hover {
        border-color: $accent;
    }
    QCheckBox::indicator:checked {
        background: $accent;
        border-color: $accent;
        image: url("$icon_check");
    }
    QCheckBox::indicator:checked:disabled {
        background: $muted;
        border-color: $muted;
    }

    /* lists */
    QListWidget {
        background: $base;
        border: 1px solid $border;
        border-radius: 10px;
        padding: 5px;
        outline: 0;
    }
    QListWidget::item {
        color: $text;
        padding: 7px 8px;
        border-radius: 6px;
    }
    QListWidget::item:hover {
        background: $surface_hover;
    }
    QListWidget::item:selected {
        background: $accent;
        color: $accent_text;
    }

    /* scrolling */
    QScrollArea {
        border: none;
        background: transparent;
    }
    QScrollArea > QWidget > QWidget {
        background: transparent;
    }
    QScrollBar:vertical {
        background: transparent;
        width: 10px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: $border;
        min-height: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: $muted;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 10px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: $border;
        min-width: 30px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover {
        background: $muted;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        width: 0;
        height: 0;
        background: transparent;
    }
    QScrollBar::add-page, QScrollBar::sub-page {
        background: transparent;
    }

    /* menus / status */
    QMenu {
        background: $surface;
        border: 1px solid $border;
        border-radius: 9px;
        padding: 5px;
    }
    QMenu::item {
        padding: 6px 24px 6px 12px;
        border-radius: 6px;
    }
    QMenu::item:selected {
        background: $accent;
        color: $accent_text;
    }
    QMenu::separator {
        height: 1px;
        background: $border;
        margin: 4px 8px;
    }
    QStatusBar {
        background: $window;
        color: $muted;
        border-top: 1px solid $border;
    }
    QStatusBar::item {
        border: none;
    }
    """
)


def apply_theme(app: QApplication | None, mode: str = "dark") -> str:
    """Apply the global theme and return the concrete palette name."""
    if app is None:
        return "dark"
    concrete = resolved_theme(mode)
    colors = LIGHT if concrete == "light" else DARK
    icons = _icons(colors, concrete)

    app.setStyle("Fusion")
    app.setPalette(_palette(colors))

    family = _font_family()
    font = QFont(family, 10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    app.setStyleSheet(
        _QSS.substitute(
            window=colors.window,
            surface=colors.surface,
            surface_hover=colors.surface_hover,
            base=colors.base,
            text=colors.text,
            muted=colors.muted,
            border=colors.border,
            accent=colors.accent,
            accent_hover=colors.accent_hover,
            accent_text=colors.accent_text,
            warning=colors.warning,
            icon_down=icons["down"],
            icon_up=icons["up"],
            icon_check=icons["check"],
        )
    )
    app.setProperty("gamohudTheme", concrete)
    return concrete
