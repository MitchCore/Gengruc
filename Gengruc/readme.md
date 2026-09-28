<div align="center">

# Gengruc

**Мини-хостинг-панель для публикации HTML-страниц**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://www.microsoft.com/windows)

</div>

---

## 🌐 О проекте

**Gengruc** — мини-хостинг-панель для публикации HTML-страниц.
Собственный веб-сервер, SSH-консоль, 5 тем, 3D-интерфейс,
пользователи, чат, QR-коды и UPnP.

Работает на **Windows**, **Linux**, **macOS**. Настраивается за **5 минут**.

---

## ✨ Возможности

### 🖥️ Серверная часть
- **HTTPS-панель** — порт 443
- **HTTP-панель** — порт 8080 (XP–11)
- **SSH-консоль** — порт 22
- **WebSocket-чат** — порт 8443
- **UPnP** — автооткрытие портов
- **Автозапуск** Windows
- **Автосоздание** SSL-сертификата

### 🎨 Интерфейс
- **5 тем:** 🌙 Ночной пляж, 🚀 Космос, 🌅 Закат, 💊 Матрица, 🌆 Киберпанк
- **3D-карточки** за курсором
- **Анимированный фон** (луна, звёзды)
- **Toast-уведомления**
- **Конфетти** при создании

### 👥 Пользователи
- **Роли:** root и user
- **Изоляция** страниц
- **Создание через SSH**

### 📄 Страницы
- **Создание** HTML
- **Редактор** без предпросмотра
- **QR-код** для каждой
- **Экспорт в CSV**
- **Топ стран** посетителей

---

## 🚀 Установка

### Быстрая установка

```bash
git clone https://github.com/MitchCore/gengruc.git
cd gengruc
python main.py