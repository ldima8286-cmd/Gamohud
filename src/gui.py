import os
import sys
import shlex
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QColorDialog,
    QMessageBox,
    QInputDialog,
    QSystemTrayIcon,
    QMenu,
    QGroupBox,
    QFormLayout,
)

from src.monitor import get_stats
from src.settings import Settings, set_mangohud_logging
from src.games import all_games, save_manual_game
from src.game_bindings import load_bindings, save_bindings, Binding, get_binding
from src.gamemode import load_profiles
from src.overlay import OverlayWindow

MANGOHUD_DIR = Path.home() / ".config" / "MangoHud"


def _hex_to_rgb(value):
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except Exception:
        return 16, 16, 20


class DashboardTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.labels = {}
        lay = QVBoxLayout(self)
        for key, text in (
            ("cpu", "CPU"),
            ("load1", "Load1"),
            ("ram", "RAM"),
            ("swap", "Swap"),
            ("temp", "CPU Temp"),
            ("gpu_load", "GPU Load"),
            ("gpu_temp", "GPU Temp"),
            ("vram", "VRAM"),
            ("fps", "FPS"),
        ):
            lb = QLabel(f"{text}: --")
            lay.addWidget(lb)
            self.labels[key] = lb
        lay.addStretch(1)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(700)

    def update(self):
        st = get_stats()
        self.labels["cpu"].setText(f"CPU: {st['cpu']}%")
        self.labels["load1"].setText(f"Load1: {st.get('load1', '-')}")
        self.labels["ram"].setText(f"RAM: {st['ram_used']}/{st['ram_total']} GB ({st['ram_percent']}%)")
        self.labels["swap"].setText(f"Swap: {st['swap_percent']}%")
        t = st.get("temp")
        self.labels["temp"].setText(f"CPU Temp: {t}\u00b0C" if t is not None else "CPU Temp: N/A")
        gl = st.get("gpu_load")
        self.labels["gpu_load"].setText(f"GPU Load: {gl}%" if gl is not None else "GPU Load: N/A")
        gt = st.get("gpu_temp")
        self.labels["gpu_temp"].setText(f"GPU Temp: {gt}\u00b0C" if gt is not None else "GPU Temp: N/A")
        vu, vt = st.get("vram_used"), st.get("vram_total")
        if vu is not None and vt is not None:
            self.labels["vram"].setText(f"VRAM: {vu}/{vt} GB")
        elif vu is not None:
            self.labels["vram"].setText(f"VRAM: {vu} GB")
        else:
            self.labels["vram"].setText("VRAM: N/A")
        try:
            from src.fps import get_fps
            fps = get_fps(self.app.settings)
            self.labels["fps"].setText(f"FPS: {fps}" if fps is not None else "FPS: --")
        except Exception:
            self.labels["fps"].setText("FPS: --")


class PresetsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = None
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter presets...")
        self.filter.textChanged.connect(self.reload)
        top.addWidget(self.filter)
        root.addLayout(top)

        mid = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        mid.addWidget(self.list, 1)
        self.editor = QPlainTextEdit()
        mid.addWidget(self.editor, 2)
        root.addLayout(mid, 1)

        btns = QHBoxLayout()
        for text, slot in (
            ("Apply to MangoHud.conf", self.apply),
            ("Save", self.save_current),
            ("New from current", self.new_from_current),
            ("Delete", self.delete),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        root.addLayout(btns)
        self.reload()

    def reload(self):
        self.list.clear()
        filt = self.filter.text().lower().strip()
        MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
        for f in sorted(MANGOHUD_DIR.glob("*.conf")):
            if not filt or filt in f.name.lower():
                it = QListWidgetItem(f.name)
                it.setData(Qt.UserRole, str(f))
                self.list.addItem(it)

    def on_select(self, row):
        if row < 0:
            self.current = None
            return
        it = self.list.item(row)
        self.current = Path(it.data(Qt.UserRole))
        try:
            self.editor.setPlainText(self.current.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            self.editor.setPlainText("")

    def apply(self):
        try:
            from src.restore import backup_conf
            backup_conf()
            target = MANGOHUD_DIR / "MangoHud.conf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.app.status.showMessage("Applied to MangoHud.conf (backup saved)", 4000)
        except Exception as e:
            self.app.status.showMessage(f"Error: {e}", 6000)

    def save_current(self):
        if not self.current:
            return
        try:
            self.current.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.app.status.showMessage(f"Saved {self.current.name}", 4000)
        except Exception as e:
            self.app.status.showMessage(f"Error: {e}", 6000)

    def new_from_current(self):
        name, ok = QInputDialog.getText(self, "New preset", "File name (.conf):")
        if not ok or not name.strip():
            return
        if not name.endswith(".conf"):
            name += ".conf"
        p = MANGOHUD_DIR / name
        try:
            p.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.reload()
        except Exception as e:
            self.app.status.showMessage(f"Error: {e}", 6000)

    def delete(self):
        if not self.current:
            return
        if QMessageBox.question(self, "Delete", f"Delete {self.current.name}?") != QMessageBox.Yes:
            return
        try:
            self.current.unlink()
            self.reload()
        except Exception as e:
            self.app.status.showMessage(f"Error: {e}", 6000)


class GamesTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.reload)
        top.addWidget(refresh)
        add = QPushButton("Add manual game")
        add.clicked.connect(self.add_manual)
        top.addWidget(add)
        top.addStretch(1)
        top.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        top.addWidget(self.preset_combo)
        top.addWidget(QLabel("Game Mode:"))
        self.gm_combo = QComboBox()
        top.addWidget(self.gm_combo)
        root.addLayout(top)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.launch(False))
        root.addWidget(self.list, 1)

        btns = QHBoxLayout()
        for text, slot in (
            ("Launch (one click)", lambda: self.launch(False)),
            ("Launch + Game Mode", lambda: self.launch(True)),
            ("Bind preset", self.bind),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        root.addLayout(btns)
        self.reload()

    def reload(self):
        self.list.clear()
        for g in all_games():
            key = g.appid or g.exec or g.name
            it = QListWidgetItem(f"{g.name}  [{g.launcher}]  {key}")
            it.setData(Qt.UserRole, (g.name, g.launcher, key))
            self.list.addItem(it)
        self.preset_combo.clear()
        self.preset_combo.addItem("")
        MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
        for f in sorted(MANGOHUD_DIR.glob("*.conf")):
            self.preset_combo.addItem(f.name)
        self.gm_combo.clear()
        self.gm_combo.addItem("")
        for p in load_profiles():
            self.gm_combo.addItem(p.name)

    def _sel(self):
        it = self.list.currentItem()
        if not it:
            return None
        return it.data(Qt.UserRole)

    def add_manual(self):
        name, ok = QInputDialog.getText(self, "Manual game", "Name:")
        if not ok or not name.strip():
            return
        exe, ok = QFileDialog.getOpenFileName(self, "Select executable")
        if not ok:
            exe, ok = QInputDialog.getText(self, "Manual game", "Executable / command:")
            if not ok or not str(exe).strip():
                return
        save_manual_game(name.strip(), str(exe).strip())
        self.reload()

    def bind(self):
        sel = self._sel()
        if not sel:
            return
        name, launcher, key = sel
        preset = self.preset_combo.currentText()
        gm = self.gm_combo.currentText()
        binds = [b for b in load_bindings() if not (b.game_key == key and b.launcher == launcher)]
        binds.append(Binding(game_key=key, launcher=launcher, preset=preset, gamemode_profile=gm))
        save_bindings(binds)
        self.app.status.showMessage(f"Bound {name} -> {preset or 'none'} / {gm or 'none'}", 4000)

    def launch(self, use_gamemode):
        sel = self._sel()
        if not sel:
            return
        name, launcher, key = sel
        b = get_binding(key)
        preset_name = b.preset if b else ""
        gm_name = b.gamemode_profile if b else ""
        if preset_name:
            from src.restore import backup_conf
            backup_conf()
            src = MANGOHUD_DIR / preset_name
            if src.exists():
                try:
                    (MANGOHUD_DIR / "MangoHud.conf").write_text(
                        src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
                    )
                except Exception:
                    pass

        cmd = None
        if launcher == "steam":
            cmd = ["steam", f"steam://rungameid/{key}"]
        elif launcher == "lutris":
            cmd = ["lutris", f"lutris:rungameid/{key}"]
        elif launcher == "heroic":
            cmd = ["xdg-open", f"heroic://launch/{key}"]
        elif launcher == "bottles":
            cmd = ["bottles", "run", "-b", key]
        elif launcher == "manual":
            cmd = shlex.split(key) if " " in key else [key]
        if not cmd:
            return
        env = dict(os.environ)
        if use_gamemode and gm_name:
            try:
                from src.gamemode import build_env, run_kill, find_gamemoderun
                profile = next((p for p in load_profiles() if p.name == gm_name), None)
                if profile:
                    env = build_env(profile, env)
                    run_kill(profile)
                    gm = find_gamemoderun()
                    if gm and profile.gamemode:
                        cmd = [gm] + cmd
            except Exception:
                pass
        try:
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.app.status.showMessage(f"Launched {name}", 4000)
        except Exception as e:
            self.app.status.showMessage(f"Launch failed: {e}", 6000)


class SettingsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        s = app.settings
        root = QVBoxLayout(self)

        ov = QGroupBox("Overlay")
        form = QFormLayout(ov)
        self.position = QComboBox()
        self.position.addItems(["top-left", "top-right", "bottom-left", "bottom-right", "center"])
        self.position.setCurrentText(s.position)
        form.addRow("Position", self.position)
        self.margin = QSpinBox()
        self.margin.setRange(0, 400)
        self.margin.setValue(s.margin)
        form.addRow("Margin (px)", self.margin)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.1, 1.0)
        self.opacity.setSingleStep(0.05)
        self.opacity.setValue(s.opacity)
        form.addRow("Opacity", self.opacity)
        self.font_size = QSpinBox()
        self.font_size.setRange(7, 48)
        self.font_size.setValue(s.font_size)
        form.addRow("Font size", self.font_size)
        self.refresh = QSpinBox()
        self.refresh.setRange(100, 5000)
        self.refresh.setSingleStep(100)
        self.refresh.setValue(s.refresh_ms)
        form.addRow("Refresh (ms)", self.refresh)
        self.click_through = QCheckBox("Click-through (ignore mouse)")
        self.click_through.setChecked(s.click_through)
        form.addRow(self.click_through)
        root.addWidget(ov)

        colors = QGroupBox("Colors")
        cform = QFormLayout(colors)
        self.font_color = s.font_color
        self.accent_color = s.accent_color
        self.bg_color = s.bg_color
        self.font_btn = QPushButton(s.font_color)
        self.font_btn.clicked.connect(lambda: self.pick("font_color", self.font_btn))
        self.accent_btn = QPushButton(s.accent_color)
        self.accent_btn.clicked.connect(lambda: self.pick("accent_color", self.accent_btn))
        self.bg_btn = QPushButton(s.bg_color)
        self.bg_btn.clicked.connect(lambda: self.pick("bg_color", self.bg_btn))
        cform.addRow("Text", self.font_btn)
        cform.addRow("Accent", self.accent_btn)
        cform.addRow("Background", self.bg_btn)
        root.addWidget(colors)

        metrics = QGroupBox("Metrics")
        mform = QFormLayout(metrics)
        self.checks = {}
        for key, text in (
            ("show_cpu", "CPU"),
            ("show_gpu", "GPU load"),
            ("show_vram", "VRAM"),
            ("show_ram", "RAM"),
            ("show_temp", "Temperature"),
            ("show_fps", "FPS"),
        ):
            cb = QCheckBox(text)
            cb.setChecked(getattr(s, key))
            self.checks[key] = cb
            mform.addRow(cb)
        root.addWidget(metrics)

        fps = QGroupBox("FPS source (MangoHud log)")
        fform = QFormLayout(fps)
        self.mh_logging = QCheckBox("Enable MangoHud FPS logging")
        self.mh_logging.setChecked(s.mangohud_logging)
        fform.addRow(self.mh_logging)
        row = QHBoxLayout()
        self.fps_log = QLineEdit(s.fps_log)
        browse = QPushButton("...")
        browse.clicked.connect(self.browse_log)
        row.addWidget(self.fps_log)
        row.addWidget(browse)
        w = QWidget()
        w.setLayout(row)
        fform.addRow("Log file", w)
        root.addWidget(fps)

        apply = QPushButton("Apply and save")
        apply.clicked.connect(self.apply)
        root.addWidget(apply)
        root.addStretch(1)

    def pick(self, attr, btn):
        cur = getattr(self, attr)
        c = QColorDialog.getColor(QColor(cur), self)
        if c.isValid():
            setattr(self, attr, c.name())
            btn.setText(c.name())

    def browse_log(self):
        p, _ = QFileDialog.getSaveFileName(self, "FPS log file", self.fps_log.text())
        if p:
            self.fps_log.setText(p)

    def apply(self):
        s = self.app.settings
        s.position = self.position.currentText()
        s.margin = self.margin.value()
        s.opacity = self.opacity.value()
        s.font_size = self.font_size.value()
        s.refresh_ms = self.refresh.value()
        s.click_through = self.click_through.isChecked()
        s.font_color = self.font_color
        s.accent_color = self.accent_color
        s.bg_color = self.bg_color
        for key, cb in self.checks.items():
            setattr(s, key, cb.isChecked())
        s.mangohud_logging = self.mh_logging.isChecked()
        s.fps_log = self.fps_log.text()
        try:
            set_mangohud_logging(s.mangohud_logging, s.fps_log)
        except Exception:
            pass
        s.save()
        self.app.overlay_settings_changed()
        self.app.status.showMessage("Settings saved", 4000)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.setWindowTitle("Gamohud")
        self.resize(980, 660)

        self.tabs = QTabWidget()
        self.dashboard = DashboardTab(self)
        self.presets = PresetsTab(self)
        self.games = GamesTab(self)
        self.settings_tab = SettingsTab(self)
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.presets, "Presets")
        self.tabs.addTab(self.games, "Games")
        self.tabs.addTab(self.settings_tab, "Overlay & Settings")
        self.setCentralWidget(self.tabs)

        self.overlay = None
        if self.settings.overlay_enabled:
            self.start_overlay()

        self._build_tray()
        self.status = self.statusBar()
        self.status.showMessage("Ready", 3000)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        try:
            from PySide6.QtGui import QIcon
            self.tray.setIcon(QIcon.fromTheme("utilities-terminal"))
        except Exception:
            pass
        menu = QMenu()
        act_show = QAction("Show window", self)
        act_show.triggered.connect(self.show_window)
        act_overlay = QAction("Toggle overlay", self)
        act_overlay.triggered.connect(self.toggle_overlay)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_show)
        menu.addAction(act_overlay)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def start_overlay(self):
        if self.overlay is None:
            self.overlay = OverlayWindow(self.settings)
        self.overlay.apply_settings(self.settings)
        self.overlay.show()
        self.settings.overlay_enabled = True

    def stop_overlay(self):
        if self.overlay is not None:
            self.overlay.hide()
        self.settings.overlay_enabled = False

    def toggle_overlay(self):
        if self.settings.overlay_enabled:
            self.stop_overlay()
        else:
            self.start_overlay()
        self.settings.save()

    def overlay_settings_changed(self):
        if self.overlay is not None:
            self.overlay.apply_settings(self.settings)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("Gamohud", "Still running in tray. Use Quit to exit.")


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("Gamohud")
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
