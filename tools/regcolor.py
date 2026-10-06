#!/usr/bin/env python3
"""Цвет региона по главному кадру (решение автора 06.10.2026).
ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.

  python tools/regcolor.py            # все страницы из PAGES -> data/colors.json
  python tools/regcolor.py 39-kaliningrad 49-magadan   # только эти, остальные записи сохраняются

Как выбирается цвет: берётся нижняя часть главного кадра (без полосы неба сверху), из неё — самый насыщенный
и заметный по площади оттенок; небесно-голубые оттенки чуть штрафуются, иначе почти все регионы вышли бы синими.
Светлота подгоняется под белый текст (контраст не ниже 4,5:1) — это цвет для светлой темы; для тёмной темы
делается светлый вариант того же тона под тёмный текст (контраст не ниже 7:1).
Если в кадре цвета нет (серый, как у Камчатки), запись не пишется и страница остаётся с охрой по умолчанию.
Сборка (build.py) берёт пары из data/colors.json, если у страницы в PAGES не задан свой color.
"""
import colorsys, json, os, sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'colors.json'
INK_DARK = (20, 16, 10)          # текст на цветной плашке в тёмной теме (#14100A)


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hx(rgb):
    return '#%02X%02X%02X' % tuple(int(round(c)) for c in rgb)


def pick(path):
    im = Image.open(path).convert('RGB'); im.thumbnail((200, 200))
    w, h = im.size
    low = im.crop((0, int(h * 0.38), w, h))            # нижние 62% кадра: земля, вода, люди
    q = low.quantize(colors=14, method=Image.Quantize.MEDIANCUT); pal = q.getpalette()[:42]
    counts = sorted(q.getcolors(), reverse=True); total = sum(n for n, _ in counts)
    cands = []
    for n, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]; hh, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255); share = n / total
        if share < 0.025 or s < 0.12: continue
        sky = 190 <= hh * 360 <= 235
        score = (s ** 1.2) * (share ** 0.4) * (1 - abs(l - 0.5) * 0.8) * (0.55 if sky else 1.0)
        cands.append((score, hh, l, s, share))
    if not cands: return None
    _, hh, l, s, share = max(cands)
    s = max(min(s * 1.2, 0.78), 0.42); L = max(min(l, 0.46), 0.12)
    light = [c * 255 for c in colorsys.hls_to_rgb(hh, L, s)]
    while L > 0.12 and contrast(light, (255, 255, 255)) < 4.6:
        L -= 0.01; light = [c * 255 for c in colorsys.hls_to_rgb(hh, L, s)]
    L2 = 0.62
    dark = [c * 255 for c in colorsys.hls_to_rgb(hh, L2, min(s, 0.7))]
    while L2 < 0.85 and contrast(dark, INK_DARK) < 7:
        L2 += 0.01; dark = [c * 255 for c in colorsys.hls_to_rgb(hh, L2, min(s, 0.7))]
    return {'light': hx(light), 'dark': hx(dark), 'hue': round(hh * 360),
            'contrast_light': round(contrast(light, (255, 255, 255)), 2), 'contrast_dark': round(contrast(dark, INK_DARK), 2)}


def main():
    sys.path.insert(0, str(ROOT))
    import build
    slugs = sys.argv[1:] or [pg['slug'] for pg in build.PAGES]
    colors = json.load(open(OUT, encoding='utf-8')) if OUT.exists() else {}
    for s in slugs:
        hero = ROOT / s / 'media' / 'hero.webp'
        if not hero.exists(): print(f'{s}: нет media/hero.webp'); continue
        c = pick(hero)
        if c: colors[s] = c; print(f'{s}: {c["light"]} / {c["dark"]} (оттенок {c["hue"]}°)')
        else:
            colors.pop(s, None); print(f'{s}: в кадре нет цвета — остаётся охра')
    OUT.parent.mkdir(exist_ok=True)
    json.dump(dict(sorted(colors.items())), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'записано {len(colors)} регионов в {OUT}')


if __name__ == '__main__':
    main()
