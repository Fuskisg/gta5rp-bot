<div align="center">

# 🎮 GTA5RP Bot

**Мощный инструмент автоматизации для GTA5RP**

[![Version](https://img.shields.io/badge/version-4.5-blue.svg)](https://t.me/bot_gta5blast)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

<img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
<img src="https://img.shields.io/badge/Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="Qt"/>

---

*Современный бот с красивым веб-интерфейсом для автоматизации рутинных действий*

</div>

---

## ✨ Особенности

- 🖥️ **Современный UI** — Красивый веб-интерфейс с тёмной темой
- ⚡ **Горячие клавиши** — Настраиваемые хоткеи для быстрого управления
- 🎮 **Xbox эмуляция** — Поддержка виртуального геймпада через ViGEm
- 🔊 **Звуковые эффекты** — Настраиваемые UI звуки
- 📦 **Портативность** — Возможность сборки в standalone EXE

---

## 🎯 Модули

<table>
<tr>
<td align="center" width="25%">

### 🎮 Anti-AFK
Эмуляция движений геймпада для предотвращения AFK-кика

</td>
<td align="center" width="25%">

### ⚓ Port
Автоматизация работы в порту

</td>
<td align="center" width="25%">

### 🏭 DeMorgan
Фарм на ферме: токарный станок и швейка

</td>
<td align="center" width="25%">

### 🍳 Cooking
Автоматическая готовка блюд

</td>
</tr>
<tr>
<td align="center">

### 💪 Gym
Автоматизация тренажёрного зала

</td>
<td align="center">

### 🏗️ Stroyka
Автоматизация стройки

</td>
<td align="center">

### 🐄 Cow
Работа с коровами

</td>
<td align="center">

### 🚕 Taxi
Автоматизация такси

</td>
</tr>
<tr>
<td align="center">

### 🎁 Bonus Point
Сбор бонусных очков

</td>
<td align="center">

### ⌨️ Keybinds
Настройка горячих клавиш

</td>
<td align="center">

### ⚙️ Settings
Настройки приложения

</td>
<td align="center">

### 📊 Dashboard
Главная панель управления

</td>
</tr>
</table>

---

## 🔧 Установка

### Системные требования

| Требование | Минимум |
|------------|---------|
| **ОС** | Windows 10/11 |
| **Python** | 3.8+ |
| **RAM** | 512 MB |
| **Драйвер** | [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus) (для Anti-AFK) |

### Быстрый старт

```bash
# 1. Клонируйте репозиторий
git clone https://codeberg.org/dornode/bot.git
cd bot

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Запустите приложение
python main.py
```

> 💡 **Совет:** Для работы Anti-AFK модуля установите [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus/releases)

---

## 📁 Структура проекта

```
bot/
├── 📄 main.py              # Точка входа приложения
├── 📄 compil.bat           # Скрипт сборки в EXE
├── 📄 version.json         # Информация о версии
│
├── 📁 core/                # Ядро приложения
│   ├── api.py              # API функции
│   └── common.py           # Общие утилиты
│
├── 📁 pages/               # Модули страниц
│   ├── antiafk.py          # Anti-AFK модуль
│   ├── cooking.py          # Готовка
│   ├── demorgan.py         # Ферма DeMorgan
│   ├── gym.py              # Тренажёрный зал
│   └── ...                 # Другие модули
│
├── 📁 templates/           # HTML шаблоны
│   ├── layout.html         # Базовый шаблон
│   ├── index.html          # Главная страница
│   └── ...                 # Шаблоны модулей
│
├── 📁 static/              # Статические файлы
│   ├── style.css           # Стили
│   ├── 📁 js/              # JavaScript
│   ├── 📁 assets/          # Изображения
│   └── 📁 wav/             # Звуки
│
├── 📁 configs/             # Конфигурация
│   └── config.json         # Настройки приложения
│
└── 📁 vgamepad/            # ViGEm библиотеки
    └── 📁 win/vigem/       # Windows DLL
```

---

## 🔌 Технологии

| Библиотека | Назначение |
|------------|------------|
| **Flask** | Веб-сервер для UI |
| **PySide6 (Qt)** | Нативное окно приложения |
| **pynput** | Перехват горячих клавиш |
| **pyautogui / pydirectinput** | Эмуляция ввода |
| **pygetwindow** | Управление окнами |
| **vgamepad** | Эмуляция Xbox геймпада |

---

## ⚙️ Конфигурация

Все настройки хранятся в `configs/config.json`:

---

## ⚠️ Важно

> **Внимание:** Использование ботов может нарушать правила сервера. Используйте на свой страх и риск!

- 🛡️ Для **Anti-AFK** требуется [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus/releases)
- 🖥️ Работает только на **Windows 10/11**
- 🔒 Запускайте от имени **администратора** для полной функциональности

---

## 🔗 Ссылки

<div align="center">

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/bot_gta5blast)
[![Codeberg](https://img.shields.io/badge/Codeberg-2185D0?style=for-the-badge&logo=Codeberg&logoColor=white)](https://codeberg.org/dornode/bot.git)
[![ViGEm](https://img.shields.io/badge/ViGEm_Driver-FF6F00?style=for-the-badge&logo=xbox&logoColor=white)](https://github.com/ViGEm/ViGEmBus)

</div>

---

<div align="center">

**⭐ Если проект был полезен — поставьте звезду!**

Made with ❤️ for GTA5RP community

</div>
