# ============================================================
# Gengruc SSH — команды для root и пользователей
# Файл 2 (подключается из main.py или gengruc.py)
# ============================================================

import os
import time
import datetime
import zipfile
import socket
import sqlite3
import json
import threading
import paramiko


# ============================================================
# ЦВЕТА
# ============================================================
C_RESET = "\033[0m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"


def colored(text, color):
    return f"{color}{text}{C_RESET}"


# ============================================================
# SSH SERVER INTERFACE
# ============================================================
class GengrucSSHServer(paramiko.ServerInterface):
    """Принимает root и обычных пользователей."""

    def __init__(self, root_password):
        self.root_password = root_password
        self.event = threading.Event()
        self.authed_user = None

    def check_auth_password(self, username, password):
        try:
            import main as gengruc
        except ImportError:
            try:
                import gengruc
            except ImportError:
                return paramiko.AUTH_FAILED

        data = gengruc.load_data()

        # root
        if username == data["username"]:
            if password == data["password"]:
                self.authed_user = username
                return paramiko.AUTH_SUCCESSFUL
            return paramiko.AUTH_FAILED

        # обычный пользователь
        if username in data["users"]:
            stored = data["users"][username].get("password_hash")
            import hashlib
            if stored == hashlib.sha256(password.encode()).hexdigest():
                self.authed_user = username
                return paramiko.AUTH_SUCCESSFUL

        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height,
                                  pw, ph, modes):
        return True


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================
def _read_logs(ctx, limit=50):
    try:
        return ctx["read_logs"](limit)
    except Exception:
        return []


def _make_backup(ctx):
    """Создаёт ZIP с data.json, pages, chat.db. Возвращает имя файла."""
    try:
        backups = ctx["BACKUPS_DIR"]
        os.makedirs(backups, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"backup_{ts}.zip"
        fpath = os.path.join(backups, fname)
        with zipfile.ZipFile(fpath, "w", zipfile.ZIP_DEFLATED) as z:
            if os.path.exists(ctx["DATA_FILE"]):
                z.write(ctx["DATA_FILE"], "data.json")
            if os.path.exists(ctx["CHAT_DB"]):
                z.write(ctx["CHAT_DB"], "chat.db")
            pages_dir = ctx["PAGES_DIR"]
            if os.path.isdir(pages_dir):
                for f in os.listdir(pages_dir):
                    z.write(os.path.join(pages_dir, f), f"pages/{f}")
        return fname
    except Exception as e:
        print(f"[Backup] Ошибка: {e}")
        return None


def _list_backups(ctx):
    backups = ctx["BACKUPS_DIR"]
    if not os.path.isdir(backups):
        return []
    files = [f for f in os.listdir(backups) if f.endswith(".zip")]
    files.sort(reverse=True)
    return files


def _sysinfo():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        return {
            "cpu": f"{cpu}%",
            "ram_used": f"{ram.used // (1024**2)} MB",
            "ram_total": f"{ram.total // (1024**2)} MB",
            "ram_percent": f"{ram.percent}%",
            "disk_used": f"{disk.used // (1024**3)} GB",
            "disk_total": f"{disk.total // (1024**3)} GB",
            "disk_percent": f"{disk.percent}%",
        }
    except ImportError:
        return None


def _user_pages(data, username):
    """Все страницы пользователя (или все — если root)."""
    admin = username == data["username"]
    result = []
    for pid, p in data["pages"].items():
        if admin or p.get("owner") == username:
            result.append((pid, p))
    return result


def _read_line(chan):
    """Читает одну строку из SSH-канала."""
    line = ""
    while True:
        b = chan.recv(1)
        if not b:
            break
        ch = b.decode("utf-8", errors="replace")
        if ch == "\r" or ch == "\n":
            chan.send("\r\n")
            break
        elif ch == "\x7f" or ch == "\b":
            if line:
                line = line[:-1]
                chan.send("\b \b")
        elif ch == "\x03":
            chan.send("^C\r\n")
            return ""
        elif ch >= " ":
            line += ch
            chan.send(ch)
    return line


# ============================================================
# HELP
# ============================================================
HELP_ADMIN = (
    colored("КОМАНДЫ (root):", C_BOLD) + "\n"
    + "  " + colored("help", C_CYAN) + "              — этот список\n"
    + "  " + colored("status", C_CYAN) + "            — статус сервера\n"
    + "  " + colored("sysinfo", C_CYAN) + "           — CPU/RAM/диск\n"
    + "  " + colored("net", C_CYAN) + "               — сеть\n"
    + "  " + colored("load", C_CYAN) + "              — нагрузка\n"
    + "  " + colored("upnp", C_CYAN) + "              — UPnP\n"
    + "  " + colored("version", C_CYAN) + "           — версия\n"
    + "\n"
    + colored("Страницы:", C_BOLD) + "\n"
    + "  " + colored("pages", C_CYAN) + "             — все страницы\n"
    + "  " + colored("page info <id>", C_CYAN) + "    — инфо о странице\n"
    + "  " + colored("page enable <id>", C_CYAN) + "  — включить\n"
    + "  " + colored("page disable <id>", C_CYAN) + " — выключить\n"
    + "  " + colored("page delete <id>", C_CYAN) + "  — удалить\n"
    + "  " + colored("page show <id>", C_CYAN) + "    — показать HTML\n"
    + "  " + colored("top", C_CYAN) + "               — топ по посещениям\n"
    + "\n"
    + colored("Пользователи:", C_BOLD) + "\n"
    + "  " + colored("users", C_CYAN) + "             — список\n"
    + "  " + colored("adduser <имя> <пароль>", C_CYAN) + " — создать\n"
    + "  " + colored("deluser <имя>", C_CYAN) + "     — удалить\n"
    + "  " + colored("userpasswd <имя> <пароль>", C_CYAN) + " — сменить пароль\n"
    + "\n"
    + colored("Блокировки:", C_BOLD) + "\n"
    + "  " + colored("kick <ip>", C_CYAN) + "         — блок IP на час\n"
    + "  " + colored("unblock <ip>", C_CYAN) + "      — разблокировать\n"
    + "  " + colored("blocks", C_CYAN) + "            — список блокировок\n"
    + "\n"
    + colored("Логи:", C_BOLD) + "\n"
    + "  " + colored("logs [N]", C_CYAN) + "          — последние N (по умолч. 20)\n"
    + "\n"
    + colored("Бэкапы:", C_BOLD) + "\n"
    + "  " + colored("backup", C_CYAN) + "            — создать\n"
    + "  " + colored("backups", C_CYAN) + "           — список\n"
    + "\n"
    + colored("UI:", C_BOLD) + "\n"
    + "  " + colored("theme [имя]", C_CYAN) + "       — сменить тему\n"
    + "\n"
    + colored("Прочее:", C_BOLD) + "\n"
    + "  " + colored("clear", C_CYAN) + "             — очистить экран\n"
    + "  " + colored("exit", C_CYAN) + "              — выйти\n"
)

HELP_USER = (
    colored("КОМАНДЫ (пользователь):", C_BOLD) + "\n"
    + "  " + colored("help", C_CYAN) + "           — этот список\n"
    + "  " + colored("status", C_CYAN) + "         — свой статус\n"
    + "  " + colored("whoami", C_CYAN) + "         — имя\n"
    + "  " + colored("pages", C_CYAN) + "          — свои страницы\n"
    + "  " + colored("new <имя>", C_CYAN) + "      — создать (многострочно)\n"
    + "  " + colored("enable <id>", C_CYAN) + "    — включить свою\n"
    + "  " + colored("disable <id>", C_CYAN) + "   — выключить свою\n"
    + "  " + colored("delete <id>", C_CYAN) + "    — удалить свою\n"
    + "  " + colored("stats", C_CYAN) + "          — статистика\n"
    + "  " + colored("passwd", C_CYAN) + "         — сменить пароль\n"
    + "  " + colored("clear", C_CYAN) + "          — очистить экран\n"
    + "  " + colored("exit", C_CYAN) + "           — выйти\n"
)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================
def ssh_run_command(cmd, chan, username, ctx):
    """Возвращает строку для отправки клиенту. None = выход."""
    cmd_strip = cmd.strip()
    cmd_lower = cmd_strip.lower()
    data = ctx["load_data"]()
    admin = ctx["is_admin"](username)

    # === ОБЩИЕ КОМАНДЫ ===
    if cmd_lower == "":
        return ""

    if cmd_lower == "exit":
        return None

    if cmd_lower == "clear":
        chan.send("\033[2J\033[H")
        return ""

    if cmd_lower == "help":
        return HELP_ADMIN if admin else HELP_USER

    if cmd_lower == "whoami":
        return colored(username, C_MAGENTA) + "\n"

    if cmd_lower == "version":
        return colored(f"Gengruc v{ctx['VERSION']}", C_CYAN) + "\n"

    if cmd_lower == "status":
        pages = _user_pages(data, username)
        enabled = sum(1 for _, p in pages if p.get("enabled", True))
        return (colored("OK", C_GREEN) + "\n"
                + f"  Пользователь:  {colored(username, C_MAGENTA)}\n"
                + f"  Админ:         {'да' if admin else 'нет'}\n"
                + f"  Страниц всего: {len(pages)}\n"
                + f"  Включено:      {enabled}\n"
                + f"  UPnP:          {'ON' if ctx['_upnp_available']() else 'OFF'}\n")

    if cmd_lower == "load":
        with ctx["_stats_lock"]:
            s = dict(ctx["_stats"])
        return (f"Панель: {s['panel_requests']}\n"
                + f"Страницы: {s['page_requests']}\n"
                + f"SSH: {s['ssh_connections']}\n"
                + f"Трафик: {s['bytes_served'] / 1024:.1f} KB\n")

    if cmd_lower == "net":
        pub = ctx["get_public_ip"]()
        local = ctx["get_local_ips"]()
        return (colored("СЕТЬ", C_BOLD) + "\n"
                + f"  Локальный IP: {ctx['LOCAL_IP']}\n"
                + f"  Публичный IP: {pub or 'не определён'}\n"
                + f"  Все локальные: {', '.join(local)}\n")

    if cmd_lower == "upnp":
        return f"UPnP: {'доступен' if ctx['_upnp_available']() else 'недоступен'}\n"

    if cmd_lower.startswith("logs"):
        if not admin:
            return colored("ERR: только для root", C_RED) + "\n"
        parts = cmd_strip.split()
        limit = 20
        if len(parts) > 1 and parts[1].isdigit():
            limit = min(int(parts[1]), 500)
        lines = _read_logs(ctx, limit)
        return "".join(lines) + "\n" if lines else "Лог пуст.\n"

    # ============================================================
    # ROOT-КОМАНДЫ
    # ============================================================
    if admin:

        if cmd_lower == "pages":
            if not data["pages"]:
                return "Нет страниц.\n"
            rows = [colored(f"Все страницы ({len(data['pages'])}):", C_BOLD)]
            for pid, p in data["pages"].items():
                st = "ON " if p.get("enabled", True) else "OFF"
                rows.append(f"  [{st}] {p['name']} — порт {p['port']} — "
                            + f"владелец: {p.get('owner', '?')} (id: {pid})")
            return "\n".join(rows) + "\n"

        if cmd_lower.startswith("page "):
            parts = cmd_strip.split()
            if len(parts) < 2:
                return colored("Использование: page info/enable/disable/delete/show <id>", C_YELLOW) + "\n"
            sub = parts[1].lower()
            if len(parts) < 3:
                return colored("Укажите ID страницы", C_RED) + "\n"
            pid = parts[2]
            if pid not in data["pages"]:
                return colored(f"ERR: страница '{pid}' не найдена", C_RED) + "\n"
            page = data["pages"][pid]

            if sub == "info":
                return (f"  ID:        {pid}\n"
                        + f"  Название:  {page['name']}\n"
                        + f"  Порт:      {page['port']}\n"
                        + f"  Владелец:  {page.get('owner', '?')}\n"
                        + f"  Включена:  {page.get('enabled', True)}\n"
                        + f"  Посещений: {page.get('visits', 0)}\n"
                        + f"  Уник. IP:  {len(page.get('unique_ips', []))}\n")

            if sub == "enable":
                page["enabled"] = True
                ctx["save_data"](data)
                return colored(f"OK: страница {pid} включена", C_GREEN) + "\n"

            if sub == "disable":
                page["enabled"] = False
                ctx["save_data"](data)
                return colored(f"OK: страница {pid} выключена", C_GREEN) + "\n"

            if sub == "delete":
                port = page["port"]
                ctx["upnp_close_port"](port)
                try:
                    os.remove(os.path.join(ctx["PAGES_DIR"], f"{pid}.html"))
                except FileNotFoundError:
                    pass
                del data["pages"][pid]
                ctx["save_data"](data)
                return colored(f"OK: страница {pid} удалена", C_GREEN) + "\n"

            if sub == "show":
                fpath = os.path.join(ctx["PAGES_DIR"], f"{pid}.html")
                if not os.path.exists(fpath):
                    return colored("ERR: файл не найден", C_RED) + "\n"
                with open(fpath, "r", encoding="utf-8") as f:
                    return f.read() + "\n"

            return colored(f"ERR: неизвестная подкоманда '{sub}'", C_RED) + "\n"

        if cmd_lower == "top":
            pages = sorted(data["pages"].items(),
                           key=lambda x: x[1].get("visits", 0), reverse=True)[:5]
            if not pages:
                return "Страниц нет.\n"
            rows = [colored("Топ-5 по посещениям:", C_BOLD)]
            for pid, p in pages:
                rows.append(f"  {p.get('visits', 0):>6}  {p['name']} ({pid})")
            return "\n".join(rows) + "\n"

        if cmd_lower == "users":
            if not data["users"]:
                return "Нет пользователей.\n"
            rows = [colored(f"Пользователи ({len(data['users'])}):", C_BOLD)]
            for u, info in data["users"].items():
                created = info.get("created", "?")
                own = sum(1 for p in data["pages"].values()
                          if p.get("owner") == u)
                rows.append(f"  {u:<15} страниц: {own}  создан: {created}")
            return "\n".join(rows) + "\n"

        if cmd_lower.startswith("adduser "):
            parts = cmd_strip.split(maxsplit=2)
            if len(parts) < 3:
                return colored("Использование: adduser <имя> <пароль>", C_YELLOW) + "\n"
            new_user, new_pass = parts[1], parts[2]
            if new_user in data["users"] or new_user == data["username"]:
                return colored(f"ERR: пользователь '{new_user}' уже существует", C_RED) + "\n"
            if len(new_pass) < 3:
                return colored("ERR: пароль от 3 символов", C_RED) + "\n"
            data["users"][new_user] = {
                "password_hash": ctx["hash_password"](new_pass),
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "sessions": []}
            ctx["save_data"](data)
            return colored(f"OK: пользователь '{new_user}' создан", C_GREEN) + "\n"

        if cmd_lower.startswith("deluser "):
            parts = cmd_strip.split(maxsplit=1)
            if len(parts) < 2:
                return colored("Использование: deluser <имя>", C_YELLOW) + "\n"
            target = parts[1].strip()
            if target not in data["users"]:
                return colored(f"ERR: '{target}' не найден", C_RED) + "\n"
            del data["users"][target]
            ctx["save_data"](data)
            return colored(f"OK: пользователь '{target}' удалён", C_GREEN) + "\n"

        if cmd_lower.startswith("userpasswd "):
            parts = cmd_strip.split(maxsplit=2)
            if len(parts) < 3:
                return colored("Использование: userpasswd <имя> <новый_пароль>", C_YELLOW) + "\n"
            target, new_pass = parts[1], parts[2]
            if target not in data["users"]:
                return colored(f"ERR: '{target}' не найден", C_RED) + "\n"
            if len(new_pass) < 3:
                return colored("ERR: пароль от 3 символов", C_RED) + "\n"
            data["users"][target]["password_hash"] = ctx["hash_password"](new_pass)
            ctx["save_data"](data)
            return colored(f"OK: пароль '{target}' изменён", C_GREEN) + "\n"

        if cmd_lower.startswith("kick "):
            ip = cmd_strip[5:].strip()
            if not ip:
                return colored("Использование: kick <ip>", C_YELLOW) + "\n"
            data.setdefault("blocked_ips", {})[ip] = time.time() + 3600
            ctx["save_data"](data)
            return colored(f"OK: IP {ip} заблокирован на 1 час", C_GREEN) + "\n"

        if cmd_lower.startswith("unblock "):
            ip = cmd_strip[8:].strip()
            if ip in data.get("blocked_ips", {}):
                del data["blocked_ips"][ip]
                ctx["save_data"](data)
                return colored(f"OK: IP {ip} разблокирован", C_GREEN) + "\n"
            return colored(f"IP {ip} не был заблокирован", C_YELLOW) + "\n"

        if cmd_lower == "blocks":
            blocked = data.get("blocked_ips", {})
            if not blocked:
                return "Заблокированных IP нет.\n"
            now = time.time()
            rows = [colored("Заблокированные IP:", C_BOLD)]
            for ip, until in blocked.items():
                left = int(until - now)
                if left > 0:
                    rows.append(f"  {ip}  (осталось {left} сек)")
            return "\n".join(rows) + "\n"

        if cmd_lower == "backup":
            fname = _make_backup(ctx)
            if fname:
                return colored(f"OK: создан {fname}", C_GREEN) + "\n"
            return colored("ERR: не удалось создать бэкап", C_RED) + "\n"

        if cmd_lower == "backups":
            files = _list_backups(ctx)
            if not files:
                return "Бэкапов нет.\n"
            rows = [colored(f"Бэкапы ({len(files)}):", C_BOLD)]
            for f in files[:20]:
                size = os.path.getsize(os.path.join(ctx["BACKUPS_DIR"], f)) / 1024
                rows.append(f"  {f}  ({size:.1f} KB)")
            return "\n".join(rows) + "\n"

        if cmd_lower == "theme":
            cur = data.get("current_theme", "beach")
            return (colored("Темы:", C_BOLD) + "\n"
                    + "  beach     — Ночной пляж\n"
                    + "  space     — Космос\n"
                    + "  sunset    — Закат\n"
                    + "  matrix    — Матрица\n"
                    + "  cyberpunk — Киберпанк\n"
                    + f"\nТекущая: {colored(cur, C_MAGENTA)}\n")

        if cmd_lower.startswith("theme "):
            name = cmd_strip[6:].strip().lower()
            allowed = ["beach", "space", "sunset", "matrix", "cyberpunk"]
            if name not in allowed:
                return colored(f"ERR: доступно: {', '.join(allowed)}", C_RED) + "\n"
            data["current_theme"] = name
            ctx["save_data"](data)
            return colored(f"OK: тема '{name}' установлена", C_GREEN) + "\n"

        if cmd_lower == "sysinfo":
            info = _sysinfo()
            if info is None:
                return colored("ERR: psutil не установлен. pip install psutil", C_YELLOW) + "\n"
            return (colored("СИСТЕМА", C_BOLD) + "\n"
                    + f"  CPU:   {info['cpu']}\n"
                    + f"  RAM:   {info['ram_used']} / {info['ram_total']} ({info['ram_percent']})\n"
                    + f"  Диск:  {info['disk_used']} / {info['disk_total']} ({info['disk_percent']})\n")

    # ============================================================
    # USER-КОМАНДЫ
    # ============================================================
    else:
        if cmd_lower == "pages":
            pages = _user_pages(data, username)
            if not pages:
                return "У вас нет страниц.\n"
            rows = [colored(f"Ваши страницы ({len(pages)}):", C_BOLD)]
            for pid, p in pages:
                st = "ON " if p.get("enabled", True) else "OFF"
                rows.append(f"  [{st}] {p['name']} — порт {p['port']} (id: {pid})")
            return "\n".join(rows) + "\n"

        if cmd_lower.startswith("new "):
            name = cmd_strip[4:].strip()
            if not name:
                return colored("Использование: new <название>", C_YELLOW) + "\n"

            chan.send(colored("Введите HTML (завершите пустой строкой):\r\n", C_YELLOW))
            html_lines = []
            while True:
                chan.send("  > ")
                line_buf = _read_line(chan)
                if line_buf == "":
                    break
                html_lines.append(line_buf)
                if len(html_lines) > 500:
                    break

            html = "\n".join(html_lines)
            html = ctx["sanitize_html"](html)
            if not html.strip():
                return colored("ERR: HTML пустой", C_RED) + "\n"

            import secrets
            used_ports = {p["port"] for p in data["pages"].values()}
            page_id = secrets.token_hex(4)
            port = ctx["find_free_port"](used_ports) or ctx["PAGE_PORT_MIN"]

            with open(os.path.join(ctx["PAGES_DIR"], f"{page_id}.html"),
                      "w", encoding="utf-8") as f:
                f.write(html)
            data["pages"][page_id] = {
                "name": name, "port": port, "enabled": True,
                "owner": username, "visits": 0, "unique_ips": []}
            ctx["save_data"](data)
            ctx["start_page_server"](page_id, port)
            ctx["upnp_open_port"](port, f"Gengruc {name}")
            return (colored("OK: страница создана", C_GREEN) + "\n"
                    + f"  ID:   {page_id}\n"
                    + f"  Порт: {port}\n"
                    + f"  URL:  http://{ctx['LOCAL_IP']}:{port}\n")

        if cmd_lower.startswith("enable "):
            pid = cmd_strip[7:].strip()
            page = data["pages"].get(pid)
            if not page or page.get("owner") != username:
                return colored("ERR: страница не найдена или не ваша", C_RED) + "\n"
            page["enabled"] = True
            ctx["save_data"](data)
            return colored(f"OK: страница {pid} включена", C_GREEN) + "\n"

        if cmd_lower.startswith("disable "):
            pid = cmd_strip[8:].strip()
            page = data["pages"].get(pid)
            if not page or page.get("owner") != username:
                return colored("ERR: страница не найдена или не ваша", C_RED) + "\n"
            page["enabled"] = False
            ctx["save_data"](data)
            return colored(f"OK: страница {pid} выключена", C_GREEN) + "\n"

        if cmd_lower.startswith("delete "):
            pid = cmd_strip[7:].strip()
            page = data["pages"].get(pid)
            if not page or page.get("owner") != username:
                return colored("ERR: страница не найдена или не ваша", C_RED) + "\n"
            ctx["upnp_close_port"](page["port"])
            try:
                os.remove(os.path.join(ctx["PAGES_DIR"], f"{pid}.html"))
            except FileNotFoundError:
                pass
            del data["pages"][pid]
            ctx["save_data"](data)
            return colored(f"OK: страница {pid} удалена", C_GREEN) + "\n"

        if cmd_lower == "stats":
            pages = _user_pages(data, username)
            total_visits = sum(p.get("visits", 0) for _, p in pages)
            unique_ips = set()
            for _, p in pages:
                unique_ips.update(p.get("unique_ips", []))
            return (colored("СТАТИСТИКА", C_BOLD) + "\n"
                    + f"  Страниц:    {len(pages)}\n"
                    + f"  Посещений:  {total_visits}\n"
                    + f"  Уник. IP:   {len(unique_ips)}\n")

        if cmd_lower == "passwd":
            chan.send(colored("Текущий пароль: ", C_YELLOW))
            old_pass = _read_line(chan)
            import hashlib
            stored = data["users"][username]["password_hash"]
            if stored != hashlib.sha256(old_pass.encode()).hexdigest():
                return colored("ERR: неверный пароль", C_RED) + "\n"
            chan.send(colored("Новый пароль: ", C_YELLOW))
            new_pass = _read_line(chan)
            if len(new_pass) < 3:
                return colored("ERR: пароль от 3 символов", C_RED) + "\n"
            data["users"][username]["password_hash"] = ctx["hash_password"](new_pass)
            ctx["save_data"](data)
            return colored("OK: пароль изменён", C_GREEN) + "\n"

    # Неизвестная команда
    return colored(f"ERR: неизвестная команда '{cmd_strip}'. Введите 'help'", C_RED) + "\n"