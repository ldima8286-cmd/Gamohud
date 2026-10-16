# gamohud

Автономное десктопное приложение (Qt GUI) с оверлеем производительности поверх
окон. **MangoHud не требуется** — метрики собираются напрямую из `/proc` и
`/sys` (а для NVIDIA — через `nvidia-smi`), профили хранятся в собственном
формате, а игровой FPS подключается сменными бэкендами.

## Возможности

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
| `vulkan_layer`    | собственный Vulkan implicit layer пишет FPS в `$XDG_RUNTIME_DIR/gamohud-fps.json` | интерфейс готов, C-слой ещё не собран |
| `gamescope`       | запуск внутри gamescope, чтение таймингов | экспериментально |
| `mesa_gallium`    | `GALLIUM_HUD` для AMD/Intel OpenGL | только переменные окружения |

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
- Linux-специфичные FPS-бэкенды (`gamescope`, `mesa_gallium`) и Vulkan implicit
  layer на других ОС просто помечаются как недоступные.
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
