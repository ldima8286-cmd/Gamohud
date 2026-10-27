"""Standalone overlay renderer for KDE Wayland (host process).

The GUI normally draws the overlay itself.  On KDE Wayland an ordinary window
cannot stay above an *active fullscreen* window, so the GUI can start this
small helper with the host Python/PySide6.  The helper creates the same
``OverlayWindow`` widget, but attaches it to the Wayland ``overlay`` layer via
``layer-shell-qt``.  State is exchanged through two small JSON files in the
shared runtime directory (``~/.local/share/gamohud/runtime``):

* ``overlay.json``           profile/metrics/visible/locked (GUI -> helper)
* ``overlay-position.json``  dragged position (helper -> GUI)

Run it manually for diagnostics with ``--state`` and ``--position``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.layer_shell import LayerShellController  # noqa: E402
from src.overlay import OverlayWindow  # noqa: E402
from src.profiles import OverlayProfile  # noqa: E402


class LayerOverlay(OverlayWindow):
    """The normal overlay, positioned by layer-shell instead of KWin."""

    def __init__(self, profile, data_provider, title):
        super().__init__(profile, data_provider, window_title=title)
        self._layer = LayerShellController(self)
        self._dragging = False
        self._drag_start_global = None
        self._drag_start_xy = None
        self._apply_layer()

    def _apply_layer(self):
        if getattr(self, "_layer", None) is not None:
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry() if screen is not None else None
            self._layer.apply(
                self.profile,
                self.width(),
                self.height(),
                geo.width() if geo is not None else 0,
                geo.height() if geo is not None else 0,
            )

    def _reposition(self, force: bool = False):
        # A layer-shell surface is positioned by anchors/margins, never by
        # QWidget.move().  Keep the content sized; __init__/refresh update the
        # layer geometry.
        self._fit_size()
        self._apply_layer()

    def refresh(self):
        super().refresh()
        self._apply_layer()

    def set_profile(self, profile):
        super().set_profile(profile)
        self._apply_layer()

    def set_locked(self, locked):
        super().set_locked(locked)
        if locked:
            self._dragging = False
            self._drag_start_global = None

    def mousePressEvent(self, event):
        if not self.locked and event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_start_xy = (int(self.profile.x), int(self.profile.y))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._dragging and self._drag_start_global is not None
                and event.buttons() & Qt.LeftButton):
            pos = event.globalPosition().toPoint()
            dx = pos.x() - self._drag_start_global.x()
            dy = pos.y() - self._drag_start_global.y()
            screen = QApplication.primaryScreen()
            max_x = max(0, (screen.availableGeometry().width() if screen else 10000)
                        - self.width())
            max_y = max(0, (screen.availableGeometry().height() if screen else 10000)
                        - self.height())
            x, y = self._drag_start_xy
            self.profile.position = "custom"
            self.profile.x = min(max(0, int(x + dx)), max_x)
            self.profile.y = min(max(0, int(y + dy)), max_y)
            self._apply_layer()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.LeftButton:
            self._dragging = False
            self._drag_start_global = None
            self._emit_position_changed()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class HelperApp:
    def __init__(self, app: QApplication, state_path: Path, position_path: Path):
        self.app = app
        self.state_path = state_path
        self.position_path = position_path
        self.overlay: LayerOverlay | None = None
        self._metrics: dict = {}
        self._profile_key: str | None = None
        self._locked: bool | None = None
        self._visible: bool | None = None
        self._last_state = 0.0
        self._missing_since = time.monotonic()
        self._last_error = ""

        self._read_timer = QTimer(self.app)
        self._read_timer.setInterval(150)
        self._read_timer.timeout.connect(self._poll)
        self._read_timer.start()

    def _poll(self):
        try:
            raw = self.state_path.read_text(encoding="utf-8")
            state = json.loads(raw)
            if not isinstance(state, dict):
                return
        except FileNotFoundError:
            if self._last_state == 0.0 and time.monotonic() - self._missing_since > 10:
                self.app.quit()
            return
        except Exception as exc:
            self._log(f"state read: {exc}")
            return

        self._last_state = time.monotonic()
        ts = float(state.get("ts") or 0.0)
        if ts and time.time() - ts > 10:
            self._log("GUI heartbeat is stale; exiting")
            self.app.quit()
            return

        profile_data = state.get("profile") or {}
        profile_key = json.dumps(profile_data, sort_keys=True)
        metrics = state.get("metrics") or {}
        if not isinstance(metrics, dict):
            metrics = {}
        self._metrics = metrics
        locked = bool(state.get("locked", True))
        visible = bool(state.get("visible", True))

        if self.overlay is None:
            profile = OverlayProfile.from_dict(profile_data)
            title = str(state.get("title") or "gamohud-layer")
            self.overlay = LayerOverlay(profile, self._data, title)
            self.overlay.on_position_changed = self._write_position
            self._profile_key = profile_key
            self._locked = locked
            self._visible = visible
            self.overlay.set_locked(locked)
            if visible:
                self.overlay.show()
            else:
                self.overlay.hide()
            self._log(f"started profile={profile.name} size={self.overlay.size().width()}x{self.overlay.size().height()}")
            return

        if profile_key != self._profile_key:
            self._profile_key = profile_key
            self.overlay.set_profile(OverlayProfile.from_dict(profile_data))
        if locked != self._locked:
            self._locked = locked
            self.overlay.set_locked(locked)
        if visible != self._visible:
            self._visible = visible
            if visible:
                self.overlay.show()
            else:
                self.overlay.hide()

    def _data(self):
        return self._metrics

    def _write_position(self):
        overlay = self.overlay
        if overlay is None:
            return
        data = {
            "name": overlay.profile.name,
            "position": "custom",
            "x": int(overlay.profile.x),
            "y": int(overlay.profile.y),
            "ts": time.time(),
        }
        try:
            self.position_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.position_path.with_suffix(self.position_path.suffix + ".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(self.position_path)
        except Exception as exc:
            self._log(f"position write: {exc}")

    def _log(self, text: str):
        # Do not spam identical errors.
        if text == self._last_error:
            return
        self._last_error = text
        print(f"gamohud overlay helper: {text}", file=sys.stderr, flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--position", required=True)
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("gamohud-overlay")
    app.setQuitOnLastWindowClosed(False)
    # Keep the controller alive for the whole event loop; otherwise Python may
    # collect it and its timer stops firing.
    helper = HelperApp(app, Path(args.state), Path(args.position))
    _ = helper
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
