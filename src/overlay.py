from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication, QGraphicsDropShadowEffect

from src.monitor import get_stats
from src.fps import get_fps


class OverlayWindow(QWidget):
    def __init__(self, settings):
        super().__init__(None)
        self.settings = settings
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if settings.click_through:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setWindowFlag(Qt.WindowTransparentForInput, True)

        self.labels = {}
        for key in ("title", "fps", "cpu", "gpu", "vram", "ram", "temp"):
            lb = QLabel("")
            lb.setTextFormat(Qt.PlainText)
            self.labels[key] = lb

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 1)

        self.container = QWidget(self)
        self.container.setObjectName("hud")
        lay = QVBoxLayout(self.container)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        for key in ("title", "fps", "cpu", "gpu", "vram", "ram", "temp"):
            lay.addWidget(self.labels[key])
        self.container.setGraphicsEffect(shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.container)

        self._apply_style()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(max(100, int(settings.refresh_ms)))

    def _apply_style(self):
        s = self.settings
        self.labels["title"].setText("GAMOHUD")
        self.labels["title"].setStyleSheet(
            f"color: {s.accent_color}; font-weight: 700; letter-spacing: 1px;"
            f" font-size: {s.font_size}px;"
        )
        for key in ("fps", "cpu", "gpu", "vram", "ram", "temp"):
            self.labels[key].setStyleSheet(
                f"color: {s.font_color}; font-size: {s.font_size}px;"
            )
        r, g, b = _hex_to_rgb(s.bg_color)
        a = int(max(0.0, min(1.0, s.opacity)) * 255)
        self.container.setStyleSheet(
            f"#hud {{ background: rgba({r},{g},{b},{a}); border-radius: 10px;"
            f" border: 1px solid rgba({r},{g},{b},255); }}"
        )
        f = QFont("Monospace")
        f.setStyleHint(QFont.Monospace)
        f.setPointSize(max(7, int(s.font_size * 0.8)))
        self.container.setFont(f)

    def refresh(self):
        st = get_stats()
        s = self.settings
        fps = get_fps(s)
        self.labels["fps"].setText(f"FPS    {fps if fps is not None else '--'}")
        self.labels["cpu"].setText(f"CPU    {st['cpu']}%")
        gl = st.get("gpu_load")
        self.labels["gpu"].setText(f"GPU    {gl}%" if gl is not None else "GPU    N/A")
        vu, vt = st.get("vram_used"), st.get("vram_total")
        if vu is not None and vt is not None:
            self.labels["vram"].setText(f"VRAM   {vu}/{vt} GB")
        else:
            self.labels["vram"].setText("VRAM   N/A")
        self.labels["ram"].setText(f"RAM    {st['ram_used']}/{st['ram_total']} GB")
        t = st.get("temp")
        self.labels["temp"].setText(f"TEMP   {t}\u00b0C" if t is not None else "TEMP   N/A")

        for key, vis in (
            ("fps", s.show_fps),
            ("cpu", s.show_cpu),
            ("gpu", s.show_gpu),
            ("vram", s.show_vram),
            ("ram", s.show_ram),
            ("temp", s.show_temp),
        ):
            self.labels[key].setVisible(bool(vis))

        self.adjustSize()
        self._reposition()

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        w, h = self.width(), self.height()
        m = self.settings.margin
        pos = self.settings.position
        if pos == "top-left":
            x, y = geo.left() + m, geo.top() + m
        elif pos == "top-right":
            x, y = geo.right() - w - m, geo.top() + m
        elif pos == "bottom-left":
            x, y = geo.left() + m, geo.bottom() - h - m
        elif pos == "bottom-right":
            x, y = geo.right() - w - m, geo.bottom() - h - m
        elif pos == "center":
            x, y = geo.center().x() - w // 2, geo.center().y() - h // 2
        else:
            x, y = geo.right() - w - m, geo.top() + m
        self.move(x, y)

    def apply_settings(self, settings):
        self.settings = settings
        self.timer.setInterval(max(100, int(settings.refresh_ms)))
        self.setWindowFlag(Qt.WindowTransparentForInput, bool(settings.click_through))
        self.setAttribute(Qt.WA_TransparentForMouseEvents, bool(settings.click_through))
        self._apply_style()
        self.refresh()
        self.show()


def _hex_to_rgb(value):
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except Exception:
        return 16, 16, 20
