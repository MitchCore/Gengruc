# ============================================================
# Gengruc Panel v3.4 — оптимизировано (мгновенное создание)
# Автор: Mitch
# Лицензия: MIT
# ============================================================

import subprocess, sys, os

REQUIRED_PACKAGES = ["paramiko", "miniupnpc", "websockets", "cryptography", "qrcode", "requests", "certifi"]

def install_if_missing():
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            print(f"[Установка] {pkg}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"])
                print(f"[Установка] {pkg} — OK")
            except Exception as e:
                print(f"[Установка] {pkg} — ошибка: {e}")

install_if_missing()

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import http.server, socketserver, json, secrets, threading, random
import urllib.parse, urllib.request, socket, ssl, datetime
import hashlib, zipfile, sqlite3, asyncio, time, re
from io import BytesIO
import paramiko

try:
    import miniupnpc
    UPNP_LIB = True
except ImportError:
    UPNP_LIB = False

try:
    import websockets
    WS_LIB = True
except ImportError:
    WS_LIB = False

# ============================================================
def get_primary_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and not ip.startswith("169.254"):
                return ip
    except Exception:
        pass
    return "127.0.0.1"

LOCAL_IP = get_primary_ip()

# ============================================================
try:
    from ui import (
        get_theme_css, get_theme_js, get_theme_switcher_html,
        get_toast_container, get_load_chart_html, get_themes_js_data
    )
    UI_AVAILABLE = True
    print("[UI] ui.py подключён")
except ImportError:
    UI_AVAILABLE = False
    print("[UI] ui.py не найден")

try:
    from favicon import ensure_favicon
    FAVICON_AVAILABLE = True
except ImportError:
    FAVICON_AVAILABLE = False
    print("[Favicon] favicon.py не найден")

try:
    from gengruc_ssh import ssh_run_command, GengrucSSHServer
    SSH_MODULE = True
    print("[SSH] gengruc_ssh.py подключён")
except ImportError:
    SSH_MODULE = False
    print("[SSH] gengruc_ssh.py не найден")

try:
    from gengruc_features import (
        build_edit_page, export_pages_csv, build_qr_page,
        get_top_countries, build_upnp_page, get_user_public_info
    )
    FEATURES_AVAILABLE = True
    print("[Features] gengruc_features.py подключён")
except ImportError as e:
    FEATURES_AVAILABLE = False
    print(f"[Features] gengruc_features.py не найден ({e})")

# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
PAGES_DIR = os.path.join(BASE_DIR, "pages")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
LOG_FILE = os.path.join(BASE_DIR, "access.log")
CERT_FILE = os.path.join(BASE_DIR, "cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "key.pem")
HOST_KEY_FILE = os.path.join(BASE_DIR, "ssh_host_key")
CHAT_DB = os.path.join(BASE_DIR, "chat.db")
FAVICON_FILE = os.path.join(BASE_DIR, "favicon.ico")

STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
STARTUP_BAT = os.path.join(STARTUP_DIR, "gengruc.bat")

PANEL_HTTPS_PORT = 443
PANEL_HTTP_PORT = 8080
SSH_PORT = 22
WS_PORT = 8443
PAGE_PORT_MIN = 2800
PAGE_PORT_MAX = 65535

SERVER_NAME = "Gserver"
DEFAULT_USERNAME = "root"
DEFAULT_PASSWORD = "root"
MAX_LOGIN_ATTEMPTS = 5
BLOCK_MINUTES = 15
VERSION = "3.4"

for d in [PAGES_DIR, BACKUPS_DIR]:
    os.makedirs(d, exist_ok=True)

C_RESET = "\033[0m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"

_data_cache = None
_stats_lock = threading.Lock()
_stats = {"panel_requests": 0, "page_requests": 0,
          "ssh_connections": 0, "bytes_served": 0}
_start_time = time.time()
_login_attempts = {}
_login_attempts_lock = threading.Lock()
_active_servers = {}
_servers_lock = threading.Lock()
_chat_clients = set()
_chat_lock = threading.Lock()
_upnp = None
_upnp_available = False
_public_ip_cache = None
_upnp_cache = {"time": 0, "data": {}}

# ============================================================
def load_data():
    global _data_cache
    if _data_cache is None:
        if not os.path.exists(DATA_FILE):
            _data_cache = {
                "username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD,
                "sessions": [], "pages": {}, "users": {},
                "autostart_asked": False, "autostart_enabled": False,
                "blocked_ips": {}, "current_theme": "beach"}
            save_data(_data_cache)
        else:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                _data_cache = json.load(f)
        defaults = {"password": DEFAULT_PASSWORD, "username": DEFAULT_USERNAME,
                    "sessions": [], "pages": {}, "users": {},
                    "autostart_asked": False, "autostart_enabled": False,
                    "blocked_ips": {}, "current_theme": "beach"}
        for k, v in defaults.items():
            if k not in _data_cache:
                _data_cache[k] = v
    return _data_cache


def save_data(data):
    global _data_cache
    _data_cache = data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_credentials(username, password):
    data = load_data()
    if username == data["username"] and password == data["password"]:
        return True
    if username in data["users"]:
        if data["users"][username].get("password_hash") == hash_password(password):
            return True
    return False


def is_admin(username):
    return username == load_data()["username"]

# ============================================================
def is_ip_blocked(ip):
    data = load_data()
    blocked = data.get("blocked_ips", {})
    if ip in blocked:
        if time.time() < blocked[ip]:
            return True
        del blocked[ip]
        save_data(data)
    return False


def register_failed_login(ip):
    with _login_attempts_lock:
        now = time.time()
        attempts = _login_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < 60 * BLOCK_MINUTES]
        attempts.append(now)
        _login_attempts[ip] = attempts
        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            data = load_data()
            data.setdefault("blocked_ips", {})[ip] = now + 60 * BLOCK_MINUTES
            save_data(data)
            return True
    return False


def reset_failed_login(ip):
    with _login_attempts_lock:
        _login_attempts.pop(ip, None)

# ============================================================
def log_access(ip, port, path, ua=""):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} | {ip} | port={port} | {path} | {ua[:60]}\n")
    except Exception:
        pass


def read_logs(limit=50):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return lines[-limit:]

# ============================================================
def get_public_ip(force=False):
    global _public_ip_cache
    if _public_ip_cache and not force:
        return _public_ip_cache
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as r:
            _public_ip_cache = r.read().decode("utf-8")
            return _public_ip_cache
    except Exception:
        return None


def get_local_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("169.254"):
                ips.append(ip)
    except Exception:
        pass
    return ips


def detect_mode():
    local = get_local_ips()
    pub = get_public_ip()
    if not pub:
        return "unknown", local, None
    for ip in local:
        if ip == pub:
            return "vps", local, pub
    return "home", local, pub

# ============================================================
# БЫСТРЫЙ ПОИСК ПОРТА
# ============================================================
def find_free_port(used):
    """Быстрый поиск — bind вместо TCPServer."""
    for _ in range(50):
        candidate = random.randint(PAGE_PORT_MIN, PAGE_PORT_MAX)
        if candidate in used:
            continue
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", candidate))
            s.close()
            return candidate
        except OSError:
            continue
    return None

# ============================================================
def sanitize_html(html):
    if not html:
        return html
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html,
                  flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script\b[^>]*/?>', '', html, flags=re.IGNORECASE)
    for tag in ['iframe', 'object', 'embed', 'applet',
                'frame', 'frameset', 'base']:
        html = re.sub(rf'<{tag}\b[^>]*>.*?</{tag}>', '', html,
                      flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(rf'<{tag}\b[^>]*/?>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\son\w+\s*=\s*"[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r"\son\w+\s*=\s*'[^']*'", '', html, flags=re.IGNORECASE)
    html = re.sub(r'\son\w+\s*=\s*[^\s>]+', '', html, flags=re.IGNORECASE)
    html = re.sub(r'(href|src|action|formaction)\s*=\s*["\']?\s*javascript:',
                  r'\1="#"', html, flags=re.IGNORECASE)
    html = re.sub(r'expression\s*\(', 'blocked(', html, flags=re.IGNORECASE)
    html = re.sub(r'<meta[^>]+http-equiv\s*=\s*["\']?refresh["\']?[^>]*>',
                  '', html, flags=re.IGNORECASE)
    return html

# ============================================================
def ensure_certificates():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print("[Сертификат] Найден")
        return True
    print("[Сертификат] Создаю...")
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress
    except ImportError:
        print("[Сертификат] cryptography не установлена")
        return False
    try:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subj = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, LOCAL_IP)])
        cert = (x509.CertificateBuilder()
            .subject_name(subj).issuer_name(subj)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() +
                             datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName(LOCAL_IP),
                x509.IPAddress(ipaddress.ip_address(LOCAL_IP)),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]), critical=False)
            .sign(key, hashes.SHA256()))
        with open(KEY_FILE, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()))
        with open(CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        print(f"[Сертификат] Создан")
        return True
    except Exception as e:
        print(f"[Сертификат] Ошибка: {e}")
        return False

# ============================================================
def upnp_init():
    global _upnp, _upnp_available
    if not UPNP_LIB:
        print("[UPnP] miniupnpc не установлена")
        return
    try:
        _upnp = miniupnpc.UPnP()
        _upnp.discoverdelay = 200
        if _upnp.discover() == 0:
            print("[UPnP] Роутер не найден")
            return
        _upnp.selectigd()
        _upnp_available = True
        print(f"[UPnP] Роутер: {_upnp.statusinfo()}")
    except Exception as e:
        print(f"[UPnP] Ошибка: {e}")


def upnp_open_port(port, description="Gengruc"):
    if not _upnp_available or _upnp is None:
        return False
    try:
        ip = _upnp.lanaddr
        _upnp.addportmapping(port, "TCP", ip, port, description, "")
        print(f"[UPnP] Порт {port} открыт")
        return True
    except Exception as e:
        print(f"[UPnP] Порт {port} — ошибка: {e}")
        return False


def upnp_close_port(port):
    global _upnp_available
    if not _upnp_available or _upnp is None:
        return False
    try:
        _upnp.deleteportmapping(port, "TCP")
        print(f"[UPnP] Порт {port} закрыт")
        return True
    except Exception as e:
        print(f"[UPnP] Ошибка порта {port}: {e}")
        _upnp_available = False
        return False

# ============================================================
def chat_db_init():
    conn = sqlite3.connect(CHAT_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT, text TEXT, ts TEXT)""")
    conn.commit()
    conn.close()


def chat_save(user, text):
    conn = sqlite3.connect(CHAT_DB)
    conn.execute("INSERT INTO messages (user, text, ts) VALUES (?, ?, ?)",
                 (user, text, datetime.datetime.now().strftime("%H:%M:%S")))
    conn.commit()
    conn.close()


def chat_load(limit=100):
    conn = sqlite3.connect(CHAT_DB)
    rows = conn.execute(
        "SELECT user, text, ts FROM messages ORDER BY id DESC LIMIT ?",
        (limit,)).fetchall()
    conn.close()
    return list(reversed(rows))

# ============================================================
def create_startup_shortcut():
    try:
        os.makedirs(STARTUP_DIR, exist_ok=True)
        script = sys.argv[0]
        with open(STARTUP_BAT, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write(f'cd /d "{BASE_DIR}"\n')
            f.write(f'start "" "{sys.executable}" "{script}"\n')
        print(f"[Автозапуск] Создан")
        return True
    except Exception as e:
        print(f"[Автозапуск] Ошибка: {e}")
        return False


def remove_startup_shortcut():
    try:
        if os.path.exists(STARTUP_BAT):
            os.remove(STARTUP_BAT)
            print("[Автозапуск] Удалён")
    except Exception:
        pass


def ask_autostart():
    data = load_data()
    if data.get("autostart_asked"):
        return
    print()
    print("=" * 60)
    print("Добавить Gengruc в автозапуск Windows? (yes/no): ",
          end="", flush=True)
    try:
        answer = input().strip().lower()
    except EOFError:
        answer = "no"
    if answer == "yes":
        data["autostart_enabled"] = create_startup_shortcut()
    else:
        remove_startup_shortcut()
        data["autostart_enabled"] = False
    data["autostart_asked"] = True
    save_data(data)
    print()

# ============================================================
SSH_CONTEXT = {
    "load_data": load_data,
    "save_data": save_data,
    "hash_password": hash_password,
    "is_admin": is_admin,
    "get_public_ip": get_public_ip,
    "get_local_ips": get_local_ips,
    "LOCAL_IP": LOCAL_IP,
    "PAGES_DIR": PAGES_DIR,
    "BACKUPS_DIR": BACKUPS_DIR,
    "DATA_FILE": DATA_FILE,
    "LOG_FILE": LOG_FILE,
    "CHAT_DB": CHAT_DB,
    "PAGE_PORT_MIN": PAGE_PORT_MIN,
    "PAGE_PORT_MAX": PAGE_PORT_MAX,
    "PANEL_HTTPS_PORT": PANEL_HTTPS_PORT,
    "PANEL_HTTP_PORT": PANEL_HTTP_PORT,
    "SSH_PORT": SSH_PORT,
    "WS_PORT": WS_PORT,
    "VERSION": VERSION,
    "_stats": _stats,
    "_stats_lock": _stats_lock,
    "_start_time": _start_time,
    "_upnp_available": lambda: _upnp_available,
    "read_logs": read_logs,
    "chat_load": chat_load,
    "find_free_port": find_free_port,
    "sanitize_html": sanitize_html,
    "start_page_server": lambda pid, port: start_page_server(pid, port),
    "upnp_open_port": upnp_open_port,
    "upnp_close_port": upnp_close_port,
}

# ============================================================
class GserverHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def version_string(self):
        return SERVER_NAME

    def log_message(self, format, *args):
        pass

# ============================================================
def make_page_handler(page_id):
    class PageHandler(GserverHandler):
        def do_GET(self):
            if self.path == "/favicon.ico":
                if os.path.exists(FAVICON_FILE):
                    try:
                        with open(FAVICON_FILE, "rb") as f:
                            data = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "image/x-icon")
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    except Exception:
                        pass
                self.send_response(404)
                self.end_headers()
                return

            data = load_data()
            page = data["pages"].get(page_id)
            if not page or not page.get("enabled", True):
                body = b"<h1>404 - not found</h1>"
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
                return
            path = os.path.join(PAGES_DIR, f"{page_id}.html")
            try:
                with open(path, "rb") as f:
                    content = f.read()
            except FileNotFoundError:
                content = b"<h1>404 - page file missing</h1>"
            with _stats_lock:
                _stats["page_requests"] += 1
                _stats["bytes_served"] += len(content)
                page["visits"] = page.get("visits", 0) + 1
                ip = self.address_string()
                if ip not in page.get("unique_ips", []):
                    page.setdefault("unique_ips", []).append(ip)
                    save_data(data)
            log_access(self.address_string(), page["port"], "/",
                       self.headers.get("User-Agent", ""))
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Security-Policy",
                    "default-src 'self'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; object-src 'none'; "
                    "frame-ancestors 'none'; base-uri 'self'; "
                    "form-action 'self'")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, format, *args):
            pass
    return PageHandler


def start_page_server(page_id, port):
    handler = make_page_handler(page_id)
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), handler)
    except OSError as e:
        print(f"[Страница] Порт {port} занят: {e}")
        return None
    with _servers_lock:
        _active_servers[page_id] = httpd
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def stop_page_server(page_id):
    with _servers_lock:
        httpd = _active_servers.pop(page_id, None)
    if httpd is None:
        return
    def _shutdown():
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
    threading.Thread(target=_shutdown, daemon=True).start()

# ============================================================
COMMON_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; }
body { font-family:'Segoe UI',Arial,sans-serif; color:#e8eaf6;
       min-height:100vh; overflow-x:hidden; position:relative;
       background:#05070f; }
.container { position:relative; z-index:1; max-width:900px;
    margin:0 auto; padding:40px 20px; }
.glass { background:rgba(10,20,45,0.55);
    border:1px solid rgba(100,150,255,0.18); border-radius:24px;
    padding:32px; margin-bottom:24px; box-shadow:0 8px 32px rgba(0,0,0,0.5);
    animation:fadeUp 0.5s ease-out; }
@keyframes fadeUp {
    from { opacity:0; transform:translateY(20px); }
    to { opacity:1; transform:translateY(0); }
}
.logo { display:flex; align-items:center; justify-content:center;
        gap:16px; margin-bottom:12px; }
.logo-mark { width:56px; height:56px; border-radius:16px;
    background:linear-gradient(135deg,#5a9fff,#a78bfa,#6366f1);
    display:flex; align-items:center; justify-content:center;
    font-size:28px; font-weight:800; color:#fff; }
.logo-text { font-size:36px; font-weight:800; letter-spacing:-1px;
    background:linear-gradient(135deg,#a5c8ff,#7aa2f7,#c0a8ff);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
h2 { font-size:20px; font-weight:600; color:#b0c4ff; margin-bottom:20px; }
.subtitle { color:#8a9bc8; font-size:14px; margin-bottom:24px; text-align:center; }
input, textarea { width:100%; padding:14px 18px; margin:8px 0;
    background:rgba(5,10,25,0.7); color:#e8eaf6;
    border:1px solid rgba(100,150,255,0.25); border-radius:14px;
    font-family:Consolas,monospace; font-size:14px; outline:none;
    box-sizing:border-box; }
textarea { height:160px; resize:vertical; line-height:1.5; }
button { padding:12px 26px;
    background:linear-gradient(135deg,#5a9fff,#6366f1);
    color:#fff; border:none; border-radius:14px; cursor:pointer;
    font-weight:600; font-size:14px; margin-right:8px; margin-top:8px; }
button.danger { background:linear-gradient(135deg,#ef4444,#dc2626); }
button.ok { background:linear-gradient(135deg,#10b981,#059669); }
.page-row { display:flex; justify-content:space-between; align-items:flex-start;
    padding:20px; margin:12px 0; background:rgba(5,10,25,0.6);
    border:1px solid rgba(100,150,255,0.15); border-radius:18px; }
.page-name { font-weight:600; font-size:16px; color:#d0daff; margin-bottom:6px; }
.page-meta { color:#8a9bc8; font-size:13px; margin-bottom:4px; }
.status-on { color:#4ade80; }
.status-off { color:#f87171; }
a { color:#7ec8ff; text-decoration:none; font-size:14px; }
.center-page { display:flex; flex-direction:column;
    justify-content:center; align-items:center;
    min-height:100vh; padding:20px; position:relative; z-index:1; gap:16px; }
.login-card { width:100%; max-width:440px; text-align:center; }
.error-msg { color:#f87171; font-size:14px; margin-top:12px; }
.info-box { background:rgba(5,10,25,0.7);
    border:1px solid rgba(100,150,255,0.25); border-radius:14px;
    padding:14px 18px; margin-top:16px;
    font-family:Consolas,monospace; font-size:13px;
    color:#7ec8ff; text-align:left; }
.info-box b { color:#a78bfa; }
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    gap:12px; margin-top:16px; }
.stat-box { background:rgba(5,10,25,0.7);
    border:1px solid rgba(100,150,255,0.2); border-radius:14px;
    padding:16px; text-align:center; }
.stat-value { font-size:28px; font-weight:700; color:#7aa2f7;
    font-family:Consolas,monospace; }
.stat-label { font-size:12px; color:#8a9bc8; margin-top:4px;
    text-transform:uppercase; letter-spacing:1px; }
.chat-box { background:rgba(2,5,15,0.85);
    border:1px solid rgba(90,159,255,0.3); border-radius:14px;
    padding:16px; height:400px; overflow-y:auto;
    font-family:Consolas,monospace; font-size:13px;
    color:#a5c8ff; margin-bottom:12px; }
.tool-btn { display:inline-block; padding:6px 12px; margin-left:6px;
    background:linear-gradient(135deg,#5a9fff,#6366f1);
    color:#fff; border-radius:8px; font-size:12px;
    text-decoration:none; font-weight:600; }
.tool-btn.purple { background:linear-gradient(135deg,#a78bfa,#6366f1); }
.tool-btn.green { background:linear-gradient(135deg,#10b981,#059669); }
"""

BG_SCENE = """
<div class="bg-scene">
<div class="bg-sky"></div><div class="bg-stars"></div>
<div class="bg-moon"></div><div class="bg-sea"></div>
<div class="bg-reflection"></div>
</div>"""

LOGO_HTML = """
<div class="logo">
<div class="logo-mark">G</div>
<div class="logo-text">Gengruc<span style="-webkit-text-fill-color:#a78bfa">.</span></div>
</div>"""


def get_full_css(theme="beach"):
    if UI_AVAILABLE:
        try:
            return COMMON_CSS + "\n" + get_theme_css(theme)
        except Exception:
            pass
    return COMMON_CSS


def get_full_js():
    if UI_AVAILABLE:
        try:
            return get_themes_js_data() + "\n" + get_theme_js()
        except Exception:
            pass
    return ""


def get_ui_switcher():
    if UI_AVAILABLE:
        try:
            return get_theme_switcher_html()
        except Exception:
            pass
    return ""


def get_ui_toast():
    if UI_AVAILABLE:
        try:
            return get_toast_container()
        except Exception:
            pass
    return ""

# ============================================================
def build_login(title, subtitle, action, button, error="", default_user=""):
    css = get_full_css("beach")
    js = get_full_js()
    switcher = get_ui_switcher()
    toast = get_ui_toast()
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
<title>{title}</title>
<style>{css}</style></head>
<body data-theme="beach">{BG_SCENE}
{switcher}
<div class="center-page"><div class="glass login-card">
{LOGO_HTML}
<p class="subtitle">{subtitle}</p>
<form method="POST" action="{action}">
<input type="text" name="username" placeholder="Логин" value="{default_user}" required autofocus>
<input type="password" name="password" placeholder="Пароль" required>
<button type="submit" style="width:100%;margin-top:16px;">{button}</button>
</form>
{error}
</div></div>
{toast}
<script>{js}</script>
</body></html>"""


def build_panel(pages_html, username, password, stats, pub_ip,
                admin, users_html, upnp_ok, autostart,
                countries_block="", user_info=""):
    admin_block = ""
    if admin:
        admin_block = f"""
<div class="glass"><h2>Пользователи</h2>
{users_html}
<h2 style="margin-top:24px;">Создать пользователя</h2>
<form method="POST" action="/create_user">
<input type="text" name="new_user" placeholder="Логин" required>
<input type="password" name="new_pass" placeholder="Пароль" required>
<button type="submit">Создать пользователя</button>
</form></div>"""

    css = get_full_css("beach")
    js = get_full_js()
    switcher = get_ui_switcher()
    toast = get_ui_toast()
    chart = get_load_chart_html() if UI_AVAILABLE else ""

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
<title>Gengruc — Панель</title>
<style>{css}</style></head>
<body data-theme="beach">{BG_SCENE}
{switcher}
<div class="container">
<div class="glass" style="text-align:center;">
{LOGO_HTML}
<p class="subtitle">Панель управления | Пользователь: <b>{username}</b></p>
</div>
<div class="glass"><h2>Нагрузка сервера</h2>
<div class="stats-grid">
<div class="stat-box"><div class="stat-value">{stats["panel_requests"]}</div><div class="stat-label">Панель</div></div>
<div class="stat-box"><div class="stat-value">{stats["page_requests"]}</div><div class="stat-label">Страницы</div></div>
<div class="stat-box"><div class="stat-value">{stats["ssh_connections"]}</div><div class="stat-label">SSH</div></div>
<div class="stat-box"><div class="stat-value">{stats["bytes_str"]}</div><div class="stat-label">Трафик</div></div>
</div>
{chart}
{user_info}
<div class="info-box">
Публичный IP: <b>{pub_ip}</b><br>
Панель HTTPS: <b>https://{LOCAL_IP}</b><br>
Панель HTTP: <b>http://{LOCAL_IP}:8080</b><br>
SSH: <b>ssh {username}@{LOCAL_IP}</b><br>
UPnP: <b>{"включён" if upnp_ok else "выключен"}</b> |
Автозапуск: <b>{"включён" if autostart else "выключен"}</b>
</div></div>
{countries_block}
{admin_block}
<div class="glass"><h2>Создать новую страницу</h2>
<form method="POST" action="/create">
<input type="text" name="name" placeholder="Название" required>
<textarea name="html" placeholder="&lt;h1&gt;Привет!&lt;/h1&gt;" required></textarea>
<button type="submit">Создать</button>
</form></div>
<div class="glass"><h2>Мои страницы</h2>
<p style="margin-bottom:12px;">
<a href="/export.csv" class="tool-btn green">📊 Экспорт CSV</a>
<a href="/upnp" class="tool-btn">🌐 UPnP</a>
</p>
{pages_html}</div>
<div class="glass" style="text-align:center;">
<form method="POST" action="/passwd" style="display:inline-block; width:100%; max-width:400px; text-align:left;">
<h2 style="text-align:center;">Сменить пароль</h2>
<input type="password" name="old" placeholder="Старый пароль" required>
<input type="password" name="new" placeholder="Новый пароль" required>
<button type="submit" style="width:100%;">Сменить пароль</button>
</form></div>
<div class="glass" style="text-align:center;">
<a href="/chat" class="tool-btn">Чат</a>
<a href="/backup" class="tool-btn green">Бэкап</a>
<form method="POST" action="/logout" style="display:inline;">
<button class="danger" type="submit">Выйти</button>
</form></div>
</div>
{toast}
<script>
{js}
function copyLink(btn, url) {{
    if (navigator.clipboard) {{
        navigator.clipboard.writeText(url).then(function() {{
            var o = btn.textContent;
            btn.textContent = '✅';
            setTimeout(function() {{ btn.textContent = o; }}, 1200);
        }});
    }} else {{
        var i = document.createElement('input');
        i.value = url;
        document.body.appendChild(i);
        i.select();
        try {{ document.execCommand('copy'); }} catch(e) {{}}
        document.body.removeChild(i);
        btn.textContent = '✅';
        setTimeout(function() {{ btn.textContent = '📋'; }}, 1200);
    }}
}}
</script>
</body></html>"""


def build_chat(username):
    css = get_full_css("beach")
    js = get_full_js()
    switcher = get_ui_switcher()
    toast = get_ui_toast()
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title>Чат — Gengruc</title>
<style>{css}</style></head>
<body data-theme="beach">{BG_SCENE}
{switcher}
<div class="container">
<div class="glass" style="text-align:center;">
{LOGO_HTML}
<p class="subtitle">Общий чат | Пользователь: {username}</p>
</div>
<div class="glass"><h2>Общий чат</h2>
<div class="chat-box" id="chat"></div>
<form method="POST" action="/chat_send">
<input type="text" name="text" placeholder="Сообщение..." required autofocus>
<button type="submit">Отправить</button>
</form></div>
<div class="glass" style="text-align:center;">
<a href="/" class="tool-btn">← Назад</a>
</div></div>
{toast}
<script>
{js}
(function() {{
    var chat = document.getElementById('chat');
    var proto = (location.protocol === 'https:') ? 'wss://' : 'ws://';
    var wsUrl = proto + location.hostname + ':8443';
    try {{
        var ws = new WebSocket(wsUrl);
        ws.onmessage = function(e) {{
            var line = document.createElement('div');
            line.textContent = e.data;
            chat.appendChild(line);
            chat.scrollTop = chat.scrollHeight;
        }};
    }} catch(err) {{
        chat.innerHTML = '<div style="color:#f87171">WebSocket не поддерживается.</div>';
    }}
}})();
</script>
</body></html>"""

# ============================================================
class PanelHandler(GserverHandler):
    is_secure = False

    def get_session(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("session="):
                return part.split("=", 1)[1]
        return None

    def current_user(self):
        token = self.get_session()
        data = load_data()
        for u in [data["username"]] + list(data["users"].keys()):
            sessions = (data["sessions"] if u == data["username"]
                        else data["users"][u].get("sessions", []))
            if token in sessions:
                return u
        return None

    def is_authed(self):
        return self.current_user() is not None

    def render(self, html, code=200):
        body = html.encode("utf-8")
        with _stats_lock:
            _stats["panel_requests"] += 1
            _stats["bytes_served"] += len(body)
        try:
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def send_favicon(self):
        if os.path.exists(FAVICON_FILE):
            try:
                with open(FAVICON_FILE, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception:
                pass
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def set_cookie(self, token):
        flags = "Path=/; HttpOnly"
        if self.is_secure:
            flags += "; Secure"
        self.send_header("Set-Cookie", f"session={token}; {flags}")

    def do_GET(self):
        if self.path == "/favicon.ico":
            return self.send_favicon()
        ip = self.address_string()
        if is_ip_blocked(ip):
            return self.render("<h1>403</h1>", 403)
        data = load_data()
        path = urllib.parse.urlparse(self.path).path
        log_access(ip, self.server.server_address[1], path,
                   self.headers.get("User-Agent", ""))
        if not self.is_authed():
            return self.render(build_login(
                "Вход в панель", "Введите логин и пароль",
                "/login", "Войти", default_user=data["username"]))
        user = self.current_user()
        if path == "/":
            return self.render(self.render_panel(user))
        if path == "/backup":
            return self.handle_backup()
        if path == "/chat":
            return self.render(build_chat(user))
        if path == "/upnp":
            return self.render(self.handle_upnp_page(user))
        if path == "/export.csv":
            return self.handle_csv_export()
        if path.startswith("/edit/"):
            return self.render(self.handle_edit_page(user, path[6:]))
        if path.startswith("/qr/"):
            return self.render(self.handle_qr_page(user, path[4:]))
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        ip = self.address_string()
        if is_ip_blocked(ip):
            return self.render("<h1>403</h1>", 403)
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
        except Exception:
            return self.render("<h1>400</h1>", 400)
        params = urllib.parse.parse_qs(body)
        path = urllib.parse.urlparse(self.path).path

        if path == "/login":
            username = params.get("username", [""])[0].strip()
            password = params.get("password", [""])[0]
            if check_credentials(username, password):
                token = secrets.token_hex(16)
                data = load_data()
                if username == data["username"]:
                    data["sessions"].append(token)
                else:
                    data["users"][username].setdefault("sessions", []).append(token)
                save_data(data)
                reset_failed_login(ip)
                self.send_response(302)
                self.send_header("Location", "/")
                self.set_cookie(token)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            blocked = register_failed_login(ip)
            err = ("<p class='error-msg'>Неверный логин или пароль</p>"
                   if not blocked else
                   "<p class='error-msg'>IP заблокирован на 15 минут</p>")
            return self.render(build_login(
                "Вход в панель", "Введите логин и пароль",
                "/login", "Войти", default_user=load_data()["username"],
                error=err))

        if not self.is_authed():
            return self.redirect("/")

        user = self.current_user()
        admin = is_admin(user)

        if path == "/create":
            name = params.get("name", [""])[0].strip()
            html = sanitize_html(params.get("html", [""])[0])
            data = load_data()
            used_ports = {p["port"] for p in data["pages"].values()}
            page_id = secrets.token_hex(4)
            port = find_free_port(used_ports) or PAGE_PORT_MIN
            with open(os.path.join(PAGES_DIR, f"{page_id}.html"),
                      "w", encoding="utf-8") as f:
                f.write(html)
            data["pages"][page_id] = {
                "name": name or f"Страница {page_id}",
                "port": port, "enabled": True, "owner": user,
                "visits": 0, "unique_ips": []}
            save_data(data)
            start_page_server(page_id, port)
            # UPnP в фоне — не блокирует ответ
            threading.Thread(
                target=upnp_open_port,
                args=(port, f"Gengruc {name}"),
                daemon=True
            ).start()
            return self.redirect("/?created=1")

        if path == "/create_user" and admin:
            new_user = params.get("new_user", [""])[0].strip()
            new_pass = params.get("new_pass", [""])[0]
            if not new_user or len(new_pass) < 3:
                return self.redirect("/")
            data = load_data()
            if new_user in data["users"] or new_user == data["username"]:
                return self.redirect("/")
            data["users"][new_user] = {
                "password_hash": hash_password(new_pass),
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "sessions": []}
            save_data(data)
            return self.redirect("/")

        if path == "/delete_user" and admin:
            target = params.get("user", [""])[0]
            data = load_data()
            if target in data["users"]:
                del data["users"][target]
                save_data(data)
            return self.redirect("/")

        if path == "/toggle":
            page_id = params.get("id", [""])[0]
            data = load_data()
            if page_id in data["pages"]:
                if admin or data["pages"][page_id].get("owner") == user:
                    data["pages"][page_id]["enabled"] = \
                        not data["pages"][page_id]["enabled"]
                    save_data(data)
            return self.redirect("/")

        if path == "/delete":
            page_id = params.get("id", [""])[0]
            data = load_data()
            if page_id in data["pages"]:
                if admin or data["pages"][page_id].get("owner") == user:
                    port = data["pages"][page_id]["port"]
                    threading.Thread(
                        target=upnp_close_port,
                        args=(port,),
                        daemon=True
                    ).start()
                    stop_page_server(page_id)
                    try:
                        os.remove(os.path.join(PAGES_DIR, f"{page_id}.html"))
                    except FileNotFoundError:
                        pass
                    del data["pages"][page_id]
                    save_data(data)
            return self.redirect("/")

        if path == "/edit_save":
            page_id = params.get("id", [""])[0]
            new_html = params.get("html", [""])[0]
            data = load_data()
            if page_id in data["pages"]:
                page = data["pages"][page_id]
                if admin or page.get("owner") == user:
                    new_html = sanitize_html(new_html)
                    with open(os.path.join(PAGES_DIR, f"{page_id}.html"),
                              "w", encoding="utf-8") as f:
                        f.write(new_html)
            return self.redirect("/")

        if path == "/upnp_close" and admin:
            try:
                port = int(params.get("port", ["0"])[0])
                threading.Thread(
                    target=upnp_close_port,
                    args=(port,),
                    daemon=True
                ).start()
            except Exception:
                pass
            return self.redirect("/upnp")

        if path == "/passwd":
            old = params.get("old", [""])[0]
            new = params.get("new", [""])[0]
            data = load_data()
            if len(new) < 3:
                return self.redirect("/")
            if user == data["username"]:
                if old == data["password"]:
                    data["password"] = new
                    save_data(data)
            else:
                u = data["users"][user]
                if u["password_hash"] == hash_password(old):
                    u["password_hash"] = hash_password(new)
                    save_data(data)
            return self.redirect("/")

        if path == "/chat_send":
            text = params.get("text", [""])[0]
            if text:
                chat_save(user, text)
                try:
                    asyncio.run_coroutine_threadsafe(
                        ws_broadcast(f"{user}: {text}"), _ws_loop)
                except Exception:
                    pass
            return self.redirect("/chat")

        if path == "/logout":
            token = self.get_session()
            data = load_data()
            if token in data["sessions"]:
                data["sessions"].remove(token)
            for u in data["users"].values():
                if token in u.get("sessions", []):
                    u["sessions"].remove(token)
            save_data(data)
            self.send_response(302)
            self.send_header("Location", "/")
            flags = "Path=/; Max-Age=0; HttpOnly"
            if self.is_secure:
                flags += "; Secure"
            self.send_header("Set-Cookie", f"session=; {flags}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def handle_edit_page(self, user, page_id):
        data = load_data()
        page = data["pages"].get(page_id)
        if not page:
            return "<h1>404 - страница не найдена</h1>"
        if not is_admin(user) and page.get("owner") != user:
            return "<h1>403 - это не ваша страница</h1>"
        fpath = os.path.join(PAGES_DIR, f"{page_id}.html")
        html = ""
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                html = f.read()
        if FEATURES_AVAILABLE:
            return build_edit_page(page_id, page["name"], html, user, LOCAL_IP)
        return f"<h1>Редактор недоступен</h1>"

    def handle_qr_page(self, user, page_id):
        data = load_data()
        page = data["pages"].get(page_id)
        if not page:
            return "<h1>404</h1>"
        if not is_admin(user) and page.get("owner") != user:
            return "<h1>403</h1>"
        url = f"http://{LOCAL_IP}:{page['port']}"
        if FEATURES_AVAILABLE:
            return build_qr_page(page_id, page["name"], url)
        return f"<h1>{url}</h1>"

    def handle_upnp_page(self, user):
        if not is_admin(user):
            return "<h1>403 - только для root</h1>"
        # Кэш на 10 секунд
        if time.time() - _upnp_cache["time"] < 10:
            ports = _upnp_cache["data"]
        else:
            ports = {}
            if _upnp_available and _upnp is not None:
                try:
                    idx = 0
                    while True:
                        entry = _upnp.getgenericportmapping(idx)
                        if entry is None:
                            break
                        ports[entry[1]] = entry[3] if len(entry) > 3 else ""
                        idx += 1
                except Exception:
                    pass
            _upnp_cache["time"] = time.time()
            _upnp_cache["data"] = ports
        if FEATURES_AVAILABLE:
            return build_upnp_page(ports, _upnp_available, LOCAL_IP, user)
        return f"<h1>UPnP: {'активен' if _upnp_available else 'нет'}</h1>"

    def handle_csv_export(self):
        data = load_data()
        csv_text = export_pages_csv(data) if FEATURES_AVAILABLE else "ID;Name\n"
        body = csv_text.encode("utf-8-sig")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="gengruc_pages.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def handle_backup(self):
        try:
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.exists(DATA_FILE):
                    z.write(DATA_FILE, "data.json")
                for f in os.listdir(PAGES_DIR):
                    z.write(os.path.join(PAGES_DIR, f), f"pages/{f}")
            buf.seek(0)
            content = buf.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition",
                             "attachment; filename=gengruc_backup.zip")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.render(f"<h1>Ошибка: {e}</h1>", 500)

    def render_panel(self, user):
        data = load_data()
        admin = is_admin(user)
        rows = []
        for page_id, page in data["pages"].items():
            if not admin and page.get("owner") != user:
                continue
            enabled = page.get("enabled", True)
            status_class = "status-on" if enabled else "status-off"
            status_text = "Включена" if enabled else "Выключена"
            toggle_label = "Выключить" if enabled else "Включить"
            visits = page.get("visits", 0)
            unique = len(page.get("unique_ips", []))
            owner_label = ""
            if admin:
                owner_label = f' <span style="color:#8a9bc8">[{page.get("owner","?")}]</span>'
            url = f"http://{LOCAL_IP}:{page['port']}"
            rows.append(
                '<div class="page-row"><div style="flex:1">'
                f'<div class="page-name">{page["name"]}{owner_label}</div>'
                f'<div class="page-meta">Порт <b>{page["port"]}</b> — '
                f'<span class="{status_class}">{status_text}</span> — '
                f'посещений: {visits} ({unique} уник.)</div>'
                f'<a href="{url}" target="_blank">{url}</a>'
                f'<button type="button" onclick="copyLink(this, \'{url}\')" '
                f'style="padding:4px 10px;font-size:12px;margin:0 0 0 8px;">📋</button>'
                f'<a href="/edit/{page_id}" class="tool-btn">✏</a>'
                f'<a href="/qr/{page_id}" class="tool-btn purple">🔲</a>'
                '</div>'
                '<div>'
                '<form method="POST" action="/toggle" style="display:inline">'
                f'<input type="hidden" name="id" value="{page_id}">'
                f'<button class="ok" type="submit">{toggle_label}</button>'
                '</form>'
                '<form method="POST" action="/delete" style="display:inline">'
                f'<input type="hidden" name="id" value="{page_id}">'
                '<button class="danger" type="submit">Удалить</button>'
                '</form></div></div>')
        pages_html = "".join(rows) if rows else \
            "<div style='color:#8a9bc8;padding:20px'>Пока нет страниц.</div>"

        users_html = ""
        if admin:
            user_rows = []
            for u in data["users"]:
                user_rows.append(
                    f'<div class="page-row"><div style="flex:1"><b>{u}</b>'
                    f'</div><div><form method="POST" action="/delete_user">'
                    f'<input type="hidden" name="user" value="{u}">'
                    f'<button class="danger" type="submit">Удалить</button>'
                    f'</form></div></div>')
            users_html = "".join(user_rows) if user_rows else \
                "<div style='color:#8a9bc8;padding:20px'>Нет пользователей.</div>"

        with _stats_lock:
            s = dict(_stats)
        bytes_s = s["bytes_served"]
        if bytes_s < 1024:
            bytes_str = f"{bytes_s} B"
        elif bytes_s < 1024 * 1024:
            bytes_str = f"{bytes_s / 1024:.1f} KB"
        else:
            bytes_str = f"{bytes_s / 1024 / 1024:.2f} MB"

        pub_ip = get_public_ip() or "не определён"
        stats = {"panel_requests": s["panel_requests"],
                 "page_requests": s["page_requests"],
                 "ssh_connections": s["ssh_connections"],
                 "bytes_str": bytes_str}
        display_pass = data["password"] if admin else "(скрыт)"

        countries_block = ""
        if FEATURES_AVAILABLE:
            try:
                top = get_top_countries(data, limit=5)
                if top:
                    crows = ""
                    for flag_country, cnt in top:
                        crows += (
                            '<div style="display:flex;justify-content:space-between;'
                            'padding:8px 12px;margin:6px 0;background:rgba(5,10,25,0.6);'
                            'border-radius:10px;"><span>' + flag_country +
                            '</span><b>' + str(cnt) + '</b></div>')
                    countries_block = f'<div class="glass"><h2>🌍 Топ стран</h2>{crows}</div>'
            except Exception:
                pass

        user_info = ""
        if FEATURES_AVAILABLE and not admin:
            try:
                user_info = get_user_public_info(pub_ip, LOCAL_IP, user)
            except Exception:
                pass

        return build_panel(pages_html, user, display_pass, stats, pub_ip,
                           admin, users_html, _upnp_available,
                           data.get("autostart_enabled", False),
                           countries_block, user_info)


class HTTPSPanelHandler(PanelHandler):
    is_secure = True


class HTTPPanelHandler(PanelHandler):
    is_secure = False

# ============================================================
_ws_loop = None


async def ws_handler(websocket):
    with _chat_lock:
        _chat_clients.add(websocket)
    try:
        for user, text, ts in chat_load(50):
            await websocket.send(f"[{ts}] {user}: {text}")
        async for message in websocket:
            if message:
                chat_save("anon", message)
                await ws_broadcast(f"anon: {message}")
    except Exception:
        pass
    finally:
        with _chat_lock:
            _chat_clients.discard(websocket)


async def ws_broadcast(message):
    with _chat_lock:
        clients = list(_chat_clients)
    for ws in clients:
        try:
            await ws.send(message)
        except Exception:
            pass


def start_ws_server():
    global _ws_loop
    if not WS_LIB:
        print("[WS] websockets не установлена.")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _ws_loop = loop

    async def main():
        async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
            await asyncio.Future()
    loop.run_until_complete(main())

# ============================================================
def get_host_key():
    if not os.path.exists(HOST_KEY_FILE):
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key_file(HOST_KEY_FILE)
        print(f"Создан SSH host key: {HOST_KEY_FILE}")
    return paramiko.RSAKey(filename=HOST_KEY_FILE)


def handle_ssh_client(client, addr, host_key):
    print(f"[SSH] Подключение {addr}")
    with _stats_lock:
        _stats["ssh_connections"] += 1
    transport = None
    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(host_key)
        data = load_data()

        if SSH_MODULE:
            server = GengrucSSHServer(data["password"])
        else:
            class SimpleSSHServer(paramiko.ServerInterface):
                def __init__(self, password):
                    self.password = password
                    self.event = threading.Event()
                    self.authed_user = "root"
                def check_auth_password(self, username, password):
                    if username == "root" and password == self.password:
                        return paramiko.AUTH_SUCCESSFUL
                    return paramiko.AUTH_FAILED
                def get_allowed_auths(self, username):
                    return "password"
                def check_channel_request(self, kind, chanid):
                    return paramiko.OPEN_SUCCEEDED
                def check_channel_shell_request(self, channel):
                    self.event.set()
                    return True
                def check_channel_pty_request(self, *args):
                    return True
            server = SimpleSSHServer(data["password"])

        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            return
        chan = transport.accept(20)
        if chan is None:
            return
        server.event.wait(10)
        if not server.event.is_set():
            return

        username = getattr(server, "authed_user", "root") or "root"
        prompt = f"{username}@{SERVER_NAME.lower()}> "
        chan.send("\033[0m")
        chan.send(f"{C_CYAN}========================================{C_RESET}\r\n")
        chan.send(f"{C_BOLD}{C_MAGENTA}   Gengruc SSH Console v{VERSION}{C_RESET}\r\n")
        chan.send(f"   Пользователь: {C_GREEN}{username}{C_RESET}\r\n")
        chan.send(f"   {C_YELLOW}Введите 'help'{C_RESET}\r\n")
        chan.send(f"{C_CYAN}========================================{C_RESET}\r\n")
        chan.send(f"{C_GREEN}{prompt}{C_RESET}")

        buffer = ""
        while True:
            try:
                data_bytes = chan.recv(1024)
            except Exception:
                break
            if not data_bytes:
                break
            text = data_bytes.decode("utf-8", errors="replace")
            for ch in text:
                if ch in ("\r", "\n"):
                    chan.send("\r\n")
                    if SSH_MODULE:
                        result = ssh_run_command(buffer, chan, username, SSH_CONTEXT)
                    else:
                        result = "ERR: SSH-модуль не подключён\n"
                    if result is None:
                        chan.send("До свидания!\r\n")
                        chan.close()
                        return
                    if result:
                        chan.send(result.replace("\n", "\r\n"))
                    chan.send(f"{C_GREEN}{prompt}{C_RESET}")
                    buffer = ""
                elif ch == "\x03":
                    chan.send("^C\r\n")
                    buffer = ""
                    chan.send(f"{C_GREEN}{prompt}{C_RESET}")
                elif ch in ("\x7f", "\b"):
                    if buffer:
                        buffer = buffer[:-1]
                        chan.send("\b \b")
                elif ch >= " ":
                    buffer += ch
                    chan.send(ch)
    except Exception as e:
        print(f"[SSH] Ошибка: {e}")
    finally:
        if transport:
            try:
                transport.close()
            except Exception:
                pass
        try:
            client.close()
        except Exception:
            pass
        print(f"[SSH] Отключение {addr}")


def ssh_server_loop(host_key):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", SSH_PORT))
        sock.listen(10)
    except PermissionError:
        print(f"[SSH] Нет прав на порт {SSH_PORT}")
        return
    except OSError as e:
        print(f"[SSH] Порт {SSH_PORT} занят: {e}")
        return
    print(f"[SSH] Сервер запущен на порту {SSH_PORT}")
    while True:
        try:
            client, addr = sock.accept()
        except KeyboardInterrupt:
            break
        t = threading.Thread(target=handle_ssh_client,
                             args=(client, addr, host_key), daemon=True)
        t.start()

# ============================================================
def start_https_panel():
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print("[HTTPS] Нет cert.pem / key.pem")
        return None
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", PANEL_HTTPS_PORT),
                                       HTTPSPanelHandler)
    except OSError as e:
        print(f"[HTTPS] Порт {PANEL_HTTPS_PORT} занят: {e}")
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:
        pass
    try:
        ctx.set_ciphers("ALL:@SECLEVEL=0")
    except Exception:
        pass
    ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"[HTTPS] Панель: https://{LOCAL_IP}")
    return httpd


def start_http_panel():
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", PANEL_HTTP_PORT),
                                       HTTPPanelHandler)
    except OSError as e:
        print(f"[HTTP] Порт {PANEL_HTTP_PORT} занят: {e}")
        return None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"[HTTP]  Панель: http://{LOCAL_IP}:{PANEL_HTTP_PORT}")
    return httpd

# ============================================================
def main():
    print("=" * 60)
    print(f"Gengruc Panel v{VERSION}")
    print("=" * 60)
    print(f"[Сеть] Локальный IP: {LOCAL_IP}")

    mode, local_ips, pub_ip = detect_mode()
    print(f"[Сеть] Все IP: {', '.join(local_ips) if local_ips else '—'}")
    print(f"[Сеть] Публичный IP: {pub_ip or 'не определён'}")
    if mode == "vps":
        print("[Сеть] Режим: VPS")
    elif mode == "home":
        print("[Сеть] Режим: ДОМАШНИЙ")
        upnp_init()

    ask_autostart()
    chat_db_init()
    ensure_certificates()

    if FAVICON_AVAILABLE:
        try:
            ensure_favicon(FAVICON_FILE)
            if os.path.exists(FAVICON_FILE):
                print(f"[Favicon] {FAVICON_FILE}")
        except Exception as e:
            print(f"[Favicon] Ошибка: {e}")

    data = load_data()
    for page_id, page in data["pages"].items():
        if page.get("enabled", True):
            try:
                start_page_server(page_id, page["port"])
                if mode == "home":
                    threading.Thread(
                        target=upnp_open_port,
                        args=(page["port"], f"Gengruc {page['name']}"),
                        daemon=True
                    ).start()
                print(f"[Страница] '{page['name']}' → {page['port']}")
            except Exception as e:
                print(f"[Страница] {page['port']}: {e}")

    start_https_panel()
    start_http_panel()

    host_key = get_host_key()
    t = threading.Thread(target=ssh_server_loop, args=(host_key,), daemon=True)
    t.start()

    if WS_LIB:
        t = threading.Thread(target=start_ws_server, daemon=True)
        t.start()
        print(f"[WS]   Чат на порту {WS_PORT}")

    print("=" * 60)
    print(f"Панель: https://{LOCAL_IP}")
    print(f"HTTP:   http://{LOCAL_IP}:{PANEL_HTTP_PORT}")
    print(f"SSH:    ssh root@{LOCAL_IP}")
    print("Сервер запущен. Ctrl+C для остановки.")
    print("=" * 60)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nОстановка...")
        sys.exit(0)


if __name__ == "__main__":
    main()