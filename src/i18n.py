"""Minimal runtime localization for the GUI.

Only the GUI is translated; the on-overlay text (metric names/values) is left
untouched on purpose. Translations are keyed by the English source string, so
``tr("Save")`` returns "Save" for English and "Сохранить" for Russian.
"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {"en": "English", "ru": "Русский"}

_current: str = "en"

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
        # common buttons
        "Save": "Сохранить",
        "New": "Создать",
        "Duplicate": "Дублировать",
        "Delete": "Удалить",
        "Launch": "Запустить",
        "Set active": "Сделать активным",
        "Apply / Preview": "Применить / Просмотр",
        # overlay tab
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
        " (active)": " (активен)",
        "(unnamed)": "(без имени)",
        "A profile with that name exists.": "Профиль с таким именем уже существует.",
        "Saved overlay profile '{name}'": "Профиль оверлея «{name}» сохранён",
        "Delete '{name}'?": "Удалить «{name}»?",
        # apps tab
        "Application profile": "Профиль приложения",
        "Match processes": "Совпадение процессов",
        "Executable / command": "Исполняемый файл / команда",
        "Game process name": "Имя процесса игры",
        "Arguments": "Аргументы",
        "Working dir": "Рабочая папка",
        "Run with gamemoderun": "Запуск через gamemoderun",
        "Command prefix": "Префикс команды",
        "Environment": "Окружение",
        "Import from installed games": "Импорт из установленных игр",
        "Detected game": "Найденная игра",
        "Import selected game": "Импортировать выбранную игру",
        "Select or save a profile first.": "Сначала выберите или сохраните профиль.",
        "Launch failed": "Не удалось запустить",
        "Launched: {command}": "Запущено: {command}",
        "Saved app profile '{name}'": "Профиль приложения «{name}» сохранён",
        "Running process": "Запущенный процесс",
        "Process name:": "Имя процесса:",
        # placeholders
        "comma-separated patterns, e.g. steam_app_*, wine*": "шаблоны через запятую, напр. steam_app_*, wine*",
        "optional, for PresentMon: game exe name, e.g. game.exe": "необязательно, для PresentMon: имя exe игры, напр. game.exe",
        "extra command prefix (shell words)": "доп. префикс команды (слова оболочки)",
        # settings tab
        "Global FPS backend": "Глобальный бэкенд FPS",
        "Backend": "Бэкенд",
        "Download PresentMon (Windows)...": "Скачать PresentMon (Windows)...",
        "Downloading...": "Скачивание...",
        "General": "Общие",
        "Language": "Язык",
        "Start overlay when the app launches": "Показывать оверлей при запуске приложения",
        "Auto-switch overlay by running process": "Автопереключение оверлея по процессу",
        "Default overlay profile": "Профиль оверлея по умолчанию",
        "Unavailable: {reason}": "Недоступно: {reason}",
        "PresentMon is only needed on Windows.\nOn Linux use the Vulkan layer, gamescope or mesa_gallium backends.": (
            "PresentMon нужен только в Windows.\n"
            "В Linux используйте Vulkan-слой, gamescope или бэкенд mesa_gallium."
        ),
        "PresentMon saved: {path}": "PresentMon сохранён: {path}",
        "PresentMon download failed": "Не удалось скачать PresentMon",
        "Settings saved": "Настройки сохранены",
        # tray
        "Show window": "Показать окно",
        "Toggle overlay": "Показать/скрыть оверлей",
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
