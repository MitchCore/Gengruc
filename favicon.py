# ============================================================
# Gengruc Favicon — генератор favicon.ico из SVG-логотипа
# Файл 3 (подключается из gengruc.py)
# ============================================================

import os
import struct


# SVG-логотип — буква G в градиентном квадрате
SVG_LOGO = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5a9fff"/>
      <stop offset="50%" stop-color="#a78bfa"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" ry="14" fill="url(#g)"/>
  <text x="32" y="46" font-family="Arial,Helvetica,sans-serif"
        font-size="42" font-weight="bold" fill="#ffffff"
        text-anchor="middle">G</text>
</svg>'''


# Готовые PNG-иконки (base64) для разных размеров
# Создаются заранее — встроены в код, чтобы не требовать Pillow
FAVICON_SIZES = [16, 32, 48, 64]


def _make_png_g(size, bg="#5a9fff", fg="#ffffff"):
    """
    Генерирует PNG вручную (без библиотек).
    Простая иконка: квадрат с буквой G (заливка белым по синему).
    """
    # Для простоты — используем 1-битную маску, буква G рисуется пиксельно
    # Это очень упрощённый рендер. Для 16x16 хватит.
    width = height = size

    # Матрица буквы G (в долях от размера)
    # 5 = закрашенный пиксель, 0 = пусто
    G_MASK_16 = [
        [0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,1,1,0,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,1,1,1,1,0,0,0,0,0,0],
        [1,1,0,0,0,0,1,1,1,1,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0],
        [0,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    ]

    # Масштабируем маску под нужный размер
    scale = size / 16.0
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            mx = int(x / scale)
            my = int(y / scale)
            if 0 <= mx < 16 and 0 <= my < 16:
                on = G_MASK_16[my][mx]
            else:
                on = 0
            row.append((255, 255, 255, 255) if on else (90, 159, 255, 255))
        pixels.append(row)

    return _encode_png(width, height, pixels)


def _encode_png(width, height, pixels):
    """Кодирует пиксели в PNG (без zlib через ручной deflate)."""
    import zlib

    raw = b""
    for row in pixels:
        raw += b"\x00"  # filter type 0
        for (r, g, b, a) in row:
            raw += bytes([r, g, b, a])

    compressed = zlib.compress(raw, 9)

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xffffffff
        return (struct.pack(">I", len(data)) + c +
                struct.pack(">I", crc))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                                       8, 6, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    return png


def _png_to_ico_bytes(png_data, size):
    """Оборачивает PNG в ICO-структуру."""
    # ICO header
    header = struct.pack("<HHH", 0, 1, 1)
    # Directory entry
    width_byte = 0 if size >= 256 else size
    height_byte = 0 if size >= 256 else size
    entry = struct.pack("<BBBBHHII",
                        width_byte, height_byte,
                        0, 0, 1, 32,
                        len(png_data),
                        6 + 16)  # offset
    return header + entry + png_data


def make_ico_from_pngs(pngs):
    """Собирает многоразмерный .ico из списка (size, png_data)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    entries = b""
    offset = 6 + 16 * len(pngs)
    for size, png in pngs:
        width_byte = 0 if size >= 256 else size
        height_byte = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII",
                               width_byte, height_byte,
                               0, 0, 1, 32,
                               len(png), offset)
        offset += len(png)
    body = b"".join(png for _, png in pngs)
    return header + entries + body


def ensure_favicon(favicon_path):
    """
    Создаёт favicon.ico, если его нет.
    Использует встроенный PNG-рендер (без Pillow).
    """
    if os.path.exists(favicon_path):
        return True

    try:
        pngs = []
        for size in [16, 32, 48, 64]:
            png = _make_png_g(size)
            pngs.append((size, png))

        ico = make_ico_from_pngs(pngs)
        with open(favicon_path, "wb") as f:
            f.write(ico)
        return True
    except Exception as e:
        print(f"[Favicon] Ошибка генерации: {e}")
        return False


def get_svg():
    """Возвращает SVG-логотип (для встраивания в HTML)."""
    return SVG_LOGO


# ============================================================
# Ручной запуск: python favicon.py
# ============================================================
if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "favicon.ico")
    if ensure_favicon(out):
        print(f"OK: {out}")
        size = os.path.getsize(out)
        print(f"Размер: {size} байт")
    else:
        print("ERR: не удалось создать favicon.ico")