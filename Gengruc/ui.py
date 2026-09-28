# ============================================================
# Gengruc UI — темы, 3D-карточки, фон, анимации
# v1.2 — фон меняется вместе с темой
# ============================================================

import json

THEMES = {
    "beach": {
        "name": "🌙 Ночной пляж",
        "bg1": "#02030a", "bg2": "#060b1f", "bg3": "#0a1230",
        "bg4": "#0f1b3d", "accent1": "#5a9fff", "accent2": "#a78bfa",
        "accent3": "#6366f1", "text": "#e8eaf6", "text_dim": "#8a9bc8",
        "card_bg": "rgba(10,20,45,0.55)",
        "border": "rgba(100,150,255,0.18)"
    },
    "space": {
        "name": "🚀 Космос",
        "bg1": "#000000", "bg2": "#0a0020", "bg3": "#150030",
        "bg4": "#200050", "accent1": "#c084fc", "accent2": "#f0abfc",
        "accent3": "#a855f7", "text": "#f3e8ff", "text_dim": "#a78bfa",
        "card_bg": "rgba(30,0,60,0.55)",
        "border": "rgba(192,132,252,0.25)"
    },
    "sunset": {
        "name": "🌅 Закат",
        "bg1": "#1a0a00", "bg2": "#3d0f1a", "bg3": "#7d1128",
        "bg4": "#b03a3a", "accent1": "#ff6b6b", "accent2": "#ffa94d",
        "accent3": "#f76707", "text": "#fff3e0", "text_dim": "#ffc9a0",
        "card_bg": "rgba(60,15,20,0.55)",
        "border": "rgba(255,140,80,0.3)"
    },
    "matrix": {
        "name": "💊 Матрица",
        "bg1": "#000000", "bg2": "#001100", "bg3": "#002200",
        "bg4": "#003300", "accent1": "#00ff41", "accent2": "#00cc33",
        "accent3": "#00aa22", "text": "#c8ffc8", "text_dim": "#66cc66",
        "card_bg": "rgba(0,20,0,0.7)",
        "border": "rgba(0,255,65,0.3)"
    },
    "cyberpunk": {
        "name": "🌆 Киберпанк",
        "bg1": "#05010f", "bg2": "#12003a", "bg3": "#2a0066",
        "bg4": "#440099", "accent1": "#ff00ff", "accent2": "#00ffff",
        "accent3": "#ff0080", "text": "#ffe6ff", "text_dim": "#cc99ff",
        "card_bg": "rgba(20,0,60,0.6)",
        "border": "rgba(255,0,255,0.35)"
    }
}


def get_theme_css(theme_key="beach"):
    """CSS для темы. Все элементы фона используют переменные."""
    t = THEMES.get(theme_key, THEMES["beach"])
    return f"""
:root {{
    --bg1: {t['bg1']};
    --bg2: {t['bg2']};
    --bg3: {t['bg3']};
    --bg4: {t['bg4']};
    --accent1: {t['accent1']};
    --accent2: {t['accent2']};
    --accent3: {t['accent3']};
    --text: {t['text']};
    --text-dim: {t['text_dim']};
    --card-bg: {t['card_bg']};
    --border: {t['border']};
}}

/* ===== ФОН ===== */
body {{
    background: var(--bg1) !important;
    color: var(--text);
    transition: background 0.8s ease, color 0.8s ease;
}}

.bg-scene {{
    position: fixed;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    filter: blur(2px) saturate(1.1);
    transform: scale(1.05);
}}

.bg-sky {{
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom,
        var(--bg1) 0%, var(--bg2) 25%, var(--bg3) 50%,
        var(--bg4) 65%, var(--bg3) 75%, var(--bg2) 85%, var(--bg1) 100%);
    transition: background 0.8s ease;
}}

.bg-moon {{
    position: absolute;
    top: 12%;
    right: 18%;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: radial-gradient(circle at 40% 40%,
        #fffef0 0%, var(--accent1) 50%, var(--accent2) 100%);
    box-shadow: 0 0 60px var(--accent1),
                0 0 120px var(--accent2);
    animation: moonGlow 6s ease-in-out infinite alternate;
    transition: background 0.8s ease, box-shadow 0.8s ease;
}}

@keyframes moonGlow {{
    0%   {{ box-shadow: 0 0 40px var(--accent1); }}
    100% {{ box-shadow: 0 0 80px var(--accent2); }}
}}

.bg-stars {{
    position: absolute;
    top: 0;
    left: 0;
    width: 2px;
    height: 2px;
    border-radius: 50%;
    background: transparent;
    box-shadow:
        12vw 8vh 0 0 #fff,
        25vw 15vh 0 0 var(--accent2),
        38vw 5vh 0 0 #fff,
        52vw 12vh 0 0 var(--accent1),
        67vw 7vh 0 0 #fff,
        80vw 18vh 0 0 var(--accent2),
        92vw 10vh 0 0 #fff,
        8vw 22vh 0 0 var(--accent1),
        20vw 28vh 0 0 #fff,
        33vw 20vh 0 0 var(--accent2),
        45vw 25vh 0 0 #fff,
        58vw 30vh 0 0 var(--accent1),
        72vw 22vh 0 0 #fff,
        88vw 28vh 0 0 var(--accent2);
    animation: twinkle 4s ease-in-out infinite alternate;
    transition: box-shadow 0.8s ease;
}}

@keyframes twinkle {{
    0%   {{ opacity: 0.5; }}
    100% {{ opacity: 1; }}
}}

.bg-sea {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 35%;
    background: linear-gradient(to bottom,
        var(--bg3) 0%, var(--bg2) 50%, var(--bg1) 100%);
    transition: background 0.8s ease;
}}

.bg-reflection {{
    position: absolute;
    bottom: 0;
    right: 12%;
    width: 14%;
    height: 35%;
    background: linear-gradient(to bottom,
        var(--accent1) 0%, transparent 100%);
    opacity: 0.35;
    filter: blur(8px);
    border-radius: 50%;
    transform: skewX(-3deg);
    animation: shimmer 5s ease-in-out infinite;
    transition: background 0.8s ease;
}}

@keyframes shimmer {{
    0%, 100% {{ opacity: 0.4; }}
    50%      {{ opacity: 0.7; }}
}}

/* ===== 3D-КАРТОЧКИ ===== */
.glass {{
    transform-style: preserve-3d;
    will-change: transform;
    transition: transform 0.15s ease-out,
                box-shadow 0.3s ease,
                border-color 0.3s ease;
}}
.glass:hover {{
    border-color: var(--accent1);
    box-shadow: 0 20px 60px rgba(0,0,0,0.6),
                0 0 40px var(--accent1);
}}

/* ===== КНОПКИ С ПЕРЕЛИВОМ ===== */
button {{
    position: relative;
    overflow: hidden;
}}
button::after {{
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg,
        transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.5s;
}}
button:hover::after {{
    left: 100%;
}}

/* ===== ПЕРЕКЛЮЧАТЕЛЬ ТЕМ ===== */
.theme-switcher {{
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 10px;
    display: flex;
    gap: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    transition: background 0.6s ease, border-color 0.6s ease;
}}
.theme-btn {{
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    padding: 0;
    margin: 0;
    transition: all 0.2s;
    font-size: 0;
}}
.theme-btn:hover {{
    transform: scale(1.15);
    box-shadow: 0 0 20px currentColor;
}}
.theme-btn.active {{
    border-color: #fff;
    box-shadow: 0 0 20px currentColor;
}}
.theme-btn[data-theme="beach"]     {{ background: linear-gradient(135deg, #0a1230, #5a9fff); }}
.theme-btn[data-theme="space"]     {{ background: linear-gradient(135deg, #0a0020, #c084fc); }}
.theme-btn[data-theme="sunset"]    {{ background: linear-gradient(135deg, #7d1128, #ffa94d); }}
.theme-btn[data-theme="matrix"]    {{ background: linear-gradient(135deg, #002200, #00ff41); }}
.theme-btn[data-theme="cyberpunk"] {{ background: linear-gradient(135deg, #2a0066, #ff00ff); }}

/* ===== TOAST-УВЕДОМЛЕНИЯ ===== */
.toast-container {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 10px;
}}
.toast {{
    min-width: 250px;
    padding: 16px 20px;
    border-radius: 14px;
    background: var(--card-bg);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    animation: toastIn 0.4s ease-out;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.toast.success {{ border-left: 4px solid #4ade80; }}
.toast.error   {{ border-left: 4px solid #f87171; }}
.toast.info    {{ border-left: 4px solid var(--accent1); }}

@keyframes toastIn {{
    from {{ opacity: 0; transform: translateX(100%); }}
    to   {{ opacity: 1; transform: translateX(0); }}
}}
.toast.hide {{
    animation: toastOut 0.4s ease-out forwards;
}}
@keyframes toastOut {{
    from {{ opacity: 1; transform: translateX(0); }}
    to   {{ opacity: 0; transform: translateX(100%); }}
}}

/* ===== КОНФЕТТИ ===== */
.confetti {{
    position: fixed;
    width: 10px;
    height: 10px;
    z-index: 99999;
    pointer-events: none;
    animation: confettiFall 3s linear forwards;
}}
@keyframes confettiFall {{
    0%   {{ opacity: 1; transform: translateY(0) rotate(0deg); }}
    100% {{ opacity: 0; transform: translateY(100vh) rotate(720deg); }}
}}

/* ===== ГРАФИК НАГРУЗКИ ===== */
.load-chart {{
    background: rgba(2,5,15,0.6);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    margin-top: 16px;
    height: 120px;
    position: relative;
    overflow: hidden;
}}
.load-chart svg {{
    width: 100%;
    height: 100%;
    overflow: visible;
}}
.load-chart .chart-label {{
    position: absolute;
    top: 8px;
    left: 12px;
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ===== МОБИЛЬНАЯ АДАПТАЦИЯ ===== */
@media (max-width: 600px) {{
    .theme-switcher {{ top: 10px; right: 10px; padding: 8px; }}
    .theme-btn {{ width: 32px; height: 32px; }}
}}
"""


def get_theme_js(theme_key="beach"):
    """JS: смена темы, 3D-карточки, уведомления, конфетти, счётчики."""
    return """
// ===== СМЕНА ТЕМЫ =====
function setTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    try { localStorage.setItem('gengruc-theme', theme); } catch(e) {}

    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === theme);
    });

    var themeData = THEMES_DATA[theme];
    if (themeData) {
        var root = document.documentElement;
        var keys = ['bg1','bg2','bg3','bg4',
                    'accent1','accent2','accent3',
                    'text','text_dim','card_bg','border'];
        for (var i = 0; i < keys.length; i++) {
            var k = keys[i];
            if (themeData[k]) {
                var cssVar = '--' + k.replace(/_/g, '-');
                root.style.setProperty(cssVar, themeData[k]);
            }
        }
    }
}

function initTheme() {
    var saved = 'beach';
    try { saved = localStorage.getItem('gengruc-theme') || 'beach'; } catch(e) {}
    setTheme(saved);
}

// ===== 3D-КАРТОЧКИ =====
function init3DCards() {
    document.querySelectorAll('.glass').forEach(card => {
        card.addEventListener('mousemove', function(e) {
            var rect = this.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;
            var cx = rect.width / 2;
            var cy = rect.height / 2;
            var dx = (x - cx) / cx;
            var dy = (y - cy) / cy;
            var rotateY = dx * 8;
            var rotateX = -dy * 8;
            this.style.transform =
                'perspective(1000px) ' +
                'rotateX(' + rotateX + 'deg) ' +
                'rotateY(' + rotateY + 'deg) ' +
                'translateY(-4px) scale(1.01)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform =
                'perspective(1000px) rotateX(0) rotateY(0)';
        });
    });
}

// ===== TOAST =====
function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    var icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = '<span style="font-size:20px">' +
                      (icons[type] || 'ℹ️') +
                      '</span><span>' + message + '</span>';
    container.appendChild(toast);
    setTimeout(function() {
        toast.classList.add('hide');
        setTimeout(function() { toast.remove(); }, 400);
    }, 4000);
}

// ===== КОНФЕТТИ =====
function launchConfetti() {
    var colors = ['#5a9fff', '#a78bfa', '#6366f1', '#ff00ff',
                  '#00ffff', '#ff6b6b', '#ffa94d', '#4ade80'];
    for (var i = 0; i < 60; i++) {
        (function(i) {
            setTimeout(function() {
                var c = document.createElement('div');
                c.className = 'confetti';
                c.style.left = Math.random() * 100 + 'vw';
                c.style.top = '-10px';
                c.style.background = colors[Math.floor(Math.random() * colors.length)];
                c.style.width = (Math.random() * 8 + 6) + 'px';
                c.style.height = (Math.random() * 8 + 6) + 'px';
                c.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
                c.style.animationDelay = (Math.random() * 0.5) + 's';
                c.style.animationDuration = (2 + Math.random() * 1.5) + 's';
                document.body.appendChild(c);
                setTimeout(function() { c.remove(); }, 4000);
            }, i * 20);
        })(i);
    }
}

// ===== СЧЁТЧИКИ =====
function animateCounter(el, target, duration) {
    duration = duration || 1000;
    var startTime = null;
    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target).toLocaleString('ru-RU');
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target.toLocaleString('ru-RU');
    }
    requestAnimationFrame(step);
}

function initCounters() {
    document.querySelectorAll('.stat-value').forEach(el => {
        var text = el.textContent.trim();
        var num = parseInt(text.replace(/[^0-9]/g, ''));
        if (!isNaN(num) && num > 0 && text.match(/^[0-9]+$/)) {
            el.textContent = '0';
            setTimeout(function() { animateCounter(el, num, 1500); }, 300);
        }
    });
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    init3DCards();
    initCounters();

    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            setTheme(this.dataset.theme);
            showToast('Тема: ' + this.title, 'info');
        });
    });

    if (window.location.search.indexOf('created=1') !== -1) {
        setTimeout(launchConfetti, 300);
        setTimeout(function() { showToast('Страница создана!', 'success'); }, 200);
    }
});
"""


def get_theme_switcher_html(current_theme="beach"):
    btns = ""
    for key, t in THEMES.items():
        active = " active" if key == current_theme else ""
        btns += (f'<button class="theme-btn{active}" data-theme="{key}" '
                 f'title="{t["name"]}" type="button"></button>')
    return f'<div class="theme-switcher">{btns}</div>'


def get_toast_container():
    return '<div class="toast-container" id="toast-container"></div>'


def get_load_chart_html():
    return """
<div class="load-chart">
    <div class="chart-label">Нагрузка (запросов/сек)</div>
    <svg id="load-chart-svg" viewBox="0 0 600 100" preserveAspectRatio="none"></svg>
</div>
"""


def get_themes_js_data():
    return "var THEMES_DATA = " + json.dumps(THEMES, ensure_ascii=False) + ";"