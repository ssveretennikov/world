#!/usr/bin/env python3
"""Значок сайта: контуры всех материков одним цветом (без границ стран) из data/map.json.

  python tools/favicon.py   ->  favicon.png (64x64), apple-touch-icon.png (180x180)

Карта мира — в проекции Робинсона (tools/map.py), поэтому значок получается шире, чем выше: контуры
по центру квадрата. Все страны рисуются одной маской, швы между ними закрываются, остаётся силуэт суши.
Цвет и фон — как у значка «России». Нужен только Pillow.
"""
import json, os, re
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLOR = (184, 117, 18)
BACKGROUND = (255, 252, 245, 255)   # фон apple-touch-icon: у iOS прозрачность превращается в чёрное

def polygons(d):
    """Путь из map.json (M x y, затем относительные l dx dy, z) -> список контуров."""
    out = []
    for sub in d.split('z'):
        if not sub: continue
        m = re.match(r'M(-?[\d.]+) (-?[\d.]+)', sub)
        x, y = float(m.group(1)), float(m.group(2)); pts = [(x, y)]
        for dx, dy in re.findall(r'l(-?[\d.]+) (-?[\d.]+)', sub):
            x += float(dx); y += float(dy); pts.append((x, y))
        out.append(pts)
    return out

def mask(mp, width, pad, scale=4):
    """Маска суши: карта вписывается по ширине (width - 2·pad), по вертикали — по центру."""
    side = width * scale
    k = (width - 2 * pad) * scale / mp['w']
    oy = (side - mp['h'] * k) / 2
    m = Image.new('L', (side, side), 0); d = ImageDraw.Draw(m)
    for r in mp['regions']:
        for ring in polygons(r['d']):
            d.polygon([(pad * scale + x * k, oy + y * k) for x, y in ring], fill=255)
    return m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))   # закрывает щели между странами

def icon(m, side, background=None):
    a = m.resize((side, side), Image.LANCZOS)
    im = Image.new('RGBA', (side, side), background or (0, 0, 0, 0))
    im.paste(Image.new('RGBA', (side, side), COLOR + (255,)), mask=a)
    return im

def main():
    mp = json.load(open(os.path.join(ROOT, 'data', 'map.json'), encoding='utf-8'))
    icon(mask(mp, 64, 2), 64).save(os.path.join(ROOT, 'favicon.png'), optimize=True)
    icon(mask(mp, 180, 14), 180, BACKGROUND).convert('RGB').save(os.path.join(ROOT, 'apple-touch-icon.png'), optimize=True)
    print('готово: favicon.png, apple-touch-icon.png')

if __name__ == '__main__':
    main()
