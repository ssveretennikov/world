#!/usr/bin/env python3
"""Обложка главной для пересылки ссылок: og.jpg (1200x630) — карта мира с подсвеченными посещёнными странами и названием серии.

  python tools/og.py

Страны и дом берутся из build.py (D, HOME, SERIES_TITLE), контуры — из data/map.json. Цвета — как на сайте («Небо»):
посещённые — синие, остальные — светло-серые, дом (Россия) — серый. Шрифты — из fonts/ (Unbounded: заголовок, Golos Text: подпись);
кириллица и латиница лежат в разных файлах, поэтому текст рисуется по символам с выбором файла.
Страницы поездок (<slug>/og.jpg) пока не делаются: у «Мира» их нет (нужны кадры постов).
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build as B
from favicon import polygons

W, H, S = 1200, 630, 2           # S — во сколько раз рисуем крупнее, потом уменьшаем (гладкие края)
BG = (237, 244, 255); LAND = (203, 211, 224); VISITED = (34, 100, 214); HOMEC = (150, 156, 165)
INK = (18, 74, 158); SOFT = (89, 96, 105)

class Face:
    """Шрифт из двух файлов (кириллица + латиница): символ берётся из того, где он есть."""
    def __init__(self, base, size):
        self.cyr = ImageFont.truetype(os.path.join(ROOT, 'fonts', base + '-cyrillic.woff2'), size)
        self.lat = ImageFont.truetype(os.path.join(ROOT, 'fonts', base + '-latin.woff2'), size)
    def pick(self, ch):
        return self.cyr if ('\u0400' <= ch <= '\u04ff' or ch == '\u2116') else self.lat
    def draw(self, d, xy, text, fill):
        x, y = xy
        for ch in text:
            f = self.pick(ch); d.text((x, y), ch, font=f, fill=fill, anchor='ls'); x += f.getlength(ch)
        return x

def main():
    mp = json.load(open(os.path.join(ROOT, 'data', 'map.json'), encoding='utf-8'))
    visited = {c for _, _, regs in B.D for c, _, _, mark, _ in regs if mark != 'n'}
    mw = 1040 * S; k = mw / mp['w']; ox = (W * S - mw) / 2; oy = 36 * S
    im = Image.new('RGB', (W * S, H * S), BG); d = ImageDraw.Draw(im)
    for r in mp['regions']:                       # порядок как в map.json: крупные снизу, мелкие сверху
        col = HOMEC if r['code'] == B.HOME else VISITED if r['code'] in visited else LAND
        for ring in polygons(r['d']):
            d.polygon([(ox + x * k, oy + y * k) for x, y in ring], fill=col)
    for r in mp['regions']:                       # у маленьких посещённых стран — кружок, иначе их не видно
        if r['tiny'] and r['code'] in visited:
            x, y = ox + r['cx'] * k, oy + r['cy'] * k; rad = 5 * S
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=VISITED, outline=BG, width=S)
    # название серии и подпись под картой
    Face('unbounded', 54 * S).draw(d, (60 * S, 568 * S), B.SERIES_TITLE, INK)
    Face('golos-text', 26 * S).draw(d, (62 * S, 604 * S), 'Сергей Веретенников · отчёты о заграничных поездках', SOFT)
    im = im.resize((W, H), Image.LANCZOS)
    out = os.path.join(ROOT, 'og.jpg')
    im.save(out, 'JPEG', quality=86, optimize=True)
    print('готово: og.jpg', os.path.getsize(out) // 1024, 'КБ')

if __name__ == '__main__':
    main()
