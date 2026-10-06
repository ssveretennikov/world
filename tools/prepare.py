#!/usr/bin/env python3
"""Пакетная подготовка архивов: создаёт trips/<slug>/source.txt по tools/sources.tsv
ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.
и при --inventory прогоняет tools/media.py inventory по всем регионам. Модель не нужна.

  python tools/prepare.py                 # только source.txt, существующие не трогает
  python tools/prepare.py --inventory     # + inventory для регионов, где ещё нет timeline.md
  python tools/prepare.py --only 23 78    # ограничить кодами регионов
  python tools/prepare.py --force         # перезаписать source.txt
  python tools/prepare.py --inventory --redo   # inventory заново и там, где timeline.md уже есть (миниатюры не пересчитываются)
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'tools' / 'sources.tsv'


def rows():
    for line in TSV.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'): continue
        code, slug, folders, *note = line.split('\t')
        yield code, slug, [f.strip() for f in folders.split('|') if f.strip()], (note[0] if note else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inventory', action='store_true'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--redo', action='store_true'); ap.add_argument('--only', nargs='*', default=None); ap.add_argument('--jobs', type=int, default=3)
    a = ap.parse_args()
    todo, missing = [], []
    for code, slug, folders, note in rows():
        if a.only and code not in a.only: continue
        d = ROOT / 'trips' / slug; d.mkdir(parents=True, exist_ok=True)
        f = d / 'source.txt'
        if a.force or not f.exists():
            f.write_text(('# ' + note + '\n' if note else '') + '\n'.join(folders) + '\n', encoding='utf-8')
        absent = [p for p in folders if not Path(p).is_dir()]
        if absent: missing.append((slug, absent)); continue
        if a.inventory and (a.redo or not (d / 'timeline.md').exists()): todo.append(slug)
    print(f'source.txt готовы: {len(list(rows()))} регионов в trips/')
    for slug, absent in missing: print(f'  {slug}: папка не найдена: {"; ".join(absent)}')
    for i, slug in enumerate(todo, 1):
        print(f'[{i}/{len(todo)}] inventory {slug}'); sys.stdout.flush()
        r = subprocess.run([sys.executable, str(ROOT / 'tools' / 'media.py'), 'inventory', slug, '--jobs', str(a.jobs)])
        if r.returncode: print(f'  ошибка в {slug}, код {r.returncode}')


if __name__ == '__main__': main()
