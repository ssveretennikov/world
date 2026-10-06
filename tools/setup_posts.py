#!/usr/bin/env python3
"""Заводит папки постов по tools/posts.tsv и запускает инвентаризацию. Модель не нужна.

  python tools/setup_posts.py              # source.txt для всех постов (существующие не трогает)
  python tools/setup_posts.py --inventory  # + inventory там, где нет timeline.md; посты «=slug» получают копию
                                           #   index.tsv, vindex.tsv, timeline.md и work/ родителя (одни и те же файлы
                                           #   архива — одни и те же номера P001…, как у страниц Москвы в «России»)

Пост с источником «=slug» делит архив поездки с родителем: отбор по датам/подпапкам делает автор текста по досье.
Пост с подпапками (Япония) получает в source.txt по строке на подпапку — у него своя нумерация.
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'tools' / 'posts.tsv'


def posts():
    out = []
    for line in TSV.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'): continue
        c = (line.split('\t') + [''] * 6)[:6]
        out.append(dict(slug=c[0], iso=c[1], title=c[2], src=c[3], subs=[s.strip() for s in c[4].split('|') if s.strip()], days=c[5]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--only', nargs='*', default=None)
    a = ap.parse_args()
    ps = posts()
    for p in ps:
        if a.only and p['slug'] not in a.only: continue
        d = ROOT / 'trips' / p['slug']; d.mkdir(parents=True, exist_ok=True)
        f = d / 'source.txt'
        # «=slug» без подпапок — общий архив с родителем, source.txt скопируется ниже;
        # «=slug» с подпапками (Япония) — свои подпапки в корне родителя, своя инвентаризация
        if p['src'].startswith('=') and not p['subs']: continue
        if not f.exists():
            src = p['src']
            if src.startswith('='): src = next(q['src'] for q in ps if q['slug'] == src[1:])
            roots = [s.strip() for s in src.split('|')]
            lines = [str(Path(r) / s) for r in roots for s in p['subs']] if p['subs'] else roots
            f.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print('source.txt:', p['slug'], len(lines), 'строк')
    if not a.inventory: return
    for p in ps:
        if a.only and p['slug'] not in a.only: continue
        if p['src'].startswith('=') and not p['subs']: continue
        d = ROOT / 'trips' / p['slug']
        if (d / 'timeline.md').exists(): print('есть:', p['slug']); continue
        print('inventory:', p['slug'], flush=True)
        r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'media.py'), 'inventory', p['slug']], cwd=ROOT)
        if r.returncode: print('ОШИБКА inventory', p['slug']); continue
    for p in ps:
        if not p['src'].startswith('=') or p['subs']: continue
        if a.only and p['slug'] not in a.only: continue
        parent = ROOT / 'trips' / p['src'][1:]; d = ROOT / 'trips' / p['slug']
        if (d / 'timeline.md').exists(): continue
        if not (parent / 'timeline.md').exists(): print('нет родителя для', p['slug']); continue
        for n in ('source.txt', 'index.tsv', 'vindex.tsv', 'timeline.md'):
            shutil.copy(parent / n, d / n)
        if (parent / 'work').exists() and not (d / 'work').exists():
            shutil.copytree(parent / 'work', d / 'work')
        print('копия от', p['src'][1:], '→', p['slug'])


if __name__ == '__main__':
    main()
