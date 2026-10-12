# mangohud-preset-manager (TUI)

Мини-TUI для управления пресетами MangoHud. Показывает список .conf из ~/.config/MangoHud/, предпросмотр выбранного пресета, позволяет быстро ориентироваться.

## Запуск

```bash
cd mangohud-preset-manager-tui
source .venv/bin/activate  # если есть
python src/main.py
```

## Зависимости

- textual
- pyyaml

## Цель

Как обсуждали: надстройка над MangoHud. MVP: список пресетов, превью, (потом) Apply/Save/Rename/Delete.
