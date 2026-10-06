#!/usr/bin/env python3
"""Черновик файла поездок data/trips.json по датам из паспортов страниц (строка «Когда» в src/<slug>.html).
ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.

  python tools/trips.py           # пишет data/trips.json и печатает поездки для проверки автором

Поездка — цепочка страниц, у которых даты идут подряд или с разрывом не больше трёх дней.
По этому файлу сборка расставляет «раньше / дальше по маршруту» внизу страниц (этап 1 плана по дизайну).
Страница может входить в несколько поездок (например, Краснодар 2022 и 2024): у неё несколько отрезков дат.
Файл — черновик: порядок внутри одного дня и спорные связки автор правит руками, после чего скрипт
не перезаписывает записи с пометкой "checked": true.
"""
import json, os, re, sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build

MONTHS = {m: i + 1 for i, m in enumerate(['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                                           'сентября', 'октября', 'ноября', 'декабря'])}
MONTHS_SHORT = {k[:3]: v for k, v in MONTHS.items()}


def spans(text):
    """Все отрезки дат из строки «Когда»: «7–12 августа 2025», «30 июля — 4 августа 2025», «12 марта 2022 и 16 июля 2023»."""
    text = text.replace(' ', ' ').replace('\xa0', ' ')
    # «6–7 марта и 19–20 августа 2022», «24 апреля, 29 мая и 6 июня 2022»: год стоит один раз, в конце —
    # дописываем его к каждой дате без года, иначе такие даты терялись (поймано автором 06.10.2026)
    parts = re.split(r'\s*(?:,|\bи\b|;)\s*', text)
    years = [re.search(r'(\d{4})', x) for x in parts]
    for i in range(len(parts) - 1, -1, -1):
        if not years[i]:
            nxt = next((y.group(1) for y in years[i + 1:] if y), None)
            if nxt: parts[i] = parts[i].rstrip() + ' ' + nxt
    text = ' и '.join(parts)
    out = []
    # «30 июля — 4 августа 2025» / «28 декабря 2023 — 2 января 2024»
    for m in re.finditer(r'(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?\s*[—–-]\s*(\d{1,2})\s+([а-я]+)\s+(\d{4})', text):
        d1, m1, y1, d2, m2, y2 = m.groups()
        y1 = int(y1 or y2); a = date(y1, MONTHS[m1], int(d1)); b = date(int(y2), MONTHS[m2], int(d2))
        out.append((a, b)); text = text.replace(m.group(0), ' ')
    # «7–12 августа 2025»
    for m in re.finditer(r'(\d{1,2})\s*[—–-]\s*(\d{1,2})\s+([а-я]+)\s+(\d{4})', text):
        d1, d2, mo, y = m.groups(); out.append((date(int(y), MONTHS[mo], int(d1)), date(int(y), MONTHS[mo], int(d2))))
        text = text.replace(m.group(0), ' ')
    # одиночные «12 марта 2022»
    for m in re.finditer(r'(\d{1,2})\s+([а-я]+)\s+(\d{4})', text):
        d, mo, y = m.groups()
        if mo in MONTHS: dd = date(int(y), MONTHS[mo], int(d)); out.append((dd, dd))
    return sorted(set(out))


def page_spans(slug):
    src = (ROOT / 'src' / f'{slug}.html').read_text(encoding='utf-8')
    m = re.search(r'<dt>Когда</dt><dd>(.*?)</dd>', src, re.S)
    return spans(re.sub(r'<[^>]+>', '', m.group(1))) if m else []


def main():
    items = []
    for pg in build.PAGES:
        # Москва и Подмосковье — дом, а не поездки; страницы-подборки за месяцы (77-moscow-3, 78-spb-month)
        # склеили бы между собой чужие поездки, поэтому отрезки длиннее 20 дней в цепочки не идут
        if pg['slug'].startswith(('77-', '50-')): continue
        for a, b in page_spans(pg['slug']):
            if (b - a).days <= 20: items.append((a, b, pg['slug'], pg['title']))
    items.sort()
    trips = []
    for a, b, slug, title in items:
        if trips and a - trips[-1]['end'] <= timedelta(days=3):
            t = trips[-1]; t['end'] = max(t['end'], b); t['legs'].append((a, b, slug, title))
        else:
            trips.append({'start': a, 'end': b, 'legs': [(a, b, slug, title)]})
    old = {}
    out_path = ROOT / 'data' / 'trips.json'
    if out_path.exists():
        for t in json.load(open(out_path, encoding='utf-8')):
            if t.get('checked'): old[t['id']] = t
    result = []
    for t in trips:
        tid = t['start'].isoformat()
        if tid in old: result.append(old[tid]); continue
        legs = sorted(t['legs'])
        result.append({'id': tid, 'start': t['start'].isoformat(), 'end': t['end'].isoformat(), 'checked': False,
                       'regions': [l[2] for l in legs]})
    json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    multi = [t for t in result if len(t['regions']) > 1]
    print(f'поездок {len(result)}, из них с несколькими страницами {len(multi)}; страниц без дат: '
          f'{[pg["slug"] for pg in build.PAGES if not page_spans(pg["slug"])]}')
    for t in result:
        print(f"{t['start']} — {t['end']}: {' → '.join(t['regions'])}" + ('  ✓' if t.get('checked') else ''))


if __name__ == '__main__':
    main()
