#!/usr/bin/env python3
"""Миниатюры для главной (WebP): <slug>/thumb.webp 360x270 для списков и <slug>/card.webp 800x600
ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.
для карточек ленты «Любимые» (регионы из FAV в build.py).

  python tools/thumbs.py            # недостающие и устаревшие
  python tools/thumbs.py --force    # все заново
Главный кадр весит 64–709 КБ — на главную с её девятью десятками регионов он не годится.
Кадр тот же, что у обложки (tools/og.py): заданный в PAGES как og, иначе главный; кадрирование то же.
Карточка ленты на экране около 19 rem (300 px) шириной: 800 px хватает и для плотных экранов, весит 50–120 КБ.
"""
import os, sys, re
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build as B

W, H = 360, 270          # вдвое больше места на экране: на телефонах с плотным экраном не мылится
CW, CH = 800, 600        # карточка ленты «Любимые»
QUALITY = 72

def hero_of(pg):
    src = open(os.path.join(ROOT, 'src', pg['slug'] + '.html'), encoding='utf-8').read()
    return pg.get('og') or re.search(r'<figure class="hero-ph"[^>]*>.*?<img src="([^"]+)"', src, re.S).group(1)

def thumb(photo, out, w=W, h=H):
    im = Image.open(photo).convert('RGB')
    sc = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    left = (im.width - w) // 2
    top = max(0, round((im.height - h) * 0.42))     # как у обложки: чуть выше середины, где обычно главное
    im.crop((left, top, left + w, top + h)).save(out, 'WEBP', quality=QUALITY, method=6)

def main():
    force = '--force' in sys.argv
    made = {}
    for pg in B.PAGES:
        photo = os.path.join(ROOT, pg['slug'], hero_of(pg))
        wanted = [('thumb.webp', W, H)] + ([('card.webp', CW, CH)] if pg['slug'] in B.FAV else [])
        for name, w, h in wanted:
            out = os.path.join(ROOT, pg['slug'], name)
            if not force and os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(photo):
                continue
            thumb(photo, out, w, h); made[name] = made.get(name, 0) + 1
    sizes = [os.path.getsize(os.path.join(ROOT, pg['slug'], 'thumb.webp')) for pg in B.PAGES]
    print(f'thumb: сделано {made.get("thumb.webp", 0)}, всего {len(sizes)}, вес {sum(sizes) // 1024} КБ, самая тяжёлая {max(sizes) // 1024} КБ')
    cards = [os.path.getsize(os.path.join(ROOT, s, 'card.webp')) for s in B.FAV]
    print(f'card: сделано {made.get("card.webp", 0)}, всего {len(cards)}, вес {sum(cards) // 1024} КБ, самая тяжёлая {max(cards) // 1024} КБ')

if __name__ == '__main__':
    main()
