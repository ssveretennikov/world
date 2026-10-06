# ТРЕБУЕТ АДАПТАЦИИ К СТРАНАМ (перенесено из «России» 06.10.2026 как есть): завязано на коды субъектов РФ, регионы и их контуры.
# Сколько весит страница при открытии на телефоне и на компьютере (Playwright + Chromium), после python build.py:
#   python tools/weigh.py [страница …] [--json=файл]
# Страница — slug региона (39-kaliningrad) или «index» для главной; без аргументов — 39-kaliningrad, 24-krasnoyarsk, index.
# Страница прокручивается до конца (чтобы сработала ленивая загрузка), байты складываются по типам ресурсов.
# Ролики с сайта world-video тоже считаются: браузер тянет их начало, если preload это разрешает.
# --json — записать итог в файл, чтобы потом сравнить «до» и «после»: python tools/weigh.py --compare=до.json
import json, os, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICES = {'телефон': dict(viewport={'width': 375, 'height': 812}, device_scale_factor=2, is_mobile=True, has_touch=True),
           'компьютер': dict(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)}
KINDS = ('image', 'font', 'media', 'document', 'stylesheet', 'script', 'other')

def weigh(page_name, dev, p):
    path = os.path.join(ROOT, 'index.html' if page_name == 'index' else os.path.join(page_name, 'index.html'))
    b = p.chromium.launch(args=['--allow-file-access-from-files'])
    ctx = b.new_context(**DEVICES[dev]); page = ctx.new_page()
    got = {}
    def on_resp(r):
        try: n = len(r.body())
        except Exception:
            n = int(r.headers.get('content-length') or 0)   # ролик частями (206) тело не отдаёт
        k = r.request.resource_type
        k = k if k in KINDS else 'other'
        got[r.url] = (k, max(n, got.get(r.url, (k, 0))[1]))
    page.on('response', on_resp)
    page.goto('file:///' + path.replace('\\', '/'), wait_until='load')
    h = page.evaluate('document.documentElement.scrollHeight')
    y = 0
    while y < h:          # шагами по экрану: ленивые картинки грузятся только у края окна
        y += 700; page.evaluate(f'window.scrollTo(0,{y})'); page.wait_for_timeout(120)
        h = page.evaluate('document.documentElement.scrollHeight')
    page.wait_for_timeout(1500)
    b.close()
    out = {k: 0 for k in KINDS}
    for k, n in got.values(): out[k] += n
    return out

def table(res, base=None):
    print(f'{"страница":<16}{"экран":<11}' + ''.join(f'{k:>11}' for k in ('image', 'font', 'media')) + f'{"всего, МБ":>12}' + ('    было' if base else ''))
    for key, v in res.items():
        pg, dev = key.split('|')
        tot = sum(v.values()) / 2**20
        old = f'{sum(base[key].values()) / 2**20:>8.2f}' if base and key in base else ''
        print(f'{pg:<16}{dev:<11}' + ''.join(f'{v[k] / 2**20:>10.2f}М' for k in ('image', 'font', 'media')) + f'{tot:>12.2f}' + old)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')] or ['39-kaliningrad', '24-krasnoyarsk', 'index']
    opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    res = {}
    with sync_playwright() as p:
        for pg in args:
            for dev in DEVICES: res[f'{pg}|{dev}'] = weigh(pg, dev, p)
    base = json.load(open(opt['compare'], encoding='utf-8')) if 'compare' in opt else None
    table(res, base)
    if 'json' in opt: json.dump(res, open(opt['json'], 'w', encoding='utf-8'), ensure_ascii=False)
