# 🌐 Gengruc

**Мини-хостинг-панель для публикации HTML-страниц**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://www.microsoft.com/windows)

![Gengruc](1.png)

---

## 📖 О проекте

**Gengruc** — лёгкая хостинг-панель, написанная с нуля на Python.
Позволяет запускать собственный веб-сервер, публиковать HTML-страницы,
управлять пользователями через SSH и общаться в чате.

Работает на **Windows**, **Linux** и **macOS**.

---

## ✨ Возможности

### 🖥️ Серверная часть
- **HTTPS-панель** — порт 443 с автосозданием сертификата
- **HTTP-панель** — порт 8080 (для старых систем XP–11)
- **SSH-консоль** — порт 22 (для root и пользователей)
- **WebSocket-чат** — порт 8443
- **UPnP** — автооткрытие портов на роутере
- **Автозапуск** при входе в Windows

### 🎨 Интерфейс
- **5 тем:** 🌙 Ночной пляж, 🚀 Космос, 🌅 Закат, 💊 Матрица, 🌆 Киберпанк
- **3D-карточки** — наклоняются за курсором
- **Анимированный фон** — луна, звёзды, море
- **Плавные переходы** между темами
- **Toast-уведомления** и **конфетти**

### 👥 Пользователи и страницы
- **Роли:** root (админ) и обычные пользователи
- **Изоляция:** каждый видит только свои страницы
- **Создание страниц** через панель или SSH
- **Редактор HTML** без предпросмотра
- **QR-код** для каждой страницы
- **Экспорт в CSV**

### 🔧 Дополнительно
- **Счётчик посещений** и **уникальных IP**
- **Топ стран** посетителей (флаги)
- **Заблокировка IP** после 5 неверных входов
- **Резервное копирование** в ZIP
- **Favicon** — генератор иконки из SVG
- **XSS-защита** (санитизация HTML + CSP)

---

## 📸 Скриншоты

![Gengruc Panel](1.png)

---

## 🚀 Установка

### Быстрая установка

```bash
git clone https://github.com/MitchCore/Gengruc.git
cd Gengruc
python main.py
Скрипт сам установит все зависимости при первом запуске.

Требования
Python 3.11+ — скачать

Права администратора — для портов 22 и 443

🎯 Быстрый старт
1. Запустите сервер
bash
python main.py
2. Откройте панель
Протокол	Адрес
HTTPS	https://localhost
HTTP	http://localhost:8080
Логин: root
Пароль: root

⚠️ Смените пароль сразу после первого входа!

3. Создайте страницу
Панель → «Создать новую страницу»

Название: Мой сайт

HTML: <h1>Привет, мир!</h1>

Создать

4. Зайдите по SSH
bash
ssh root@localhost
💻 SSH-команды
Для root
bash
help                       # список команд
status                     # статус сервера
sysinfo                    # CPU/RAM/диск
users                      # список пользователей
adduser <имя> <пароль>     # создать пользователя
deluser <имя>              # удалить
pages                      # все страницы
page info <id>             # инфо
backup                     # создать бэкап
kick <ip>                  # заблокировать IP
theme <имя>                # сменить тему
logs <N>                   # последние N логов
Для пользователей
bash
help                       # список команд
status                     # свой статус
pages                      # свои страницы
new <имя>                  # создать страницу
enable <id>                # включить свою
disable <id>               # выключить свою
delete <id>                # удалить свою
stats                      # статистика
passwd                     # сменить пароль
📁 Структура проекта
text
Gengruc/
├── main.py                 # Ядро сервера и панели
├── gengruc_ssh.py          # SSH-команды
├── gengruc_features.py     # Редактор, QR, CSV, карта
├── ui.py                   # Темы, 3D-карточки, фон
├── favicon.py              # Генератор иконки
├── requirements.txt        # Зависимости
├── LICENSE                 # MIT
├── README.md               # Этот файл
└── .gitignore              # Исключения git
🔐 Безопасность
✅ XSS-защита — санитизация HTML + CSP-заголовки

✅ Защита от брутфорса — блокировка IP после 5 попыток

✅ HTTPS — самоподписанный сертификат

✅ Изоляция сессий — HttpOnly cookies

✅ Разделение ролей — root / user

🤝 Как помочь
Fork репозиторий

Ветка (git checkout -b feature/amazing)

Коммит (git commit -m "Add amazing feature")

Push (git push origin feature/amazing)

Pull Request

🐛 Баги и идеи
Issues: открыть

Discussions: обсудить

📜 Лицензия
MIT License — см. файл LICENSE.

👤 Автор
MitchCore

GitHub: @MitchCore

Проект: Gengruc

<div align="center">
⭐ Поставьте звезду, если проект полезен!
Сделано с ❤️ на Python

© 2026 MitchCore

</div> ```
