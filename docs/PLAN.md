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
- [x] Обнаружение Steam (базово)
- [x] Привязка пресета к игре (AppID)
- [x] Быстрый запуск игры с автоприменением пресета (Steam)
- [ ] Автовосстановление MangoHud.conf после выхода

## 3. Game Mode с профилями
- [x] Профили Game Mode (базовые: хранение)
- [x] Привязка через bindings (preset + gamemode_profile)
- [ ] Один клик: применить пресет + запустить Game Mode + игра
- [ ] Триггер по запуску/завершению

## 4. Мониторинг/оверлей инфо (dashboard)
- [x] Панель статуса (читаем текущий MangoHud.conf)
- [ ] Быстрый просмотр активных параметров
