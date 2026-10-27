"""MangoHud CSV-log FPS backend (Linux).

MangoHud can write a CSV log while a game is running.  Unlike the custom
Vulkan layer this also covers OpenGL, and it works for games launched outside
gamohud (Steam, Lutris, Heroic) as long as MangoHud logging is enabled.

The backend can either:

* launch a game with ``MANGOHUD=1`` / ``mangohud`` and an ``output_folder``
  pointing at our log directory, or
* simply read the newest CSV from a folder configured in Settings.

The CSV has a metadata line, a header line such as ``fps,frametime,...`` and
one row per sample.  We read the header and the last complete row.
"""
from __future__ import annotations

import csv
import os
import threading
import time
from pathlib import Path

from src.platform_utils import (
    IS_LINUX,
    default_mangohud_log_dir,
    host_command,
    host_run,
    host_which,
    in_flatpak,
)

from ..base import BackendStatus, FPSBackend

# MangoHud only writes the CSV when its own HUD is displayed at startup.
# ``no_display`` disables logging, so we hide the HUD a moment *after* launch
# via mangohudctl; logging continues (verified with MangoHud 0.8.4).
_HIDE_DELAY = 4.0
_MAX_LOG_AGE = 8.0

_MANAGED_START = "# >>> gamohud fps log >>>"
_MANAGED_END = "# <<< gamohud fps log <<<"
_MANAGED_KEYS = (
    "output_folder",
    "output_file",
    "autostart_log",
    "log_duration",
    "log_interval",
    "fps_only",
)


def mangohud_config_path() -> Path:
    """Host MangoHud config path (``$HOME`` is shared inside a Flatpak)."""
    return Path.home() / ".config" / "MangoHud" / "MangoHud.conf"


def set_mangohud_logging(
    enabled: bool,
    log_dir: str | Path,
    config_path: str | Path | None = None,
) -> Path:
    """Add/remove a managed MangoHud logging block.

    The block is delimited with comments so enabling and then disabling it
    does not destroy unrelated user settings.  MangoHud reads the last value
    for an option, so the block is appended at the end.
    """
    path = Path(config_path).expanduser() if config_path else mangohud_config_path()
    folder = Path(log_dir).expanduser()
    folder.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []

    cleaned: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped == _MANAGED_START:
            skipping = True
            continue
        if skipping:
            if stripped == _MANAGED_END:
                skipping = False
            continue
        cleaned.append(line)

    # A block written by the old version used bare keys.  Remove those too,
    # but only when they point at a gamohud log folder, so unrelated settings
    # survive.
    final: list[str] = []
    for line in cleaned:
        stripped = line.strip()
        key, _, value = stripped.partition("=")
        if key in _MANAGED_KEYS and "gamohud" in value:
            continue
        final.append(line)

    if enabled:
        final.extend(
            [
                "",
                _MANAGED_START,
                f"output_folder={folder}",
                "autostart_log=1",
                "log_duration=0",
                "log_interval=100",
                "fps_only=0",
                _MANAGED_END,
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(final).strip()
    path.write_text(text + "\n" if text else "", encoding="utf-8")
    return path


def mangohud_logging_enabled(
    log_dir: str | Path,
    config_path: str | Path | None = None,
) -> bool:
    path = Path(config_path).expanduser() if config_path else mangohud_config_path()
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    folder = str(Path(log_dir).expanduser())
    return _MANAGED_START in text and f"output_folder={folder}" in text


class MangoHudLogBackend(FPSBackend):
    name = "mangohud_log"
    label = "MangoHud log"
    description = (
        "Reads FPS from MangoHud's CSV log (Vulkan and OpenGL). Enable "
        "MangoHud logging in Settings and launch the game with MangoHud."
    )
    env_only = False

    def __init__(self, log_dir: str | Path | None = None):
        self._log_dir = Path(log_dir).expanduser() if log_dir else default_mangohud_log_dir()
        self._started_at = 0.0
        self._last_path: Path | None = None
        self._last_key: tuple | None = None
        self._last_data: dict | None = None
        self._hide_timer: threading.Timer | None = None
        self.hide_hud = True
        self.max_age = _MAX_LOG_AGE

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def set_log_dir(self, path: str | Path | None) -> None:
        value = Path(path).expanduser() if path else default_mangohud_log_dir()
        if value != self._log_dir:
            self._log_dir = value
            self._last_path = None
            self._last_key = None
            self._last_data = None

    def set_hide_hud(self, hide: bool) -> None:
        self.hide_hud = bool(hide)

    def available(self) -> BackendStatus:
        if not IS_LINUX:
            return BackendStatus(False, "MangoHud log is Linux-only")
        if host_which("mangohud") or host_which("mangohudctl") or host_which("mangoapp"):
            return BackendStatus(True)
        return BackendStatus(
            False,
            "MangoHud is not installed. Install MangoHud or use another backend.",
        )

    # -- launching --------------------------------------------------------
    def _config_string(self) -> str:
        folder = self._log_dir
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        wanted = {
            "output_folder": str(folder),
            "autostart_log": "1",
            "log_duration": "0",
            "log_interval": "100",
            "fps_only": "0",
        }
        kept: list[str] = []
        for token in (os.environ.get("MANGOHUD_CONFIG") or "").split(","):
            token = token.strip()
            if not token:
                continue
            key = token.split("=", 1)[0].strip()
            if key in wanted:
                continue
            kept.append(token)
        kept.extend(f"{key}={value}" for key, value in wanted.items())
        return ",".join(kept)

    def launch_env(self, profile=None) -> dict:
        return {"MANGOHUD": "1", "MANGOHUD_CONFIG": self._config_string()}

    def command_prefix(self, profile=None) -> list:
        exe = host_which("mangohud")
        if not exe:
            return []
        if profile is not None:
            existing = [str(x) for x in (getattr(profile, "command_prefix", None) or [])]
            if any(Path(x).name == "mangohud" for x in existing):
                return []
        if in_flatpak():
            # Environment variables are not forwarded by flatpak-spawn, so
            # pass the MangoHud config through env(1) explicitly.
            return [
                *host_command(
                    [
                        "env",
                        "MANGOHUD=1",
                        f"MANGOHUD_CONFIG={self._config_string()}",
                        "mangohud",
                    ]
                )
            ]
        return ["mangohud"]

    def start(self, command=None, profile=None) -> None:
        self.stop()
        self._started_at = time.time()
        self._last_path = None
        self._last_key = None
        self._last_data = None
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if self.hide_hud:
            timer = threading.Timer(_HIDE_DELAY, self._hide_mangohud_hud)
            timer.daemon = True
            self._hide_timer = timer
            timer.start()

    def _hide_mangohud_hud(self) -> None:
        try:
            host_run(["mangohudctl", "set", "no_display", "true"], timeout=3)
        except Exception:
            pass

    def stop(self) -> None:
        timer = self._hide_timer
        self._hide_timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
        self._started_at = 0.0
        self._last_path = None
        self._last_key = None
        self._last_data = None

    # -- reading ----------------------------------------------------------
    def _newest_file(self, require_fresh: bool = True) -> Path | None:
        try:
            entries = list(self._log_dir.glob("*.csv"))
        except OSError:
            return None
        now = time.time()
        floor = max(self._started_at - 2.0, now - self.max_age) if require_fresh else 0.0
        if not require_fresh:
            floor = 0.0
        candidates: list[tuple[float, Path]] = []
        for path in entries:
            try:
                if not path.is_file():
                    continue
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime < floor:
                continue
            candidates.append((mtime, path))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def read(self) -> dict | None:
        path = self._newest_file(require_fresh=True)
        if path is None:
            return None
        try:
            stat = path.stat()
        except OSError:
            return None
        key = (str(path), stat.st_mtime_ns, stat.st_size)
        if key == self._last_key:
            return dict(self._last_data) if self._last_data else None
        data = _read_mangohud_csv(path)
        self._last_path = path
        self._last_key = key
        self._last_data = data
        return dict(data) if data else None


def _read_mangohud_csv(path: Path) -> dict | None:
    """Parse the ``fps``/``frametime`` columns from a MangoHud CSV file."""
    try:
        with path.open("rb") as handle:
            head = handle.read(8192).decode("utf-8-sig", errors="replace")
            header = None
            for line in head.splitlines():
                row = next(csv.reader([line]), [])
                lowered = [cell.strip().lower() for cell in row]
                if "fps" in lowered:
                    header = lowered
                    break
            if header is None:
                return None
            fps_idx = header.index("fps")
            frame_idx = header.index("frametime") if "frametime" in header else None

            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 32768))
            tail = handle.read().decode("utf-8", errors="replace").splitlines()
    except (OSError, csv.Error):
        return None

    for line in reversed(tail):
        row = next(csv.reader([line]), [])
        if len(row) <= fps_idx:
            continue
        try:
            fps = float(row[fps_idx])
        except (TypeError, ValueError):
            continue
        data: dict = {"fps": round(fps, 1)}
        if frame_idx is not None and frame_idx < len(row):
            try:
                data["frametime"] = round(float(row[frame_idx]), 2)
            except (TypeError, ValueError):
                pass
        return data
    return None
