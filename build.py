#!/usr/bin/env python3
"""Сборка серии отчётов о заграничных поездках («Мир»). Копия сборки «России» с минимальной адаптацией.
Запуск: python build.py
Тексты поездок лежат в src/<slug>.html (slug: <iso>-<год>-<тема>), общие стили — series.css, скрипт — series.js.
Список стран, отметок и ссылок — в переменной D ниже. Без src/ и без data/*.json сборка тоже идёт: главная без карты.
"""
import os, html, shutil, re, json

ROOT = os.path.dirname(os.path.abspath(__file__))
CSS = open(os.path.join(ROOT, 'series.css'), encoding='utf-8').read()
JS = open(os.path.join(ROOT, 'series.js'), encoding='utf-8').read()
MAPJS = open(os.path.join(ROOT, 'map.js'), encoding='utf-8').read()
import hashlib
# метка версии в ссылках на общие файлы: GitHub Pages разрешает браузеру держать их в кэше 10 минут,
# а с новой меткой после выкладки браузер берёт новый файл сразу
VER = {n: hashlib.md5(t.encode('utf-8')).hexdigest()[:8] for n, t in (('css', CSS), ('js', JS), ('map', MAPJS))}
# Шрифты — в fonts/ на сайте, правила @font-face в series.css. Здесь только предзагрузка двух файлов, нужных
# с первого экрана (кириллица текста и заголовков): браузер начнёт качать их, не дожидаясь разбора стилей.
# Латиница тоже нужна с первого экрана: цифры кодов, дат и чисел лежат в латинском наборе; Oswald — подписи шапки.
# Пять файлов, около 150 КБ, — те же, что страница всё равно скачает, только раньше.
def fonts(up):
    return ''.join(f'<link rel="preload" href="{up}fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>'
                   for f in ('unbounded-cyrillic', 'unbounded-latin', 'golos-text-cyrillic', 'golos-text-latin', 'oswald-cyrillic'))
SERIES_TITLE = 'Мир: страна за страной'   # рабочее название серии: автор его ещё не утвердил (06.10.2026), меняется здесь
SITE = 'https://ssveretennikov.github.io/world/'   # адрес сайта; от него считаются ссылки для пересылки
# Ролики лежат рядом с фото, в <slug>/media/ (решение автора 06.10.2026: сайт с видео ~550 МБ, в 1 ГБ Pages укладывается,
# отдельный репозиторий world-video, как в «России», не нужен). Константы ниже оставлены ради --local-video и сверки.
# В src/<slug>.html адрес ролика по-прежнему пишется как media/имя.mp4; при сборке он заменяется на адрес ниже.
# python build.py --local-video — проверка до выкладки: рядом с каждой страницей пишется index.local.html (в git не идёт),
# где ролики берутся из папки world-video. Сами страницы сайта (index.html) этот ключ не трогает.
VIDEO_SITE = ''      # пусто: адрес ролика на странице — media/<имя>.mp4, как написано в src
VIDEO_BASE = VIDEO_SITE
VIDEO_USED = []      # (slug, имя.mp4) — все ролики, на которые сослались страницы; сверяется с папкой world-video в конце сборки
INDEX_DESC = 'Отчёты о заграничных поездках: страна за страной, по частям света.'
SITE_NAME = SERIES_TITLE
THEME_INIT = "<script>try{var t=localStorage.getItem('world-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}</script>"
SHOW_COUNTS = False   # счётчики «посещено / всего» по частям света; без команды автора не включать
# Страница «Поездки» — в папке journeys/, а не trips/, как в «России»: trips/ здесь — закрытые рабочие материалы (world-trips)
TRIPS_PAGE = 'journeys'
# Дом автора — Россия, отсюда начинаются поездки; отчёты о России — на отдельном сайте. На карте серая заливка без штриховки,
# в счётчик стран и в «Ещё не был» не входит.
HOME = 'RU'
HOME_NAME = 'Россия'
HOME_URL = 'https://ssveretennikov.github.io/russia/'

# Части света вместо федеральных округов (решение автора 06.10.2026); Северная и Южная Америка — одна группа.
# Строка страны: (код ISO 3166-1 alpha-2, название, столица, отметка v/h/n, [(подпись, 'LOCAL:<slug>/index.html'), …]);
# h = понравилось (сердечко), n = ещё не был. Первая ссылка — главная страница страны, остальные — другие поездки
# (подпись — их название). slug поездки: <iso строчными>-<год>-<тема>, например by-2025-grodno.
# Отметки пока у всех v: сердечки автор не расставлял.
D = [
 ('Европа', 'Европа', [
  ('BY','Беларусь','Минск','v',[('Минск за день','LOCAL:by-2023-minsk/index.html'),('Гродно, Поставы, Несвиж и Мир','LOCAL:by-2025-grodno/index.html')]),
  ('TR','Турция','Анкара','v',[('Кемер','LOCAL:tr-2020-kemer/index.html')]),
  ('UA','Украина','Киев','v',[('Закарпатье','LOCAL:ua-2011-zakarpattia/index.html')]),
 ]),
 ('Азия', 'Азия', [
  ('JP','Япония','Токио','v',[('Токио','LOCAL:jp-2024-tokyo/index.html'),('Никко','LOCAL:jp-2024-nikko/index.html'),('Хаконе','LOCAL:jp-2024-hakone/index.html'),
     ('Накасендо','LOCAL:jp-2024-nakasendo/index.html'),('Нагоя','LOCAL:jp-2024-nagoya/index.html'),('Киото','LOCAL:jp-2024-kyoto/index.html'),
     ('Коя-сан','LOCAL:jp-2024-koyasan/index.html'),('Осака и Нара','LOCAL:jp-2024-osaka/index.html'),('Снова Токио','LOCAL:jp-2024-tokyo-2/index.html')]),
  ('VN','Вьетнам','Ханой','v',[('Нячанг','LOCAL:vn-2026-nhatrang/index.html'),('VinWonders','LOCAL:vn-2026-vinwonders/index.html'),('Далат','LOCAL:vn-2026-dalat/index.html'),('Дананг','LOCAL:vn-2026-danang/index.html')]),
  ('CN','Китай','Пекин','v',[('Гуанчжоу за день','LOCAL:cn-2026-guangzhou/index.html')]),
 ]),
 ('Африка', 'Африка', [
  ('EG','Египет','Каир','v',[('Шарм-эль-Шейх 2015','LOCAL:eg-2015-sharm/index.html'),('Шарм-эль-Шейх 2021','LOCAL:eg-2021-sharm/index.html'),('Каир, Гиза и Александрия','LOCAL:eg-2021-cairo/index.html'),('Луксор','LOCAL:eg-2021-luxor/index.html')]),
  ('TZ','Танзания','Додома','v',[('Сафари','LOCAL:tz-2014-safari/index.html'),('Килиманджаро','LOCAL:tz-2014-kilimanjaro/index.html'),('Моши и дорога','LOCAL:tz-2014-moshi/index.html')]),
 ]),
 ('Америка', 'Америка', [
  ('CU','Куба','Гавана','v',[('Варадеро','LOCAL:cu-2025-varadero/index.html'),('Гавана','LOCAL:cu-2025-havana/index.html'),('Залив Свиней','LOCAL:cu-2025-zapata/index.html'),('Сьенфуэгос и Тринидад','LOCAL:cu-2025-trinidad/index.html')]),
 ]),
]

def e(s): return html.escape(s, quote=True)

def href(slug):
    # все отчёты — на сайте; ссылки во ВКонтакте убраны по решению автора 05.10.2026
    assert slug.startswith('LOCAL:'), f'ссылка не на страницу сайта: {slug}'
    return slug[6:]

def flag(code):
    """Флаг-эмодзи из кода ISO: две буквы -> два «региональных индикатора» Юникода (BY -> 🇧🇾)."""
    return ''.join(chr(0x1F1E6 + ord(ch) - ord('A')) for ch in code.upper()) if len(code) == 2 and code.isalpha() else ''

def code_badge(code, link=None):
    """Плашка страны: флаг и код ISO (решение автора 06.10.2026: «флаг и/или код страны»;
    запрет на флаги из «России» сюда не переносится)."""
    f = flag(code)
    inner = (f'<span class="flag" aria-hidden="true">{f}</span>&nbsp;' if f else '') + code
    if link:
        return f'<a class="code" href="{e(link)}" aria-label="Страна {code}">{inner}</a>'
    return f'<span class="code">{inner}</span>'


# Лента «Любимые» на главной (макет Б, 06.10.2026): шесть регионов с сердечком, с запада на восток.
# Набор и порядок — заготовка из макета, уточняет автор. У каждого должен быть card.webp (tools/thumbs.py).
FAV = []   # в «Мире» пока пусто: сердечек автор не ставил; пустой список — ленты нет

def places_of(slug):
    """Места из шапки отчёта (<div class="reg-places"> в src/<slug>.html) — для строки поиска на главной:
    так находятся Тобольск, Мирный, Куршская коса, а не только название региона и столица."""
    f = os.path.join(ROOT, 'src', slug + '.html')
    if not os.path.exists(f): return ''
    m = re.search(r'<div class="reg-places"[^>]*>(.*?)</div>', open(f, encoding='utf-8').read(), re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).replace('·', ' ') if m else ''

ALIASES = {'BY': 'белоруссия', 'CU': 'остров свободы'}   # разговорные имена, которых нет ни в названии, ни в столице

def hook_of(slug):
    """Крючок отчёта (<p class="hook"> в src/<slug>.html) как чистый текст: для строки списка и карточки ленты."""
    f = os.path.join(ROOT, 'src', slug + '.html')
    if not os.path.exists(f): return ''
    m = re.search(r'<p class="hook"[^>]*>(.*?)</p>', open(f, encoding='utf-8').read(), re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).strip() if m else ''

FOKEY = {'Европа': 'eu', 'Азия': 'as', 'Африка': 'af', 'Америка': 'am', '': 'x'}   # части света вместо округов

# значки кнопок хронологии: рисунок, а не символ — символы ⏮ ▶ ⏭ телефоны подменяют цветными эмодзи
def _icon(name, d):
    return f'<svg class="i-{name}" viewBox="0 0 24 24" aria-hidden="true"><path d="{d}"/></svg>'
ICON = {'prev': _icon('prev', 'M6 5h2v14H6zM20 5v14L9 12z'), 'next': _icon('next', 'M16 5h2v14h-2zM4 5v14l11-7z'),
        'play': _icon('play', 'M8 5v14l11-7z'), 'pause': _icon('pause', 'M7 5h4v14H7zM13 5h4v14h-4z')}

def load_map():
    """Контуры стран (tools/map.py). Файла нет — None: главная собирается без карты."""
    f = os.path.join(ROOT, 'data', 'map.json')
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else None

def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11: return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14: return few
    return many

def month_year(iso):
    mon = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь']
    y, m, _ = iso.split('-')
    return f'{mon[int(m) - 1]} {y}'

def find_key(s):
    """Строка для поиска на главной: строчные, ё = е — «орел» находит «Орёл»."""
    return s.lower().replace('ё', 'е')

def ru_date(iso):
    mon = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']
    y, m, d = iso.split('-')
    return f'{int(d)} {mon[int(m) - 1]} {y}'

def index_body():
    total = sum(len(r) for _, _, r in D)
    # Сколько всего стран в мире, автор не решал (06.10.2026): счётчик — «N стран» без «из 195»
    mp = load_map()   # None, пока нет data/map.json — тогда главная без карты
    import json
    tp = os.path.join(ROOT, 'data', 'transport.json')
    trans = json.load(open(tp, encoding='utf-8')) if os.path.exists(tp) else {}   # код -> car/bus/plane/train/other
    # Дата первой поездки в страну — из data/trips.json (slug начинается с кода страны строчными).
    # Дома в списке нет: Москва — не страна этой серии, поэтому все даты — поездки.
    trips = {}
    for t in TRIPS:
        for sl in t['regions']:
            c = sl.split('-')[0].upper()
            if c not in trips or t['start'] < trips[c]: trips[c] = t['start']
    info = {}                                    # код -> (ключ части света, посещена, ссылка на отчёт)
    for short, full, regs in D:
        for code, name, cap, mark, links in regs:
            info[code] = (FOKEY[short], mark != 'n', href(links[0][1]) if links else None, bool(links) and links[0][1].startswith('LOCAL:'))
    visited = {c for c, v in info.items() if v[1]}
    years = sorted({d[:4] for d in trips.values()})
    # Цвет на карте — по «возрасту» года первой поездки: 0 — последний год, 3 — третий с конца и раньше.
    def age(y): return min(3, len(years) - 1 - years.index(y))
    legend = (''.join(f'<li><button type="button" class="ychip" data-k="year" data-v="{y}" aria-pressed="false" data-age="{age(y)}"><i class="k-a{age(y)}"></i>{y}</button></li>' for y in years)
              + '<li class="k-ahead"><i class="k-n"></i>Ещё не был</li>')
    # Шаги «Пути по годам» — поездки из data/trips.json: [начало, конец, [коды стран]]
    tsteps = []
    for t in sorted(TRIPS, key=lambda t: t['start']):
        cs = []
        for sl in t['regions']:
            c = sl.split('-')[0].upper()
            if c not in cs: cs.append(c)
        tsteps.append([t['start'], t['end'], cs])
    tsteps_json = e(json.dumps(tsteps, ensure_ascii=False, separators=(',', ':')))
    # ---- прогресс для шапки: считается из дат поездок, руками не правится ----
    names = {code: name for _, _, regs in D for code, name, *_ in regs}
    facts = []
    if trips:
        first_iso, last_iso = min(trips.values()), max(trips.values())
        last = [names[c] for c in sorted(trips) if trips[c] == last_iso and c in names]
        last_txt = (last[0] + (f' и ещё {len(last) - 1}' if len(last) > 1 else '')) if last else ''
        since = ru_date(first_iso).split(' ', 1)[1]
        facts = [f'<div><dt>В пути</dt><dd>с {since}</dd></div>',
                 f'<div><dt>Последняя новая страна</dt><dd>{ru_date(last_iso)} · {e(last_txt)}</dd></div>']
    else:
        first_iso = ''
    nv = len(visited)
    stats = f'''<div class="ix-stats">
    <p class="ix-big"><b>{nv}</b> <span>{plural(nv, "страна", "страны", "стран")}</span></p>
    {'<dl class="ix-facts">' + ''.join(facts) + '</dl>' if facts else ''}
  </div>'''
    # ---- карта: только если есть data/map.json (tools/map.py по GeoJSON Natural Earth) ----
    mapbox = ''
    if mp:
        paths, dots = [], []
        for r in mp['regions']:
            fo, _, link, local = info.get(r['code'], ('x', False, None, False))
            if r['code'] == HOME:       # дом: ровная серая заливка, карточка со ссылкой на сайт «России»
                paths.append(f'<path class="r home" data-code="{HOME}" data-fo="home" d="{r["d"]}" tabindex="0" role="link" aria-label="{e(HOME_NAME)} · дом"/>')
                continue
            been = r['code'] in visited
            small = bool(r['tiny']) and been    # кружок и обводка — только у посещённых маленьких стран: острова без поездок не засоряют карту
            cls = 'r' + ('' if been else ' no') + (' tiny' if small else '')
            label = e(f"{names.get(r['code'], r['name'])}" + ('' if been else ' (ещё не был)'))
            yr = f' data-year="{trips[r["code"]][:4]}" data-age="{age(trips[r["code"]][:4])}"' if r['code'] in trips else ''
            paths.append(f'<path class="{cls}" data-code="{r["code"]}" data-fo="{fo}"{yr} d="{r["d"]}" tabindex="0" role="{"link" if link else "img"}" aria-label="{label}"/>')
            if small:
                dots.append(f'<circle class="r dot" data-code="{r["code"]}" data-fo="{fo}"{yr} cx="{r["cx"]}" cy="{r["cy"]}" r="5" tabindex="0" role="{"link" if link else "img"}" aria-label="{label}"/>')
        chips_fo = '<button type="button" class="chip" data-k="fo" data-v="" aria-pressed="true">Все</button>' + ''.join(
            f'<button type="button" class="chip" data-k="fo" data-v="{FOKEY[s]}" aria-pressed="false" title="{e(f)}">{s}</button>' for s, f, _ in D if s)
        mapbox = f'''<section class="mapbox" id="karta" aria-label="Карта посещённых стран" data-trips="{tsteps_json}">
  <div class="filters">
    <div class="chips" role="group" aria-label="Часть света">{chips_fo}</div>
  </div>
  <div class="mapwrap">
  <svg class="rumap" viewBox="0 0 {mp['w']} {mp['h']}" role="group" aria-label="Карта мира, посещённые страны" data-home="{HOME}" data-home-name="{e(HOME_NAME)}" data-home-url="{HOME_URL}">
<defs><pattern id="hatch" class="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7"/><line x1="0" y1="0" x2="0" y2="7"/></pattern></defs>
{chr(10).join(paths + dots)}
  </svg>
  <p class="mapdate" id="mapdate" aria-hidden="true" hidden></p>
  </div>
  <div class="mapbar">
    <ul class="legend" role="group" aria-label="Год первой поездки — нажмите, чтобы оставить только его">{legend}</ul>
    <div class="mapbtns"><button type="button" class="zoom" id="zoom" aria-pressed="false">Европа</button></div>
  </div>
  <div class="mcard" id="mcard" aria-live="polite"><p class="mhint"><span class="h-mouse">Наведите на страну или нажмите на неё.</span><span class="h-touch">Нажмите на страну — появится ссылка на отчёт.</span></p></div>
  <div class="tl" aria-label="Хронология поездок">
    <div class="tl-ctl"><button type="button" id="tprev" aria-label="Предыдущая поездка">{ICON['prev']}</button><button type="button" class="play" id="play" aria-label="Посмотреть маршрут: воспроизвести">{ICON['play']}{ICON['pause']}<span>Посмотреть маршрут</span></button><button type="button" id="tnext" aria-label="Следующая поездка">{ICON['next']}</button></div>
    <div class="tl-track"><input type="range" id="track" min="0" value="0" aria-label="Поездка на временной шкале"><div class="ruler" id="ruler" aria-hidden="true"></div></div>
    <div class="tl-read" aria-live="polite"><strong id="tdate">Все поездки</strong><span id="tnote"></span><span class="tl-chain" id="tchain" hidden></span></div>
    <button type="button" class="tl-all" id="tall" hidden>Показать весь период</button>
  </div>
</section>
'''
    else:
        print('внимание: нет data/map.json — главная собрана без карты (python tools/map.py <GeoJSON стран>)')
    out = [f'''<div class="page ix-page">
<header class="ix-head">
  <div class="ix-top"><div class="ix-kicker">Сергей Веретенников · отчёты о поездках</div><button class="theme-btn" type="button" id="themeBtn" hidden>Тема</button></div>
  <h1>{e(SERIES_TITLE)}</h1>
  <div class="ix-intro">
    <p>Заграничные поездки: страна за страной, по частям света.</p>
    <p class="ix-how">{"Нажмите на страну на карте или выберите поездку из списка ниже, чтобы открыть отчёт." if mp else "Выберите поездку из списка ниже, чтобы открыть отчёт."}</p>
  </div>
  {stats}
</header>
{mapbox}''']
    def reg_li(short, code, name, cap, mark, links):
        main = href(links[0][1]) if links else None
        cls = 'reg' + (' none' if mark == 'n' else '')
        nm = f'<a href="{e(main)}">{e(name)}</a>' if main else f'<span class="nm">{e(name)}</span>'
        # сердечко читателю не объясняется (решение автора): без всплывающей подсказки; &nbsp; — чтобы не отрывалось от названия
        if mark == 'h': nm += '&nbsp;<span class="hrt" role="img" aria-label="понравилось">❤</span>'
        d = trips.get(code)
        sub = [e(cap)] if cap else []
        if d: sub.append(month_year(d))
        for lab, slug in links[1:]:   # другие поездки в страну: подпись из D, «2» → «часть 2»
            # название второй страницы из PAGES («Центр и вода») без кода и региона; нет его — «часть N»
            t = next((pg['title'] for pg in PAGES if pg['slug'] == href(slug).split('/')[0]), '')
            sname = t.rsplit(' · ', 1)[1] if t.count(' · ') >= 2 else ('часть ' + lab if lab.isdigit() else lab)
            sub.append(f'<a href="{e(href(slug))}">{e(sname)}</a>')
        small = f'<small>{" · ".join(sub)}</small>' if sub else ''
        # строка крючка из отчёта (у региона с несколькими страницами — с первой), серым с многоточием
        hook = main and hook_of(main.split('/')[0])
        hk = f'<span class="hk">{e(hook)}</span>' if hook else ''
        q = ' '.join([name, cap, ALIASES.get(code, '')] + [places_of(href(sl).split('/')[0]) for _, sl in links]
                     + [lab for lab, _ in links[1:] if not lab.isdigit()])
        attrs = f' data-code="{code}" data-fo="{FOKEY[short]}" data-cap="{e(cap)}" data-q="{e(find_key(q))}"'
        if mark != 'n': attrs += ' data-visited="1"'   # посещена — с датой поездки или без неё (без даты горит с первого шага хронологии)
        if d: attrs += f' data-date="{ru_date(d)}" data-year="{d[:4]}" data-iso="{d}" data-tr="{trans.get(code, "other")}"'
        # миниатюра — tools/thumbs.py; грузится по мере прокрутки, карточка на карте берёт её же; нажимается — ведёт на отчёт
        th = main and main.split('/')[0] + '/thumb.webp'
        img = (f'<a class="th-a" href="{e(main)}" tabindex="-1" aria-hidden="true"><img class="th" src="{th}" alt="" width="360" height="270" loading="lazy" decoding="async"></a>'
               if th and os.path.exists(os.path.join(ROOT, th)) else '')
        return f'<li class="{cls}"{attrs}>{code_badge(code, main)}<div class="reg-t"><div>{nm}</div>{small}{hk}</div>{img}</li>'

    # подписи «❤ — понравилось» у поиска нет: сердечко читателю не объясняется (решение автора)
    out.append(f'''<div class="ix-find">
  <input type="search" id="find" placeholder="Найти страну или город" aria-label="Найти страну или город" autocomplete="off">
  <a class="ix-trips" href="{TRIPS_PAGE}/index.html">Все поездки →</a>
</div>
<p class="ix-none" id="none" hidden>Ничего не нашлось.</p>''')
    out.append(fav_section(trips))
    out.append('<div class="fnote" id="fnote" role="status" hidden><span id="fnoteText"></span> <button type="button" id="fnoteBtn"></button></div>')
    for short, full, regs in D:
        been = [r for r in regs if r[3] != 'n']
        if not been: continue
        title = full if short == full or not short else f'{short} · {full}'
        count = f'<span>{len(been)} / {len(regs)}</span>' if SHOW_COUNTS else ''
        out.append(f'<section class="fo" data-fo="{FOKEY[short]}"><div class="fo-h"><h2>{e(title)}</h2>{count}</div><ul class="regs">')
        out += [reg_li(short, *r) for r in been]
        out.append('</ul></section>')
    # шесть оставшихся — отдельным блоком в конце (макет Б): серыми строками внутри округов они терялись,
    # а наверху отодвигали посещённые регионы от карты
    ahead = [(s, r) for s, _, regs in D for r in regs if r[3] == 'n']
    if ahead: out.append(f'<section class="fo ahead" data-fo="ahead"><div class="fo-h"><h2>Ещё не был · {len(ahead)} '
               f'{plural(len(ahead), "страна", "страны", "стран")}</h2></div><ul class="regs">')
    out += [reg_li(s, *r) for s, r in ahead]
    if ahead: out.append('</ul></section>')
    out.append('<a class="totop" id="totop" href="#karta" hidden>↑ К карте</a>\n</div>')
    return '\n'.join(out)

def fav_section(trips):
    """Лента «Любимые» (макет Б): карточки регионов из FAV — card.webp, код, название, столица · дата, крючок, ссылка.
    Скрипт map.js прячет её, пока работает поиск, фильтр или хронология."""
    if not FAV: return ''
    rows = {}
    for short, full, regs in D:
        for code, name, cap, mark, links in regs:
            if links: rows[href(links[0][1]).split('/')[0]] = (code, name, cap, mark)
    cards = []
    for slug in FAV:
        code, name, cap, mark = rows[slug]
        assert mark == 'h', f'{slug}: в ленте «Любимые» только страны с сердечком'
        img = slug + '/card.webp'
        assert os.path.exists(os.path.join(ROOT, img)), f'нет {img}: запустите python tools/thumbs.py'
        meta = [e(cap)] if cap else []
        if code in trips: meta.append(month_year(trips[code]))
        cards.append(
            f'<li class="fc"><a href="{slug}/index.html">'
            f'<span class="fc-ph"><img src="{img}" alt="" width="800" height="600" decoding="async">'
            f'{code_badge(code)}</span>'
            f'<span class="fc-t"><strong class="fc-nm">{e(name)}</strong>'
            f'<span class="fc-meta">{" · ".join(meta)}</span>'
            f'<span class="fc-hook">{e(hook_of(slug))}</span>'
            f'<span class="fc-go">Открыть отчёт →</span></span></a></li>')
    arrow = lambda d: f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{d}"/></svg>'
    return ('<section class="fav" id="fav" aria-labelledby="fav-h">\n'
            '  <div class="fav-h"><h2 id="fav-h">Любимые</h2><div class="fav-nav" id="favNav">'
            f'<button type="button" id="favPrev" aria-label="Предыдущие">{arrow("M15 5l-7 7 7 7")}</button>'
            f'<button type="button" id="favNext" aria-label="Следующие">{arrow("M9 5l7 7-7 7")}</button>'
            '</div></div>\n  <ul class="fav-row" id="favRow">\n' + '\n'.join(cards) + '\n  </ul>\n</section>')

# ---- Карта дня и профиль высоты: строятся из GPS снимков (regions/<slug>/index.tsv) и отбора (selection.tsv).
#   В тексте страницы: <!--daymap: 44.608,40.098 Майкоп; 44.237,40.157 Смотровая--> и <!--profile-->.
#   Точки отобранных фото — ссылки на <figure id="P016">. Если данных нет, метки просто убираются.
import math, csv

def _gps_rows(slug):
    f = os.path.join(ROOT, 'trips', slug, 'index.tsv')
    if not os.path.exists(f): return [], {}
    rows = []
    for r in csv.DictReader(open(f, encoding='utf-8'), delimiter='\t'):
        if r['lat'] and r['lon'] and r['taken']:
            rows.append(dict(id=r['id'], t=r['taken'], lat=float(r['lat']), lon=float(r['lon']), alt=float(r['alt'] or 0)))
    rows.sort(key=lambda r: r['t'])
    sel = {}
    sf = os.path.join(ROOT, 'trips', slug, 'selection.tsv')
    if os.path.exists(sf):
        for line in open(sf, encoding='utf-8'):
            c = line.rstrip('\n').split('\t')
            if len(c) > 1 and c[1].startswith('P'): sel[c[1]] = c[0]
    return rows, sel

def _tmin(t):
    return int(t[11:13]) * 60 + int(t[14:16])


def _km(la1, lo1, la2, lo2):
    k = math.cos(math.radians((la1 + la2) / 2))
    return 111.2 * math.hypot(la1 - la2, (lo1 - lo2) * k)

def daymap_svg(slug, labels, ids=()):
    """Карта мест дня: только названные места из метки, пронумерованные и соединённые линией по порядку.
    Снимки архива не рисуются — каждый относится к ближайшему месту (не дальше 15 км) и даёт число «N фото».
    Названия — под картой списком со ссылкой на первый кадр места на странице: на телефоне подписи в SVG
    становились мельче 7 px, а сотни ссылок внутри картинки мешали читалкам."""
    if not labels: return ''
    rows, sel = _gps_rows(slug)
    n = len(labels)
    counts = [0] * n; first = [None] * n
    for r in rows:   # строки уже по времени: первый попавший кадр — самый ранний
        d = [_km(r['lat'], r['lon'], la, lo) for la, lo, _ in labels]
        i = min(range(n), key=d.__getitem__)
        if d[i] > 15: continue
        counts[i] += 1
        if first[i] is None and r['id'] in ids: first[i] = r['id']
    W, pad = 360, 26   # ширина как у колонки текста на телефоне: номер 13 px читается без увеличения
    lat0 = sum(l[0] for l in labels) / n; k = math.cos(math.radians(lat0))
    xs = [lo * k for _, lo, _ in labels]; ys = [la for la, _, _ in labels]
    dx, dy = max(max(xs) - min(xs), 1e-4), max(max(ys) - min(ys), 1e-4)
    iw = W - 2 * pad; ih = max(120, min(300, iw * dy / dx)); H = int(ih + 2 * pad + 18)
    span = max(dx, dy * iw / ih)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    P = lambda la, lo: (pad + iw * (0.5 + (lo * k - cx) / span), pad + ih * (0.5 - (la - cy) / span * iw / ih))
    true = [P(la, lo) for la, lo, _ in labels]
    # близкие места раздвигаются, к настоящему положению ведёт тонкая линия
    R, gap = 11, 25
    pos = [list(p) for p in true]
    for _ in range(200):
        moved = False
        for a in range(n):
            for b in range(a + 1, n):
                vx, vy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]; d = math.hypot(vx, vy)
                if d < gap:
                    if d < 1e-6: vx, vy, d = 1.0, 0.3 * (b - a), math.hypot(1.0, 0.3 * (b - a))
                    s = (gap - d) / 2 / d
                    pos[a][0] -= vx * s; pos[a][1] -= vy * s; pos[b][0] += vx * s; pos[b][1] += vy * s; moved = True
        for p in pos:
            p[0] = min(max(p[0], R + 2), W - R - 2); p[1] = min(max(p[1], R + 2), H - 28)
        if not moved: break
    for a in range(n):
        for b in range(a + 1, n):
            if math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]) < 2 * R + 1:
                print(f'ВНИМАНИЕ: {slug}: номера {a + 1} и {b + 1} на карте мест накладываются')
    name = next((nm for _, _, regs in D for _, nm, _, _, links in regs for _, sl in links
                 if href(sl).split('/')[0] == slug), '')
    out = [f'<svg class="daymap-svg" viewBox="0 0 {W} {H}" role="img" aria-label="Карта мест{(" — " + e(name)) if name else ""}: '
           f'{n} {plural(n, "место", "места", "мест")} по порядку, названия — списком под картой">']
    for i in range(n - 1):   # переезд дальше 50 км — пунктир: между точками не шли, а ехали
        far = _km(labels[i][0], labels[i][1], labels[i + 1][0], labels[i + 1][1]) > 50
        (x1, y1), (x2, y2) = true[i], true[i + 1]
        out.append(f'<line class="dm-route{" dm-far" if far else ""}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for i in range(n):
        (tx, ty), (x, y) = true[i], pos[i]
        if math.hypot(tx - x, ty - y) > 1:
            out.append(f'<line class="dm-lead" x1="{tx:.1f}" y1="{ty:.1f}" x2="{x:.1f}" y2="{y:.1f}"/><circle class="dm-dot" cx="{tx:.1f}" cy="{ty:.1f}" r="2.5"/>')
    for i in range(n):
        x, y = pos[i]
        out.append(f'<g class="dm-num"><circle cx="{x:.1f}" cy="{y:.1f}" r="{R}"/><text x="{x:.1f}" y="{y + 4.5:.1f}" text-anchor="middle">{i + 1}</text></g>')
    # линейка: круглое число километров не длиннее четверти ширины
    km_px = iw / (span * 111.2)
    step = next((v for v in (1000, 500, 200, 100, 50, 20, 10, 5, 2, 1, .5, .2, .1) if v * km_px <= iw / 4), .1)
    L = step * km_px; lab = f'{step:g} км' if step >= 1 else f'{int(step * 1000)} м'
    out.append(f'<g class="dm-scale"><path d="M{pad},{H - 14} v-5 h{L:.1f} v5"/><text x="{pad + L + 6:.1f}" y="{H - 13}">{lab}</text></g>')
    out.append('</svg>')
    li = []
    for i, (_, _, nm) in enumerate(labels):
        t = f'<a href="#{first[i]}">{e(nm)}</a>' if first[i] else e(nm)
        c = f' <span class="dm-n">· {counts[i]} фото</span>' if counts[i] else ''
        li.append(f'<li>{t}{c}</li>')
    return '\n'.join(out) + '\n<ol class="dm-list">' + ''.join(li) + '</ol>'


# ---- Схема точек съёмки (замысел автора 06.10.2026). DAYMAP_MODE = 'v2' — по умолчанию; None — прежняя карта мест.
#   Вид выбирается сам по названным местам из метки и контурам городов (tools/cities.py, data/cities/):
#   «город» — места в одном городе, 0–1 место за ним (условно у края окна, с расстоянием в списке);
#   «регион» — несколько мест за городом, городские места собраны в одну точку;
#   «две схемы» — за городом два места и больше, а в городе тоже много (два места или треть снимков): город и регион
#   (на компьютере в ряд, на телефоне друг под другом). Нет города у мест — берётся столица региона (Дагестан).
#   Схема города приближена к местам (поля ~15 %), силуэт обрезается краем, но в кадре не меньше трети силуэта;
#   место за городом — условной точкой за контуром по азимуту (окно расширяется, чтобы точка не легла в силуэт).
#   Схема региона — силуэт целиком, без приближения.
#   Мелкие точки — все снимки архива с координатами: виден путь автора.
DAYMAP_MODE = 'v2'
NO_TRACK = ('77-',)   # Москва: где живёт автор — точки снимков не рисуются (приватность); Подмосковье — рисуются
DM_W, DM_PAD = 360, 14
MARGIN = 0.7          # места занимают 70 % окна — по 15 % полей с каждой стороны
MIN_SIL = 1 / 3       # окно не уже трети силуэта: иначе от города остаётся заливка без формы

_GEO = {}
def _geo(name):
    if name not in _GEO:
        f = os.path.join(ROOT, 'data', name)
        _GEO[name] = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    return _GEO[name]

def _city_rings(slug):
    """[(название, кольцо [[lon, lat], …])] — города страницы из data/cities/index.json, без повторов по названию."""
    out = {}
    for fn in _geo('cities/index.json').get(slug, []):
        f = os.path.join(ROOT, 'data', 'cities', fn)
        if not os.path.exists(f): continue
        ft = json.load(open(f, encoding='utf-8'))['features'][0]
        nm, ring = ft['properties']['name'], ft['geometry']['coordinates'][0]
        if nm not in out or len(ring) > len(out[nm]): out[nm] = ring
    return list(out.items())

def _code(slug):
    return slug.split('-')[0].upper()   # код страны ISO из slug поездки

def _region_rings(slug):
    return [[[lo, la] for la, lo in r] for r in _geo('regions-geo.json').get(_code(slug), [])]

def _inside(ring, la, lo):
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > la) != (y2 > la) and lo < x1 + (la - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c

def _ring_center(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    return (cy / (3 * a), cx / (3 * a)) if a else (ring[0][1], ring[0][0])

def _ring_exit(ring, la, lo):
    """Где луч из центра города к месту за городом в последний раз пересекает контур — (широта, долгота)."""
    cla, clo = _ring_center(ring); k = math.cos(math.radians(cla))
    dx, dy = (lo - clo) * k, la - cla; best = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        ax, ay = (x1 - clo) * k, y1 - cla; bx, by = (x2 - clo) * k, y2 - cla
        ex, ey = bx - ax, by - ay; den = dx * ey - dy * ex
        if abs(den) < 1e-15: continue
        t = (ax * ey - ay * ex) / den; u = (ax * dy - ay * dx) / den
        if t > 0 and 0 <= u <= 1: best = max(best, t)
    best = min(best, 1.0)
    return cla + dy * best, clo + dx * best / k

def _seg_d(x, y, a, b):
    """Расстояние от точки до отрезка a–b (в пикселях схемы)."""
    ex, ey = b[0] - a[0], b[1] - a[1]; L = ex * ex + ey * ey
    t = max(0, min(1, ((x - a[0]) * ex + (y - a[1]) * ey) / L)) if L else 0
    return math.hypot(x - a[0] - t * ex, y - a[1] - t * ey)

def _capital_city(slug):
    """Контур столицы региона из data/cities/ — если у страницы город обратным геокодированием не нашёлся."""
    cap = _geo('capitals.json').get(_code(slug))
    if not cap: return []
    d = os.path.join(ROOT, 'data', 'cities')
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith('.geojson'): continue
        ft = json.load(open(os.path.join(d, fn), encoding='utf-8'))['features'][0]
        if ft['properties']['name'] == cap[2]: return [(cap[2], ft['geometry']['coordinates'][0])]
    return []

class _Frame:
    """Окно схемы: равнопромежуточная проекция «север вверх» вокруг мест, масштаб по правилу полей и трети силуэта."""
    def __init__(self, pts, sil, H, avoid=None, whole=False):
        self.W, self.H = DM_W, H
        self.iw, self.ih = DM_W - 2 * DM_PAD, H - 2 * DM_PAD - 18      # внизу полоса под линейку
        la0 = sum(p[0] for p in pts) / len(pts); self.k = math.cos(math.radians(la0))
        xs = [lo * self.k for _, lo in pts]; ys = [la for la, _ in pts]
        sx = [p[0] * self.k for r in sil for p in r]; sy = [p[1] for r in sil for p in r]
        if whole and sil:   # схема региона: силуэт целиком, поля ~4 %; места за силуэтом тоже в окне
            xs += sx; ys += sy
            self.s = max((max(xs) - min(xs)) / self.iw, (max(ys) - min(ys)) / self.ih) * 1.08
            self.cx, self.cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            return
        s_pl = max((max(xs) - min(xs)) / self.iw, (max(ys) - min(ys)) / self.ih) / MARGIN
        s_sil = max((max(sx) - min(sx)) / self.iw, (max(sy) - min(sy)) / self.ih) if sil else s_pl
        s = max(s_pl, s_sil * MIN_SIL, 1.2 / 111.2 / self.iw)          # и не меньше 1,2 км на окно
        s = min(s, max(s_sil * 1.08, s_pl))                              # и не шире всего силуэта, если места позволяют
        self.cx, self.cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        if sil and s >= s_sil:   # силуэт целиком в окне — по центру силуэта, если места не выпадают
            ccx, ccy = (max(sx) + min(sx)) / 2, (max(sy) + min(sy)) / 2
            hx, hy = self.iw * s / 2 * .95, self.ih * s / 2 * .95
            self.cx = min(max(ccx, max(xs) - hx), min(xs) + hx); self.cy = min(max(ccy, max(ys) - hy), min(ys) + hy)
        self.s = s
        if avoid:   # врезка в углу: места под ней — окно чуть шире
            for _ in range(6):
                if not any(avoid[0] - 12 < x < avoid[2] + 12 and avoid[1] - 12 < y < avoid[3] + 12
                           for x, y in (self.P(la, lo) for la, lo in pts)): break
                self.s *= 1.15
    def P(self, la, lo):
        return (DM_W / 2 + (lo * self.k - self.cx) / self.s, DM_PAD + self.ih / 2 - (la - self.cy) / self.s)
    def edge(self, la, lo, inset=0):
        """Место за окном — у края окна по лучу из центра в его сторону."""
        x, y = self.P(la, lo); ox, oy = DM_W / 2, DM_PAD + self.ih / 2
        vx, vy = x - ox, y - oy; L = math.hypot(vx, vy) or 1; vx, vy = vx / L, vy / L
        hx, hy = self.iw / 2 - 2 - inset, self.ih / 2 - 2 - inset
        t = min(hx / abs(vx) if vx else 1e9, hy / abs(vy) if vy else 1e9)
        return ox + vx * t, oy + vy * t
    def visible(self, x, y):
        return 0 <= x <= self.W and 0 <= y <= self.H - 18
    def path(self, ring):
        return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in (self.P(la, lo) for lo, la in ring)) + ' Z'
    def scale(self):
        km_px = 1 / (self.s * 111.2)
        step = next((v for v in (1000, 500, 200, 100, 50, 20, 10, 5, 2, 1, .5, .2, .1) if v * km_px <= self.iw / 4), .1)
        L = step * km_px; lab = f'{step:g} км' if step >= 1 else f'{int(step * 1000)} м'
        return (f'<g class="dm-scale"><path d="M{DM_PAD},{self.H - 14} v-5 h{L:.1f} v5"/>'
                f'<text x="{DM_PAD + L + 6:.1f}" y="{self.H - 13}">{lab}</text></g>')

def _spread(slug, true, W, H, R=11, gap=25):
    """Близкие номера раздвигаются; к настоящему положению ведёт тонкая линия."""
    pos = [list(p) for p in true]; n = len(pos)
    for _ in range(300):
        moved = False
        for a in range(n):
            for b in range(a + 1, n):
                vx, vy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]; d = math.hypot(vx, vy)
                if d < gap:
                    if d < 1e-6: vx, vy, d = 1.0, 0.3 * (b - a), math.hypot(1.0, 0.3 * (b - a))
                    s = (gap - d) / 2 / d
                    pos[a][0] -= vx * s; pos[a][1] -= vy * s; pos[b][0] += vx * s; pos[b][1] += vy * s; moved = True
        for p in pos:
            p[0] = min(max(p[0], R + 2), W - R - 2); p[1] = min(max(p[1], R + 2), H - 30)
        if not moved: break
    for a in range(n):
        for b in range(a + 1, n):
            if math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]) < 2 * R + 1:
                print(f'ВНИМАНИЕ: {slug}: номера на схеме точек накладываются')
    return pos

def _marks(out, marks, true, pos, route):
    """marks: [(текст, класс)]; route: [(откуда, куда, далеко)] — номера отметок по порядку маршрута."""
    for a, b, far in route:
        (x1, y1), (x2, y2) = true[a], true[b]
        out.append(f'<line class="dm-route{" dm-far" if far else ""}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for (tx, ty), (x, y) in zip(true, pos):
        if math.hypot(tx - x, ty - y) > 1:
            out.append(f'<line class="dm-lead" x1="{tx:.1f}" y1="{ty:.1f}" x2="{x:.1f}" y2="{y:.1f}"/><circle class="dm-dot" cx="{tx:.1f}" cy="{ty:.1f}" r="2.5"/>')
    for (t, cls), (x, y) in zip(marks, pos):
        w = max(22, 8 + 7 * len(t))
        shape = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11"/>' if w <= 22 else
                 f'<rect x="{x - w / 2:.1f}" y="{y - 11:.1f}" width="{w}" height="22" rx="11"/>')
        out.append(f'<g class="dm-num{cls}">{shape}<text x="{x:.1f}" y="{y + 4.5:.1f}" text-anchor="middle">{t}</text></g>')

def _shots(out, slug, F, rows, keep=lambda x, y, r: True):
    if slug.startswith(NO_TRACK): return
    for r in rows:
        x, y = F.P(r['lat'], r['lon'])
        if F.visible(x, y) and keep(x, y, r):
            out.append(f'<circle class="dms-shot" cx="{x:.1f}" cy="{y:.1f}" r="3"/>')

def _inset(slug, cname, cring):
    """Врезка: маленький силуэт региона, точка столицы и рамка — где этот город."""
    reg = _region_rings(slug)
    if not reg: return '', None
    S = 74; x0, y0 = DM_W - DM_PAD - S, DM_PAD
    pts = [p for r in reg for p in r]
    la0 = sum(p[1] for p in pts) / len(pts); k = math.cos(math.radians(la0))
    xs = [p[0] * k for p in pts]; ys = [p[1] for p in pts]
    s = max(max(xs) - min(xs), max(ys) - min(ys)) / (S - 10)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    P = lambda la, lo: (x0 + S / 2 + (lo * k - cx) / s, y0 + S / 2 - (la - cy) / s)
    o = [f'<g class="dms-inset"><rect class="dms-box" x="{x0}" y="{y0}" width="{S}" height="{S}" rx="6"/>']
    o.append('<path class="dms-reg" d="' + ''.join('M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in (P(la, lo) for lo, la in r)) + 'Z' for r in reg) + '"/>')
    cap = _geo('capitals.json').get(_code(slug))
    la, lo = _ring_center(cring); x, y = P(la, lo)
    o.append(f'<rect class="dms-here" x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" rx="2"/>')
    if cap:
        cxp, cyp = P(cap[0], cap[1])
        o.append(f'<circle class="dms-cap" cx="{cxp:.1f}" cy="{cyp:.1f}" r="2.4"><title>{e(cap[2])} — столица</title></circle>')
    o.append('</g>')
    return ''.join(o), (x0, y0, x0 + S, y0 + S)

def daymap_v2(slug, labels, ids=()):
    if not labels: return ''
    rows, _ = _gps_rows(slug)
    n = len(labels)
    counts = [0] * n; first = [None] * n
    for r in rows:   # строки уже по времени: первый попавший кадр — самый ранний
        d = [_km(r['lat'], r['lon'], la, lo) for la, lo, _ in labels]
        i = min(range(n), key=d.__getitem__)
        if d[i] > 15: continue
        counts[i] += 1
        if first[i] is None and r['id'] in ids: first[i] = r['id']
    reg = _region_rings(slug)
    if any(p[0] > 180 for r in reg for p in r):   # Чукотка за линией перемены дат: долготы в одну сторону
        labels = [(la, lo + 360 if lo < 0 else lo, nm) for la, lo, nm in labels]
        rows = [dict(r, lon=r['lon'] + 360 if r['lon'] < 0 else r['lon']) for r in rows]
    cities = _city_rings(slug) or _capital_city(slug)   # Дагестан: места вне городов — город по столице
    where = [next((ci for ci, (_, ring) in enumerate(cities) if _inside(ring, la, lo)), None) for la, lo, _ in labels]
    main = (max(range(len(cities)), key=lambda ci: (where.count(ci), sum(_inside(cities[ci][1], r['lat'], r['lon']) for r in rows)))
            if cities else None)
    inc = [main is not None and w == main for w in where]
    nin = sum(inc); nout = n - nin
    # Город «весомый», если в нём два места или треть снимков (Анадырь: одно место, но две трети кадров).
    # Мест в метке обычно 4–7, поэтому «от трёх в городе и за ним» почти не встречается — порог ниже.
    in_shots = sum(_inside(cities[main][1], r['lat'], r['lon']) for r in rows) if main is not None else 0
    rich = nin >= 2 or (in_shots >= 10 and in_shots >= len(rows) / 3)
    kind = 'city' if nin and nout <= 1 else 'both' if rich else 'region'
    if kind != 'city' and not reg: kind = 'city' if nin else 'region'
    cname, cring = cities[main] if main is not None else ('', None)
    name = next((nm for _, _, regs in D for _, nm, _, _, links in regs for _, sl in links
                 if href(sl).split('/')[0] == slug), '')
    svgs = []; dist = [''] * n

    def city_svg(show_out):
        H = 330
        ins, box = _inset(slug, cname, cring)
        pts = [(la, lo) for (la, lo, _), c in zip(labels, inc) if c]
        if not pts:   # город взят по столице, а мест в нём нет — окно по снимкам в контуре, иначе по контуру
            pts = [(r['lat'], r['lon']) for r in rows if _inside(cring, r['lat'], r['lon'])] or [(la, lo) for lo, la in cring]
        far_i = [i for i in range(n) if show_out and not inc[i]]
        brd = {i: _ring_exit(cring, labels[i][0], labels[i][1]) for i in far_i}
        F = _Frame(pts + list(brd.values()), [cring], H, box)
        IN = (DM_PAD + 12, DM_W - DM_PAD - 12, DM_PAD + 12, H - 42)   # куда ставить условную точку
        def cond(i):
            """Место за окном: за контуром города по азимуту на 9 % ширины окна, не внутри силуэта."""
            bx, by = F.P(*brd[i]); tx, ty = F.P(labels[i][0], labels[i][1])
            vx, vy = tx - bx, ty - by; L = math.hypot(vx, vy) or 1
            return bx + vx / L * .09 * DM_W, by + vy / L * .09 * DM_W
        def ok(x, y):
            """В окне, не под врезкой, вне контура и не вплотную к нему (6 % ширины окна до любой точки контура)."""
            if not (IN[0] <= x <= IN[1] and IN[2] <= y <= IN[3]): return False
            if box and box[0] - 12 < x < box[2] + 12 and box[1] - 12 < y < box[3] + 12: return False
            px = [F.P(la, lo) for lo, la in cring]; seg = list(zip(px, px[1:] + px[:1]))
            if _inside(px, y, x) or min(_seg_d(x, y, a, b) for a, b in seg) < .06 * DM_W: return False
            # рядом не должно быть места, где окно обрезает силуэт: иначе точка кажется лежащей в городе (Оренбург)
            cut = [(a, b) for a, b in seg if not (F.visible(*a) and F.visible(*b))]
            return not cut or min(_seg_d(x, y, a, b) for a, b in cut) >= .2 * DM_W
        for _ in range(40):   # окно расширяется, пока условная точка не встанет в нём за контуром
            bad = [i for i in far_i if not F.visible(*F.P(labels[i][0], labels[i][1])) and not ok(*cond(i))]
            if not bad: break
            F.s *= 1.08
            bx, by = F.P(*brd[bad[0]])   # и сдвигается в сторону места, если край силуэта уже у границы
            F.cx += (bx - DM_W / 2) * F.s * .15; F.cy -= (by - DM_PAD - F.ih / 2) * F.s * .15
        idx = [i for i in range(n) if inc[i] or show_out]
        true = []
        for i in idx:
            la, lo, _ = labels[i]; x, y = F.P(la, lo)
            if not inc[i] and not F.visible(x, y):
                x, y = cond(i)
                cla, clo = _ring_center(cring)
                dist[i] = f' <span class="dm-n">· ≈{max(10, int(round(_km(la, lo, cla, clo), -1)))} км</span>'
            true.append((x, y))
        out = [f'<svg class="daymap-svg dms dms-city" viewBox="0 0 {DM_W} {H}" role="img" aria-label="Схема города {e(cname)}: '
               f'{len(idx)} {plural(len(idx), "место", "места", "мест")} по порядку, названия — списком под схемой">',
               f'<path class="dms-city" d="{F.path(cring)}"/>']
        _shots(out, slug, F, rows)
        pos = _spread(slug, true, DM_W, H)
        route = [(j, j + 1, not inc[a] or not inc[b]) for j, (a, b) in enumerate(zip(idx, idx[1:]))]
        _marks(out, [(str(i + 1), '' if inc[i] else ' dms-out') for i in idx], true, pos, route)
        out += [ins, F.scale(), '</svg>']
        return '\n'.join(out)

    def region_svg():
        H = 330
        group = nin >= 2   # городские места — одна точка с их номерами
        pts = [(la, lo) for la, lo, _ in labels]
        F = _Frame(pts, reg, H, whole=True)
        marks, true, seq = [], [], []
        gi = [i for i in range(n) if inc[i]]
        g = None   # номер отметки города: маршрут возвращается на неё, если автор заезжал в город дважды
        for i, (la, lo, _) in enumerate(labels):
            if group and inc[i]:
                if g is None:
                    t = (f'{gi[0] + 1}–{gi[-1] + 1}' if gi == list(range(gi[0], gi[-1] + 1)) else
                         ','.join(str(j + 1) for j in gi) if len(gi) <= 3 else f'{len(gi)} мест')
                    cla, clo = _ring_center(cring); g = len(marks); marks.append((t, ' dms-group')); true.append(F.P(cla, clo))
                if not seq or seq[-1] != g: seq.append(g)
            else:
                seq.append(len(marks)); marks.append((str(i + 1), '')); true.append(F.P(la, lo))
        far = [(a, b, math.hypot(true[a][0] - true[b][0], true[a][1] - true[b][1]) * F.s * 111.2 > 50) for a, b in zip(seq, seq[1:])]
        out = [f'<svg class="daymap-svg dms dms-region" viewBox="0 0 {DM_W} {H}" role="img" aria-label="Схема страны{(" — " + e(name)) if name else ""}: '
               f'{n} {plural(n, "место", "места", "мест")} по порядку, названия — списком под схемой">',
               '<path class="dms-reg" d="' + ''.join(F.path(r) for r in reg) + '"/>']
        if cring and kind == 'both': out.append(f'<path class="dms-city" d="{F.path(cring)}"/>')
        _shots(out, slug, F, rows)
        pos = _spread(slug, true, DM_W, H)
        _marks(out, marks, true, pos, far)
        out += [F.scale(), '</svg>']
        return '\n'.join(out)

    if kind == 'city': svgs.append(city_svg(True)); leg = f'Схема города: {e(cname)}'
    elif kind == 'both': svgs.append('<div class="dms-pair">' + city_svg(False) + region_svg() + '</div>'); leg = f"Город и страна: {e(cname)}"
    else: svgs.append(region_svg()); leg = "Схема страны"
    if kind != 'region': leg += ' <span class="dms-osm">· Контур города — © участники OpenStreetMap</span>'
    li = []
    for i, (_, _, nm) in enumerate(labels):
        t = f'<a href="#{first[i]}">{e(nm)}</a>' if first[i] else e(nm)
        c = f' <span class="dm-n">· {counts[i]} фото</span>' if counts[i] else ''
        li.append(f'<li>{t}{dist[i]}{c}</li>')
    return ('\n'.join(svgs) + f'\n<p class="dms-legend" data-kind="{kind}">{leg}</p>'
            '\n<ol class="dm-list">' + ''.join(li) + '</ol>')


def profile_svg(slug):
    rows, sel = _gps_rows(slug)
    rows = [r for r in rows if r['alt'] > 0]
    if len(rows) < 2: return ''
    W, H, pl, pb, pt = 640, 220, 60, 26, 14
    t0 = min(_tmin(r['t']) for r in rows) - 15; t1 = max(_tmin(r['t']) for r in rows) + 15
    a0 = max(0, min(r['alt'] for r in rows) - 50); a1 = max(r['alt'] for r in rows) + 50
    def P(r):
        return (pl + (W - pl - 10) * (_tmin(r['t']) - t0) / (t1 - t0), pt + (H - pt - pb) * (1 - (r['alt'] - a0) / (a1 - a0)))
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in map(P, rows))
    out = [f'<svg class="profile-svg" viewBox="0 0 {W} {H}" role="img" aria-label="Высота по времени дня">']
    for h in range((t0 // 60) + 1, (t1 // 60) + 1):
        x = pl + (W - pl - 10) * (h * 60 - t0) / (t1 - t0)
        out.append(f'<line class="pf-grid" x1="{x:.1f}" y1="{pt}" x2="{x:.1f}" y2="{H - pb}"/><text class="pf-ax" x="{x:.1f}" y="{H - 8}" text-anchor="middle">{h}:00</text>')
    for a in (a0 + 50, a1 - 50):
        y = pt + (H - pt - pb) * (1 - (a - a0) / (a1 - a0))
        out.append(f'<text class="pf-ax" x="{pl - 6}" y="{y + 4:.1f}" text-anchor="end">{int(round(a, -1))} м</text>')
    out.append(f'<polyline class="pf-line" points="{pts}"/>')
    for r in rows:
        if r['id'] in sel:
            x, y = P(r)
            out.append(f'<a href="#{r["id"]}" class="dm-pt"><circle cx="{x:.1f}" cy="{y:.1f}" r="5"><title>{r["t"][11:16]} · {int(r["alt"])} м</title></circle></a>')
    out.append('</svg>')
    return '\n'.join(out)

# Ширина кадра на экране по виду фигуры — по раскладке series.css: медиа до 74rem (1184 px) на компьютере
# и до 62rem между 640 и 900 px, текст 42rem, ряд — половина; на телефоне всё во всю ширину.
SIZES = {'wide': '(max-width: 640px) 100vw, (max-width: 1200px) 90vw, 1184px',
         'col': '(max-width: 640px) 100vw, 672px',
         'row': '(max-width: 640px) 100vw, (max-width: 1200px) 45vw, 592px',
         'hero': '100vw'}

def mobile_srcset(slug, fig, inner):
    """Если рядом с media/x.webp лежит копия для телефона x.m.webp (tools/media.py mobile), картинке
    добавляются srcset и sizes: телефон берёт копию в 1080 px, компьютер — оригинал. src остаётся оригиналом —
    его открывает лайтбокс."""
    cls = re.search(r'class="([^"]*)"', fig)
    cls = cls.group(1).split() if cls else []
    kind = 'hero' if 'hero-ph' in cls else 'wide' if 'wide' in cls else 'col' if ('mid' in cls or 'tall' in cls) else 'row'
    def one(m):
        tag = m.group(0)
        s = re.search(r'src="media/([^"]+)\.webp"', tag); w = re.search(r'width="(\d+)"', tag)
        if not s or not w or 'srcset=' in tag: return tag
        if not os.path.exists(os.path.join(ROOT, slug, 'media', s.group(1) + '.m.webp')): return tag
        return tag.replace(s.group(0), s.group(0) + f' srcset="media/{s.group(1)}.m.webp 1080w, media/{s.group(1)}.webp {w.group(1)}w" sizes="{SIZES[kind]}"', 1)
    return re.sub(r'<img [^>]*>', one, inner)

def inject_data(slug, src):
    """Подставляет карту дня, профиль высоты и реальные размеры картинок из regions/<slug>/media.tsv."""
    def dm(m):
        labels = []
        for part in (m.group(1) or '').split(';'):
            part = part.strip()
            mm = re.match(r'(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\s+(.+)', part)
            if mm: labels.append((float(mm[1]), float(mm[2]), mm[3].strip()))
        return (daymap_v2 if DAYMAP_MODE == 'v2' else daymap_svg)(slug, labels, ids)
    ids = set(re.findall(r'<figure[^>]* id="(P[0-9]+)"', src))
    src = src.replace('<figure class="wide daymap">', '<figure class="daymap">')   # в ширину колонки текста
    src = re.sub(r'<!--daymap:?(.*?)-->', dm, src, flags=re.S)
    src = re.sub(r'<!--profile-->', lambda m: profile_svg(slug), src)
    mt = os.path.join(ROOT, 'trips', slug, 'media.tsv')
    if os.path.exists(mt):
        dims = {r['name']: (r['w'], r['h']) for r in csv.DictReader(open(mt, encoding='utf-8'), delimiter='\t')}
        def fix(m):
            name = m.group(2).rsplit('.', 1)[0]
            if name in dims:
                w, h = dims[name]; return f'{m.group(1)}width="{w}" height="{h}"'
            return m.group(0)
        src = re.sub(r'(src="media/([^"]+)" )width="\d+" height="\d+"', fix, src)
    src = re.sub(r'(<figure\b[^>]*>)(.*?)(</figure>)', lambda m: m.group(1) + mobile_srcset(slug, m.group(1), m.group(2)) + m.group(3), src, flags=re.S)
    # ролик — с отдельного сайта; обложка (poster) остаётся в media/ рядом со страницей
    def video(m):
        VIDEO_USED.append((slug, m.group(1)))
        return f'src="media/{m.group(1)}"' if not VIDEO_BASE else f'src="{VIDEO_BASE}{slug}/{m.group(1)}"'
    src = re.sub(r'src="media/([^"]+\.mp4)"', video, src)
    # ролик и его обложка не качаются, пока до них не докрутили: preload="none", а poster подставляет
    # series.js у края окна (атрибут poster браузер грузит сразу, даже у ролика в конце страницы)
    src = re.sub(r'<video [^>]*>', lambda m: m.group(0).replace('preload="metadata"', 'preload="none"').replace(' poster="', ' data-poster="'), src)
    return src

def cover_head(src):
    """Шапка-обложка (решение автора 06.10.2026, вариант А): главное фото первым во всю ширину, код и название
    поверх нижней части кадра, остальное — под кадром. Исходники src/*.html остаются «анкетой» (код, название,
    места, крючок, паспорт, маршрут, фото) — их 90 и они содержание, а не вёрстка; перестановка делается здесь.
    Если шапка исходника устроена иначе и какой-то части нет — ошибка сборки, а не молча кривая страница."""
    m = re.search(r'<header class="reg-head">(.*?)</header>', src, re.S)
    if not m: raise ValueError('в исходнике нет <header class="reg-head">')
    h = m.group(1)
    def part(rx, name):
        mm = re.search(rx, h, re.S)
        if not mm: raise ValueError(f'в шапке исходника нет части «{name}»')
        return mm
    code = part(r'<span class="code"[^>]*>.*?</span>', 'код').group(0)
    h1 = part(r'<h1>(.*?)</h1>', 'название')
    places = part(r'<div class="reg-places">.*?</div>', 'места').group(0)
    hook = part(r'<p class="hook">.*?</p>', 'крючок').group(0)
    passport = part(r'<dl class="passport">.*?</dl>', 'паспорт').group(0)
    route = part(r'<ol class="route"[^>]*>.*?</ol>', 'маршрут').group(0)
    fig = part(r'<figure class="hero-ph"([^>]*)>\s*<div class="ph"><img ([^>]*)></div>\s*(<figcaption>.*?</figcaption>)\s*</figure>', 'главный кадр')
    fig_attrs, img_attrs, caption = fig.groups()
    w = re.search(r'width="(\d+)"', img_attrs); hh = re.search(r'height="(\d+)"', img_attrs)
    portrait = bool(w and hh and int(w.group(1)) < int(hh.group(1)))
    img_src = re.search(r'src="([^"]+)"', img_attrs).group(1)
    ss = ''.join(re.findall(r' (?:srcset|sizes)="[^"]*"', ' ' + img_attrs))   # размытой копии — тот же файл, что главному кадру
    # вертикальный кадр в широкую полосу не режем: он целиком, а поля по бокам — его же размытая копия.
    # Копия — отдельная картинка, а не url() в стилях: адрес в style="" считался бы от series.css в корне сайта
    ph = (f'<div class="ph"><img class="cover-bg" src="{img_src}"{ss} alt="" aria-hidden="true">' if portrait else '<div class="ph">')
    # на узком телефоне кегль названия подбирается так, чтобы самое длинное слово встало в строку целиком
    longest = max(len(wd) for wd in re.sub(r'<[^>]+>', '', h1.group(1)).split()) if h1.group(1).strip() else 1
    head = (f'<header class="reg-head cover-head">\n'
            f'  <figure class="hero-ph cover{" portrait" if portrait else ""}"{fig_attrs}>\n'
            f'    {ph}<img fetchpriority="high" {img_attrs}></div>\n'
            f'    <div class="reg-id" style="--nw:{longest}">\n      {code}\n      <h1>{h1.group(1)}</h1>\n    </div>\n'
            f'    {caption}\n  </figure>\n'
            f'  <div class="under">\n    {places}\n    {hook}\n    {passport}\n    {route}\n  </div>\n'
            f'</header>')
    return src[:m.start()] + head + src[m.end():]

def _page_code(slug):
    """Код страны ISO из slug поездки: by-2025-grodno -> BY."""
    return slug.split('-')[0].upper()

def _page_name(slug):
    """Название страницы из PAGES без кода: «77 · Москва · Центр и вода» -> «Москва · Центр и вода»."""
    t = next((pg['title'] for pg in PAGES if pg['slug'] == slug), slug)
    return t.split(' · ', 1)[1] if ' · ' in t else t

def _ref(slug, label):
    return (_page_code(slug), _page_name(slug), f'../{slug}/index.html', label)

def read_next(slug, prev, nxt):
    """Соседи внизу страницы. Порядок: prev/next из PAGES (расставлял автор) -> соседи в той же поездке
    из data/trips.json -> «Следующий отчёт» (ближайший по дате первой поездки в регион, у Москвы и Подмосковья —
    по коду: их в trips.json нет намеренно). Пустое место слева занимает «Все регионы» — только слева,
    чтобы на странице не стояли две одинаковые ссылки подряд."""
    slugs = [pg['slug'] for pg in PAGES]
    if not (prev and nxt):
        for t in TRIPS:
            rs = [r for r in t['regions'] if r in slugs]
            if slug in rs and len(rs) > 1:
                i = rs.index(slug)
                if not prev and i > 0: prev = _ref(rs[i - 1], 'Раньше по маршруту')
                if not nxt and i < len(rs) - 1: nxt = _ref(rs[i + 1], 'Дальше по маршруту')
                break
    aria = 'Соседние поездки по маршруту'
    if not nxt and len(slugs) > 1:
        # «Следующий отчёт» — по году в slug (<iso>-<год>-<тема>), при равенстве по slug
        order = sorted(slugs, key=lambda s: (s.split('-')[1] if s.count('-') >= 2 else '', s))
        i = order.index(slug)
        taken = {prev and prev[2], f'../{slug}/index.html'}
        for k in range(1, len(order)):
            cand = order[(i + k) % len(order)]
            if f'../{cand}/index.html' not in taken:
                nxt = _ref(cand, 'Следующий отчёт'); break
        aria = 'Читать дальше'
    return prev, nxt, aria

def _tail_block(body):
    """Если тело главы кончается блоком оценки (div.verdict) или счёта (dl.bill) — (тело без него, блок).
    Берётся только хвост: ценник посреди главы (Камчатка, «Лава с ценником») остаётся на месте."""
    s = body.rstrip()
    if s.endswith('</dl>'):
        i = s.rfind('<dl class="bill"')
        if i >= 0 and '</dl>' not in s[i:-5]: return s[:i], s[i:]
    if s.endswith('</div>'):
        i = s.rfind('<div class="verdict"')
        if i >= 0:
            depth, k = 0, i                       # в оценке вложенный div — ищем её парный </div>
            for m in re.finditer(r'<div\b|</div>', s[i:]):
                depth += 1 if m.group(0) == '<div' else -1
                if depth == 0: k = i + m.end(); break
            if k == len(s): return s[:i], s[i:]
    return None

def _plain(x):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', x)).strip()

def chapters_and_final(src):
    """Оглавление и финал страницы региона (этап 2). Исходники src/*.html не трогаем: здесь у каждого h2
    появляется якорь g1, g2…, оценка и «Счёт по региону» из хвоста последней главы уходят в отдельный
    section.sec.final, а после вводки (первой секции) встаёт список глав. Возвращает (страница, липкая строка)."""
    secs = list(re.finditer(r'<section class="sec">(.*?)</section>', src, re.S))
    if not secs: return src, ''
    last = secs[-1]
    body, moved = last.group(1), []
    while True:
        t = _tail_block(body)
        if not t: break
        body, blk = t; moved.insert(0, blk)
    final = ''
    if moved:
        final = ('\n\n<section class="sec final" id="final" aria-labelledby="final-h">\n'
                 '  <div class="day final-h" id="final-h">Итого</div>\n  ' + '\n  '.join(moved) + '\n</section>')
        src = src[:last.start()] + f'<section class="sec">{body}\n</section>' + final + src[last.end():]
    n = 0
    def anchor(m):
        nonlocal n
        n += 1
        return f'<h2 id="g{n}">'
    src = re.sub(r'<h2>', anchor, src)
    items = []
    for sm in re.finditer(r'<section class="sec">(.*?)</section>', src, re.S):
        h = re.search(r'<h2 id="(g\d+)">(.*?)</h2>', sm.group(1), re.S)
        if not h: continue
        d = re.search(r'<div class="day">(.*?)</div>', sm.group(1), re.S)
        day = f'<span class="toc-d">{_plain(d.group(1))}</span>' if d else ''
        items.append(f'<li><a href="#{h.group(1)}">{day}<span class="toc-t">{_plain(h.group(2))}</span></a></li>')
    if final:
        items.append('<li><a href="#final"><span class="toc-t">Итого</span></a></li>')
    if len(items) < 2: return src, ''
    toc = ('<section class="sec toc-sec"><nav class="toc" id="toc" aria-label="Главы">\n'
           '  <div class="toc-h">Главы</div>\n  <ol>\n    ' + '\n    '.join(items) + '\n  </ol>\n</nav></section>')
    first = re.search(r'<section class="sec">.*?</section>', src, re.S)
    if 'class="lead"' in first.group(0) and '<h2' not in first.group(0):
        src = src[:first.end()] + '\n\n' + toc + src[first.end():]
    else:
        src = src[:first.start()] + toc + '\n\n' + src[first.start():]
    # строка для телефона: название текущей главы (ссылка к оглавлению) и «наверх»; показывает series.js
    bar = ('<div class="chap-bar" id="chapBar" hidden><a class="cb-t" href="#toc"></a>'
           '<a class="cb-up" href="#top">Наверх ↑</a></div>')
    return src, bar

def region_body(code, prev=None, nxt=None):
    """prev / nxt — соседи ПО МАРШРУТУ ПОЕЗДКИ: (код, название, ссылка, подпись) или None."""
    src = cover_head(inject_data(code, open(os.path.join(ROOT, 'src', f'{code}.html'), encoding='utf-8').read()))
    src, bar = chapters_and_final(src)
    top = ('<nav class="topbar"><a href="../index.html">← Все страны</a>'
           '<div class="topbar-r"><button class="theme-btn" type="button" id="themeBtn" hidden>Тема</button>'
           '<button class="draft-toggle" type="button" id="draftToggle" hidden>Пометки</button></div></nav>')
    prev, nxt, aria = read_next(code, prev, nxt)
    def pl(x, cls):
        if not x:
            return '<a class="%s" href="../index.html"><span>Все страны</span></a>' % cls
        c, name, link, label = x
        txt = f'<span><small>{e(label)}</small>{e(name)}</span>'
        b = code_badge(c)
        return f'<a class="{cls}" href="{e(link)}">' + (b + txt if cls == 'prev' else txt + b) + '</a>'
    pager = f'<nav class="pager" aria-label="{aria}">' + pl(prev, 'prev') + pl(nxt, 'next') + '</nav>'
    return f'<div class="page page-cover">\n{top}\n{bar}\n{src}\n{pager}\n</div>'

def meta_tags(title, desc, path, image):
    """Ссылки для пересылки (Open Graph) и значок. path — адрес страницы от корня сайта: '' или '49-magadan/'."""
    url = SITE + path
    img = SITE + image
    t = [
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{e(url)}">',
        f'<link rel="icon" href="{SITE}favicon.png" type="image/png">',
        f'<link rel="apple-touch-icon" href="{SITE}apple-touch-icon.png">',
        '<meta property="og:type" content="article">' if path else '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{e(SITE_NAME)}">',
        f'<meta property="og:locale" content="ru_RU">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:image" content="{e(img)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(desc)}">',
        f'<meta name="twitter:image" content="{e(img)}">',
    ]
    return '\n'.join(t)

def footer(up, home):
    """Общий подвал. На главной название без ссылки (она и есть главная). Контактов автор не давал —
    если появятся, им место строкой после .ft-who."""
    name = f'<span class="ft-name">{e(SERIES_TITLE)}</span>' if home else f'<a class="ft-name" href="{up}index.html">{e(SERIES_TITLE)}</a>'
    return (f'<footer class="site-foot{" ft-home" if home else ""}" role="contentinfo"><div class="ft-in">'
            f'<div class="ft-t">{name}<p class="ft-who">Сергей Веретенников · отчёты о поездках</p>'
            f'<p class="ft-aim">Заграничные поездки: страна за страной.</p>'
            f'<p class="ft-nav"><a href="{up}{TRIPS_PAGE}/index.html">Поездки</a> · <a href="{up}about/index.html">О проекте</a></p></div>'
            f'<a class="ft-top" href="#top">Наверх ↑</a></div></footer>')

def doc(title, body, depth, inline, reg_color=None, meta=''):
    up = '../' * depth
    if 'class="lost"' not in body:   # на 404 подвала нет: её пути относительные, а открывается она по любому адресу
        body += '\n' + footer(up, 'ix-page' in body)
    style = f'<style>\n{CSS}\n</style>' if inline else f'<link rel="stylesheet" href="{up}series.css?v={VER["css"]}">'
    script = f'<script>\n{JS}\n</script>' if inline else f'<script src="{up}series.js?v={VER["js"]}"></script>'
    extra = f'<style>{reg_color}</style>' if reg_color else ''
    # цвет адресной строки телефона: на главной — синяя шапка, на страницах регионов — фон страницы
    light, dark = ('#1F6FE5', '#2A63C4') if 'ix-page' in body else ('#F1F2EE', '#101315')
    meta += (f'\n<meta name="theme-color" content="{light}" media="(prefers-color-scheme: light)">'
             f'\n<meta name="theme-color" content="{dark}" media="(prefers-color-scheme: dark)">')
    # главный кадр региона браузер начинает качать сразу, не дожидаясь стилей: он — самое крупное на первом экране
    hero = re.search(r'<img fetchpriority="high" ([^>]*)>', body)
    if hero:
        a = dict(re.findall(r'\b(src|srcset|sizes)="([^"]*)"', hero.group(1)))
        meta += (f'\n<link rel="preload" as="image" href="{a["src"]}" fetchpriority="high"'
                 + (f' imagesrcset="{a["srcset"]}" imagesizes="{a["sizes"]}"' if 'srcset' in a else '') + '>')
    if 'ix-page' in body:                      # главная: карта и фильтры
        script += f'\n<script>\n{MAPJS}\n</script>' if inline else f'\n<script src="{up}map.js?v={VER["map"]}"></script>'
    return (f'<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{e(title)}</title>\n{meta}\n{THEME_INIT}\n{fonts(up)}\n{style}\n{extra}\n</head>\n<body id="top">\n{body}\n{script}\n</body>\n</html>\n')

def fragment(title, body):
    """Главная страница артефакта: без doctype/html/head/body."""
    return f'<title>{e(title)}</title>\n<style>\n{CSS}\n</style>\n{body}\n<script>\n{JS}\n</script>\n<script>\n{MAPJS}\n</script>\n'

# Страницы поездок. Чтобы добавить поездку:
#   1) положить текст в src/<slug>.html, медиа — в <slug>/media/ (tools/media.py export);
#   2) добавить запись сюда; 3) в списке D выше добавить стране ссылку 'LOCAL:<slug>/index.html';
#   4) python tools/og.py <slug> и python tools/thumbs.py — обложка для ссылок и миниатюра для главной.
# prev / next — соседи по маршруту поездки: (код, название, ссылка, подпись) или None.
# og — кадр для обложки ссылки (tools/og.py), если главный кадр для неё не годится, например вертикальный; по умолчанию hero.
# color — цвет страницы (CSS-переменные --reg и --reg-ink для светлой темы); None = охра по умолчанию.
PAGES = [
    # две разные поездки в Беларусь — не одна дорога, поэтому соседей по маршруту нет
    dict(slug='by-2023-minsk', title='BY · Беларусь · Минск за день', prev=None, next=None, color=None),
    dict(slug='by-2025-grodno', title='BY · Беларусь · Гродно, Поставы, Несвиж и Мир', prev=None, next=None, color=None),
    # Япония, сентябрь–октябрь 2024: одна поездка кольцом, посты по порядку маршрута (ПОСТЫ.md)
    dict(slug='jp-2024-tokyo', title='JP · Япония · Токио: первые дни и зоопарк', prev=None, next=('JP', 'Никко', '../jp-2024-nikko/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-nikko', title='JP · Япония · Никко', prev=('JP', 'Токио: первые дни и зоопарк', '../jp-2024-tokyo/index.html', 'Раньше по маршруту'), next=('JP', 'Хаконе', '../jp-2024-hakone/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-hakone', title='JP · Япония · Хаконе', prev=('JP', 'Никко', '../jp-2024-nikko/index.html', 'Раньше по маршруту'), next=('JP', 'Путь Накасендо', '../jp-2024-nakasendo/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-nakasendo', title='JP · Япония · Путь Накасендо', prev=('JP', 'Хаконе', '../jp-2024-hakone/index.html', 'Раньше по маршруту'), next=('JP', 'Нагоя', '../jp-2024-nagoya/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-nagoya', title='JP · Япония · Нагоя', prev=('JP', 'Путь Накасендо', '../jp-2024-nakasendo/index.html', 'Раньше по маршруту'), next=('JP', 'Киото', '../jp-2024-kyoto/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-kyoto', title='JP · Япония · Киото', prev=('JP', 'Нагоя', '../jp-2024-nagoya/index.html', 'Раньше по маршруту'), next=('JP', 'Коя-сан', '../jp-2024-koyasan/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-koyasan', title='JP · Япония · Коя-сан', prev=('JP', 'Киото', '../jp-2024-kyoto/index.html', 'Раньше по маршруту'), next=('JP', 'Осака и Нара', '../jp-2024-osaka/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-osaka', title='JP · Япония · Осака и Нара', prev=('JP', 'Коя-сан', '../jp-2024-koyasan/index.html', 'Раньше по маршруту'), next=('JP', 'Снова Токио', '../jp-2024-tokyo-2/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='jp-2024-tokyo-2', title='JP · Япония · Снова Токио', prev=('JP', 'Осака и Нара', '../jp-2024-osaka/index.html', 'Раньше по маршруту'), next=None, color=None),
    # Вьетнам, май 2026, и стыковка в Гуанчжоу — одна поездка (решение автора 06.10.2026)
    dict(slug='vn-2026-nhatrang', title='VN · Вьетнам · Нячанг и Амиана', prev=None, next=('VN', 'VinWonders', '../vn-2026-vinwonders/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='vn-2026-vinwonders', title='VN · Вьетнам · VinWonders', prev=('VN', 'Нячанг и Амиана', '../vn-2026-nhatrang/index.html', 'Раньше по маршруту'), next=('VN', 'Далат', '../vn-2026-dalat/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='vn-2026-dalat', title='VN · Вьетнам · Далат', prev=('VN', 'VinWonders', '../vn-2026-vinwonders/index.html', 'Раньше по маршруту'), next=('VN', 'Дананг', '../vn-2026-danang/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='vn-2026-danang', title='VN · Вьетнам · Дананг', prev=('VN', 'Далат', '../vn-2026-dalat/index.html', 'Раньше по маршруту'), next=('CN', 'Гуанчжоу за день', '../cn-2026-guangzhou/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='cn-2026-guangzhou', title='CN · Китай · Гуанчжоу за день', prev=('VN', 'Дананг', '../vn-2026-danang/index.html', 'Раньше по маршруту'), next=None, color=None),
    # Куба, февраль 2025: база Варадеро, выезды по дням — порядок по датам
    dict(slug='cu-2025-varadero', title='CU · Куба · Варадеро', prev=None, next=('CU', 'Залив Свиней', '../cu-2025-zapata/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='cu-2025-zapata', title='CU · Куба · Залив Свиней', prev=('CU', 'Варадеро', '../cu-2025-varadero/index.html', 'Раньше по маршруту'), next=('CU', 'Гавана', '../cu-2025-havana/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='cu-2025-havana', title='CU · Куба · Гавана', prev=('CU', 'Залив Свиней', '../cu-2025-zapata/index.html', 'Раньше по маршруту'), next=('CU', 'Сьенфуэгос и Тринидад', '../cu-2025-trinidad/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='cu-2025-trinidad', title='CU · Куба · Сьенфуэгос и Тринидад', prev=('CU', 'Гавана', '../cu-2025-havana/index.html', 'Раньше по маршруту'), next=None, color=None),
    # Танзания, 2014: Моши → сафари → Килиманджаро
    dict(slug='tz-2014-moshi', title='TZ · Танзания · Моши, дорога и прочее', prev=None, next=('TZ', 'Сафари', '../tz-2014-safari/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='tz-2014-safari', title='TZ · Танзания · Сафари', prev=('TZ', 'Моши, дорога и прочее', '../tz-2014-moshi/index.html', 'Раньше по маршруту'), next=('TZ', 'Килиманджаро', '../tz-2014-kilimanjaro/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='tz-2014-kilimanjaro', title='TZ · Танзания · Килиманджаро', prev=('TZ', 'Сафари', '../tz-2014-safari/index.html', 'Раньше по маршруту'), next=None, color=None),
    # отдельные поездки
    dict(slug='eg-2015-sharm', title='EG · Египет · Шарм-эль-Шейх 2015', prev=None, next=None, color=None),
    dict(slug='eg-2021-sharm', title='EG · Египет · Шарм-эль-Шейх 2021', prev=None, next=None, color=None),
    dict(slug='eg-2021-cairo', title='EG · Египет · Каир, Гиза и Александрия', prev=None, next=('EG', 'Луксор', '../eg-2021-luxor/index.html', 'Дальше по маршруту'), color=None),
    dict(slug='eg-2021-luxor', title='EG · Египет · Луксор', prev=('EG', 'Каир, Гиза и Александрия', '../eg-2021-cairo/index.html', 'Раньше по маршруту'), next=None, color=None),
    dict(slug='tr-2020-kemer', title='TR · Турция · Кемер', prev=None, next=None, color=None),
    dict(slug='ua-2011-zakarpattia', title='UA · Украина · Закарпатье', prev=None, next=None, color=None),
]

TRIPS = [t for t in (json.load(open(os.path.join(ROOT, 'data', 'trips.json'), encoding='utf-8'))
         if os.path.exists(os.path.join(ROOT, 'data', 'trips.json')) else []) if t.get('regions')]   # пустая поездка = убрана автором

COLORS = json.load(open(os.path.join(ROOT, 'data', 'colors.json'), encoding='utf-8')) if os.path.exists(os.path.join(ROOT, 'data', 'colors.json')) else {}

def region_style(color, slug=None):
    """Свой цвет региона — по главному кадру (tools/regcolor.py -> data/colors.json), если в PAGES не задан явно.
    Пара на каждую тему: в светлой — тёмный цвет с белым текстом, в тёмной — светлый с тёмным текстом.
    Тёмные правила повторяют селекторы series.css, иначе её тёмная тема перебьёт цвет региона."""
    if color:
        return f':root{{--reg:{color[0]};--reg-ink:{color[1]}}}'
    c = COLORS.get(slug)
    if not c: return None
    dark = f'--reg:{c["dark"]};--reg-ink:#14100A'
    return (f':root{{--reg:{c["light"]};--reg-ink:#FFFFFF}}'
            f'@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{dark}}}}}'
            f':root[data-theme="dark"]{{{dark}}}')

# ---------- страницы «Поездки» и «О проекте» (этап 4) ----------
TRANSPORT_WORD = {'plane': 'самолётом', 'train': 'поездом', 'bus': 'автобусом', 'car': 'на машине'}   # other — без подписи: что именно, неизвестно
MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']

def trip_dates(a, b):
    """«19–20 февраля 2022», «24 апреля — 10 мая 2022», «30 декабря 2023 — 2 января 2024»."""
    (y1, m1, d1), (y2, m2, d2) = (tuple(int(x) for x in s.split('-')) for s in (a, b))
    if a == b: return f'{d1} {MONTHS[m1 - 1]} {y1}'
    if y1 != y2: return f'{d1} {MONTHS[m1 - 1]} {y1} — {d2} {MONTHS[m2 - 1]} {y2}'
    if m1 != m2: return f'{d1} {MONTHS[m1 - 1]} — {d2} {MONTHS[m2 - 1]} {y1}'
    return f'{d1}–{d2} {MONTHS[m1 - 1]} {y1}'

def trip_days(a, b):
    import datetime
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days + 1

def _top(up):
    return (f'<nav class="topbar"><a href="{up}index.html">← Все страны</a>'
            '<div class="topbar-r"><button class="theme-btn" type="button" id="themeBtn" hidden>Тема</button></div></nav>')

def trips_body():
    """Все поездки из data/trips.json по годам. Пометка checked — внутренняя, на страницу не выводится."""
    import json
    trips = sorted(TRIPS, key=lambda t: t['start'])   # TRIPS уже без пустых поездок, убранных автором
    tp = os.path.join(ROOT, 'data', 'transport.json')
    trans = json.load(open(tp, encoding='utf-8')) if os.path.exists(tp) else {}
    regs = {_page_code(s) for t in trips for s in t['regions']}
    if not trips:   # data/trips.json ещё пуст: страница-заглушка
        lead = 'Список поездок появится, когда будут готовы первые отчёты.'
        return '\n'.join(['<div class="page tr-page">', _top('../'), '<header class="tr-head"><h1>Поездки</h1>',
                          f'<p class="tr-lead">{e(lead)}</p></header>', '</div>']), lead   # по кодам: у Якутии две страницы (14-yakutia, 14-mirny)
    longest = max(trips, key=lambda t: (trip_days(t['start'], t['end']), t['start']))
    ld = trip_days(longest['start'], longest['end'])
    n = len(trips)
    lead = (f'{n} {plural(n, "поездка", "поездки", "поездок")}, в них '
            f'{len(regs)} {plural(len(regs), "страна", "страны", "стран")}. Самая длинная — {ld} {plural(ld, "день", "дня", "дней")}, '
            f'{trip_dates(longest["start"], longest["end"])}. Поездки — по годам, страны в каждой — по маршруту.')
    out = ['<div class="page tr-page">', _top('../'), '<header class="tr-head"><h1>Поездки</h1>',
           f'<p class="tr-lead">{e(lead)}</p></header>']
    for y in sorted({t['start'][:4] for t in trips}):
        ts = [t for t in trips if t['start'][:4] == y]
        ry = len({_page_code(s) for t in ts for s in t['regions']})
        out.append(f'<section class="tr-year" aria-labelledby="y{y}"><div class="tr-yh"><h2 id="y{y}">{y}</h2>'
                   f'<span>{len(ts)} {plural(len(ts), "поездка", "поездки", "поездок")} · {ry} {plural(ry, "страна", "страны", "стран")}</span></div><ol class="tr-list">')
        for t in ts:
            first = t['regions'][0]
            days, k = trip_days(t['start'], t['end']), len(t['regions'])
            how = TRANSPORT_WORD.get(trans.get(_page_code(first), ''), '')
            how = f' · <span class="tr-how">{how}</span>' if how else ''
            chain = []
            for s in t['regions']:
                c = COLORS.get(s)
                st = f' style="--c:{c["light"]};--cd:{c["dark"]}"' if c else ''
                chain.append(f'<li><a href="../{s}/index.html"{st}>{code_badge(_page_code(s))}'
                             f'<small>{e(_page_name(s))}</small></a></li>')
            th = f'{first}/thumb.webp'
            img = (f'<img class="tr-th" src="../{th}" alt="" width="360" height="270" loading="lazy" decoding="async">'
                   if os.path.exists(os.path.join(ROOT, th)) else '')
            out.append(f'<li class="tr-card">{img}<div class="tr-t"><div class="tr-d">{trip_dates(t["start"], t["end"])}</div>'
                       f'<div class="tr-m">{days} {plural(days, "день", "дня", "дней")} · {k} {plural(k, "страна", "страны", "стран")}{how}</div>'
                       f'<ol class="tr-chain" aria-label="Страны по маршруту">{"".join(chain)}</ol></div></li>')
        out.append('</ol></section>')
    out.append('</div>')
    return '\n'.join(out), lead

ABOUT = [
    'Заграничные поездки: страна за страной, по частям света.',   # цель серии автор ещё не формулировал (06.10.2026)
    'По каждой поездке — отчёт в одном формате: главный кадр, несколько фактов, дни поездки с фотографиями '
    'и короткими подписями, оценка и «счёт по поездке» — цифры этой поездки, серьёзные вперемешку с дурацкими. '
    'Рядом с названием страны — её флаг и код ISO.',
    'Фотографии и видео — мои, если не подписано иначе. Цены — из чеков и ценников, время — из снимков. Чего не знаю — не пишу.',
    'Автор — Сергей Веретенников. Сайт собран из статических страниц и живёт на GitHub Pages.',
]

def about_body():
    ps = '\n'.join(f'<p>{e(p)}</p>' for p in ABOUT)
    return (f'<div class="page ab-page">\n{_top("../")}\n<article class="ab-text"><h1>О проекте</h1>\n{ps}\n'
            '<!-- Контакты: автор их пока не давал. Появятся — строкой здесь, например <p>Написать: …</p> -->\n'
            f'<p class="ab-links"><a href="../index.html">Все страны</a> · <a href="../{TRIPS_PAGE}/index.html">Поездки</a></p>'
            '\n</article>\n</div>'), ABOUT[0]

def write_extra_pages():
    for slug, title, fn in ((TRIPS_PAGE, 'Поездки', trips_body), ('about', 'О проекте', about_body)):
        body, desc = fn()
        full = f'{title} · {SITE_NAME}'
        os.makedirs(os.path.join(ROOT, slug), exist_ok=True)
        open(os.path.join(ROOT, slug, 'index.html'), 'w', encoding='utf-8').write(
            doc(full, body, 1, False, None, meta_tags(full, desc, slug + '/', 'og.jpg')))
        print('готово:', slug + '/index.html')

def write_service_files():
    """404.html, sitemap.xml, robots.txt. На странице 404 пути абсолютные: она открывается по любому адресу."""
    base = '/' + SITE.split('/', 3)[3]
    page = (f'<div class="page"><div class="lost">'
            f'<span class="code">404</span><h1>Такой страницы нет</h1>'
            f'<p>Адрес мог устареть или в нём опечатка. Отчёты о поездках собраны на главной.</p>'
            f'<p><a href="{base}">← Все страны</a></p></div></div>')
    h = doc('Страница не найдена', page, 0, False, None, f'<link rel="icon" href="{base}favicon.png" type="image/png">\n<meta name="robots" content="noindex">')
    h = (h.replace('href="series.css', f'href="{base}series.css').replace('src="series.js', f'src="{base}series.js')
          .replace('href="fonts/', f'href="{base}fonts/'))
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(h)
    urls = [SITE, SITE + TRIPS_PAGE + '/', SITE + 'about/'] + [SITE + pg['slug'] + '/' for pg in PAGES if has_src(pg['slug'])]
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8').write(f'User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n')

def has_src(slug):
    return os.path.exists(os.path.join(ROOT, 'src', slug + '.html'))

def build(artifact=False):
    """Без аргументов собирает страницы на месте: index.html и <slug>/index.html рядом со скриптом.
    С ключом --artifact дополнительно кладёт в _artifact/ вариант со вшитыми стилями (для предпросмотра)."""
    local = VIDEO_BASE != VIDEO_SITE            # --local-video: пишем только index.local.html, страницы сайта не трогаем
    page_name = 'index.local.html' if local else 'index.html'
    ix = index_body()
    if artifact and not local:
        os.makedirs(os.path.join(ROOT, '_artifact'), exist_ok=True)
        open(os.path.join(ROOT, '_artifact', 'page.html'), 'w', encoding='utf-8').write(fragment(SERIES_TITLE, ix))
    if not local:
        open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(
            doc(SERIES_TITLE, ix, 0, False, None, meta_tags(SERIES_TITLE, INDEX_DESC, '', 'og.jpg')))
    for pg in PAGES:
        if not has_src(pg['slug']):
            print(f'пропуск: {pg["slug"]} — нет src/{pg["slug"]}.html')
            continue
        body = region_body(pg['slug'], pg['prev'], pg['next'])
        src = open(os.path.join(ROOT, 'src', pg['slug'] + '.html'), encoding='utf-8').read()
        m = re.search(r'<p class="hook">(.*?)</p>', src, re.S)
        desc = re.sub(r'<.*?>', '', m.group(1)).strip() if m else INDEX_DESC
        pg_meta = meta_tags(pg['title'] + ' · ' + SITE_NAME, desc, pg['slug'] + '/', pg['slug'] + '/og.jpg')
        os.makedirs(os.path.join(ROOT, pg['slug']), exist_ok=True)
        open(os.path.join(ROOT, pg['slug'], page_name), 'w', encoding='utf-8').write(
            doc(pg['title'], body, 1, False, region_style(pg['color'], pg['slug']), pg_meta))
        if artifact and not local:
            out = os.path.join(ROOT, '_artifact', pg['slug']); os.makedirs(out, exist_ok=True)
            open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(
                doc(pg['title'], body, 1, True, region_style(pg['color'], pg['slug'])))
        print('готово:', pg['slug'] + '/' + page_name)
    if not local:
        write_extra_pages()
        write_service_files()
        print('готово: index.html')
    return check_video()


def check_video():
    """Сверка: у каждого ролика, на который ссылается страница, есть файл в <slug>/media/ (ролики лежат рядом с фото,
    решение автора 06.10.2026). Страница без ролика — пустой чёрный прямоугольник на сайте."""
    used = sorted(set(VIDEO_USED))
    missing = [f'{s}/media/{n}' for s, n in used
               if not os.path.isfile(os.path.join(ROOT, s, 'media', n)) or os.path.getsize(os.path.join(ROOT, s, 'media', n)) == 0]
    if missing:
        print(f'ОШИБКА: {len(missing)} роликов нет в media/: ' + ', '.join(missing[:8]) + (' …' if len(missing) > 8 else ''))
        print('Выгрузите их (python tools/media.py export <slug> --video-only) или уберите со страницы.')
        return False
    print(f'ролики: {len(used)} ссылок, все файлы на месте в media/')
    return True


if __name__ == '__main__':
    import sys
    if '--local-video' in sys.argv:
        VIDEO_BASE = ''   # ролики и так рядом с фото; ключ оставлен для совместимости с ПОРЯДОК.md
    if '--daymap-old' in sys.argv:   # прежняя карта мест вместо схемы точек съёмки
        DAYMAP_MODE = None
    ok = build('--artifact' in sys.argv)
    if not ok and '--allow-missing-video' not in sys.argv:
        sys.exit(1)
