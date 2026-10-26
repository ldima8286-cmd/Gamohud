"""Minimal runtime localization for the GUI.

Only the GUI is translated; the on-overlay text (metric names/values) is left
untouched on purpose. Translations are keyed by the English source string, so
``tr("Save")`` returns "Save" for English and "Сохранить" for Russian.
"""
from __future__ import annotations

import locale
import os

LANGUAGES: dict[str, str] = {"en": "English", "ru": "Русский"}

_current: str = "en"


def system_language() -> str:
    """Best-effort language from the desktop locale, defaulting to English."""
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        for candidate in os.environ.get(name, "").split(":"):
            code = candidate.split(".")[0].split("@")[0].replace("-", "_").split("_")[0]
            if code.lower() in LANGUAGES:
                return code.lower()
    try:
        locale_name = locale.getlocale()[0] or ""
    except Exception:
        locale_name = ""
    code = locale_name.split("_")[0].split("-")[0].lower()
    return code if code in LANGUAGES else "en"


_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        # tabs / app
        "Dashboard": "Панель",
        "Overlay Profiles": "Профили оверлея",
        "Applications": "Приложения",
        "Settings": "Настройки",
        "Ready": "Готово",
        # dashboard
        "Live metrics": "Метрики",
        "N/A": "н/д",
        "FPS backend": "Бэкенд FPS",
        "Overlay profile": "Профиль оверлея",
        "Live system metrics from /proc, /sys and your GPU driver.": (
            "Системные метрики в реальном времени из /proc, /sys и драйвера GPU."
        ),
        "FPS is unavailable: {reason}. Pick another backend in Settings.": (
            "FPS недоступен: {reason}. Выберите другой бэкенд в настройках."
        ),
        "Open Settings": "Открыть настройки",
        # common buttons
        "Save": "Сохранить",
        "New": "Создать",
        "Duplicate": "Дублировать",
        "Delete": "Удалить",
        "Launch": "Запустить",
        "Set active": "Сделать активным",
        "Apply / Preview": "Применить / Просмотр",
        "Apply": "Применить",
        "All": "Все",
        "None": "Ничего",
        "Profiles": "Профили",
        "Pick a color": "Выберите цвет",
        "unavailable": "недоступен",
        # overlay tab
        "Profiles and appearance of the on-screen overlay.": (
            "Профили и внешний вид оверлея поверх игры."
        ),
        "Appearance": "Внешний вид",
        "Name": "Имя",
        "Position": "Позиция",
        "Custom x / y": "Свои x / y",
        "Margin": "Отступ",
        "Font": "Шрифт",
        "Font size": "Размер шрифта",
        "Bold": "Жирный",
        "Opacity": "Прозрачность",
        "Background opacity": "Прозрачность фона",
        "Corner radius": "Радиус углов",
        "Refresh (ms)": "Обновление (мс)",
        "Click-through (ignore mouse)": "Сквозной клик (игнорировать мышь)",
        "Show FPS graph": "График FPS",
        "Value color": "Цвет значений",
        "Label color": "Цвет подписей",
        "Accent color": "Акцентный цвет",
        "Background color": "Цвет фона",
        "Metrics": "Метрики",
        "Colors": "Цвета",
        "Choose what the overlay shows.": "Выберите, что показывать в оверлее.",
        "Presets": "Пресеты",
        "Apply a ready-made metric set to this profile.": (
            "Применить готовый набор метрик к этому профилю."
        ),
        "Applied preset '{name}'": "Применён пресет «{name}»",
        "Auto-switch follows the matched running game.": (
            "Автопереключение следует за запущенной игрой."
        ),
        " (active)": " (активен)",
        "(unnamed)": "(без имени)",
        "A profile with that name exists.": "Профиль с таким именем уже существует.",
        "Saved overlay profile '{name}'": "Профиль оверлея «{name}» сохранён",
        "Delete '{name}'?": "Удалить «{name}»?",
        "Unlock to move": "Разблокировать для перемещения",
        "Lock overlay": "Заблокировать оверлей",
        "Unlock, then drag the overlay with the mouse to place it. "
        "Ctrl+Shift+L toggles the lock.": (
            "Разблокируйте и перетащите оверлей мышью, чтобы разместить его. "
            "Ctrl+Shift+L переключает блокировку."
        ),
        "Ctrl+Shift+L toggles the lock.": "Ctrl+Shift+L переключает блокировку.",
        "Overlay locked": "Оверлей заблокирован",
        "Overlay unlocked - drag it with the mouse": "Оверлей разблокирован — перетащите его мышью",
        "Overlay position saved": "Позиция оверлея сохранена",
        "Overlay set to stay above other windows (KWin)": "Оверлей закреплён поверх других окон (KWin)",
        "Keep-above unavailable: {reason}": "Закрепление поверх окон недоступно: {reason}",
        # apps tab
        "Application profile": "Профиль приложения",
        "Match processes": "Процессы",
        "Executable / command": "Команда",
        "Game process name": "Процесс игры",
        "Arguments": "Аргументы",
        "Working dir": "Рабочая папка",
        "Run with gamemoderun": "gamemoderun",
        "Command prefix": "Префикс",
        "Environment": "Окружение",
        "Import from installed games": "Импорт игр",
        "Detected game": "Игра",
        "Import selected game": "Импортировать",
        "Select or save a profile first.": "Сначала выберите или сохраните профиль.",
        "Launch failed": "Не удалось запустить",
        "Launched: {command}": "Запущено: {command}",
        "Saved app profile '{name}'": "Профиль приложения «{name}» сохранён",
        "Running process": "Запущенный процесс",
        "Process name:": "Имя процесса:",
        "From running process": "Из запущенного процесса",
        "Game profiles, launch options and automatic overlay switching.": (
            "Профили игр, параметры запуска и автопереключение оверлея."
        ),
        "Profiles are saved with the Save button.": (
            "Профили сохраняются кнопкой «Сохранить»."
        ),
        # placeholders
        "comma-separated patterns, e.g. steam_app_*, wine*": "шаблоны через запятую, напр. steam_app_*, wine*",
        "optional, for PresentMon: game exe name, e.g. game.exe": "необязательно, для PresentMon: имя exe игры, напр. game.exe",
        "extra command prefix (shell words)": "доп. префикс команды (слова оболочки)",
        # settings tab
        "Global FPS backend": "Глобальный бэкенд FPS",
        "Global FPS backend, behavior and updates.": (
            "Бэкенд FPS по умолчанию, поведение и обновления."
        ),
        "Backend": "Бэкенд",
        # backend descriptions / availability reasons
        "Our own implicit Vulkan layer. Real FPS in Vulkan/DXVK/VKD3D apps.": (
            "Собственный неявный Vulkan-слой. Настоящий FPS в приложениях Vulkan/DXVK/VKD3D."
        ),
        "Run the app inside gamescope (nested compositor). Experimental stats.": (
            "Запуск приложения внутри gamescope (вложенный композитор). "
            "Экспериментальная статистика."
        ),
        "Draws Mesa's own HUD (AMD/Intel OpenGL). Env only; not shown in overlay.": (
            "HUD Mesa (AMD/Intel OpenGL). Только переменные окружения; не показывается в оверлее."
        ),
        "No FPS measurement. Shows system metrics only.": (
            "Без измерения FPS. Показываются только системные метрики."
        ),
        "Intel PresentMon ETW capture. Covers DirectX 9/10/11/12, OpenGL and Vulkan. Windows only; needs admin or Performance Log Users.": (
            "Захват ETW через Intel PresentMon. DirectX 9/10/11/12, OpenGL и Vulkan. "
            "Только Windows; нужны права администратора или Performance Log Users."
        ),
        "gamohud Vulkan layer not built/installed": "Vulkan-слой gamohud не собран/не установлен",
        "gamescope is Linux-only": "gamescope доступен только в Linux",
        "gamescope not installed": "gamescope не установлен",
        "Windows only": "Только Windows",
        "no AMD/Intel free-driver GPU detected": (
            "Не найдена видеокарта AMD/Intel на свободном драйвере"
        ),
        "PresentMon.exe not found (run tools/fetch_presentmon.py or set GAMOHUD_PRESENTMON)": (
            "PresentMon.exe не найден (запустите tools/fetch_presentmon.py "
            "или задайте GAMOHUD_PRESENTMON)"
        ),
        "Download PresentMon (Windows)...": "Скачать PresentMon (Windows)...",
        "Downloading...": "Скачивание...",
        "General": "Общие",
        "Updates": "Обновления",
        "Language": "Язык",
        "Start overlay when the app launches": "Показывать оверлей при запуске приложения",
        "Auto-switch overlay by running process": "Автопереключение оверлея по процессу",
        "Default overlay profile": "Оверлей по умолчанию",
        "Launch gamohud at login": "Запускать gamohud при входе в систему",
        "Check for updates": "Проверить обновления",
        "Check for updates on startup": "Проверять обновления при запуске",
        "Checking...": "Проверка...",
        "Update available": "Доступно обновление",
        "You are up to date (gamohud {version}).": "У вас последняя версия (gamohud {version}).",
        "gamohud {new} is available (you have {current}).\n\nOpen the download page?": (
            "Доступна версия gamohud {new} (у вас {current}).\n\nОткрыть страницу загрузки?"
        ),
        "Settings are saved with the Save button.": "Настройки сохраняются кнопкой «Сохранить».",
        "Unavailable: {reason}": "Недоступно: {reason}",
        "PresentMon is only needed on Windows.\nOn Linux use the Vulkan layer, gamescope or mesa_gallium backends.": (
            "PresentMon нужен только в Windows.\n"
            "В Linux используйте Vulkan-слой, gamescope или бэкенд mesa_gallium."
        ),
        "PresentMon saved: {path}": "PresentMon сохранён: {path}",
        "PresentMon download failed": "Не удалось скачать PresentMon",
        "Settings saved": "Настройки сохранены",
        "Autostart": "Автозапуск",
        "Autostart enabled: {path}": "Автозапуск включён: {path}",
        "Autostart disabled": "Автозапуск отключён",
        # overlay presets
        "Compact": "Компактный",
        "Detailed": "Подробный",
        "Power": "Энергопотребление",
        "Memory": "Память",
        "Network": "Сеть",
        "Smoothness": "Плавность",
        "Just FPS and the two loads": "Только FPS и две нагрузки",
        "FPS, frametime, loads, temperatures and memory": (
            "FPS, frametime, нагрузки, температуры и память"
        ),
        "Clocks, power draw and fan speeds": "Частоты, энергопотребление и кулеры",
        "VRAM, RAM and swap": "VRAM, RAM и swap",
        "FPS, network and disk throughput": "FPS, сеть и диски",
        "FPS with 1% and 0.1% low frame rates": "FPS с 1% и 0.1% low",
        # tray
        "Show window": "Показать окно",
        "Toggle overlay": "Показать/скрыть оверлей",
        "Move overlay (unlock)": "Перемещать оверлей",
        "Quit": "Выход",
        "Gamohud": "Gamohud",
        "Still running in tray. Use Quit to exit.": "Приложение свёрнуто в трей. Для выхода выберите «Выход».",
    },
    "en": {},
}


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else "en"


def get_language() -> str:
    return _current


def tr(text: str) -> str:
    """Translate an English source string to the current language."""
    return _STRINGS.get(_current, {}).get(text, text)
