#!/usr/bin/env python3
"""Контуры городов и столицы регионов из OpenStreetMap (Nominatim) — для схемы точек съёмки (build.py).
ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.

  python tools/cities.py            # скачать недостающее (разовое обращение, разрешено автором 06.10.2026)
  python tools/cities.py --offline  # только пересобрать файлы из кэша, ни одного запроса

Для каждой страницы с меткой <!--daymap: …--> названные места и снимки с координатами собираются в кучки
радиусом ~15 км; для центра кучки — обратное геокодирование (zoom=10) -> город; затем контур города
(lookup, polygon_geojson=1). Контур упрощается до ≤300 точек и ложится в data/cities/<тип><id>.geojson,
список файлов страницы — в data/cities/index.json. Столицы регионов (из списка D в build.py) — поиском
«<столица>, <регион>», центр контура -> data/capitals.json (код -> [широта, долгота, название]).

Правила Nominatim: свой User-Agent, не чаще запроса в секунду, всё кэшируется на диске
(trips/_osm-cache, вне git) — повторный запуск ничего не качает. Предел — MAX_REQ запросов за запуск.
"""
import hashlib, json, math, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build

UA = 'world-site/1.0 (ssveretennikov.github.io/world)'
BASE = 'https://nominatim.openstreetmap.org/'
CACHE = os.path.join(ROOT, 'trips', '_osm-cache')
OUT = os.path.join(ROOT, 'data', 'cities')
MAX_REQ = 300
RADIUS = 15        # км — кучка мест одного города
MAX_PTS = 300      # точек в упрощённом контуре
CITY_TYPES = ('city', 'town')   # село и район — не «город», для них остаётся схема региона
# Где в D вместо столицы стоит другое: у Подмосковья — Подольск (город поездки), у городов федерального
# значения — пояснение. Административный центр Московской области — Красногорск.
CAPITAL_FIX = {'50': 'Красногорск', '77': 'Москва', '78': 'Санкт-Петербург', '92': 'Севастополь', '20': 'Грозный'}

stats = dict(net=0, cache=0)
OFFLINE = '--offline' in sys.argv
_last = [0.0]

def get(path, **q):
    q.setdefault('format', 'jsonv2')
    url = BASE + path + '?' + urllib.parse.urlencode(sorted(q.items()))
    f = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + '.json')
    if os.path.exists(f):
        stats['cache'] += 1
        return json.load(open(f, encoding='utf-8'))
    if OFFLINE: return None
    if stats['net'] >= MAX_REQ: raise SystemExit(f'предел {MAX_REQ} запросов исчерпан')
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ru'})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    _last[0] = time.time(); stats['net'] += 1
    os.makedirs(CACHE, exist_ok=True)
    json.dump(data, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    return data

def dp(pts, tol):
    keep = [False] * len(pts); keep[0] = keep[-1] = True; st = [(0, len(pts) - 1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        (x1, y1), (x2, y2) = pts[a], pts[b]; L = math.hypot(x2 - x1, y2 - y1)
        best, k = -1, a
        for i in range(a + 1, b):
            x, y = pts[i]   # у замкнутого кольца концы совпадают — тогда расстояние до точки, а не до прямой
            d = abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / L if L > 1e-9 else math.hypot(x - x1, y - y1)
            if d > best: best, k = d, i
        if best > tol: keep[k] = True; st += [(a, k), (k, b)]
    return [p for p, f in zip(pts, keep) if f]

def simplify(ring):
    tol = 1e-5
    out = ring
    while len(out) > MAX_PTS: out = dp(ring, tol); tol *= 1.5
    return [[round(x, 5), round(y, 5)] for x, y in out]

def outer_ring(geom):
    if geom['type'] == 'Polygon': return geom['coordinates'][0]
    if geom['type'] == 'MultiPolygon':   # самый большой по площади (у Владивостока самый длинный — остров Русский)
        return max((p[0] for p in geom['coordinates']), key=lambda r: abs(centroid_area(r)))
    return None

def centroid_area(ring):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))

def centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    return (cy / (3 * a), cx / (3 * a)) if a else (sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring))

def pages():
    """slug -> (названные места, снимки с координатами) по меткам в src/*.html."""
    res = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, 'src'))):
        s = open(os.path.join(ROOT, 'src', fn), encoding='utf-8').read()
        m = re.search(r'<!--daymap:?(.*?)-->', s, re.S)
        if not m: continue
        slug = fn[:-5]
        labels = []
        for part in m.group(1).split(';'):
            mm = re.match(r'\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\s+(.+)', part)
            if mm: labels.append((float(mm[1]), float(mm[2])))
        rows, _ = build._gps_rows(slug)
        res[slug] = (labels, [(r['lat'], r['lon']) for r in rows])
    return res

def clusters(labels, shots):
    """Жадные кучки радиусом RADIUS: сначала названные места, потом снимки. Кучка без мест и с <20 снимками
    не спрашивается — это дорога между городами."""
    cl = []
    for kind, pts in (('l', labels), ('s', shots)):
        for la, lo in pts:
            for c in cl:
                if build._km(la, lo, c['la'], c['lo']) <= RADIUS:
                    c['n'] += 1; c['l'] += kind == 'l'
                    c['sla'] += la; c['slo'] += lo; break
            else:
                cl.append(dict(la=la, lo=lo, sla=la, slo=lo, n=1, l=int(kind == 'l')))
    return [(c['sla'] / c['n'], c['slo'] / c['n']) for c in cl if c['l'] or c['n'] >= 20]

def save_city(item, extra=None):
    ring = outer_ring(item.get('geojson') or {})
    if not ring: return None
    name = item.get('name') or item.get('display_name', '').split(',')[0]
    name = NAME_FIX.get(name, re.sub(r'^городской округ |^городское поселение ', '', name))
    fn = f"{item['osm_type'][0].upper()}{item['osm_id']}.geojson"
    feat = dict(type='Feature', properties=dict(name=name, osm=f"{item['osm_type']}/{item['osm_id']}",
                licence=item.get('licence', 'Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright')),
                geometry=dict(type='Polygon', coordinates=[simplify(ring)]))
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(type='FeatureCollection', features=[feat]), open(os.path.join(OUT, fn), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    return fn, name, ring

def is_city(r):
    """Город или посёлок городского типа; «городской округ X» и «X городское поселение» — тоже город, если
    контур не шире MAX_KM (бывают округа размером с район — это уже не силуэт города)."""
    t, nm = r.get('addresstype'), r.get('name', '')
    if t not in CITY_TYPES and not (nm.startswith('городской округ ') or 'городское поселение' in nm): return False
    b = [float(x) for x in r.get('boundingbox', [0, 0, 0, 0])]
    return build._km(b[0], b[2], b[1], b[3]) <= MAX_KM

MAX_KM = 80
# Поселения называются по-канцелярски — для подписи схемы берётся город (ручная правка, проверено по контуру)
NAME_FIX = {'Выборгское городское поселение': 'Выборг', 'Приозерское городское поселение': 'Приозерск',
            'Елизовское городское поселение': 'Елизово', 'Щебетовский поселковый совет': 'Коктебель',
            'Голубинское сельское поселение': 'Голубинка'}

def lookup(ids):
    """osm-id -> ответ с контуром; до 50 id в одном запросе."""
    got = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        for it in get('lookup', osm_ids=','.join(ids[i:i + 50]), polygon_geojson=1) or []:
            got[it['osm_type'][0].upper() + str(it['osm_id'])] = it
    return got

def main():
    P = pages()
    per = {}; want = set(); missing = []
    for slug, (labels, shots) in P.items():
        ids = []
        for la, lo in clusters(labels, shots):
            r = get('reverse', lat=f'{la:.4f}', lon=f'{lo:.4f}', zoom=10)
            if not r or 'osm_id' not in r: continue
            if r.get('osm_type') == 'node' or not is_city(r): continue
            oid = r['osm_type'][0].upper() + str(r['osm_id'])
            if oid not in ids: ids.append(oid)
        per[slug] = ids; want.update(ids)
        if not ids: missing.append(slug)
    got = lookup(want)
    index = {}; names = {}
    for slug, ids in per.items():
        files = []
        for oid in ids:
            if oid not in got: continue
            s = save_city(got[oid])
            if s: files.append(s[0]); names[s[1]] = s
        if files: index[slug] = files
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    # столицы
    caps = {}; nocap = []
    for _, _, regs in build.D:
        for code, reg, cap, _, links in regs:
            cap = CAPITAL_FIX.get(code, cap.split(' · ')[0])
            if not cap: continue
            if cap in names:   # контур уже скачан для страницы — второй раз не спрашиваем
                la, lo = centroid(names[cap][2])
            else:
                r = get('search', q=f'{cap}, {reg}', polygon_geojson=1, limit=1, countrycodes='ru,ua')
                ring = outer_ring(r[0].get('geojson', {})) if r else None
                if ring and len(ring) > 3:
                    la, lo = centroid(ring)
                    if r[0]['osm_type'] != 'node' and is_city(r[0]): names[cap] = save_city(r[0])
                elif r: la, lo = float(r[0]['lat']), float(r[0]['lon'])
                else: nocap.append(code); continue
            caps[code] = [round(la, 4), round(lo, 4), cap]
    # место или кучка страницы внутри контура столицы, а город обратным геокодированием не нашёлся (например, точка у берега)
    for slug, (labels, shots) in P.items():
        code = slug.split('-')[0].lstrip('0'); cap = caps.get(code)
        if not cap or cap[2] not in names or not names[cap[2]]: continue
        fn, _, ring = names[cap[2]]
        if fn in index.get(slug, []): continue
        if any(build._inside(ring, la, lo) for la, lo in labels + clusters(labels, shots)):
            index.setdefault(slug, []).append(fn)
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(caps, open(os.path.join(ROOT, 'data', 'capitals.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'запросов в сеть: {stats["net"]}, из кэша: {stats["cache"]}')
    print(f'страниц: {len(P)}, с контуром города: {len(index)}, контуров: {len(set(f for v in index.values() for f in v))}')
    print('без города:', ' '.join(sl for sl in P if sl not in index) or '—')
    print(f'столиц: {len(caps)}; не нашлись:', ' '.join(nocap) or '—')

# ---- Контуры регионов «север вверх». Исходного GeoJSON атласа в проекте нет, есть только data/map.json —
# контуры в конической проекции карты главной (tools/favicon.py, lcc). Проекция Ламберта обращается формулой,
# неизвестен только сдвиг и масштаб сетки 1000 px: они подобраны по столицам (data/capitals.json) так, чтобы
# каждая из 85 столиц попала внутрь своего региона на карте, в том числе Москва, Петербург и Севастополь —
# значит, ошибка не больше пикселя сетки (~8 км). Точность контура — как у карты главной (упрощение 0,6 px).
MAP_K, MAP_X, MAP_Y = 770.2775, 551.6644, 434.6916   # px = MAP_K * lcc + (MAP_X, MAP_Y)

def inv_lcc(x, y, lon0=100.0, lat0=55.0, p1=52.0, p2=64.0):
    r = math.radians
    n = math.log(math.cos(r(p1)) / math.cos(r(p2))) / math.log(math.tan(math.pi/4 + r(p2)/2) / math.tan(math.pi/4 + r(p1)/2))
    F = math.cos(r(p1)) * math.tan(math.pi/4 + r(p1)/2) ** n / n
    rho0 = F / math.tan(math.pi/4 + r(lat0)/2) ** n
    X, Y = (x - MAP_X) / MAP_K, (y - MAP_Y) / MAP_K
    rho = math.copysign(math.hypot(X, rho0 + Y), n)
    th = math.atan2(X, rho0 + Y)
    lon = lon0 + math.degrees(th / n)
    lat = math.degrees(2 * math.atan((F / rho) ** (1 / n)) - math.pi / 2)
    return round(lat, 4), round(lon, 4)   # у Чукотки долгота за 180° не сворачивается: контур остаётся целым

def regions_geo():
    m = json.load(open(os.path.join(ROOT, 'data', 'map.json'), encoding='utf-8'))
    out = {}
    for reg in m['regions']:
        rings = []
        for part in re.findall(r'M[^M]*', reg['d']):
            nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', part)]
            x, y = nums[0], nums[1]; ring = [inv_lcc(x, y)]
            for i in range(2, len(nums) - 1, 2):
                x += nums[i]; y += nums[i + 1]; ring.append(inv_lcc(x, y))
            rings.append(ring)
        out[reg['code']] = rings
    json.dump(out, open(os.path.join(ROOT, 'data', 'regions-geo.json'), 'w', encoding='utf-8'), separators=(',', ':'))
    print('контуры регионов: data/regions-geo.json,', len(out), 'регионов')

if __name__ == '__main__':
    main()
    regions_geo()
