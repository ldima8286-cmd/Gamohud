# gamohud

Автономное десктопное приложение (Qt GUI) с оверлеем производительности поверх окон. **MangoHud не обязателен для системных метрик** — они собираются напрямую из `/proc` и `/sys` (а для NVIDIA — через `nvidia-smi`), профили хранятся в собственном формате. Игровой FPS подключается сменными бэкендами: на Linux проще всего читать CSV-лог MangoHud, также есть собственный Vulkan-слой.

## Быстрый старт

**Самый простой путь (готовые бинарники)**

1. Зайди в [Releases](https://github.com/ldima8286-cmd/Gamohud/releases).
2. Скачай архив под свою ОС: `gamohud-windows-x64.zip` (Windows) или `gamohud-linux-x64.tar.gz` (Linux).
3. Распакуй и запусти `gamohud-gui.exe` (Windows) или `gamohud-gui` (Linux).

**Linux/macOS (одна команда из терминала)**

```bash
curl -fsSL https://raw.githubusercontent.com/ldima8286-cmd/Gamohud/main/install.sh | sh
```

**Из исходников (скачал репозиторий)**

```bash
git clone https://github.com/ldima8286-cmd/Gamohud.git
cd Gamohud

# Linux/macOS
./run-gui.sh
# Windows
run-gui.bat
```

Первый запуск автоматически создаст `.venv` и поставит зависимости. Компилятор нужен **только** если ты хочешь собрать свой Vulkan-слой (см. ниже).

# Возможности

- **Оверлей производительности**: CPU/GPU load/temp/power/freq, VRAM/RAM, swap,
  сеть, диски, FPS/frametime. Настраиваются положение, шрифт, цвета, прозрачность,
  скругление, click-through и набор метрик.
- **Пресеты раскладки**: готовые наборы метрик в один клик (Compact, Detailed,
  Power, Memory, Network, Smoothness).
- **Плавность кадров**: кроме FPS показываются среднее и «низкие» значения
  (1% low / 0.1% low) по скользящему окну — видно не только средний, но и
  «проседающий» FPS.
- **Профили оверлея** (не только для игр): несколько наборов оформления,
  переключение вручную или автоматически по запущенному процессу **или по
  заголовку активного окна**.
- **Автозапуск при входе в систему** (Linux XDG autostart, Windows Run, macOS
  LaunchAgent) — включается галочкой в настройках.
- **Проверка обновлений**: вручную из настроек и (опционально) на старте.
- **Профили приложений**: команда/аргументы, рабочая папка, переменные окружения,
  command-prefix, Game Mode, привязка оверлея и FPS-бэкенда.
- **Запуск в один клик** из GUI и из командной строки через `gamohud-run`.
- **Современная светлая и тёмная тема**: переключение в настройках, из трея
  или по `Ctrl+Shift+D`.
- **Трей-иконка**, статус в реальном времени.

## FPS-бэкенды (сменные)

Настоящий FPS игры невозможно получить извне процесса, поэтому измерение
подключается одним из способов:

| Бэкенд            | Что делает | Статус |
|-------------------|------------|--------|
| `null`            | только системные метрики | всегда доступен |
| `mangohud_log`    | читает CSV-лог MangoHud (`fps`, `frametime`); работает с Vulkan и OpenGL, в том числе с играми из Steam/Lutris | Linux; нужен установленный MangoHud |
| `vulkan_layer`    | собственный Vulkan implicit layer (C) считает кадры и пишет FPS в `gamohud-fps.json` | исходники в `layer/`, нужно собрать |
| `presentmon`      | Intel PresentMon по ETW: DirectX 9/10/11/12, OpenGL и Vulkan | Windows; нужен PresentMon.exe и права администратора |
| `gamescope`       | запуск внутри gamescope, чтение таймингов | экспериментально |
| `mesa_gallium`    | `GALLIUM_HUD` для AMD/Intel OpenGL | только переменные окружения |

Если сохранённый бэкенд недоступен (например, Vulkan-слой не собран), Gamohud
автоматически выбирает первый рабочий в порядке `mangohud_log` →
`vulkan_layer` → `presentmon` → `gamescope` и сохраняет выбор в настройках.

### MangoHud log на Linux (проще всего)

MangoHud умеет писать CSV с FPS и frametime. Gamohud читает самый свежий файл
из выбранной папки; сам MangoHud при этом может быть установлен отдельно.

1. Установи MangoHud (в Bazzite/Fedora обычно `rpm-ostree install MangoHud`).
2. Открой **Settings → MangoHud FPS log**, включи
   **Enable MangoHud FPS logging** и при необходимости выбери папку логов
   (по умолчанию `~/.local/share/gamohud/mangohud`). Нажми **Сохранить**.
3. Запускай игру с MangoHud: в Steam добавь в параметры запуска
   `mangohud %command%`, либо запусти её через Gamohud
   (`gamohud-run --backend mangohud_log -- игра`).
4. При запуске игры через Gamohud он сам скрывает собственный HUD MangoHud
   после старта (галочка **Hide MangoHud's own HUD after launch**), чтобы не
   было двух оверлеев. Логирование при этом продолжается.

Gamohud добавляет в `~/.config/MangoHud/MangoHud.conf` управляемый блок с
`output_folder`, `autostart_log=1`, `log_duration=0` и `log_interval=100`.
Остальные настройки MangoHud не затрагиваются. Если игра запущена без MangoHud,
FPS будет `--`: это ограничение любого внешнего логгера.

### Оверлей поверх полноэкранных игр (KDE Wayland)

На KDE Wayland обычное окно с `keepAbove` всё равно оказывается **под активным
полноэкранным окном**: KWin размещает fullscreen на слое выше. Поэтому Gamohud
автоматически запускает небольшой helper на системном Python с `layer-shell-qt`
и создаёт поверхность в слое `overlay` — она остаётся видимой и над fullscreen.
GUI при этом продолжает работать как обычно, а состояние оверлея передаётся
helper'у через `~/.local/share/gamohud/runtime/`.

Для этого нужны системный Python 3 с PySide6 и пакет `layer-shell-qt`. Если их
нет (или запущен X11), Gamohud откатывается на прежний путь через KWin
`keepAbove`; оверлей продолжит работать, но над активным fullscreen может быть
не виден. Принудительно отключить layer-shell helper можно переменной
`GAMOHUD_NO_LAYER_SHELL=1`.

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
- Linux-специфичные FPS-бэкенды (`mangohud_log`, `gamescope`, `mesa_gallium`)
  недоступны на других ОС; Vulkan implicit layer доступен на всех ОС (нужно
  собрать); `presentmon` доступен только на Windows.
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
- **Settings** — глобальный FPS-бэкенд, папка и включение логирования MangoHud,
  профиль оверлея по умолчанию, авто-переключение, запуск оверлея.

## gamohud-run

```
gamohud-run --list
gamohud-run --profile "Steam game"
gamohud-run --backend mangohud_log --env DXVK_HUD=0 -- mygame --fullscreen
```

Обёртка подставляет окружение выбранного бэкенда, env из профиля, Game Mode и
command-prefix, после чего `exec`-запускает приложение.

## Сборка и установка (для разработчиков)

Linux/macOS:
```bash
git clone https://github.com/ldima8286-cmd/Gamohud.git
cd Gamohud
./run-gui.sh
```

Windows:
```cmd
git clone https://github.com/ldima8286-cmd/Gamohud.git
cd Gamohud
run-gui.bat
```

При первом запуске автоматически создаётся `.venv` и ставятся зависимости.

**Сборка PyInstaller-бандла**

Linux: `./build-gui.sh` → `dist/gamohud-gui/`
Windows: `build-gui.bat` → `dist\gamohud-gui\gamohud-gui.exe`

**Готовый релиз**: самодостаточный, копируй всю папку целиком. На Windows для температур/нагрузки AMD/Intel опционально запусти LibreHardwareMonitor; `wmi/pywin32` ставятся при желании (`pip install "gamohud[windows]"`).


## Статус

WIP
