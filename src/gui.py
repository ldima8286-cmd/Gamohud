import os
import sys
import shlex

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QAction, QIcon
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
    QScrollArea,
)

from src.metrics import (
    METRICS,
    collect_all,
    format_metric,
    metric_label,
    metric_unit,
)
from src.fps import FPSManager
from src.overlay import OverlayWindow
from src.profiles import (
    POSITIONS,
    AppProfile,
    OverlayProfile,
    ProfileStore,
    default_overlay_profiles,
    find_profile,
    running_process_names,
)
from src.launcher import launch as launch_profile
from src import games as games_mod


class DashboardTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.labels = {}
        root = QVBoxLayout(self)
        box = QGroupBox("Live metrics")
        form = QFormLayout(box)
        for key in METRICS:
            lb = QLabel("--")
            form.addRow(metric_label(key), lb)
            self.labels[key] = lb
        root.addWidget(box)
        self.info = QLabel("")
        root.addWidget(self.info)
        root.addStretch(1)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(700)

    def refresh(self):
        data = collect_all(self.app.fps_manager.read())
        for key, lb in self.labels.items():
            text = format_metric(key, data.get(key))
            lb.setText(f"{text} {metric_unit(key)}".strip() if text is not None else "N/A")
        self.info.setText(
            f"FPS backend: {self.app.fps_manager.backend.label}  |  "
            f"Overlay profile: {self.app.current_overlay_name()}"
        )


def _color_button(initial, parent=None):
    btn = QPushButton(initial or "#000000")
    btn._value = initial or "#000000"

    def pick():
        c = QColorDialog.getColor(QColor(btn._value), parent or btn)
        if c.isValid():
            btn._value = c.name()
            btn.setText(c.name())

    btn.clicked.connect(pick)
    return btn


class OverlayTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = None
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, slot in (
            ("New", self.new),
            ("Duplicate", self.duplicate),
            ("Delete", self.delete),
            ("Set active", self.set_active),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        left.addLayout(row)
        root.addLayout(left, 1)

        right = QScrollArea()
        right.setWidgetResizable(True)
        holder = QWidget()
        rl = QVBoxLayout(holder)

        appearance = QGroupBox("Appearance")
        af = QFormLayout(appearance)
        self.name = QLineEdit()
        af.addRow("Name", self.name)
        self.position = QComboBox()
        self.position.addItems(POSITIONS)
        af.addRow("Position", self.position)
        self.x = QSpinBox(); self.x.setRange(0, 10000)
        self.y = QSpinBox(); self.y.setRange(0, 10000)
        xy = QHBoxLayout(); xy.addWidget(self.x); xy.addWidget(self.y)
        xw = QWidget(); xw.setLayout(xy)
        af.addRow("Custom x / y", xw)
        self.margin = QSpinBox(); self.margin.setRange(0, 500)
        af.addRow("Margin", self.margin)
        self.font_family = QLineEdit()
        af.addRow("Font", self.font_family)
        self.font_size = QSpinBox(); self.font_size.setRange(7, 48)
        af.addRow("Font size", self.font_size)
        self.font_bold = QCheckBox("Bold")
        af.addRow(self.font_bold)
        self.opacity = QDoubleSpinBox(); self.opacity.setRange(0.05, 1.0); self.opacity.setSingleStep(0.05)
        af.addRow("Opacity", self.opacity)
        self.bg_opacity = QDoubleSpinBox(); self.bg_opacity.setRange(0.0, 1.0); self.bg_opacity.setSingleStep(0.05)
        af.addRow("Background opacity", self.bg_opacity)
        self.border_radius = QSpinBox(); self.border_radius.setRange(0, 40)
        af.addRow("Corner radius", self.border_radius)
        self.refresh_ms = QSpinBox(); self.refresh_ms.setRange(100, 5000); self.refresh_ms.setSingleStep(100)
        af.addRow("Refresh (ms)", self.refresh_ms)
        self.click_through = QCheckBox("Click-through (ignore mouse)")
        af.addRow(self.click_through)
        self.graph = QCheckBox("Show FPS graph")
        af.addRow(self.graph)
        self.fg_btn = _color_button("#ffffff", self)
        self.label_btn = _color_button("#9ad1ff", self)
        self.accent_btn = _color_button("#7CFC00", self)
        self.bg_btn = _color_button("#000000", self)
        af.addRow("Value color", self.fg_btn)
        af.addRow("Label color", self.label_btn)
        af.addRow("Accent color", self.accent_btn)
        af.addRow("Background color", self.bg_btn)
        rl.addWidget(appearance)

        metrics = QGroupBox("Metrics")
        mf = QFormLayout(metrics)
        self.checks = {}
        for key in METRICS:
            cb = QCheckBox(metric_label(key))
            self.checks[key] = cb
            mf.addRow(cb)
        rl.addWidget(metrics)

        btn_row = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        preview = QPushButton("Apply / Preview")
        preview.clicked.connect(self.preview)
        btn_row.addWidget(save)
        btn_row.addWidget(preview)
        rl.addLayout(btn_row)
        rl.addStretch(1)
        right.setWidget(holder)
        root.addWidget(right, 3)

        self.reload()

    def reload(self):
        self.list.clear()
        for p in self.app.store.overlay_profiles:
            tag = " (active)" if p.name == self.app.store.active_overlay else ""
            it = QListWidgetItem(f"{p.name}{tag}")
            it.setData(Qt.UserRole, p.name)
            self.list.addItem(it)

    def on_select(self, row):
        if row < 0:
            self.current = None
            return
        name = self.list.item(row).data(Qt.UserRole)
        profile = self.app.store.get_overlay(name)
        self.current = profile
        if profile is None:
            return
        self.name.setText(profile.name)
        self.position.setCurrentText(profile.position)
        self.x.setValue(profile.x)
        self.y.setValue(profile.y)
        self.margin.setValue(profile.margin)
        self.font_family.setText(profile.font_family)
        self.font_size.setValue(profile.font_size)
        self.font_bold.setChecked(profile.font_bold)
        self.opacity.setValue(profile.opacity)
        self.bg_opacity.setValue(profile.bg_opacity)
        self.border_radius.setValue(profile.border_radius)
        self.refresh_ms.setValue(profile.refresh_ms)
        self.click_through.setChecked(profile.click_through)
        self.graph.setChecked(profile.graph)
        self.fg_btn._value = profile.fg_color; self.fg_btn.setText(profile.fg_color)
        self.label_btn._value = profile.label_color; self.label_btn.setText(profile.label_color)
        self.accent_btn._value = profile.accent_color; self.accent_btn.setText(profile.accent_color)
        self.bg_btn._value = profile.bg_color; self.bg_btn.setText(profile.bg_color)
        for key, cb in self.checks.items():
            cb.setChecked(key in profile.metrics)

    def _collect(self) -> OverlayProfile:
        metrics = [k for k in METRICS if self.checks[k].isChecked()]
        return OverlayProfile(
            name=self.name.text().strip() or "unnamed",
            position=self.position.currentText(),
            x=self.x.value(), y=self.y.value(), margin=self.margin.value(),
            opacity=self.opacity.value(),
            font_family=self.font_family.text().strip() or "monospace",
            font_size=self.font_size.value(), font_bold=self.font_bold.isChecked(),
            fg_color=self.fg_btn._value, label_color=self.label_btn._value,
            accent_color=self.accent_btn._value, bg_color=self.bg_btn._value,
            bg_opacity=self.bg_opacity.value(), border_radius=self.border_radius.value(),
            click_through=self.click_through.isChecked(),
            refresh_ms=self.refresh_ms.value(), graph=self.graph.isChecked(),
            metrics=metrics,
        )

    def save(self):
        if not self.current:
            return
        new = self._collect()
        if new.name != self.current.name:
            if self.app.store.get_overlay(new.name):
                QMessageBox.warning(self, "Save", "A profile with that name exists.")
                return
            self.app.store.delete_overlay(self.current.name)
        self.app.store.upsert_overlay(new)
        self.app.store.save()
        self.reload()
        self.app.refresh_overlay()
        self.app.status.showMessage(f"Saved overlay profile '{new.name}'", 4000)

    def preview(self):
        if not self.current:
            return
        self.app.preview_overlay(self._collect())

    def new(self):
        p = OverlayProfile(name="new-profile")
        self.app.store.upsert_overlay(p)
        self.app.store.save()
        self.reload()

    def duplicate(self):
        if not self.current:
            return
        data = self.current.to_dict()
        data["name"] = self.current.name + "-copy"
        self.app.store.upsert_overlay(OverlayProfile.from_dict(data))
        self.app.store.save()
        self.reload()

    def delete(self):
        if not self.current:
            return
        if QMessageBox.question(self, "Delete", f"Delete '{self.current.name}'?") != QMessageBox.Yes:
            return
        self.app.store.delete_overlay(self.current.name)
        self.app.store.save()
        self.reload()
        self.app.refresh_overlay()

    def set_active(self):
        if not self.current:
            return
        self.app.store.active_overlay = self.current.name
        self.app.store.save()
        self.reload()
        self.app.refresh_overlay()


class AppsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = None
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, slot in (
            ("New", self.new),
            ("Delete", self.delete),
            ("From running process", self.from_running),
        ):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        left.addLayout(row)
        root.addLayout(left, 1)

        right = QScrollArea()
        right.setWidgetResizable(True)
        holder = QWidget()
        rl = QVBoxLayout(holder)

        basic = QGroupBox("Application profile")
        bf = QFormLayout(basic)
        self.name = QLineEdit()
        bf.addRow("Name", self.name)
        self.match = QLineEdit()
        self.match.setPlaceholderText("comma-separated patterns, e.g. steam_app_*, wine*")
        bf.addRow("Match processes", self.match)
        self.executable = QLineEdit()
        bf.addRow("Executable / command", self.executable)
        self.args = QLineEdit()
        bf.addRow("Arguments", self.args)
        self.cwd = QLineEdit()
        bf.addRow("Working dir", self.cwd)
        self.overlay_combo = QComboBox()
        bf.addRow("Overlay profile", self.overlay_combo)
        self.backend_combo = QComboBox()
        bf.addRow("FPS backend", self.backend_combo)
        self.gamemode = QCheckBox("Run with gamemoderun")
        bf.addRow(self.gamemode)
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText("extra command prefix (shell words)")
        bf.addRow("Command prefix", self.prefix)
        self.env = QPlainTextEdit()
        self.env.setPlaceholderText("KEY=value per line")
        self.env.setMaximumHeight(90)
        bf.addRow("Environment", self.env)
        rl.addWidget(basic)

        detect = QGroupBox("Import from installed games")
        df = QFormLayout(detect)
        self.game_combo = QComboBox()
        df.addRow("Detected game", self.game_combo)
        imp = QPushButton("Import selected game")
        imp.clicked.connect(self.import_game)
        df.addRow(imp)
        rl.addWidget(detect)

        btns = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self.save)
        run = QPushButton("Launch")
        run.clicked.connect(self.launch)
        btns.addWidget(save)
        btns.addWidget(run)
        rl.addLayout(btns)
        rl.addStretch(1)
        right.setWidget(holder)
        root.addWidget(right, 3)

        self.reload()

    def reload(self):
        self.list.clear()
        for p in self.app.store.app_profiles:
            it = QListWidgetItem(p.name or "(unnamed)")
            it.setData(Qt.UserRole, p.name)
            self.list.addItem(it)
        self._reload_combos()
        self._reload_games()

    def _reload_combos(self):
        cur_ov = self.overlay_combo.currentText()
        self.overlay_combo.clear()
        self.overlay_combo.addItem("")
        for p in self.app.store.overlay_profiles:
            self.overlay_combo.addItem(p.name)
        if cur_ov:
            self.overlay_combo.setCurrentText(cur_ov)

        cur_be = self.backend_combo.currentText()
        self.backend_combo.clear()
        self.backend_combo.addItem("")
        for backend in self.app.fps_manager.backends():
            status = backend.available()
            label = backend.label if status.available else f"{backend.label} (unavailable)"
            self.backend_combo.addItem(label, backend.name)
        if cur_be:
            self.backend_combo.setCurrentText(cur_be)

    def _reload_games(self):
        self.game_combo.clear()
        try:
            self._games = games_mod.all_games()
        except Exception:
            self._games = []
        for g in self._games:
            self.game_combo.addItem(f"{g.name}  [{g.launcher}]", g)

    def on_select(self, row):
        if row < 0:
            self.current = None
            return
        name = self.list.item(row).data(Qt.UserRole)
        profile = next((p for p in self.app.store.app_profiles if p.name == name), None)
        self.current = profile
        if profile is None:
            return
        self.name.setText(profile.name)
        self.match.setText(", ".join(profile.match))
        self.executable.setText(profile.executable or "")
        self.args.setText(profile.args or "")
        self.cwd.setText(profile.cwd or "")
        self.overlay_combo.setCurrentText(profile.overlay or "")
        idx = self.backend_combo.findData(profile.fps_backend or "")
        self.backend_combo.setCurrentIndex(max(0, idx))
        self.gamemode.setChecked(profile.gamemode)
        self.prefix.setText(" ".join(profile.command_prefix or []))
        self.env.setPlainText("\n".join(f"{k}={v}" for k, v in (profile.env or {}).items()))

    def _parse_env(self) -> dict:
        env = {}
        for line in self.env.toPlainText().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
        return env

    def _collect(self) -> AppProfile:
        return AppProfile(
            name=self.name.text().strip() or "unnamed",
            match=[m.strip() for m in self.match.text().split(",") if m.strip()],
            executable=self.executable.text().strip() or None,
            args=self.args.text().strip(),
            cwd=self.cwd.text().strip() or None,
            overlay=self.overlay_combo.currentText() or None,
            fps_backend=self.backend_combo.currentData() or None,
            gamemode=self.gamemode.isChecked(),
            command_prefix=shlex.split(self.prefix.text()) if self.prefix.text().strip() else [],
            env=self._parse_env(),
        )

    def save(self):
        new = self._collect()
        old_name = self.current.name if self.current else None
        if old_name and old_name != new.name:
            self.app.store.delete_app(old_name)
        self.app.store.upsert_app(new)
        self.app.store.save()
        self.reload()
        self.app.status.showMessage(f"Saved app profile '{new.name}'", 4000)

    def new(self):
        self.app.store.upsert_app(AppProfile(name="new-app"))
        self.app.store.save()
        self.reload()

    def delete(self):
        if not self.current:
            return
        self.app.store.delete_app(self.current.name)
        self.app.store.save()
        self.reload()

    def from_running(self):
        names = sorted(set(running_process_names()))
        name, ok = QInputDialog.getItem(self, "Running process", "Process name:", names, 0, False)
        if not ok or not name:
            return
        self.app.store.upsert_app(AppProfile(name=name, match=[name]))
        self.app.store.save()
        self.reload()

    def import_game(self):
        g = self.game_combo.currentData()
        if g is None:
            return
        executable = g.exec or ""
        if g.launcher == "steam" and g.appid:
            executable = f"steam steam://rungameid/{g.appid}"
        elif g.launcher == "lutris" and g.appid:
            executable = f"lutris lutris:rungameid/{g.appid}"
        elif g.launcher == "heroic" and g.appid:
            executable = f"xdg-open heroic://launch/{g.appid}"
        elif g.launcher == "bottles" and g.appid:
            executable = f"bottles run -b {g.appid}"
        profile = AppProfile(
            name=g.name,
            match=[f"*{g.name.lower().replace(' ', '')}*"],
            executable=executable or None,
            overlay=self.app.store.active_overlay,
        )
        self.app.store.upsert_app(profile)
        self.app.store.save()
        self.reload()

    def launch(self):
        if not self.current:
            QMessageBox.information(self, "Launch", "Select or save a profile first.")
            return
        profile = self._collect()
        try:
            _proc, command = launch_profile(profile, self.app.store, self.app.fps_manager)
            self.app.start_overlay()
            self.app.status.showMessage(f"Launched: {' '.join(command)}", 5000)
        except Exception as e:
            QMessageBox.warning(self, "Launch failed", str(e))


class SettingsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        root = QVBoxLayout(self)

        backend = QGroupBox("Global FPS backend")
        bf = QFormLayout(backend)
        self.backend_combo = QComboBox()
        bf.addRow("Backend", self.backend_combo)
        self.backend_desc = QLabel("")
        self.backend_desc.setWordWrap(True)
        bf.addRow(self.backend_desc)
        root.addWidget(backend)

        general = QGroupBox("General")
        gf = QFormLayout(general)
        self.start_overlay = QCheckBox("Start overlay when the app launches")
        gf.addRow(self.start_overlay)
        self.auto_switch = QCheckBox("Auto-switch overlay by running process")
        gf.addRow(self.auto_switch)
        self.active_combo = QComboBox()
        gf.addRow("Default overlay profile", self.active_combo)
        root.addWidget(general)

        save = QPushButton("Save")
        save.clicked.connect(self.apply)
        root.addWidget(save)
        root.addStretch(1)
        self.reload()

    def reload(self):
        self.backend_combo.clear()
        for backend in self.app.fps_manager.backends():
            status = backend.available()
            label = backend.label if status.available else f"{backend.label} — {status.reason}"
            self.backend_combo.addItem(label, backend.name)
        idx = self.backend_combo.findData(self.app.store.global_fps_backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.backend_combo.currentIndexChanged.connect(self._sync_desc)
        self._sync_desc()
        self.start_overlay.setChecked(self.app.start_overlay_enabled)
        self.auto_switch.setChecked(self.app.auto_switch_enabled)
        self.active_combo.clear()
        for p in self.app.store.overlay_profiles:
            self.active_combo.addItem(p.name)
        self.active_combo.setCurrentText(self.app.store.active_overlay)

    def _sync_desc(self):
        name = self.backend_combo.currentData()
        backend = next((b for b in self.app.fps_manager.backends() if b.name == name), None)
        status = backend.available() if backend else None
        text = backend.description if backend else ""
        if status and not status.available:
            text += f"  (Unavailable: {status.reason})"
        self.backend_desc.setText(text)

    def apply(self):
        self.app.store.global_fps_backend = self.backend_combo.currentData() or "null"
        self.app.store.active_overlay = self.active_combo.currentText()
        self.app.start_overlay_enabled = self.start_overlay.isChecked()
        self.app.auto_switch_enabled = self.auto_switch.isChecked()
        self.app.store.save()
        self.app.fps_manager.set_backend(self.app.store.global_fps_backend)
        self.app.refresh_overlay()
        self.app.status.showMessage("Settings saved", 4000)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = ProfileStore()
        self.fps_manager = FPSManager(self.store.global_fps_backend)
        self.start_overlay_enabled = True
        self.auto_switch_enabled = True

        self.setWindowTitle("Gamohud")
        self.resize(1040, 700)

        self.tabs = QTabWidget()
        self.dashboard = DashboardTab(self)
        self.overlay_tab = OverlayTab(self)
        self.apps_tab = AppsTab(self)
        self.settings_tab = SettingsTab(self)
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.overlay_tab, "Overlay Profiles")
        self.tabs.addTab(self.apps_tab, "Applications")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.setCentralWidget(self.tabs)

        self.overlay = None
        self._overlay_profile_name = None
        if self.start_overlay_enabled:
            self.start_overlay()

        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_switch)
        self._auto_timer.start(2000)

        self._build_tray()
        self.status = self.statusBar()
        self.status.showMessage("Ready", 3000)

    def current_overlay_name(self):
        return self._overlay_profile_name or self.store.active_overlay

    def _overlay_data(self):
        return collect_all(self.fps_manager.read())

    def start_overlay(self):
        profile = self.store.active_overlay_profile()
        if self.overlay is None:
            self.overlay = OverlayWindow(profile, self._overlay_data)
        self.overlay.set_profile(profile)
        self._overlay_profile_name = profile.name
        self.overlay.show()

    def stop_overlay(self):
        if self.overlay is not None:
            self.overlay.hide()
            self._overlay_profile_name = None

    def refresh_overlay(self):
        if self.overlay is None:
            return
        profile = self.store.get_overlay(self._overlay_profile_name) or self.store.active_overlay_profile()
        self.overlay.set_profile(profile)

    def preview_overlay(self, profile):
        if self.overlay is None:
            self.overlay = OverlayWindow(profile, self._overlay_data)
        self.overlay.set_profile(profile)
        self._overlay_profile_name = profile.name
        self.overlay.show()

    def _auto_switch(self):
        if self.overlay is None or not self.auto_switch_enabled:
            return
        names = running_process_names(limit=200)
        matched = find_profile(self.store.app_profiles, names)
        target_name = None
        if matched and matched.overlay:
            target_name = matched.overlay
        if target_name is None:
            target_name = self.store.active_overlay
        if target_name != self._overlay_profile_name:
            profile = self.store.get_overlay(target_name)
            if profile is not None:
                self.overlay.set_profile(profile)
                self._overlay_profile_name = profile.name

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        try:
            self.tray.setIcon(QIcon.fromTheme("utilities-system-monitor"))
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

    def toggle_overlay(self):
        if self.overlay is not None and self.overlay.isVisible():
            self.stop_overlay()
        else:
            self.start_overlay()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.tray.isVisible():
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
