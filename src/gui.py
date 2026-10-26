import os
import sys

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import games as games_mod
from src.fps import FPSManager
from src.i18n import LANGUAGES, get_language, set_language, tr
from src.keep_above import KeepAbove
from src.launcher import launch as launch_profile
from src.metrics import (
    LAYOUT_PRESETS,
    METRICS,
    collect_all,
    format_metric,
    metric_label,
    metric_unit,
)
from src.overlay import OverlayWindow, overlay_position
from src.overlay_bridge import GeometryReceiver
from src.platform_utils import IS_WINDOWS, open_uri_command, split_args
from src.profiles import (
    POSITIONS,
    AppProfile,
    OverlayProfile,
    ProfileStore,
    active_window_title,
    find_profile,
    find_profile_by_window,
    running_process_names,
)
from src.theme import (
    THEME_LABELS,
    THEME_MODES,
    apply_theme,
    resolved_theme,
    warning_color,
)
from src.ui_utils import (
    MetricTile,
    StatusBanner,
    color_button,
    form_label,
    group_box,
    hint_label,
    muted_color,
    page_header,
    section_label,
)


class DashboardTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.tiles = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        root.addWidget(
            page_header(
                tr("Dashboard"),
                tr("Live system metrics from /proc, /sys and your GPU driver."),
            )
        )

        self.warning = StatusBanner()
        self.warning.button.clicked.connect(self._open_settings)
        root.addWidget(self.warning)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        columns = 4
        for index, key in enumerate(METRICS):
            tile = MetricTile(metric_label(key))
            self.tiles[key] = tile
            grid.addWidget(tile, index // columns, index % columns)
        root.addLayout(grid, 1)

        self.info = QLabel("")
        self.info.setStyleSheet(f"color: {muted_color()};")
        root.addWidget(self.info)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(700)
        self.refresh()

    def _open_settings(self):
        settings = getattr(self.app, "settings_tab", None)
        tabs = getattr(self.app, "tabs", None)
        if settings is not None and tabs is not None:
            tabs.setCurrentWidget(settings)

    def refresh(self):
        data = collect_all(self.app.fps_manager.read())
        for key, tile in self.tiles.items():
            text = format_metric(key, data.get(key))
            if text is None:
                tile.set_value(tr("N/A"))
            else:
                unit = metric_unit(key)
                tile.set_value(f"{text} {unit}".strip())
        backend = self.app.fps_manager.backend
        status = backend.available()
        if status.available:
            self.warning.hide()
        else:
            self.warning.set_message(
                tr("FPS is unavailable: {reason}. Pick another backend in Settings.").format(
                    reason=tr(status.reason)
                )
            )
        self.info.setText(
            f"{tr('FPS backend')}: {backend.label}  \u00b7  "
            f"{tr('Overlay profile')}: {self.app.current_overlay_name()}"
        )


class OverlayTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current = None

        page = QVBoxLayout(self)
        page.setContentsMargins(18, 16, 18, 12)
        page.setSpacing(12)
        page.addWidget(
            page_header(
                tr("Overlay Profiles"),
                tr("Profiles and appearance of the on-screen overlay."),
            )
        )

        body = QHBoxLayout()
        body.setSpacing(14)

        left_panel = QWidget()
        left_panel.setFixedWidth(190)
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        left.addWidget(section_label(tr("Profiles")))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        left.addWidget(self.list, 1)
        for text, slot in (
            (tr("New"), self.new),
            (tr("Duplicate"), self.duplicate),
            (tr("Delete"), self.delete),
            (tr("Set active"), self.set_active),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            left.addWidget(button)
        left.addWidget(hint_label(tr("Auto-switch follows the matched running game.")))
        body.addWidget(left_panel, 0)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        rl = QVBoxLayout(holder)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)
        columns = QHBoxLayout()
        columns.setSpacing(10)
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        columns.addLayout(left_col, 5)
        columns.addLayout(right_col, 4)
        rl.addLayout(columns)

        appearance = group_box(tr("Appearance"))
        af = QGridLayout(appearance)
        af.setContentsMargins(12, 14, 12, 10)
        af.setHorizontalSpacing(10)
        af.setVerticalSpacing(7)
        af.setColumnStretch(1, 3)
        af.setColumnStretch(3, 2)

        self.name = QLineEdit()
        af.addWidget(form_label(tr("Name")), 0, 0)
        af.addWidget(self.name, 0, 1, 1, 3)

        self.position = QComboBox()
        self.position.addItems(POSITIONS)
        af.addWidget(form_label(tr("Position")), 1, 0)
        af.addWidget(self.position, 1, 1)
        self.margin = QSpinBox(); self.margin.setRange(0, 500)
        af.addWidget(form_label(tr("Margin")), 1, 2)
        af.addWidget(self.margin, 1, 3)

        self.x = QSpinBox(); self.x.setRange(0, 10000); self.x.setPrefix("X  ")
        self.y = QSpinBox(); self.y.setRange(0, 10000); self.y.setPrefix("Y  ")
        xy = QHBoxLayout(); xy.setSpacing(6); xy.addWidget(self.x, 1); xy.addWidget(self.y, 1)
        af.addWidget(form_label(tr("Custom x / y")), 2, 0)
        af.addLayout(xy, 2, 1, 1, 3)

        self.font_family = QLineEdit()
        af.addWidget(form_label(tr("Font")), 3, 0)
        af.addWidget(self.font_family, 3, 1)
        self.font_size = QSpinBox(); self.font_size.setRange(7, 48)
        af.addWidget(form_label(tr("Font size")), 3, 2)
        af.addWidget(self.font_size, 3, 3)

        self.opacity = QDoubleSpinBox(); self.opacity.setRange(0.05, 1.0); self.opacity.setSingleStep(0.05)
        af.addWidget(form_label(tr("Opacity")), 4, 0)
        af.addWidget(self.opacity, 4, 1)
        self.bg_opacity = QDoubleSpinBox(); self.bg_opacity.setRange(0.0, 1.0); self.bg_opacity.setSingleStep(0.05)
        af.addWidget(form_label(tr("Background opacity")), 4, 2)
        af.addWidget(self.bg_opacity, 4, 3)

        self.border_radius = QSpinBox(); self.border_radius.setRange(0, 40)
        af.addWidget(form_label(tr("Corner radius")), 5, 0)
        af.addWidget(self.border_radius, 5, 1)
        self.refresh_ms = QSpinBox(); self.refresh_ms.setRange(100, 5000); self.refresh_ms.setSingleStep(100)
        af.addWidget(form_label(tr("Refresh (ms)")), 5, 2)
        af.addWidget(self.refresh_ms, 5, 3)

        self.font_bold = QCheckBox(tr("Bold"))
        self.click_through = QCheckBox(tr("Click-through (ignore mouse)"))
        self.graph = QCheckBox(tr("Show FPS graph"))
        flags = QHBoxLayout()
        flags.setSpacing(16)
        flags.addWidget(self.font_bold)
        flags.addWidget(self.click_through)
        flags.addWidget(self.graph)
        flags.addStretch(1)
        af.addLayout(flags, 6, 0, 1, 4)
        left_col.addWidget(appearance)

        colors = group_box(tr("Colors"))
        cf = QGridLayout(colors)
        cf.setContentsMargins(12, 14, 12, 10)
        cf.setHorizontalSpacing(10)
        cf.setVerticalSpacing(7)
        self.fg_btn = color_button("#ffffff", self)
        self.label_btn = color_button("#9ad1ff", self)
        self.accent_btn = color_button("#7CFC00", self)
        self.bg_btn = color_button("#000000", self)
        cf.addWidget(form_label(tr("Value color")), 0, 0)
        cf.addWidget(self.fg_btn, 0, 1)
        cf.addWidget(form_label(tr("Background color")), 0, 2)
        cf.addWidget(self.bg_btn, 0, 3)
        cf.addWidget(form_label(tr("Label color")), 1, 0)
        cf.addWidget(self.label_btn, 1, 1)
        cf.addWidget(form_label(tr("Accent color")), 1, 2)
        cf.addWidget(self.accent_btn, 1, 3)
        cf.setColumnStretch(1, 1)
        cf.setColumnStretch(3, 1)
        left_col.addWidget(colors)

        metrics = group_box(tr("Metrics"))
        ml = QVBoxLayout(metrics)
        ml.setContentsMargins(12, 14, 12, 10)
        ml.setSpacing(6)
        metric_top = QHBoxLayout()
        metric_top.addWidget(hint_label(tr("Choose what the overlay shows.")), 1)
        all_button = QPushButton(tr("All"))
        all_button.setFlat(True)
        all_button.clicked.connect(lambda: self._set_all_metrics(True))
        none_button = QPushButton(tr("None"))
        none_button.setFlat(True)
        none_button.clicked.connect(lambda: self._set_all_metrics(False))
        metric_top.addWidget(all_button)
        metric_top.addWidget(none_button)
        ml.addLayout(metric_top)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        self.checks = {}
        columns = 2
        for index, key in enumerate(METRICS):
            cb = QCheckBox(metric_label(key))
            cb.setToolTip(f"{metric_label(key)} ({metric_unit(key)})".strip())
            self.checks[key] = cb
            grid.addWidget(cb, index // columns, index % columns)
        ml.addLayout(grid)
        right_col.addWidget(metrics)

        presets = group_box(tr("Presets"))
        pl = QVBoxLayout(presets)
        pl.setContentsMargins(12, 14, 12, 10)
        pl.setSpacing(6)
        pl.addWidget(hint_label(tr("Apply a ready-made metric set to this profile.")))
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.preset_combo.setMinimumContentsLength(12)
        for key, (label, desc, _keys) in LAYOUT_PRESETS.items():
            self.preset_combo.addItem(tr(label), key)
            self.preset_combo.setItemData(
                self.preset_combo.count() - 1, tr(desc), Qt.ItemDataRole.ToolTipRole
            )
        apply_preset = QPushButton(tr("Apply"))
        apply_preset.clicked.connect(lambda: self.apply_preset(self.preset_combo.currentData()))
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(apply_preset)
        pl.addLayout(preset_row)
        right_col.addWidget(presets)
        left_col.addStretch(1)
        right_col.addStretch(1)

        self.scroll.setWidget(holder)
        right.addWidget(self.scroll, 1)

        btn_row = QHBoxLayout()
        save = QPushButton(tr("Save"))
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self.save)
        preview = QPushButton(tr("Apply / Preview"))
        preview.clicked.connect(self.preview)
        self.lock_btn = QPushButton(tr("Unlock to move"))
        self.lock_btn.setCheckable(True)
        self.lock_btn.toggled.connect(self._on_lock_toggled)
        self.lock_btn.setToolTip(
            tr("Unlock, then drag the overlay with the mouse to place it. "
               "Ctrl+Shift+L toggles the lock.")
        )
        btn_row.addWidget(save)
        btn_row.addWidget(preview)
        btn_row.addWidget(self.lock_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(hint_label(tr("Ctrl+Shift+L toggles the lock.")))
        right.addLayout(btn_row)

        body.addLayout(right, 3)
        page.addLayout(body, 1)
        self.reload()

    def reload(self):
        keep = self.current.name if self.current else self.app.store.active_overlay
        self.list.blockSignals(True)
        self.list.clear()
        for p in self.app.store.overlay_profiles:
            tag = " (active)" if p.name == self.app.store.active_overlay else ""
            it = QListWidgetItem(f"{p.name}{tr(tag)}")
            it.setData(Qt.UserRole, p.name)
            font = it.font()
            font.setBold(p.name == self.app.store.active_overlay)
            it.setFont(font)
            self.list.addItem(it)
        self.list.blockSignals(False)
        if self.list.count():
            row = next(
                (i for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole) == keep),
                0,
            )
            self.list.setCurrentRow(row)
        self.sync_lock_button()

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
        self.fg_btn._set_value(profile.fg_color)
        self.label_btn._set_value(profile.label_color)
        self.accent_btn._set_value(profile.accent_color)
        self.bg_btn._set_value(profile.bg_color)
        for key, cb in self.checks.items():
            cb.setChecked(key in profile.metrics)

    def _set_all_metrics(self, checked: bool):
        for cb in self.checks.values():
            cb.setChecked(checked)

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
                QMessageBox.warning(self, tr("Save"), tr("A profile with that name exists."))
                return
            self.app.store.delete_overlay(self.current.name)
        self.app.store.upsert_overlay(new)
        self.app.store.save()
        self.current = new
        self.reload()
        self.app.refresh_overlay()
        self.app.status.showMessage(tr("Saved overlay profile '{name}'").format(name=new.name), 4000)

    def preview(self):
        if not self.current:
            return
        self.app.preview_overlay(self._collect())

    def apply_preset(self, key):
        preset = LAYOUT_PRESETS.get(key)
        if preset is None:
            return
        _, _, keys = preset
        wanted = set(keys)
        for k, cb in self.checks.items():
            cb.setChecked(k in wanted)
        self.app.status.showMessage(
            tr("Applied preset '{name}'").format(name=tr(preset[0])), 4000
        )

    def _on_lock_toggled(self, checked):
        self.app.set_overlay_locked(not checked)

    def sync_lock_button(self):
        self.lock_btn.blockSignals(True)
        self.lock_btn.setChecked(not self.app.overlay_locked)
        self.lock_btn.blockSignals(False)
        self.lock_btn.setText(tr("Lock overlay") if not self.app.overlay_locked else tr("Unlock to move"))

    def new(self):
        p = OverlayProfile(name="new-profile")
        self.app.store.upsert_overlay(p)
        self.app.store.save()
        self.current = p
        self.reload()

    def duplicate(self):
        if not self.current:
            return
        data = self.current.to_dict()
        data["name"] = self.current.name + "-copy"
        p = OverlayProfile.from_dict(data)
        self.app.store.upsert_overlay(p)
        self.app.store.save()
        self.current = p
        self.reload()

    def delete(self):
        if not self.current:
            return
        if QMessageBox.question(self, tr("Delete"), tr("Delete '{name}'?").format(name=self.current.name)) != QMessageBox.Yes:
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

        page = QVBoxLayout(self)
        page.setContentsMargins(18, 14, 18, 10)
        page.setSpacing(10)
        page.addWidget(
            page_header(
                tr("Applications"),
                tr("Game profiles, launch options and automatic overlay switching."),
            )
        )

        body = QHBoxLayout()
        body.setSpacing(14)

        left_panel = QWidget()
        left_panel.setFixedWidth(190)
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        left.addWidget(section_label(tr("Profiles")))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        left.addWidget(self.list, 1)
        buttons = QGridLayout()
        buttons.setHorizontalSpacing(6)
        buttons.setVerticalSpacing(6)
        for index, (text, slot) in enumerate(
            ((tr("New"), self.new), (tr("Delete"), self.delete))
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button, 0, index)
        from_running = QPushButton(tr("From running process"))
        from_running.clicked.connect(self.from_running)
        buttons.addWidget(from_running, 1, 0, 1, 2)
        left.addLayout(buttons)
        left.addWidget(hint_label(tr("Auto-switch follows the matched running game.")))
        body.addWidget(left_panel, 0)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        rl = QVBoxLayout(holder)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        basic = group_box(tr("Application profile"))
        bf = QFormLayout(basic)
        bf.setContentsMargins(12, 10, 12, 8)
        bf.setSpacing(5)
        self.name = QLineEdit()
        bf.addRow(tr("Name"), self.name)
        self.match = QLineEdit()
        self.match.setPlaceholderText(tr("comma-separated patterns, e.g. steam_app_*, wine*"))
        bf.addRow(tr("Match processes"), self.match)
        self.executable = QLineEdit()
        bf.addRow(tr("Executable / command"), self.executable)
        self.process_name = QLineEdit()
        self.process_name.setPlaceholderText(tr("optional, for PresentMon: game exe name, e.g. game.exe"))
        bf.addRow(tr("Game process name"), self.process_name)
        self.args = QLineEdit()
        bf.addRow(tr("Arguments"), self.args)
        self.cwd = QLineEdit()
        bf.addRow(tr("Working dir"), self.cwd)
        self.overlay_combo = QComboBox()
        bf.addRow(tr("Overlay profile"), self.overlay_combo)
        self.backend_combo = QComboBox()
        bf.addRow(tr("FPS backend"), self.backend_combo)
        self.gamemode = QCheckBox(tr("Run with gamemoderun"))
        bf.addRow(self.gamemode)
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText(tr("extra command prefix (shell words)"))
        bf.addRow(tr("Command prefix"), self.prefix)
        self.env = QPlainTextEdit()
        self.env.setPlaceholderText("KEY=value")
        self.env.setMaximumHeight(64)
        bf.addRow(tr("Environment"), self.env)
        rl.addWidget(basic)

        detect = group_box(tr("Import from installed games"))
        df = QFormLayout(detect)
        df.setContentsMargins(12, 10, 12, 8)
        df.setSpacing(5)
        self.game_combo = QComboBox()
        df.addRow(tr("Detected game"), self.game_combo)
        imp = QPushButton(tr("Import selected game"))
        imp.setMaximumWidth(320)
        imp.clicked.connect(self.import_game)
        df.addRow(imp)
        rl.addWidget(detect)
        rl.addStretch(1)

        self.scroll.setWidget(holder)
        right.addWidget(self.scroll, 1)

        btns = QHBoxLayout()
        save = QPushButton(tr("Save"))
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self.save)
        run = QPushButton(tr("Launch"))
        run.clicked.connect(self.launch)
        btns.addWidget(save)
        btns.addWidget(run)
        btns.addStretch(1)
        btns.addWidget(hint_label(tr("Profiles are saved with the Save button.")))
        right.addLayout(btns)

        body.addLayout(right, 3)
        page.addLayout(body, 1)
        self.reload()

    def reload(self):
        keep = self.current.name if self.current else None
        self.list.blockSignals(True)
        self.list.clear()
        for p in self.app.store.app_profiles:
            it = QListWidgetItem(p.name or tr("(unnamed)"))
            it.setData(Qt.UserRole, p.name)
            self.list.addItem(it)
        self.list.blockSignals(False)
        self._reload_combos()
        self._reload_games()
        if self.list.count():
            row = next(
                (i for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole) == keep),
                0,
            )
            self.list.setCurrentRow(row)

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
            label = backend.label if status.available else f"{backend.label} ({tr('unavailable')})"
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
        self.process_name.setText(profile.process_name or "")
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
            process_name=self.process_name.text().strip() or None,
            args=self.args.text().strip(),
            cwd=self.cwd.text().strip() or None,
            overlay=self.overlay_combo.currentText() or None,
            fps_backend=self.backend_combo.currentData() or None,
            gamemode=self.gamemode.isChecked(),
            command_prefix=split_args(self.prefix.text()) if self.prefix.text().strip() else [],
            env=self._parse_env(),
        )

    def save(self):
        new = self._collect()
        old_name = self.current.name if self.current else None
        if old_name and old_name != new.name:
            self.app.store.delete_app(old_name)
        self.app.store.upsert_app(new)
        self.app.store.save()
        self.current = new
        self.reload()
        self.app.status.showMessage(tr("Saved app profile '{name}'").format(name=new.name), 4000)

    def new(self):
        p = AppProfile(name="new-app")
        self.app.store.upsert_app(p)
        self.app.store.save()
        self.current = p
        self.reload()

    def delete(self):
        if not self.current:
            return
        self.app.store.delete_app(self.current.name)
        self.app.store.save()
        self.reload()

    def from_running(self):
        names = sorted(set(running_process_names()))
        name, ok = QInputDialog.getItem(self, tr("Running process"), tr("Process name:"), names, 0, False)
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
            executable = " ".join(open_uri_command(f"heroic://launch/{g.appid}"))
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
            QMessageBox.information(self, tr("Launch"), tr("Select or save a profile first."))
            return
        profile = self._collect()
        try:
            _proc, command = launch_profile(profile, self.app.store, self.app.fps_manager)
            self.app.start_overlay()
            self.app.status.showMessage(tr("Launched: {command}").format(command=" ".join(command)), 5000)
        except Exception as e:
            QMessageBox.warning(self, tr("Launch failed"), str(e))


class _PresentMonDownloader(QThread):
    ok = Signal(str)
    err = Signal(str)

    def run(self):
        try:
            from src.fps.presentmon_common import download_presentmon

            path = download_presentmon(log=lambda _m: None)
            self.ok.emit(str(path))
        except Exception as exc:  # noqa: BLE001
            self.err.emit(str(exc))


class _UpdateChecker(QThread):
    found = Signal(dict)
    none = Signal()

    def run(self):
        try:
            from src.update_check import is_newer, latest_release
            from src.version import __version__

            release = latest_release()
            if release and is_newer(release.get("tag", ""), __version__):
                self.found.emit(release)
                return
        except Exception:
            pass
        self.none.emit()


class SettingsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        page = QVBoxLayout(self)
        page.setContentsMargins(18, 16, 18, 12)
        page.setSpacing(12)
        page.addWidget(
            page_header(
                tr("Settings"),
                tr("Global FPS backend, behavior and updates."),
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        outer = QHBoxLayout(holder)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        content.setMinimumWidth(680)
        content.setMaximumWidth(840)
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        backend = group_box(tr("Global FPS backend"))
        bf = QFormLayout(backend)
        bf.setContentsMargins(12, 14, 12, 10)
        bf.setSpacing(7)
        self.backend_combo = QComboBox()
        bf.addRow(tr("Backend"), self.backend_combo)
        self.backend_desc = QLabel("")
        self.backend_desc.setWordWrap(True)
        bf.addRow(self.backend_desc)
        self.download_pm = QPushButton(tr("Download PresentMon (Windows)..."))
        self.download_pm.setMaximumWidth(320)
        self.download_pm.clicked.connect(self.download_presentmon)
        bf.addRow(self.download_pm)
        self._pm_worker = None
        root.addWidget(backend)

        general = group_box(tr("General"))
        gf = QFormLayout(general)
        gf.setContentsMargins(12, 14, 12, 10)
        gf.setSpacing(7)
        self.language_combo = QComboBox()
        for code in LANGUAGES:
            self.language_combo.addItem(LANGUAGES[code], code)
        gf.addRow(tr("Language"), self.language_combo)
        self.theme_combo = QComboBox()
        for mode in THEME_MODES:
            self.theme_combo.addItem(tr(THEME_LABELS[mode]), mode)
        self.theme_combo.setToolTip("Ctrl+Shift+D")
        gf.addRow(tr("Theme"), self.theme_combo)
        self.start_overlay = QCheckBox(tr("Start overlay when the app launches"))
        gf.addRow(self.start_overlay)
        self.auto_switch = QCheckBox(tr("Auto-switch overlay by running process"))
        gf.addRow(self.auto_switch)
        self.active_combo = QComboBox()
        gf.addRow(tr("Default overlay profile"), self.active_combo)
        self.autostart = QCheckBox(tr("Launch gamohud at login"))
        gf.addRow(self.autostart)
        root.addWidget(general)

        updates = group_box(tr("Updates"))
        uf = QFormLayout(updates)
        uf.setContentsMargins(12, 14, 12, 10)
        uf.setSpacing(7)
        self.check_updates = QPushButton(tr("Check for updates"))
        self.check_updates.setMaximumWidth(260)
        self.check_updates.clicked.connect(self.run_update_check)
        uf.addRow(self.check_updates)
        self._update_worker = None
        self.check_updates_start = QCheckBox(tr("Check for updates on startup"))
        uf.addRow(self.check_updates_start)
        root.addWidget(updates)
        root.addStretch(1)

        outer.addWidget(content, 0)
        outer.addStretch(1)
        scroll.setWidget(holder)
        page.addWidget(scroll, 1)

        bar = QHBoxLayout()
        save = QPushButton(tr("Save"))
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self.apply)
        bar.addWidget(save)
        saved_hint = hint_label(tr("Settings are saved with the Save button."))
        saved_hint.setWordWrap(False)
        bar.addWidget(saved_hint)
        bar.addStretch(1)
        page.addLayout(bar)

        self.reload()
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.backend_combo.currentIndexChanged.connect(self._sync_desc)

    def _on_language_changed(self, _index):
        code = self.language_combo.currentData()
        if not code or code == self.app.store.language:
            return
        self.app.store.language = code
        self.app.store.save()
        set_language(code)
        QTimer.singleShot(0, self.app.rebuild_ui)

    def _on_theme_changed(self, _index):
        mode = self.theme_combo.currentData()
        if mode:
            self.app.set_theme(mode)

    def reload(self):
        self.backend_combo.clear()
        for backend in self.app.fps_manager.backends():
            status = backend.available()
            label = backend.label if status.available else f"{backend.label} ({tr('unavailable')})"
            self.backend_combo.addItem(label, backend.name)
        idx = self.backend_combo.findData(self.app.store.global_fps_backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self._sync_desc()
        self.start_overlay.setChecked(self.app.start_overlay_enabled)
        self.auto_switch.setChecked(self.app.auto_switch_enabled)
        self.check_updates_start.setChecked(getattr(self.app.store, "check_updates_on_start", True))
        try:
            from src import autostart
            self.autostart.setChecked(autostart.is_enabled())
        except Exception:
            self.autostart.setChecked(False)
            self.autostart.setEnabled(False)
        self.active_combo.clear()
        for p in self.app.store.overlay_profiles:
            self.active_combo.addItem(p.name)
        self.active_combo.setCurrentText(self.app.store.active_overlay)
        idx = self.language_combo.findData(get_language())
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        idx = self.theme_combo.findData(self.app.store.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

    def _sync_desc(self):
        name = self.backend_combo.currentData()
        backend = next((b for b in self.app.fps_manager.backends() if b.name == name), None)
        status = backend.available() if backend else None
        text = tr(backend.description) if backend else ""
        if status and not status.available:
            text += "  (" + tr("Unavailable: {reason}").format(reason=tr(status.reason)) + ")"
            self.backend_desc.setStyleSheet(f"color: {warning_color()};")
        else:
            self.backend_desc.setStyleSheet("")
        self.backend_desc.setText(text)

    def download_presentmon(self):
        if not IS_WINDOWS:
            QMessageBox.information(
                self, "PresentMon",
                tr("PresentMon is only needed on Windows.\nOn Linux use the Vulkan layer, gamescope or mesa_gallium backends."),
            )
            return
        self.download_pm.setEnabled(False)
        self.download_pm.setText(tr("Downloading..."))
        self._pm_worker = _PresentMonDownloader(self)
        self._pm_worker.ok.connect(self._pm_download_done)
        self._pm_worker.err.connect(self._pm_download_failed)
        self._pm_worker.start()

    def _pm_reset_button(self):
        self.download_pm.setEnabled(True)
        self.download_pm.setText(tr("Download PresentMon (Windows)..."))

    def _pm_download_done(self, path):
        self._pm_reset_button()
        self.app.status.showMessage(tr("PresentMon saved: {path}").format(path=path), 8000)
        self.reload()

    def _pm_download_failed(self, message):
        self._pm_reset_button()
        QMessageBox.warning(self, tr("PresentMon download failed"), message)

    def apply(self):
        self.app.store.global_fps_backend = self.backend_combo.currentData() or "null"
        self.app.store.active_overlay = self.active_combo.currentText()
        self.app.start_overlay_enabled = self.start_overlay.isChecked()
        self.app.auto_switch_enabled = self.auto_switch.isChecked()
        self.app.store.check_updates_on_start = self.check_updates_start.isChecked()
        self.app.store.save()
        self._sync_autostart()
        self.app.fps_manager.set_backend(self.app.store.global_fps_backend)
        self.app.refresh_overlay()
        self.app.status.showMessage(tr("Settings saved"), 4000)
        new_lang = self.language_combo.currentData()
        if new_lang and new_lang != self.app.store.language:
            self.app.store.language = new_lang
            self.app.store.save()
            set_language(new_lang)
            self.app.rebuild_ui()
            self.app.status.showMessage(tr("Settings saved"), 4000)

    def _sync_autostart(self):
        try:
            from src import autostart
        except Exception:
            return
        want = self.autostart.isChecked()
        try:
            if want and not autostart.is_enabled():
                path = autostart.enable()
                self.app.status.showMessage(
                    tr("Autostart enabled: {path}").format(path=str(path)), 6000
                )
            elif not want and autostart.is_enabled():
                autostart.disable()
                self.app.status.showMessage(tr("Autostart disabled"), 6000)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("Autostart"), str(exc))

    def run_update_check(self):
        if self._update_worker is not None:
            return
        self.check_updates.setEnabled(False)
        self.check_updates.setText(tr("Checking..."))
        self._update_worker = _UpdateChecker(self)
        self._update_worker.found.connect(self._on_update_found)
        self._update_worker.none.connect(self._on_update_none)
        self._update_worker.start()

    def _reset_update_button(self):
        self.check_updates.setEnabled(True)
        self.check_updates.setText(tr("Check for updates"))
        self._update_worker = None

    def _on_update_found(self, release):
        self._reset_update_button()
        from src.version import __version__
        answer = QMessageBox.information(
            self,
            tr("Update available"),
            tr("gamohud {new} is available (you have {current}).\n\nOpen the download page?").format(
                new=release.get("name") or release.get("tag"), current=__version__
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._open_release(release.get("url"))

    def _on_update_none(self):
        self._reset_update_button()
        from src.version import __version__
        QMessageBox.information(
            self, tr("Check for updates"),
            tr("You are up to date (gamohud {version}).").format(version=__version__),
        )

    def _open_release(self, url):
        if not url:
            return
        import subprocess
        try:
            subprocess.Popen(open_uri_command(url))
        except Exception:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = ProfileStore()
        self.fps_manager = FPSManager(self.store.global_fps_backend)
        self.start_overlay_enabled = True
        self.auto_switch_enabled = True
        self.overlay_locked = self.store.overlay_locked
        self.keep_above = KeepAbove()
        self._geometry_receiver: GeometryReceiver | None = None
        self._external_overlay_position = False
        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.setInterval(250)
        self._geometry_save_timer.timeout.connect(self._save_overlay_geometry)
        self._overlay_restore_timer = QTimer(self)
        self._overlay_restore_timer.setSingleShot(True)
        self._overlay_restore_timer.setInterval(700)
        self._overlay_restore_timer.timeout.connect(self._restore_overlay_position)

        apply_theme(QApplication.instance(), self.store.theme)
        set_language(self.store.language)
        self.setWindowTitle("Gamohud")
        self.resize(1040, 700)
        self.setMinimumSize(900, 600)

        self.overlay = None
        self._overlay_profile_name = None

        self._build_tabs()

        if self.start_overlay_enabled:
            self.start_overlay()

        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_switch)
        self._auto_timer.start(2000)

        self._build_tray()
        self._lock_shortcut = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
        self._lock_shortcut.activated.connect(self.toggle_overlay_lock)
        self._theme_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self._theme_shortcut.activated.connect(self.toggle_theme)
        self.status = self.statusBar()
        self.status.showMessage(tr("Ready"), 3000)
        self._enable_keep_above()

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.dashboard = DashboardTab(self)
        self.overlay_tab = OverlayTab(self)
        self.apps_tab = AppsTab(self)
        self.settings_tab = SettingsTab(self)
        self.tabs.addTab(self.dashboard, tr("Dashboard"))
        self.tabs.addTab(self.overlay_tab, tr("Overlay Profiles"))
        self.tabs.addTab(self.apps_tab, tr("Applications"))
        self.tabs.addTab(self.settings_tab, tr("Settings"))
        self.setCentralWidget(self.tabs)

    def rebuild_ui(self):
        old = self.tabs
        index = old.currentIndex()
        self._build_tabs()
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
        old.deleteLater()

    def set_theme(self, mode: str):
        if mode not in THEME_MODES:
            mode = "dark"
        changed = mode != self.store.theme
        self.store.theme = mode
        if changed:
            self.store.save()
        apply_theme(QApplication.instance(), mode)
        self._sync_theme_action()
        if changed:
            QTimer.singleShot(0, self.rebuild_ui)

    def toggle_theme(self):
        concrete = resolved_theme(self.store.theme)
        self.set_theme("light" if concrete == "dark" else "dark")

    def _sync_theme_action(self):
        action = getattr(self, "act_theme", None)
        if action is None:
            return
        action.blockSignals(True)
        action.setChecked(resolved_theme(self.store.theme) == "dark")
        action.blockSignals(False)

    def current_overlay_name(self):
        return self._overlay_profile_name or self.store.active_overlay

    def _overlay_data(self):
        return collect_all(self.fps_manager.read())

    def start_overlay(self):
        profile = self.store.active_overlay_profile()
        if self.overlay is None:
            self.overlay = OverlayWindow(profile, self._overlay_data)
            self._wire_overlay(self.overlay)
        self.keep_above.set_window_title(self.overlay.windowTitle())
        self.overlay.external_position = self._external_overlay_position
        self.overlay.set_profile(profile)
        self.overlay.set_locked(self.overlay_locked)
        self._overlay_profile_name = profile.name
        self.overlay.show()
        self.keep_above.reapply()
        # Wayland maps the surface asynchronously and KWin may place it after
        # the first script run.  Re-apply once the window is really on screen.
        self._overlay_restore_timer.start()

    def _restore_overlay_position(self):
        if self.overlay is not None and self.overlay.isVisible():
            self.keep_above.reapply()

    def _wire_overlay(self, overlay):
        overlay.on_position_changed = self._overlay_moved

    def _enable_keep_above(self):
        if not self.keep_above.available:
            return
        if self.overlay is not None:
            self.keep_above.set_window_title(self.overlay.windowTitle())
        self.keep_above.set_position_provider(self._overlay_position)

        service = None
        if self._geometry_receiver is None:
            self._geometry_receiver = GeometryReceiver(
                self._overlay_geometry_received, self
            )
        if self._geometry_receiver.available:
            service = self._geometry_receiver.service
        self.keep_above.set_geometry_bus(service)

        ok, msg = self.keep_above.enable()
        self._external_overlay_position = bool(ok and service)
        if self.overlay is not None:
            self.overlay.external_position = self._external_overlay_position
        if ok:
            self.status.showMessage(tr("Overlay set to stay above other windows (KWin)"), 4000)
            self._overlay_restore_timer.start()
        else:
            self.status.showMessage(tr("Keep-above unavailable: {reason}").format(reason=msg), 6000)

    def _overlay_position(self):
        overlay = self.overlay
        if overlay is None:
            return None
        profile = getattr(overlay, "profile", None)
        if profile is None:
            return None
        screen = QApplication.primaryScreen()
        if screen is None:
            return None
        geo = screen.availableGeometry()
        return overlay_position(profile, overlay.width(), overlay.height(), geo)

    def _overlay_geometry_received(self, token, x, y, width, height):
        """KWin reported the real overlay geometry (Wayland drag/placement)."""
        overlay = self.overlay
        if overlay is None or token != overlay.windowTitle():
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = width if width > 0 else overlay.width()
        h = height if height > 0 else overlay.height()
        profile = overlay.profile
        profile.position = "custom"
        profile.x = min(max(int(x) - geo.left(), 0), max(0, geo.width() - w))
        profile.y = min(max(int(y) - geo.top(), 0), max(0, geo.height() - h))
        self._geometry_save_timer.start()

    def _save_overlay_geometry(self):
        if self.overlay is not None:
            self.store.save()

    def _overlay_moved(self):
        self.store.save()
        if self.overlay is not None:
            self.status.showMessage(tr("Overlay position saved"), 3000)

    def set_overlay_locked(self, locked: bool):
        self.overlay_locked = bool(locked)
        self.store.overlay_locked = self.overlay_locked
        self.store.save()
        if self.overlay is not None:
            self.overlay.set_locked(self.overlay_locked)
        self.overlay_tab.sync_lock_button()
        if hasattr(self, "act_move"):
            self.act_move.blockSignals(True)
            self.act_move.setChecked(not self.overlay_locked)
            self.act_move.blockSignals(False)
        self.status.showMessage(
            tr("Overlay locked") if self.overlay_locked else tr("Overlay unlocked - drag it with the mouse"),
            3000,
        )

    def toggle_overlay_lock(self):
        self.set_overlay_locked(not self.overlay_locked)

    def stop_overlay(self):
        if self.overlay is not None:
            self.overlay.hide()
            self._overlay_profile_name = None

    def refresh_overlay(self):
        if self.overlay is None:
            return
        profile = self.store.get_overlay(self._overlay_profile_name) or self.store.active_overlay_profile()
        before = self.overlay.profile
        before_geom = (before.position, before.x, before.y, before.margin)
        self.overlay.set_profile(profile)
        after_geom = (profile.position, profile.x, profile.y, profile.margin)
        if after_geom != before_geom:
            self.keep_above.reapply()

    def preview_overlay(self, profile):
        if self.overlay is None:
            self.overlay = OverlayWindow(profile, self._overlay_data)
            self._wire_overlay(self.overlay)
        self.keep_above.set_window_title(self.overlay.windowTitle())
        self.overlay.external_position = self._external_overlay_position
        self.overlay.set_profile(profile)
        self.overlay.set_locked(self.overlay_locked)
        self._overlay_profile_name = profile.name
        self.overlay.show()
        self.keep_above.reapply()
        self._overlay_restore_timer.start()

    def _auto_switch(self):
        if self.overlay is None or not self.auto_switch_enabled:
            return
        names = running_process_names(limit=200)
        matched = find_profile(self.store.app_profiles, names)
        if matched is None:
            matched = find_profile_by_window(self.store.app_profiles, active_window_title())
        target_name = None
        if matched and matched.overlay:
            target_name = matched.overlay
        if target_name is None:
            target_name = self.store.active_overlay
        if target_name != self._overlay_profile_name:
            profile = self.store.get_overlay(target_name)
            if profile is not None:
                before = self.overlay.profile
                before_geom = (before.position, before.x, before.y, before.margin)
                self.overlay.set_profile(profile)
                after_geom = (profile.position, profile.x, profile.y, profile.margin)
                self._overlay_profile_name = profile.name
                if after_geom != before_geom:
                    self.keep_above.reapply()

    def _app_icon(self):
        icon = QIcon.fromTheme("utilities-system-monitor")
        if icon.isNull():
            icon = QIcon.fromTheme("gamohud")
        if icon.isNull():
            pm = QPixmap(32, 32)
            pm.fill(QColor("#7CFC00"))
            icon = QIcon(pm)
        return icon

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        try:
            self.tray.setIcon(self._app_icon())
        except Exception:
            pass
        menu = QMenu()
        act_show = QAction(tr("Show window"), self)
        act_show.triggered.connect(self.show_window)
        act_overlay = QAction(tr("Toggle overlay"), self)
        act_overlay.triggered.connect(self.toggle_overlay)
        self.act_move = QAction(tr("Move overlay (unlock)"), self)
        self.act_move.setCheckable(True)
        self.act_move.setChecked(not self.overlay_locked)
        self.act_move.toggled.connect(lambda checked: self.set_overlay_locked(not checked))
        self.act_theme = QAction(tr("Dark theme"), self)
        self.act_theme.setCheckable(True)
        self.act_theme.setToolTip("Ctrl+Shift+D")
        self.act_theme.triggered.connect(lambda _checked=False: self.toggle_theme())
        act_quit = QAction(tr("Quit"), self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_show)
        menu.addAction(act_overlay)
        menu.addAction(self.act_move)
        menu.addSeparator()
        menu.addAction(self.act_theme)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        self._sync_theme_action()

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
            self.tray.showMessage("Gamohud", tr("Still running in tray. Use Quit to exit."))


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("Gamohud")
    app.setQuitOnLastWindowClosed(False)
    win = MainWindow()
    try:
        app.setWindowIcon(win._app_icon())
    except Exception:
        pass
    app.aboutToQuit.connect(win.fps_manager.stop)
    win.show()
    if win.overlay is not None:
        QTimer.singleShot(0, win.overlay.raise_)
        QTimer.singleShot(300, win.overlay.raise_)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
