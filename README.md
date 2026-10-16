# gamohud

Автономное десктопное приложение (Qt GUI) с оверлеем производительности поверх окон. **MangoHud не требуется** — метрики собираются напрямую из `/proc` и `/sys` (а для NVIDIA — через `nvidia-smi`), профили хранятся в собственном формате, а игровой FPS подключается сменными бэкендами.

## Быстрый старт

**Самый простой путь (готовые бинарники)**

1. Зайди в [Releases](https://github.com/ldima8286-cmd/mangohud-preset-manager-tui/releases).
2. Скачай архив под свою ОС: `gamohud-windows-x64.zip` (Windows) или `gamohud-linux-x64.tar.gz` (Linux).
3. Распакуй и запусти `gamohud-gui.exe` (Windows) или `gamohud-gui` (Linux).

**Linux/macOS (одна команда из терминала)**

```bash
curl -fsSL https://raw.githubusercontent.com/ldima8286-cmd/mangohud-preset-manager-tui/main/install.sh | sh
```

**Из исходников (скачал репозиторий)**

```bash
git clone https://github.com/ldima8286-cmd/mangohud-preset-manager-tui.git
cd mangohud-preset-manager-tui

# Linux/macOS
./run-gui.sh
# Windows
run-gui.bat
```

Первый запуск автоматически создаст `.venv` и поставит зависимости. Компилятор нужен **только** если ты хочешь собрать свой Vulkan-слой (см. ниже).

# Возможности

- **Оверлей в стиле MangoHud**: CPU/GPU load/temp/power/freq, VRAM/RAM, swap,
  сеть, диски, FPS/frametime. Настраиваются положение, шрифт, цвета, прозрачность,
  скругление, click-through и набор метрик.
- **Профили оверлея** (не только для игр): несколько наборов оформления,
  переключение вручную или автоматически по запущенному процессу.
- **Профили приложений**: команда/аргументы, рабочая папка, переменные окружения,
  command-prefix, Game Mode, привязка оверлея и FPS-бэкенда.
- **Запуск в один клик** из GUI и из командной строки через `gamohud-run`.
- **Трей-иконка**, статус в реальном времени.

## FPS-бэкенды (сменные)

Настоящий FPS игры невозможно получить извне процесса, поэтому измерение
подключается одним из способов:

| Бэкенд            | Что делает | Статус |
|-------------------|------------|--------|
| `null`            | только системные метрики | всегда доступен |
| `vulkan_layer`    | собственный Vulkan implicit layer (C) считает кадры и пишет FPS в `gamohud-fps.json` | исходники в `layer/`, нужно собрать |
| `presentmon`      | Intel PresentMon по ETW: DirectX 9/10/11/12, OpenGL и Vulkan | Windows; нужен PresentMon.exe и права администратора |
| `gamescope`       | запуск внутри gamescope, чтение таймингов | экспериментально |
| `mesa_gallium`    | `GALLIUM_HUD` для AMD/Intel OpenGL | только переменные окружения |

### PresentMon на Windows (FPS не только в Vulkan-играх)

Vulkan-слой видит только Vulkan-приложения, а большинство Windows-игр работает на
DirectX. Для них используется `presentmon`: наш помощник запускает Intel
**PresentMon** (открытый, MIT) в режиме ETW и парсит его вывод в `gamohud-fps.json`.

Скачать бинарник PresentMon в `tools/presentmon/`:
```
python tools/fetch_presentmon.py
```
Либо укажите существующий: `GAMOHUD_PRESENTMON=C:\path\PresentMon.exe`. Файл можно
задать и вручную рядом с приложением. Захват требует прав администратора или
членства в группе «Performance Log Users» (иначе будет «access denied»).

Полезные переменные окружения: `GAMOHUD_PROCESS_NAME` — имя exe игры (нужно для
игр, запускаемых через Steam/Lutris, где имя процесса заранее неизвестно, иначе
бэкенд ловит все процессы и выбирает активный); `GAMOHUD_PRESENTMON_ADMIN=1` —
попросить PresentMon перезапуститься с повышением прав.

### Сборка своего Vulkan-слоя (настоящий FPS)

Слой написан на C и перехватывает `vkQueuePresentKHR`. Требуется компилятор и
Vulkan-заголовки.

Linux:
```
./layer/build_layer.sh --install
```
Windows (Vulkan SDK, `VULKAN_SDK` задан):
```
layer\build_layer.bat
```
Подробности — в `layer/README.md`.

## Кроссплатформенность

Приложение работает на **Windows**, **Linux** и **macOS**.

- Портативные метрики (CPU/RAM/swap/сеть/диски) собираются через `psutil`.
- NVIDIA-карты читаются через `nvidia-smi` на всех ОС; на Linux AMD/Intel —
  через sysfs/hwmon; на Windows — best-effort через LibreHardwareMonitor (WMI),
  если он запущен (для температур/нагрузки AMD/Intel нужен запущенный
  LibreHardwareMonitor; NVIDIA работает и без него).
- Пути конфигурации выбираются по ОС автоматически:
  Windows `%APPDATA%\gamohud`, macOS `~/Library/Application Support/gamohud`,
  Linux `$XDG_CONFIG_HOME/gamohud` (по умолчанию `~/.config/gamohud`).
- Linux-специфичные FPS-бэкенды (`gamescope`, `mesa_gallium`) недоступны на других
  ОС; Vulkan implicit layer доступен на всех ОС (нужно собрать); `presentmon`
  доступен только на Windows.
- Game Mode (`gamemoderun`) доступен только на Linux.

## Запуск из исходников

Linux:
```
./run-gui.sh          # GUI
./run-wrapper.sh ...  # CLI-обёртка gamohud-run
```

Windows:
```
run-gui.bat           # GUI
run-wrapper.bat ...   # CLI-обёртка gamohud-run
```

## Вкладки

- **Dashboard** — живые метрики и статус выбранного бэкенда/оверлея.
- **Overlay Profiles** — редактор профилей оверлея с предпросмотром.
- **Applications** — профили приложений, запуск, импорт из установленных игр
  (Steam/Lutris/Bottles/Heroic) и из запущенных процессов.
- **Settings** — глобальный FPS-бэкенд, профиль оверлея по умолчанию,
  авто-переключение, запуск оверлея.

## gamohud-run

```
gamohud-run --list
gamohud-run --profile "Steam game"
gamohud-run --backend vulkan_layer --env DXVK_HUD=0 -- mygame --fullscreen
```

Обёртка подставляет окружение выбранного бэкенда, env из профиля, Game Mode и
command-prefix, после чего `exec`-запускает приложение.

## Сборка и установка

Linux:
```
./build-gui.sh     # сборка dist/gamohud-gui (PyInstaller)
./install.sh       # установка в ~/.local + .desktop ярлык + gamohud-run
```

Windows:
```
build-gui.bat      # сборка dist\gamohud-gui\gamohud-gui.exe
```

Готовый `gamohud-gui.exe` самодостаточен — переносите папку `dist\gamohud-gui`
целиком. Для температур/нагрузки AMD/Intel на Windows опционально установите
`pip install "gamohud[windows]"` и запустите LibreHardwareMonitor.

Linux-сборка требует наличия системного glibc (библиотеки из `/run/host`
намеренно не бандлятся, чтобы не тащить несовместимую версию).

## Статус

WIP
