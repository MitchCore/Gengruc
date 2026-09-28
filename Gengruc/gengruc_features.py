# ============================================================
# Gengruc Features — модуль дополнительных функций
# Файл 4: редактор HTML, QR, CSV, карта, UPnP
# ============================================================

import os
import io
import csv
import json
import urllib.request
import urllib.parse


# ============================================================
# 1. РЕДАКТОР HTML (без предпросмотра)
# ============================================================
def build_edit_page(page_id, page_name, page_html, username, LOCAL_IP):
    """Страница редактирования HTML — простое поле, без live-preview."""
    escaped = (page_html
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title>Редактор — {page_name}</title>
<style>
body {{ font-family:'Segoe UI',Arial,sans-serif; background:#05070f; color:#e8eaf6;
       min-height:100vh; padding:40px 20px; margin:0; }}
.container {{ max-width:1000px; margin:0 auto; }}
.glass {{ background:rgba(10,20,45,0.55);
         border:1px solid rgba(100,150,255,0.18);
         border-radius:24px; padding:32px; box-shadow:0 8px 32px rgba(0,0,0,0.5); }}
h1 {{ background:linear-gradient(135deg,#a5c8ff,#7aa2f7,#c0a8ff);
     -webkit-background-clip:text; -webkit-text-fill-color:transparent;
     margin-bottom:12px; font-size:28px; }}
.meta {{ color:#8a9bc8; font-size:14px; margin-bottom:20px; }}
.meta b {{ color:#a78bfa; }}
textarea {{ width:100%; height:600px; padding:16px; border-radius:14px;
           background:rgba(5,10,25,0.8); color:#e8eaf6;
           border:1px solid rgba(100,150,255,0.3);
           font-family:Consolas,monospace; font-size:14px;
           line-height:1.5; resize:vertical; outline:none;
           box-sizing:border-box; tab-size:2; }}
textarea:focus {{ border-color:#5a9fff;
    box-shadow:0 0 0 4px rgba(90,159,255,0.2); }}
button {{ padding:14px 32px;
         background:linear-gradient(135deg,#10b981,#059669);
         color:#fff; border:none; border-radius:14px; cursor:pointer;
         font-weight:600; font-size:15px; margin-right:12px; margin-top:16px;
         transition:all 0.2s; }}
button.back {{ background:linear-gradient(135deg,#6b7280,#4b5563); }}
button:hover {{ transform:translateY(-2px); }}
.stats {{ color:#8a9bc8; font-size:12px; margin-top:12px;
         font-family:Consolas,monospace; }}
a {{ color:#7ec8ff; text-decoration:none; }}
</style></head>
<body>
<div class="container">
<div class="glass">
<h1>✏ Редактор: {page_name}</h1>
<p class="meta">ID: <b>{page_id}</b> | Пользователь: <b>{username}</b></p>
<form method="POST" action="/edit_save">
<input type="hidden" name="id" value="{page_id}">
<textarea name="html" id="editor" autofocus spellcheck="false">{escaped}</textarea>
<div class="stats">
  Символов: <span id="char-count">0</span> |
  Строк: <span id="line-count">0</span>
</div>
<button type="submit">💾 Сохранить</button>
<a href="/"><button class="back" type="button">← Назад</button></a>
</form>
</div>
</div>
<script>
var ta = document.getElementById('editor');
var cc = document.getElementById('char-count');
var lc = document.getElementById('line-count');
function updateStats() {{
    cc.textContent = ta.value.length;
    lc.textContent = ta.value.split('\\n').length;
}}
ta.addEventListener('input', updateStats);
updateStats();

// Tab = 2 пробела
ta.addEventListener('keydown', function(e) {{
    if (e.key === 'Tab') {{
        e.preventDefault();
        var start = this.selectionStart;
        var end = this.selectionEnd;
        this.value = this.value.substring(0, start) + '  ' + this.value.substring(end);
        this.selectionStart = this.selectionEnd = start + 2;
        updateStats();
    }}
}});
</script>
</body></html>"""


# ============================================================
# 2. CSV-ЭКСПОРТ
# ============================================================
def export_pages_csv(data):
    """CSV со всеми страницами."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Название", "Порт", "Владелец",
                     "Включена", "Посещений", "Уникальных IP"])
    for pid, p in data["pages"].items():
        writer.writerow([
            pid, p.get("name", ""), p.get("port", ""), p.get("owner", ""),
            "да" if p.get("enabled", True) else "нет",
            p.get("visits", 0), len(p.get("unique_ips", [])),
        ])
    return output.getvalue()


# ============================================================
# 3. QR-КОД
# ============================================================
def build_qr_page(page_id, page_name, url):
    """HTML с QR-кодом."""
    qr_url = ("https://api.qrserver.com/v1/create-qr-code/?size=300x300&data="
              + urllib.parse.quote(url))
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title>QR — {page_name}</title>
<style>
body {{ font-family:'Segoe UI',Arial,sans-serif; background:#05070f; color:#e8eaf6;
       min-height:100vh; display:flex; justify-content:center; align-items:center;
       margin:0; padding:20px; }}
.card {{ background:rgba(10,20,45,0.7);
        border:1px solid rgba(100,150,255,0.25);
        border-radius:24px; padding:40px; text-align:center; max-width:500px; }}
h1 {{ color:#a5c8ff; margin-bottom:20px; }}
img {{ background:#fff; padding:16px; border-radius:16px; margin:16px 0; }}
.url {{ font-family:Consolas,monospace; font-size:14px; color:#7ec8ff;
       word-break:break-all; margin:16px 0; }}
button {{ padding:12px 26px;
         background:linear-gradient(135deg,#5a9fff,#6366f1);
         color:#fff; border:none; border-radius:14px; cursor:pointer;
         font-weight:600; font-size:14px; margin-top:12px; }}
a {{ color:#7ec8ff; text-decoration:none; margin-top:12px;
    display:inline-block; }}
</style></head>
<body><div class="card">
<h1>🔲 QR-код</h1>
<p>{page_name}</p>
<img src="{qr_url}" alt="QR">
<div class="url">{url}</div>
<button onclick="window.print()">🖨 Печать</button><br>
<a href="/">← Назад в панель</a>
</div></body></html>"""


# ============================================================
# 4. ГЕОЛОКАЦИЯ / ФЛАГИ СТРАН
# ============================================================
_geo_cache = {}

COUNTRY_FLAGS = {
    "RU": "🇷🇺 Россия", "US": "🇺🇸 США", "DE": "🇩🇪 Германия",
    "FR": "🇫🇷 Франция", "GB": "🇬🇧 Британия", "CN": "🇨🇳 Китай",
    "JP": "🇯🇵 Япония", "IN": "🇮🇳 Индия", "BR": "🇧🇷 Бразилия",
    "UA": "🇺🇦 Украина", "KZ": "🇰🇿 Казахстан", "BY": "🇧🇾 Беларусь",
    "TR": "🇹🇷 Турция", "IT": "🇮🇹 Италия", "ES": "🇪🇸 Испания",
    "PL": "🇵🇱 Польша", "NL": "🇳🇱 Нидерланды", "FI": "🇫🇮 Финляндия",
    "SE": "🇸🇪 Швеция", "KR": "🇰🇷 Корея", "AU": "🇦🇺 Австралия",
    "CA": "🇨🇦 Канада", "MX": "🇲🇽 Мексика", "AR": "🇦🇷 Аргентина",
    "ZZ": "🌍 Прочие",
}


def get_country_by_ip(ip):
    if not ip or ip in ("127.0.0.1", "localhost"):
        return "ZZ"
    if ip.startswith(("192.168.", "10.", "172.")):
        return "ZZ"
    if ip in _geo_cache:
        return _geo_cache[ip]
    try:
        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        with urllib.request.urlopen(url, timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
            code = data.get("countryCode", "ZZ")
            _geo_cache[ip] = code
            return code
    except Exception:
        _geo_cache[ip] = "ZZ"
        return "ZZ"


def get_top_countries(data, limit=5):
    counts = {}
    for page in data["pages"].values():
        for ip in page.get("unique_ips", []):
            code = get_country_by_ip(ip)
            counts[code] = counts.get(code, 0) + 1
    sorted_c = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [(COUNTRY_FLAGS.get(code, f"🌍 {code}"), cnt)
            for code, cnt in sorted_c]


# ============================================================
# 5. UPnP-ПАНЕЛЬ
# ============================================================
def build_upnp_page(upnp_ports, upnp_available, LOCAL_IP, username):
    status = ('<span style="color:#4ade80">✅ UPnP активен</span>'
              if upnp_available
              else '<span style="color:#f87171">❌ UPnP недоступен</span>')

    if upnp_ports:
        rows = ""
        for port, desc in upnp_ports.items():
            rows += (
                '<div style="display:flex;justify-content:space-between;'
                'align-items:center;padding:12px 16px;margin:8px 0;'
                'background:rgba(5,10,25,0.6);border-radius:12px;">'
                f'<div><b>Порт {port}</b><br>'
                f'<span style="color:#8a9bc8;font-size:13px;">{desc}</span></div>'
                f'<div><button onclick="closePort(\'{port}\')" '
                f'style="background:linear-gradient(135deg,#ef4444,#dc2626);">'
                f'Закрыть</button></div></div>')
    else:
        rows = '<div style="color:#8a9bc8;padding:20px;">Нет открытых портов.</div>'

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<title>UPnP — Gengruc</title>
<style>
body {{ font-family:'Segoe UI',Arial,sans-serif; background:#05070f; color:#e8eaf6;
       min-height:100vh; padding:40px 20px; margin:0; }}
.container {{ max-width:900px; margin:0 auto; }}
.glass {{ background:rgba(10,20,45,0.55);
         border:1px solid rgba(100,150,255,0.18);
         border-radius:24px; padding:32px; margin-bottom:24px; }}
h2 {{ color:#a5c8ff; margin-bottom:20px; }}
button {{ padding:8px 16px;
         background:linear-gradient(135deg,#5a9fff,#6366f1);
         color:#fff; border:none; border-radius:12px; cursor:pointer;
         font-weight:600; font-size:13px; }}
a {{ color:#7ec8ff; text-decoration:none; }}
</style></head>
<body><div class="container">
<div class="glass">
<h2>🌐 Настройка UPnP</h2>
<p>Статус: {status}</p>
</div>
<div class="glass">
<h2>Открытые порты ({len(upnp_ports)})</h2>
{rows}
</div>
<div class="glass" style="text-align:center;">
<a href="/"><button>← Назад</button></a>
</div>
</div>
<script>
function closePort(port) {{
    if (!confirm('Закрыть порт ' + port + '?')) return;
    fetch('/upnp_close', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
        body: 'port=' + encodeURIComponent(port)
    }}).then(function() {{ location.reload(); }})
      .catch(function() {{ alert('Ошибка'); }});
}}
</script>
</body></html>"""


# ============================================================
# 6. ИНФО О ПОЛЬЗОВАТЕЛЕ (публичный IP)
# ============================================================
def get_user_public_info(public_ip, local_ip, username):
    return (f'<div class="info-box">'
            f'<b>Ваш сервер:</b><br>'
            f'Публичный IP: <b>{public_ip}</b><br>'
            f'Локальный IP: <b>{local_ip}</b><br>'
            f'SSH: <b>ssh {username}@{local_ip}</b><br>'
            f'</div>')