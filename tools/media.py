#!/usr/bin/env python3
"""Работа с фото- и видеоархивом региона. Модель не тратит токены на то, что умеет скрипт.

  python tools/media.py check
  python tools/media.py inventory 49-magadan            # миниатюры, контактные листы, timeline.md
  python tools/media.py detail 49-magadan P159 P731 --size 1700
  python tools/media.py detail 49-magadan P622 P623 P002 --sheet cand1   # лист кандидатов 4 в ряд
  python tools/media.py vstrip 49-magadan V46 --n 10    # раскадровка видео, чтобы выбрать фрагмент
  python tools/media.py cands 49-magadan                # все фото из candidates.md листами по 5 в ряд -> work/detail/cands-01.jpg…
  python tools/media.py export 49-magadan               # по selection.tsv -> <регион>/media/ (фото в WebP), ролики -> world-video/<регион>/
  python tools/media.py export 49-magadan --video-only  # заново выгрузить только ролики
  # кадр из видео как фото: строка selection.tsv «hero<TAB>V05<TAB>2200<TAB>frame=10» (секунда)
  python tools/media.py webp 49-magadan                 # перевести уже выгруженные JPEG в WebP

Источник архива: trips/<поездка>/source.txt, по одному пути к папке в строке.
Нужны: Python 3.10+, Pillow (pip install pillow pillow-heif), ffmpeg и ffprobe в PATH.
"""
import argparse, json, os, re, shutil, subprocess, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC = True
except Exception:
    HEIC = False

ROOT = Path(__file__).resolve().parent.parent
PHOTO_EXT = {'.jpg', '.jpeg', '.png'} | ({'.heic'} if HEIC else set())
VIDEO_EXT = {'.mp4', '.mov', '.m4v'}
MOBILE_W = 1080      # ширина копии фото для телефона (*.m.webp)
WEBP_Q = 76          # качество фото на сайте; на глаз не отличить от JPEG 80, файлы легче примерно на 25–30%
# Ролики лежат не на основном сайте, а в отдельном репозитории world-video (папка рядом со скриптами, в git основного
# сайта не идёт): GitHub Pages даёт 1 ГБ на сайт, а одно видео весит почти столько же. Обложки роликов остаются в <регион>/media/.
VIDEO_DIR = None     # ролики лежат рядом с фото в <slug>/media/ (решение автора 06.10.2026), отдельного репозитория нет
VIDEO_CRF = '28'     # было 26: при 28 и медленном пресете ролики легче примерно на четверть (решение автора 06.10.2026; замер 06.10: 76% прежнего веса)
VIDEO_PRESET = 'slow'
TONEMAP = ('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,'
           'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')
FALLBACK = 'format=yuv420p,eq=contrast=1.5:saturation=1.4:brightness=-0.05'


def rdir(region): return ROOT / 'trips' / region
def wdir(region, *sub):
    p = rdir(region) / 'work' / Path(*sub); p.mkdir(parents=True, exist_ok=True); return p


def sources(region):
    f = rdir(region) / 'source.txt'
    if not f.exists(): sys.exit(f'Нет файла {f}: впишите в него путь к папке с архивом.')
    out = [Path(l.strip()) for l in f.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]
    for p in out:
        if not p.is_dir(): sys.exit(f'Папка не найдена: {p}')
    return out


def font(size):
    for name in ('DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf', 'arial.ttf'):
        try: return ImageFont.truetype(name, size)
        except Exception: pass
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    try: return ImageFont.load_default(size)
    except TypeError: return ImageFont.load_default()


def scan(region):
    """Все файлы архива в стабильном порядке: сначала корень, потом подпапки, внутри по имени."""
    photos, videos = [], []
    for si, src in enumerate(sources(region)):
        files = sorted((p for p in src.rglob('*') if p.is_file()),
                       key=lambda p: (len(p.relative_to(src).parts), str(p.relative_to(src)).lower()))
        for p in files:
            rel = str(p.relative_to(src)).replace('\\', '/')
            if any(part.startswith('.') for part in p.relative_to(src).parts[:-1]): continue   # подпапки с «_» не пропускаем: в Танзании «_ разобрать» нужна автору (06.10.2026)
            ext = p.suffix.lower()
            if ext in PHOTO_EXT: photos.append((si, rel, str(p)))
            elif ext in VIDEO_EXT: videos.append((si, rel, str(p)))
    return photos, videos


def name_time(name):
    m = re.search(r'(20\d\d)[-_]?(\d\d)[-_]?(\d\d)[ _-]+(\d\d)[-_:]?(\d\d)[-_:]?(\d\d)', name)
    return f'{m[1]}-{m[2]}-{m[3]} {m[4]}:{m[5]}:{m[6]}' if m else ''


def _gps(ex):
    try:
        g = ex.get_ifd(0x8825)
        def c(v, r):
            d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
            return -d if r in ('S', 'W') else d
        return round(c(g[2], g[1]), 5), round(c(g[4], g[3]), 5), round(float(g.get(6, 0)))
    except Exception:
        return '', '', ''


def _thumb(job):
    pid, path, dst = job
    try:
        im = Image.open(path); ex = im.getexif()
        dt = str(ex.get_ifd(0x8769).get(0x9003) or '')
        dt = (dt[:10].replace(':', '-') + dt[10:]) if dt else name_time(os.path.basename(path))
        lat, lon, alt = _gps(ex); w, h = im.size; model = str(ex.get(0x110) or '')
        if not os.path.exists(dst):
            im.draft('RGB', (640, 640)); im = ImageOps.exif_transpose(im); im.thumbnail((360, 360))
            im.convert('RGB').save(dst, quality=80)
        return pid, dt, lat, lon, alt, w, h, model, ''
    except Exception as e:
        return pid, name_time(os.path.basename(path)), '', '', '', '', '', '', str(e)[:80]


def sheet(items, dst, cols, cell, label_h=26, fsize=19):
    """items: [(подпись, путь к картинке)]"""
    rows = (len(items) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cell, rows * (cell + label_h)), (20, 20, 20)); d = ImageDraw.Draw(sh); f = font(fsize)
    for k, (lab, path) in enumerate(items):
        x, y = (k % cols) * cell, (k // cols) * (cell + label_h)
        try:
            im = Image.open(path).convert('RGB'); im.thumbnail((cell, cell))
            sh.paste(im, (x + (cell - im.width) // 2, y + label_h + (cell - im.height) // 2))
        except Exception: pass
        d.text((x + 4, y + 2), lab, fill=(255, 230, 80), font=f)
    sh.save(dst, quality=82)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'format=duration,size:format_tags=creation_time:stream=codec_type,width,height,codec_name,r_frame_rate,color_transfer',
                        '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}'); v = next((s for s in j.get('streams', []) if s.get('width')), {})
    audio = any(s.get('codec_type') == 'audio' for s in j.get('streams', []))
    ct = (j.get('format', {}).get('tags', {}) or {}).get('creation_time', '')   # 2022-07-06T14:47:10.000000Z (UTC)
    return dict(dur=float(j.get('format', {}).get('duration', 0) or 0), size=int(j.get('format', {}).get('size', 0) or 0),
                w=v.get('width', 0), h=v.get('height', 0), hdr=v.get('color_transfer') in ('smpte2084', 'arib-std-b67'), audio=audio,
                taken=ct[:19].replace('T', ' ') if len(ct) >= 19 else '')


def ff(args):
    return subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, capture_output=True, text=True)


def frame(path, t, dst, width, hdr):
    """Один кадр; для HDR пробует тонмаппинг, при неудаче — простую коррекцию."""
    base = ['-ss', f'{t:.2f}', '-i', path, '-frames:v', '1', '-q:v', '4']
    sc = f"scale='if(gt(iw,ih),{width},-2)':'if(gt(iw,ih),-2,{width})'"
    for vf in ([f'{sc},{TONEMAP}', f'{sc},{FALLBACK}'] if hdr else [sc]):
        ff(base + ['-vf', vf, dst])
        if os.path.exists(dst) and os.path.getsize(dst) > 0: return True
    return False


def _vframes(job):
    vid, path, out = job
    info = probe(path)
    for i, fr in enumerate((0.15, 0.5, 0.85)):
        dst = os.path.join(out, f'{vid}_{i}.jpg')
        if not os.path.exists(dst):
            # Кадры для листа — через frame(): с тонмаппингом HDR, иначе ролики с телефона выходят на листе чёрными
            # (Нагоя, Хаконе — поймано 06.10.2026). Короткий ролик (1–2 с) без ключевого кадра у метки — берём с начала.
            if not frame(path, info['dur'] * fr, dst, 360, info['hdr']):
                frame(path, 0, dst, 360, info['hdr'])
    return vid, info


def cmd_check(a):
    ok = True
    for tool in ('ffmpeg', 'ffprobe'):
        found = shutil.which(tool); ok &= bool(found); print(f'{tool}: {found or "НЕ НАЙДЕН — установите и добавьте в PATH"}')
    import PIL; print('Pillow:', PIL.__version__, '| HEIC:', 'да' if HEIC else 'нет (pip install pillow-heif)')
    r = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True).stdout if shutil.which('ffmpeg') else ''
    print('тонмаппинг HDR-видео (zscale):', 'да' if ' zscale ' in r else 'нет — будет простая коррекция цвета')
    sys.exit(0 if ok else 1)


def cmd_inventory(a):
    photos, videos = scan(a.region); th = wdir(a.region, 'thumbs'); sh = wdir(a.region, 'sheets'); vf = wdir(a.region, 'vframes')
    # Номера P… и V… держат selection.tsv, досье и id на готовых страницах. Если архив с тех пор переставили или пополнили
    # (так случилось с Краснодаром и Камчаткой при переезде папок 06.10.2026), новая нумерация молча указала бы на чужие кадры.
    if not getattr(a, 'force', False):
        for name, items, pref in (('index.tsv', photos, 'P'), ('vindex.tsv', videos, 'V')):
            f = rdir(a.region) / name
            if not f.exists(): continue
            old = [l.split('\t')[1] for l in f.read_text(encoding='utf-8').splitlines()[1:] if '\t' in l]
            new = [rel for _, rel, _ in items]
            if old != new[:len(old)]:
                k = next((i for i, (x, y) in enumerate(zip(old, new)) if x != y), min(len(old), len(new)))
                sys.exit(f'{name} уже есть, и новая нумерация разошлась бы со старой начиная с {pref}{k + 1:03d}: '
                         f'папки архива переставлены или пополнены. Перезапись сломает отбор, досье и страницы. Если это осознанно — --force.')
    jobs = [(f'P{i + 1:03d}', path, str(th / f'P{i + 1:03d}.jpg')) for i, (_, rel, path) in enumerate(photos)]
    with ProcessPoolExecutor(a.jobs) as ex: meta = list(ex.map(_thumb, jobs, chunksize=4))
    rows = []
    for (si, rel, path), m in zip(photos, meta):
        rows.append([m[0], rel, m[1], *map(str, m[2:9])])
    (rdir(a.region) / 'index.tsv').write_text('id\tfile\ttaken\tlat\tlon\talt\tw\th\tcamera\terror\n' +
                                               '\n'.join('\t'.join(r) for r in rows), encoding='utf-8')
    for p in range(0, len(rows), 30):
        items = []
        for r in rows[p:p + 30]:
            sub = r[1].rsplit('/', 1)[0][:10] + ' ' if '/' in r[1] else ''
            items.append((f'{r[0]} {sub}{r[2][8:10]}.{r[2][5:7]} {r[2][11:16]}' if r[2] else f'{r[0]} {sub}', str(th / f'{r[0]}.jpg')))
        sheet(items, sh / f'p{p // 30 + 1:02d}.jpg', 6, 360)
    vjobs = [(f'V{i + 1:02d}', path, str(vf)) for i, (_, rel, path) in enumerate(videos)]
    with ProcessPoolExecutor(max(1, a.jobs - 1)) as ex: vmeta = dict(ex.map(_vframes, vjobs))
    # время видео без даты: по ближайшему по номеру фото в той же папке (нумерация камеры сквозная), помечается «≈»
    def num(rel):
        mm = re.match(r'(\d+)', os.path.basename(rel)); return int(mm[1]) if mm else None
    bynum = {}
    for r in rows:
        n = num(r[1])
        if n is not None and r[2]: bynum.setdefault(r[1].rsplit('/', 1)[0] if '/' in r[1] else '', []).append((n, r[2]))
    def near_time(rel):
        n = num(rel); cand = bynum.get(rel.rsplit('/', 1)[0] if '/' in rel else '', [])
        if n is None or not cand: return ''
        return '≈' + min(cand, key=lambda c: abs(c[0] - n))[1]
    vrows = []
    for i, (si, rel, path) in enumerate(videos):
        vid = f'V{i + 1:02d}'; m = vmeta[vid]
        tk = name_time(os.path.basename(rel)) or m.get('taken', '') or near_time(rel)
        vrows.append([vid, rel, tk, f'{m["dur"]:.1f}', f'{m["w"]}x{m["h"]}', 'hdr' if m['hdr'] else '', str(m['size'] // 2 ** 20)])
    (rdir(a.region) / 'vindex.tsv').write_text('id\tfile\ttaken\tseconds\tsize\thdr\tmb\n' + '\n'.join('\t'.join(r) for r in vrows), encoding='utf-8')
    for old in sh.glob('v*.jpg'): old.unlink()
    f = font(18)
    for p in range(0, len(vrows), 12):
        chunk = vrows[p:p + 12]; W = 360; L = 26
        im = Image.new('RGB', (6 * W, ((len(chunk) + 1) // 2) * (W + L)), (20, 20, 20)); d = ImageDraw.Draw(im)
        for k, r in enumerate(chunk):
            col, row = (k % 2) * 3, k // 2
            t = r[2].lstrip('≈'); ap = '≈' if r[2].startswith('≈') else ''
            d.text((col * W + 4, row * (W + L) + 3), f'{r[0]} {ap}{t[8:10]}.{t[5:7]} {t[11:16]} {float(r[3]):.0f}s {r[4]}', fill=(255, 230, 80), font=f)
            for i in range(3):
                fp = vf / f'{r[0]}_{i}.jpg'
                if fp.exists():
                    t = Image.open(fp); im.paste(t, ((col + i) * W + (W - t.width) // 2, row * (W + L) + L + (W - t.height) // 2))
        im.save(sh / f'v{p // 12 + 1:02d}.jpg', quality=82)
    # timeline.md: по дням, с точками, где менялось место
    days = {}
    for r in rows:
        if r[2]: days.setdefault(r[2][:10], []).append(r)
    tl = [f'# Хронология архива: {a.region}', '', f'Фото: {len(rows)}, видео: {len(vrows)}. Листы: work/sheets/ (p01… фото, v01… видео).', '']
    subs = sorted({r[1].rsplit('/', 1)[0] for r in rows + vrows if '/' in r[1]})
    if subs: tl += ['Подпапки (часто чужие кадры — проверить авторство): ' + '; '.join(subs), '']
    if any(v[2].startswith('≈') for v in vrows):
        tl += ['Время видео со знаком ≈ взято у ближайшего по номеру фото (в файле видео даты нет); точность — минуты.', '']
    elif any(not name_time(os.path.basename(v[1])) and v[2] for v in vrows):
        tl += ['Время видео взято из метаданных файла: оно может быть в UTC и отличаться от времени фото на часовой пояс.', '']
    for day in sorted(days):
        rs = sorted(days[day], key=lambda r: r[2]); tl.append(f'## {day} — {len(rs)} фото, {rs[0][2][11:16]}–{rs[-1][2][11:16]} ({rs[0][0]}…{rs[-1][0]})')
        last = None
        for r in rs:
            if not r[3]: continue
            key = (round(float(r[3]), 2), round(float(r[4]), 2))
            if key != last: tl.append(f'- {r[2][11:16]} {r[0]} — {r[3]}, {r[4]}, высота {r[5]} м'); last = key
        vs = [v for v in vrows if v[2].lstrip('≈')[:10] == day]
        if vs: tl.append('- видео: ' + ', '.join(f'{v[0]} {"≈" if v[2].startswith("≈") else ""}{v[2].lstrip("≈")[11:16]} {float(v[3]):.0f}с' for v in vs))
        tl.append('')
    nodate = [r[0] for r in rows if not r[2]]
    if nodate: tl.append(f'Без даты: {nodate[0]}…{nodate[-1]} ({len(nodate)} шт.)')
    (rdir(a.region) / 'timeline.md').write_text('\n'.join(tl), encoding='utf-8')
    print(f'фото {len(rows)}, видео {len(vrows)}; листов {len(list(sh.glob("*.jpg")))}; ошибок чтения {sum(1 for r in rows if r[9])}')


def load_index(region, name='index.tsv'):
    lines = (rdir(region) / name).read_text(encoding='utf-8').splitlines()[1:]
    srcs = sources(region); out = {}
    for l in lines:
        c = l.split('\t')
        path = next((s / c[1] for s in srcs if (s / c[1]).exists()), srcs[0] / c[1])
        out[c[0]] = (str(path), c)
    return out


def cmd_detail(a):
    idx = load_index(a.region); out = wdir(a.region, 'detail'); items = []
    for pid in a.ids:
        path = idx[pid][0]
        im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        if a.sheet:
            im.thumbnail((540, 540)); tmp = out / f'_{pid}.jpg'; im.save(tmp, quality=84); items.append((pid, str(tmp)))
        else:
            im.thumbnail((a.size, a.size)); dst = out / f'{pid}_{a.size}.jpg'; im.save(dst, quality=82); print(dst)
    if a.sheet:
        dst = out / f'{a.sheet}.jpg'; sheet(items, dst, 4, 540, 30, 22); print(dst)
        for _, t in items: os.remove(t)


def cmd_cands(a):
    """Листы всех фото-кандидатов из candidates.md (id в первом столбце таблиц), 5 в ряд, 480 px.
    Таблиц «Фото» может быть несколько (регион из частей или тем), поэтому берутся строки из всего файла."""
    text = (rdir(a.region) / 'candidates.md').read_text(encoding='utf-8')
    ids = list(dict.fromkeys(re.findall(r'^\|\s*(P\d{3,4})\s*\|', text, re.M)))
    if not ids: sys.exit('В candidates.md не найдено строк вида | P001 | …')
    idx = load_index(a.region); out = wdir(a.region, 'detail')
    for old in out.glob('cands-*.jpg'): old.unlink()
    per = 20
    for p in range(0, len(ids), per):
        items = []
        for pid in ids[p:p + per]:
            if pid not in idx: print(f'нет в index.tsv: {pid}'); continue
            im = ImageOps.exif_transpose(Image.open(idx[pid][0])).convert('RGB'); im.thumbnail((480, 480))
            tmp = out / f'_{pid}.jpg'; im.save(tmp, quality=82); items.append((f'{pid} {idx[pid][1][2][11:16]}', str(tmp)))
        dst = out / f'cands-{p // per + 1:02d}.jpg'; sheet(items, dst, 5, 480, 28, 21); print(dst)
        for _, t in items: os.remove(t)
    print(f'кандидатов {len(ids)}, листов {(len(ids) + per - 1) // per}')


def cmd_vstrip(a):
    idx = load_index(a.region, 'vindex.tsv'); out = wdir(a.region, 'detail'); path = idx[a.vid][0]; info = probe(path); items = []
    for i in range(a.n):
        t = info['dur'] * (i + 0.5) / a.n; tmp = out / f'_{a.vid}_{i}.jpg'
        if frame(path, t, str(tmp), 480, info['hdr']): items.append((f'{t:.1f}s', str(tmp)))
    dst = out / f'{a.vid}_strip.jpg'; sheet(items, dst, 5, 480, 26, 20); print(dst, f'длина {info["dur"]:.1f} c')
    for _, t in items: os.remove(t)


def cmd_export(a):
    """selection.tsv: имя<TAB>ID<TAB>размер[<TAB>отрезки видео «3-11,24-32» в секундах]
    Фото, обложки и сами ролики — в <slug>/media/ (решение автора 06.10.2026: отдельного репозитория для видео нет).
    С ключом --video-only заново выгружаются только ролики: фото, обложки и media.tsv не трогаются."""
    only_video = getattr(a, 'video_only', False)
    pidx = load_index(a.region); vidx = load_index(a.region, 'vindex.tsv') if (rdir(a.region) / 'vindex.tsv').exists() else {}
    out = ROOT / a.region / 'media'; out.mkdir(parents=True, exist_ok=True); rows = []; failed = []
    vout = out            # ролики — в ту же папку media/, что и фото
    sel = (rdir(a.region) / 'selection.tsv').read_text(encoding='utf-8')
    for line in (rdir(a.region) / 'selection.tsv').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'): continue
        c = line.split('\t'); name, mid, size = c[0], c[1], int(c[2])
        if only_video and (mid.startswith('P') or (len(c) > 3 and c[3].startswith('frame='))): continue
        if mid.startswith('V') and len(c) > 3 and c[3].startswith('frame='):   # кадр из видео как фото: hero<TAB>V05<TAB>2200<TAB>frame=10
            path, meta = vidx[mid]; tmp = out / f'_{name}.jpg'
            ff(['-ss', c[3][6:], '-i', path, '-frames:v', '1', '-q:v', '2', str(tmp)])
            im = Image.open(tmp).convert('RGB'); im.thumbnail((size, size), Image.LANCZOS)
            im.save(out / f'{name}.webp', 'WEBP', quality=WEBP_Q, method=6); tmp.unlink()
            rows.append([name, mid, str(im.width), str(im.height), meta[2]])
        elif mid.startswith('P'):
            path, meta = pidx[mid]; im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
            im.thumbnail((size, size), Image.LANCZOS); im.save(out / f'{name}.webp', 'WEBP', quality=WEBP_Q, method=6)
            rows.append([name, mid, str(im.width), str(im.height), meta[2]])
        else:
            path, meta = vidx[mid]; info = probe(path)
            segs = [tuple(map(float, s.split('-'))) for s in c[3].split(',')] if len(c) > 3 and c[3] else [(0, min(info['dur'], 15))]
            t0, t1 = segs[0][0], segs[-1][1]
            sc = f"scale='if(gt(iw,ih),{size},-2)':'if(gt(iw,ih),-2,{size})',fps=30"
            vout.mkdir(parents=True, exist_ok=True)
            dst = vout / f'{name}.mp4'
            au = info.get('audio', True)   # у видео с дрона звука нет: фильтр и вывод только по видео
            # Кодировщики по порядку: сначала видеокарта (NVENC, решение автора 06.10.2026 — процессор не должен
            # жевать ролики часами), при отказе — libx264 на процессоре с прежними настройками.
            # -cq у NVENC сопоставим с -crf по смыслу, но не по шкале: 28 даёт файл заметно тяжелее, чем libx264 crf 28,
            # поэтому -cq на три единицы больше; p6 — медленный качественный пресет, аналог slow.
            codecs = [['-c:v', 'h264_nvenc', '-preset', 'p6', '-rc', 'vbr', '-cq', str(int(VIDEO_CRF) + 3), '-b:v', '0'],
                      ['-c:v', 'libx264', '-preset', VIDEO_PRESET, '-crf', VIDEO_CRF]]
            tones = [TONEMAP, FALLBACK] if info['hdr'] else ['format=yuv420p']
            for codec, tone in [(c, t) for c in codecs for t in tones]:
                fc = f'[0:v]{sc},{tone},split={len(segs)}' + ''.join(f'[v{i}]' for i in range(len(segs))) + ';'
                if au: fc += f'[0:a]asplit={len(segs)}' + ''.join(f'[a{i}]' for i in range(len(segs))) + ';'
                for i, (s, e) in enumerate(segs):
                    fc += f'[v{i}]trim={s - t0}:{e - t0},setpts=PTS-STARTPTS[x{i}];'
                    if au: fc += f'[a{i}]atrim={s - t0}:{e - t0},asetpts=PTS-STARTPTS[y{i}];'
                fc += ''.join(f'[x{i}]' + (f'[y{i}]' if au else '') for i in range(len(segs))) + f'concat=n={len(segs)}:v=1:a={int(au)}[v]' + ('[a]' if au else '')
                r = ff(['-ss', str(t0), '-t', str(t1 - t0), '-i', path, '-filter_complex', fc, '-map', '[v]'] + (['-map', '[a]'] if au else [])
                       + codec + (['-c:a', 'aac', '-b:a', '96k'] if au else ['-an'])
                       + ['-movflags', '+faststart', str(dst)])
                if r.returncode == 0 and dst.exists() and dst.stat().st_size > 0: break
                if dst.exists(): dst.unlink()        # недописанный файл не должен уйти в коммит
            else:
                print('НЕ УДАЛОСЬ:', name, r.stderr[-300:]); failed.append(name); continue
            poster = out / f'{name}.jpg'
            if not (only_video and poster.exists()):   # при повторной выгрузке роликов обложки не перезаписываются: кадр тот же
                ff(['-ss', '2', '-i', str(dst), '-frames:v', '1', '-q:v', '3', str(poster)])
            p = probe(str(dst)); rows.append([name, mid, str(p['w']), str(p['h']), meta[2]])
        print(*rows[-1])
    if not only_video:
        cmd_mobile(a)   # копии для телефона — сразу, чтобы новый регион не остался без них
        (rdir(a.region) / 'media.tsv').write_text('name\tid\tw\th\ttaken\n' + '\n'.join('\t'.join(r) for r in rows), encoding='utf-8')
    total = sum(f.stat().st_size for f in out.iterdir()) / 2 ** 20
    vtotal = sum(f.stat().st_size for f in vout.iterdir()) / 2 ** 20 if vout.is_dir() else 0
    print(f'готово: {len(rows)} файлов, {total:.0f} МБ в {out}' + (f', ролики {vtotal:.0f} МБ в {vout}' if vtotal else ''))
    if failed: sys.exit('не выгружены ролики: ' + ', '.join(failed))   # ненулевой код: publish.py не станет выкладывать страницу без роликов


def cmd_mobile(a):
    """Копия фото для телефона: <имя>.m.webp шириной MOBILE_W рядом с <имя>.webp, если оригинал шире.
    Телефону 375 px с плотностью 2 хватает 750–1080 px, а оригинал до 2200 px весит втрое больше.
    Страница отдаёт копию через srcset (build.py), лайтбокс открывает оригинал. Свежая копия не пересчитывается."""
    regs = [a.region] if getattr(a, 'region', None) else sorted(d.name for d in ROOT.iterdir() if (d / 'media').is_dir() and re.match(r'\d', d.name))
    made = skip = 0; size = 0
    for r in regs:
        for f in sorted((ROOT / r / 'media').glob('*.webp')):
            if f.name.endswith('.m.webp'): continue
            dst = f.with_name(f.stem + '.m.webp')
            with Image.open(f) as im:
                if im.width <= MOBILE_W:
                    if dst.exists(): dst.unlink()   # оригинал стал узким — копия лишняя
                    continue
                if dst.exists() and dst.stat().st_mtime >= f.stat().st_mtime:
                    skip += 1; size += dst.stat().st_size; continue
                im = im.convert('RGB'); im = im.resize((MOBILE_W, round(im.height * MOBILE_W / im.width)), Image.LANCZOS)
                im.save(dst, 'WEBP', quality=WEBP_Q, method=6)
            made += 1; size += dst.stat().st_size
    print(f'копии для телефона: новых {made}, свежих {skip}, всего {size / 2**20:.0f} МБ')


def cmd_webp(a):
    """Перевод уже выгруженных фото региона из JPEG в WebP (обложки видео v-*.jpg остаются JPEG).
    Меняет ссылки в src/<регион>.html. Лучше, когда есть архив, заново выполнить export: так нет двойного сжатия."""
    out = ROOT / a.region / 'media'; n = 0; before = after = 0
    for f in sorted(out.glob('*.jpg')):
        if f.name.startswith('v-'): continue
        dst = f.with_suffix('.webp')
        Image.open(f).convert('RGB').save(dst, 'WEBP', quality=WEBP_Q, method=6)
        before += f.stat().st_size; after += dst.stat().st_size; f.unlink(); n += 1
    page = ROOT / 'src' / f'{a.region}.html'
    if page.exists():
        t = page.read_text(encoding='utf-8')
        t = re.sub(r'(src="media/(?!v-)[^"]+)\.jpg"', r'\1.webp"', t)
        page.write_text(t, encoding='utf-8')
    print(f'готово: {n} фото, {before / 2**20:.1f} -> {after / 2**20:.1f} МБ')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('check').set_defaults(fn=cmd_check)
    p = sp.add_parser('inventory'); p.add_argument('region'); p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--force', action='store_true', help='перезаписать index.tsv и vindex.tsv, даже если нумерация кадров изменится'); p.set_defaults(fn=cmd_inventory)
    p = sp.add_parser('detail'); p.add_argument('region'); p.add_argument('ids', nargs='+'); p.add_argument('--size', type=int, default=1100)
    p.add_argument('--sheet'); p.set_defaults(fn=cmd_detail)
    p = sp.add_parser('vstrip'); p.add_argument('region'); p.add_argument('vid'); p.add_argument('--n', type=int, default=10); p.set_defaults(fn=cmd_vstrip)
    p = sp.add_parser('cands'); p.add_argument('region'); p.set_defaults(fn=cmd_cands)
    p = sp.add_parser('export'); p.add_argument('region'); p.add_argument('--video-only', action='store_true'); p.set_defaults(fn=cmd_export)
    p = sp.add_parser('mobile'); p.add_argument('region', nargs='?'); p.set_defaults(fn=cmd_mobile)
    p = sp.add_parser('webp'); p.add_argument('region'); p.set_defaults(fn=cmd_webp)
    a = ap.parse_args(); a.fn(a)


if __name__ == '__main__':
    main()
