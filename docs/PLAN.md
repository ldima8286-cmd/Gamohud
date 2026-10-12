# PLAN (TUI)

## 1. Preset Manager (MVP)
- [x] Скелет TUI (Textual)
- [x] Чтение пресетов из ~/.config/MangoHud/*.conf
- [x] Apply: копировать выбранный пресет в MangoHud.conf (редактор -> применяет текущее)
- [x] Save current: New from current (из текущего редактора)
- [x] Rename/Delete
- [x] Фильтр по имени
- [x] Поддержка Flatpak путей (~/.var/app/*/config/MangoHud/)

## UI
- Левая панель: список пресетов
- Правая: предпросмотр + действия

## 2. Game Launchers integration
- [ ] Обнаружение Steam/Lutris/Bottles/Flatpak игр
- [ ] Привязка пресета к игре (AppID/путь)
- [ ] Быстрый запуск игры с автоприменением пресета
- [ ] Автовосстановление MangoHud.conf после выхода

## 3. Game Mode с профилями
- [ ] Профили Game Mode (actions): gamemode, kill/restore процессы, env vars
- [ ] Привязка Game Mode профиля + пресета к игре
- [ ] Один клик: применить пресет + запустить Game Mode + игра
- [ ] Триггер по запуску/завершению

## 4. Мониторинг/оверлей инфо (dashboard)
- [ ] Панель статуса (читаем текущий MangoHud.conf, активный пресет)
- [ ] Быстрый просмотр активных параметров
