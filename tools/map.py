#!/usr/bin/env python3
"""Карта мира для главной: контуры стран из GeoJSON Natural Earth -> data/map.json.

  python tools/map.py путь/к/ne_110m_admin_0_countries.geojson

Файл GeoJSON автор ещё не разрешил скачивать (06.10.2026): пока его нет, build.py собирает главную без карты.
Когда файл появится — один запуск этого скрипта, и карта на главной заработает сама.

Код страны — поле ISO_A2; у части стран Natural Earth пишет там «-99» (Франция, Норвегия), тогда берётся ISO_A2_EH.
Название — NAME_RU, если есть, иначе NAME. Проекция Робинсона (таблица Робинсона с линейной интерполяцией):
мир на ней выглядит привычно, без раздутых полярных областей. Контуры упрощаются (Дуглас — Пекер), координаты
округляются до десятых долей пикселя в сетке 1000 по ширине. Нужен numpy.

Дата первого визита — из data/trips.json: самая ранняя поездка, в которой есть страница этой страны
(slug начинается с её кода строчными: by-2023-minsk -> BY). Нет поездки — null («ещё не был»).
Формат выхода тот же, что в «России»: w, h, regions[] {code, name, d, date, tiny, cx, cy}.
"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = 1000.0          # ширина карты в пикселях сетки
TOL = 0.5           # допуск упрощения, px
MIN_AREA = 0.3      # мелкие острова (px^2) отбрасываем, кроме главного контура страны
TINY = 220          # страна меньше этого (px^2 на карте 1000 px) — «маленькая»: Беларусь (204), Куба (88) да, Вьетнам (252), Япония (343), Египет (783) нет.
                    # build.py рисует у посещённой маленькой страны кружок-метку в центре (cx, cy) и обводку

# Таблица Робинсона: широта через 5°, множители длины параллели и расстояния от экватора
_RX = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427, 0.9216, 0.8962,
       0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732, 0.6213, 0.5722, 0.5322]
_RY = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340, 0.4958, 0.5571,
       0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936, 0.9394, 0.9761, 1.0000]

def robinson(lon, lat):
    a = min(abs(lat), 90.0) / 5.0
    i = min(int(a), 17); t = a - i
    px = _RX[i] + (_RX[i + 1] - _RX[i]) * t
    py = _RY[i] + (_RY[i + 1] - _RY[i]) * t
    # y вниз, как в SVG
    return 0.8487 * px * np.radians(lon), -1.3523 * py * (1 if lat >= 0 else -1)

def rings(geom):
    if geom['type'] == 'Polygon': return [geom['coordinates'][0]]
    if geom['type'] == 'MultiPolygon': return [p[0] for p in geom['coordinates']]
    return []

def dp(pts, tol):
    """Дуглас — Пекер без рекурсии; pts — массив (n, 2)."""
    n = len(pts)
    if n < 3: return pts
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1: continue
        p, q = pts[a], pts[b]
        seg = pts[a + 1:b]
        d = q - p; L = np.hypot(*d)
        dist = np.hypot(*(seg - p).T) if L == 0 else np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / L
        i = int(np.argmax(dist))
        if dist[i] > tol:
            k = a + 1 + i; keep[k] = True
            stack += [(a, k), (k, b)]
    return pts[keep]

def area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

def path(rs):
    out = []
    for r in rs:
        r = np.round(r, 1)
        s = f'M{r[0][0]:g} {r[0][1]:g}'
        prev = r[0]
        for p in r[1:]:
            dx, dy = round(p[0] - prev[0], 1), round(p[1] - prev[1], 1)
            if dx or dy: s += f'l{dx:g} {dy:g}'
            prev = p
        out.append(s + 'z')
    return ''.join(out)

def first_dates():
    """ISO -> дата первой поездки из data/trips.json (по slug страниц)."""
    f = os.path.join(ROOT, 'data', 'trips.json')
    if not os.path.exists(f): return {}
    out = {}
    for t in json.load(open(f, encoding='utf-8')):
        for s in t.get('regions') or []:
            c = s.split('-')[0].upper()
            if c not in out or t['start'] < out[c]: out[c] = t['start']
    return out

def iso_of(p):
    c = p.get('ISO_A2') or ''
    if c in ('', '-99'): c = p.get('ISO_A2_EH') or ''
    return c.upper() if len(c) == 2 and c.isalpha() else None

def main():
    g = json.load(open(sys.argv[1], encoding='utf-8'))
    dates = first_dates()
    raw = []
    for f in g['features']:
        p = f['properties']; code = iso_of(p)
        if not code or code == 'AQ': continue          # Антарктида только съедает высоту карты
        rs = [np.array([robinson(x, y) for x, y in r]) for r in rings(f['geometry'])]
        if rs: raw.append((code, p.get('NAME_RU') or p.get('NAME') or code, rs))
    allp = np.vstack([r for _, _, rs in raw for r in rs])
    x0, y0 = allp.min(0); x1, y1 = allp.max(0)
    k = W / (x1 - x0); H = (y1 - y0) * k
    items = []
    for code, name, rs in raw:
        rs = [np.column_stack(((r[:, 0] - x0) * k, (r[:, 1] - y0) * k)) for r in rs]
        areas = [area(r) for r in rs]
        big = max(areas)
        rs = [dp(r, TOL) for r, a in zip(rs, areas) if a >= MIN_AREA or a == big]
        rs = [r for r in rs if len(r) >= 3 and (area(r) >= MIN_AREA or area(r) == max(map(area, rs)))]
        if not rs: continue
        main_r = max(rs, key=area)
        items.append(dict(code=code, name=name, date=dates.get(code), area=float(sum(area(r) for r in rs)),
                          cx=round(float(main_r[:, 0].mean()), 1), cy=round(float(main_r[:, 1].mean()), 1),
                          d=path(rs)))
    items.sort(key=lambda i: -i['area'])             # крупные снизу, мелкие сверху
    for i in items:
        i['tiny'] = int(i['area'] < TINY)
        del i['area']
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    out = os.path.join(ROOT, 'data', 'map.json')
    json.dump(dict(w=int(W), h=round(H), regions=items), open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('готово: data/map.json', os.path.getsize(out) // 1024, 'КБ,', len(items), 'стран, карта', int(W), 'x', round(H))

if __name__ == '__main__':
    main()
