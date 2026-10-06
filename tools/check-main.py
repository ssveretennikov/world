# ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.
# Проверка главной страницы без сервера (Playwright + Chromium), после python build.py:
#   python tools/check-main.py
# Что проверяется: карта нарисована (89 регионов); фильтр округа и года прячет лишние строки и ленту «Любимые»;
# поиск находит регион и прячет ленту, сброс возвращает её; «Посмотреть маршрут» запускается и останавливается;
# все ссылки карточек ленты и строк списка ведут на существующие страницы; горизонтальной прокрутки нет.
import os, sys
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
fails = []

def check(cond, what):
    print(('ок    ' if cond else 'ОШИБКА') + ' — ' + what)
    if not cond: fails.append(what)

def run(page, width):
    page.set_viewport_size({'width': width, 'height': 900})
    page.goto('file:///' + INDEX.replace('\\', '/'))
    page.wait_for_timeout(500)
    visible = lambda sel: page.evaluate('s => [...document.querySelectorAll(s)].filter(e => !e.closest("[hidden]")).length', sel)
    fav_shown = lambda: page.evaluate('!document.getElementById("fav").hidden')
    print(f'--- окно {width} px')
    check(page.evaluate('document.querySelectorAll(".rumap path[data-code]").length') == 89, 'на карте 89 регионов')
    check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'нет горизонтальной прокрутки')
    check(fav_shown(), 'лента «Любимые» видна при загрузке')
    check(page.evaluate('document.querySelectorAll("#favRow .fc").length') >= 1, 'в ленте есть карточки')
    check(page.evaluate('document.querySelector(".hrt-key")') is None, 'подписи «❤ — понравилось» нет')
    check(page.evaluate('document.querySelectorAll(".reg .hrt[title]").length') == 0, 'у сердечек нет всплывающей подсказки')
    check(page.evaluate('[...document.querySelectorAll("section.fo")].pop().classList.contains("ahead")'), 'блок «Впереди» — последний')
    check(page.evaluate('document.querySelectorAll(".fo:not(.ahead) .reg .hk").length') == visible('.fo:not(.ahead) .reg'),
          'у каждой строки списка есть крючок')
    # фильтр округа
    page.click('.chip[data-k="fo"][data-v="dv"]'); page.wait_for_timeout(100)
    check(visible('li.reg[data-code]') == visible('li.reg[data-fo="dv"]') and visible('li.reg[data-fo="dv"]') > 0, 'фильтр округа: видны только строки ДВФО')
    check(not fav_shown(), 'фильтр округа: лента скрыта')
    page.click('.chip[data-k="fo"][data-v=""]'); page.wait_for_timeout(100)
    check(fav_shown(), 'сброс округа: лента вернулась')
    # фильтр года
    page.click('.ychip[data-v="2025"]'); page.wait_for_timeout(100)
    check(visible('li.reg[data-code]') == visible('li.reg[data-year="2025"]') and visible('li.reg[data-year="2025"]') > 0, 'фильтр года по легенде: видны только строки 2025')
    check(not fav_shown(), 'фильтр года: лента скрыта')
    page.click('.ychip[data-v="2025"]'); page.wait_for_timeout(100)
    check(fav_shown(), 'повторное нажатие года: лента вернулась')
    # поиск
    page.fill('#find', 'магадан'); page.wait_for_timeout(100)
    check(visible('li.reg[data-code]') == 1 and visible('li.reg[data-code="49"]') == 1, 'поиск «магадан» находит один регион — 49')
    check(not fav_shown(), 'поиск: лента скрыта')
    page.fill('#find', ''); page.wait_for_timeout(100)
    check(fav_shown() and visible('li.reg[data-code]') == 89, 'сброс поиска: лента вернулась, все 89 строк на месте')
    # «Посмотреть маршрут»
    page.click('#play'); page.wait_for_timeout(300)
    check(page.evaluate('document.getElementById("play").classList.contains("playing")'), '«Посмотреть маршрут» запустился')
    check(not page.evaluate('document.getElementById("mapdate").hidden'), 'над картой показана дата')
    check(not fav_shown(), 'хронология: лента скрыта')
    page.click('#play'); page.wait_for_timeout(100)
    check(not page.evaluate('document.getElementById("play").classList.contains("playing")'), '«Посмотреть маршрут» остановился')
    page.click('#tall'); page.wait_for_timeout(100)
    check(fav_shown(), '«Показать весь период»: лента вернулась')
    # ссылки
    hrefs = page.evaluate('[...document.querySelectorAll(".fc a, .reg a")].map(a => a.getAttribute("href"))')
    missing = sorted({h for h in hrefs if not os.path.exists(os.path.join(ROOT, unquote(h)))})
    check(not missing, f'все {len(hrefs)} ссылок карточек и строк ведут на существующие страницы' + (f': нет {missing}' if missing else ''))
    imgs = page.evaluate('[...document.querySelectorAll(".fc img, img.th")].map(i => i.getAttribute("src"))')
    missing = sorted({s for s in imgs if not os.path.exists(os.path.join(ROOT, s))})
    check(not missing, f'все {len(imgs)} картинок карточек и миниатюр есть на диске' + (f': нет {missing}' if missing else ''))

def phone(b):
    # телефон с касаниями: «Европейская часть» увеличивает карту, касание Московской области открывает карточку
    ctx = b.new_context(viewport={'width': 375, 'height': 812}, has_touch=True, is_mobile=True, device_scale_factor=1)
    page = ctx.new_page()
    page.goto('file:///' + INDEX.replace('\\', '/')); page.wait_for_timeout(500)
    print('--- телефон 375 px, касания')
    size = lambda: page.evaluate('''(() => { const r = document.querySelector('.rumap path[data-code="50"]').getBoundingClientRect(); return Math.min(r.width, r.height); })()''')
    before = size()
    page.click('#zoom'); page.wait_for_timeout(600)
    after = size()
    check(after >= 24 and after / before >= 2.5, f'«Европейская часть»: Московская область {before:.0f} → {after:.0f} px')
    page.locator('.rumap path[data-code="50"]').scroll_into_view_if_needed(); page.wait_for_timeout(200)
    box = page.evaluate('''(() => { const r = document.querySelector('.rumap path[data-code="50"]').getBoundingClientRect(); 
        // посередине области — Москва, поэтому ищем точку, где сверху именно Подмосковье
        for (let fy = .3; fy <= .7; fy += .05) for (let fx = .2; fx <= .8; fx += .05) {
          const x = r.x + r.width * fx, y = r.y + r.height * fy, el = document.elementFromPoint(x, y);
          if (el && el.dataset && el.dataset.code === '50') return [x, y];
        }
        return [r.x + r.width / 2, r.y + r.height / 2]; })()''')
    page.touchscreen.tap(box[0], box[1]); page.wait_for_timeout(300)
    check(page.evaluate('(document.querySelector("#mcard .code") || {}).textContent') == '50', 'касание Московской области после увеличения: карточка с кодом 50')
    page.click('#zoom'); page.wait_for_timeout(600)
    check(abs(size() - before) < 1, '«Вся страна» возвращает карту целиком')
    ctx.close()

def player(page):
    # проигрыватель проходит все поездки и сам останавливается на полной карте
    n = page.evaluate('JSON.parse(document.getElementById("karta").dataset.trips).length')
    import json as _j, os as _o
    want = sum(1 for t in _j.load(open(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))), 'data', 'trips.json'), encoding='utf-8')) if t.get('regions'))
    check(n == want, f'шагов «Поездок по порядку» — поездок: {n} (в data/trips.json непустых {want})')
    page.click('#play'); page.wait_for_timeout(200)
    check(page.evaluate('document.getElementById("track").value') == '0', 'проигрыватель начал с первой поездки')
    trips = [t for t in _j.load(open(_o.path.join(ROOT, 'data', 'trips.json'), encoding='utf-8')) if t.get('regions')]
    page.click('#play'); page.wait_for_timeout(100)          # пауза
    page.click('#tnext'); page.click('#tnext'); page.wait_for_timeout(100)   # стрелками на шаг 3
    k = len(trips[2]['regions'])
    check('Поездка 3 из' in page.evaluate('document.getElementById("tdate").textContent'), 'шаг 3: подпись «Поездка 3 из …»')
    check(page.evaluate('document.querySelectorAll("#tchain a.st").length') == k, f'шаг 3: в цепочке {k} ссылок-плашек')
    check(page.evaluate('document.querySelector(".tl-read a.more, #mcard a")') is None, 'шаг 3: отдельной кнопки «открыть отчёт» нет')
    page.click('#tprev'); page.wait_for_timeout(100)
    check('Поездка 2 из' in page.evaluate('document.getElementById("tdate").textContent'), 'стрелка ‹: подпись «Поездка 2 из …»')
    page.evaluate('(() => { const t = document.getElementById("track"); t.value = 0; t.dispatchEvent(new Event("input")); })()')
    page.click('#play'); page.wait_for_timeout(200)
    page.wait_for_timeout(n * 1500 + 1500)
    check(not page.evaluate('document.getElementById("play").classList.contains("playing")')
          and page.evaluate('document.getElementById("track").value') == str(n), 'проигрыватель прошёл все поездки и остановился')
    check(page.evaluate('document.getElementById("tdate").textContent') == 'Все поездки'
          and page.evaluate('document.getElementById("tchain").hidden'), 'после последней поездки — «Все поездки»')

with sync_playwright() as p:
    b = p.chromium.launch(args=['--allow-file-access-from-files'])
    ctx = b.new_context(device_scale_factor=1)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    for w in (375, 1440):
        run(page, w)
    player(page)
    phone(b)
    check(not errors, 'ошибок скрипта на странице нет' + (f': {errors[:3]}' if errors else ''))
    b.close()
print('\nИТОГ:', 'всё в порядке' if not fails else f'ошибок {len(fails)}')
sys.exit(1 if fails else 0)
