# BOT [GTA5RP]

Автоматизация для GTA5RP

## 🎮 Возможности

| Модуль | Описание |
|--------|----------|
| **Anti-AFK** | Эмуляция движений геймпада для предотвращения AFK |
| **Port** | Автоматический порт |
| **DeMorgan** | Автоматизация работы на ферме (токарь, швейка) |
| **Cooking** | Автоматизация готовки |
| **Gym** | Тренажёрный зал |
| **Stroyka** | Стройка |
| **Cow** | Коровы |
| **Taxi** | Такси |
| **Bonus Point** | Бонусные очки |
| **Keybinds** | Настройка горячих клавиш |

## 🔧 Установка

### Требования

- Python 3.8 или выше
- Windows 10/11

### Шаги

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://gitflic.ru/project/dornode/bot.git
   cd botnew
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Запустите приложение:**
   ```bash
   python main.py
   ```

## 📦 Сборка в EXE

Для создания standalone-версии используйте `compil.bat`:

```batch
compil.bat
```

Сборка требует [Nuitka](https://pypi.org/project/nuitka/):
```bash
pip install nuitka
```

## ⚙️ Конфигурация

Настройки хранятся в `configs/config.json`:

## 🔌 Зависимости

Основные библиотеки:

- **Flask** — веб-сервер для UI
- **pywebview** — нативное окно приложения
- **pynput** — перехват горячих клавиш
- **pyautogui / pydirectinput** — эмуляция ввода
- **pygetwindow** — управление окнами
- **vgamepad** — эмуляция геймпада Xbox (ViGEm)

## ⚠️ Важные замечания

**ViGEm Driver** — для работы Anti-AFK требуется установленный [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus)

## 🔗 Ссылки

- [GitFlic проект](https://gitflic.ru/project/dornode/bot/release)
- [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus)
