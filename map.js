/* Главная: карта, фильтры, карточка региона. Данные берутся из списка регионов на странице (li[data-code]). */
(function () {
  var svg = document.querySelector('.rumap');
  if (!svg) return;
  var card = document.getElementById('mcard');
  var hint = card.innerHTML;
  var paths = [].slice.call(svg.querySelectorAll('path, circle.dot'));   // контуры стран и кружки-метки маленьких стран
  var items = [].slice.call(document.querySelectorAll('li.reg[data-code]'));
  var secs = [].slice.call(document.querySelectorAll('section.fo'));
  var byCode = {};
  items.forEach(function (li) { byCode[li.dataset.code] = li; });
  var state = { fo: '', year: '', q: '' };
  var picked = null;
  var TR = { car: { icon: '🚗', text: 'на машине' }, bus: { icon: '🚌', text: 'на автобусе' },
             plane: { icon: '✈️', text: 'на самолёте' }, train: { icon: '🚆', text: 'на поезде' } };

  function plural(n, one, few, many) {
    if (n % 10 === 1 && n % 100 !== 11) return one;
    if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14)) return few;
    return many;
  }
  function linkOf(code) {
    var li = byCode[code], a = li && li.querySelector('a.code');
    return a ? a.getAttribute('href') : null;
  }
  // Дом автора — Россия: в списке стран её нет, данные — в атрибутах карты (build.py, константа HOME)
  var home = { code: svg.dataset.home || '', name: svg.dataset.homeName || '', url: svg.dataset.homeUrl || '' };
  function showHome() {
    card.innerHTML = '';
    var t = document.createElement('div'); t.className = 'mt';
    var h = document.createElement('div'); h.className = 'mh';
    var b = document.createElement('span'); b.className = 'code'; b.textContent = home.code;
    var n = document.createElement('strong'); n.textContent = home.name;
    var s = document.createElement('small'); s.textContent = 'Дом — отсюда начинаются поездки';
    h.appendChild(b); h.appendChild(n); t.appendChild(h); t.appendChild(s); card.appendChild(t);
    if (home.url) {
      var a = document.createElement('a'); a.className = 'go'; a.href = home.url;
      a.textContent = 'Отчёты о России →';
      card.appendChild(a);
    }
  }
  function show(code) {
    if (home.code && code === home.code) { showHome(); return; }
    var li = byCode[code];
    if (!li) { card.innerHTML = hint; return; }
    var href = linkOf(code);
    var name = li.querySelector('.nm, a:not(.code)');
    var sub = li.querySelector('small');
    var cap = li.dataset.cap || '';
    var parts = sub ? [].slice.call(sub.querySelectorAll('a')) : [];
    var date = li.dataset.home ? 'Дом — отсюда начинаются поездки'
      : li.dataset.date ? 'В отчёте: ' + li.dataset.date : li.dataset.visited ? '' : 'Ещё не был';
    var tr = TR[li.dataset.tr];
    if (tr) date += ' · ' + tr.icon + ' ' + tr.text;
    card.innerHTML = '';
    var th = li.querySelector('img.th');
    if (th) {
      var im = document.createElement('img'); im.className = 'mth'; im.alt = ''; im.src = th.getAttribute('src');
      card.appendChild(im);
    }
    var t = document.createElement('div'); t.className = 'mt';
    var h = document.createElement('div'); h.className = 'mh';     // номер рядом с названием: на телефоне рядом с фото отдельной колонке нет места
    var b = document.createElement('span'); b.className = 'code'; b.textContent = code;
    var n = document.createElement('strong'); n.textContent = name ? name.textContent : code;
    var s = document.createElement('small'); s.textContent = [cap, date].filter(Boolean).join(' · ');
    h.appendChild(b); h.appendChild(n);
    t.appendChild(h); t.appendChild(s);
    card.appendChild(t);
    if (href) {
      var a = document.createElement('a'); a.className = 'go'; a.href = href;
      a.textContent = 'Открыть отчёт →';
      card.appendChild(a);
    }
    if (parts.length) {
      var ps = document.createElement('small'); ps.className = 'parts';
      ps.appendChild(document.createTextNode('Ещё: '));
      parts.forEach(function (x, i) {
        if (i) ps.appendChild(document.createTextNode(' · '));
        var pa = document.createElement('a'); pa.href = x.getAttribute('href'); pa.textContent = x.textContent;
        ps.appendChild(pa);
      });
      t.appendChild(ps);
    }
  }
  // Наведение с задержкой: карточка остаётся на последнем регионе, пока мышь идёт к её ссылкам
  // через соседние регионы, и меняется, только если задержаться на другом регионе.
  var hovered = null, hoverTimer = null;
  function hoverTo(code) {
    clearTimeout(hoverTimer);
    if (hovered === null) { hovered = code; show(code); mark(code); return; }
    hoverTimer = setTimeout(function () { hovered = code; show(code); mark(code); }, 250);
  }
  var box = svg.closest('.mapbox') || svg.parentNode;
  box.addEventListener('pointerleave', function (ev) {
    if (ev.pointerType !== 'mouse' || picked) return;
    clearTimeout(hoverTimer); hovered = null; card.innerHTML = hint; mark('');
  });
  function mark(code) {
    paths.forEach(function (p) { p.classList.toggle('on', p.dataset.code === code); });
  }
  function go(code) {
    var href = home.code && code === home.code ? home.url : linkOf(code);
    if (href) location.href = href;
  }

  // Увеличение. Маленькие страны мельче пальца, поэтому выбор части света
  // приближает карту к ней, а кнопка — к Европе. Пропорции окна не меняются: страница не прыгает.
  var vb0 = svg.viewBox.baseVal, W = vb0.width, H = vb0.height, FULL = [0, 0, W, H];
  // Рамка «Европа» в системе карты 1000×423 (проекция Робинсона, tools/map.py): от Исландии (x≈449) до Урала (x≈635),
  // по широте от мыса Нордкап (y≈29) до южного берега Турции (y≈134); x, y, ширина, высота.
  var EUROPE = [440, 28, 200, 112];
  var zoomBtn = document.getElementById('zoom'), view = FULL.slice(), zoomed = false, anim = 0;
  var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function fit(b) {
    var pad = Math.max(b[2], b[3]) * 0.06, x = b[0] - pad, y = b[1] - pad, w = b[2] + 2 * pad, h = b[3] + 2 * pad;
    if (w / h < W / H) { x -= (h * W / H - w) / 2; w = h * W / H; } else { y -= (w * H / W - h) / 2; h = w * H / W; }
    return w >= W ? FULL : [x, y, w, h];
  }
  function foBox(fo) {
    var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    paths.forEach(function (p) {
      if (p.dataset.fo !== fo) return;
      var b = p.getBBox();
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
    });
    return [x0, y0, x1 - x0, y1 - y0];
  }
  function clamp(v) {                           // не уводить карту за край при перетаскивании
    var w = Math.min(W, v[2]), h = Math.min(H, v[3]);
    return [Math.max(0, Math.min(W - w, v[0])), Math.max(0, Math.min(H - h, v[1])), w, h];
  }
  function setView(v) { view = v; svg.setAttribute('viewBox', v.join(' ')); }
  function zoomTo(target) {
    cancelAnimationFrame(anim);
    zoomed = target !== FULL;
    zoomBtn.textContent = zoomed ? 'Весь мир' : 'Европа';
    zoomBtn.setAttribute('aria-pressed', zoomed ? 'true' : 'false');
    svg.classList.toggle('zoomed', zoomed);
    if (still) { setView(target); return; }
    var from = view.slice(), t0 = null;
    anim = requestAnimationFrame(function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / 350), e = 1 - Math.pow(1 - k, 3);
      setView(from.map(function (a, i) { return a + (target[i] - a) * e; }));
      if (k < 1) anim = requestAnimationFrame(step);
    });
  }
  zoomBtn.addEventListener('click', function () { zoomTo(zoomed ? FULL : fit(EUROPE)); });

  // Перетаскивание и щипок у увеличенной карты. Захват указателя — только когда палец уже сдвинулся:
  // иначе касание региона ушло бы самой карте, а не региону, и карточка не открылась бы.
  var ptrs = {}, drag = null, moved = false;
  function svgScale() { return view[2] / svg.getBoundingClientRect().width; }   // единиц карты на пиксель
  function startDrag() {
    var ids = Object.keys(ptrs), a = ptrs[ids[0]], b = ptrs[ids[1]];
    drag = { v: view.slice(), a: { x: a.x, y: a.y }, b: b ? { x: b.x, y: b.y } : null, k: svgScale() };
  }
  svg.addEventListener('pointerdown', function (ev) {
    if (!zoomed) return;
    ptrs[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
    moved = false; startDrag();
  });
  svg.addEventListener('pointermove', function (ev) {
    if (!zoomed || !ptrs[ev.pointerId]) return;
    ptrs[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
    var ids = Object.keys(ptrs), a = ptrs[ids[0]], b = ptrs[ids[1]];
    var dx = a.x - drag.a.x, dy = a.y - drag.a.y;
    if (!moved && Math.abs(dx) + Math.abs(dy) < 6 && !b) return;
    if (!moved) { moved = true; try { svg.setPointerCapture(ev.pointerId); } catch (e) {} }
    cancelAnimationFrame(anim);
    var v = drag.v, k = drag.k;
    if (b && drag.b) {                          // щипок: масштаб по расстоянию между пальцами, центр — между ними
      var d0 = Math.hypot(drag.b.x - drag.a.x, drag.b.y - drag.a.y), d1 = Math.hypot(b.x - a.x, b.y - a.y);
      var s = Math.max(W / v[2] / 6, Math.min(v[2] / W, d0 / Math.max(d1, 1)));   // не крупнее ×6 и не мельче всей страны
      var r = svg.getBoundingClientRect();
      var m0x = (drag.a.x + drag.b.x) / 2 - r.left, m0y = (drag.a.y + drag.b.y) / 2 - r.top;
      var m1x = (a.x + b.x) / 2 - r.left, m1y = (a.y + b.y) / 2 - r.top;
      var px = v[0] + m0x * k, py = v[1] + m0y * k, w = v[2] * s, h = v[3] * s;
      setView(clamp([px - m1x * k * s, py - m1y * k * s, w, h]));
    } else {
      setView(clamp([v[0] - dx * k, v[1] - dy * k, v[2], v[3]]));
    }
  });
  function endPtr(ev) {
    if (!ptrs[ev.pointerId]) return;
    delete ptrs[ev.pointerId];
    if (Object.keys(ptrs).length) startDrag();   // один палец остался — продолжаем тянуть от него
  }
  svg.addEventListener('pointerup', endPtr);
  svg.addEventListener('pointercancel', endPtr);
  // после перетаскивания отпускание пальца не считается нажатием на регион
  svg.addEventListener('click', function (ev) { if (moved) { ev.stopPropagation(); ev.preventDefault(); moved = false; } }, true);

  // «К карте»: список длинный, на телефоне — несколько тысяч точек; кнопка видна, когда карта ушла за верх экрана
  var totop = document.getElementById('totop');
  function onScroll() { totop.hidden = box.getBoundingClientRect().bottom > 0; }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  paths.forEach(function (p) {
    var code = p.dataset.code;
    p.addEventListener('pointerenter', function (ev) { if (ev.pointerType === 'mouse' && !picked) hoverTo(code); });
    p.addEventListener('pointerleave', function (ev) { if (ev.pointerType === 'mouse') clearTimeout(hoverTimer); });
    p.addEventListener('focus', function () { show(code); mark(code); });
    p.addEventListener('click', function (ev) {
      if (ev.pointerType === 'touch' || ev.pointerType === 'pen') { picked = code; show(code); mark(code); card.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); return; }
      go(code);
    });
    p.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(code); } });
  });
  document.addEventListener('click', function (ev) {
    if (picked && !ev.target.closest('.rumap, .mcard')) { picked = null; card.innerHTML = hint; mark(''); }
  });

  // фильтры
  function apply() {
    paths.forEach(function (p) { p.classList.toggle('dim', !okFilter(p)); });
    items.forEach(function (li) { li.hidden = !okFilter(li); });
    secs.forEach(function (s) { s.hidden = !s.querySelector('li.reg:not([hidden])'); });
    none.hidden = items.some(function (li) { return !li.hidden; });
    syncFav();
    syncNote();
  }

  // Лента «Любимые» — для первого взгляда на всю страну. Когда читатель что-то ищет, выбрал округ или год
  // или смотрит «Путь по годам», лента убирается, чтобы найденное стояло сразу под поиском.
  var fav = document.getElementById('fav'), favRow = document.getElementById('favRow');
  var favNav = document.getElementById('favNav'), favPrev = document.getElementById('favPrev'), favNext = document.getElementById('favNext');
  function favStep() {
    // листаем на столько карточек, сколько целиком помещается в ленте: на компьютере — по три
    var cards = favRow.querySelectorAll('.fc');
    if (cards.length < 2) return favRow.clientWidth;
    var pitch = cards[1].offsetLeft - cards[0].offsetLeft, gap = pitch - cards[0].offsetWidth;
    return Math.max(1, Math.floor((favRow.clientWidth + gap + 1) / pitch)) * pitch;
  }
  function favSyncNav() {
    if (!fav) return;
    var max = favRow.scrollWidth - favRow.clientWidth;
    favPrev.disabled = favRow.scrollLeft <= 2;
    favNext.disabled = favRow.scrollLeft >= max - 2;
    favNav.hidden = max <= 2;
  }
  function syncFav() {
    if (!fav) return;
    var busy = !!(state.fo || state.year || state.q) || idx < N;
    if (fav.hidden !== busy) fav.hidden = busy;
    if (!busy) favSyncNav();
  }
  if (fav) {
    favPrev.addEventListener('click', function () { favRow.scrollBy({ left: -favStep(), behavior: 'smooth' }); });
    favNext.addEventListener('click', function () { favRow.scrollBy({ left: favStep(), behavior: 'smooth' }); });
    favRow.addEventListener('scroll', favSyncNav, { passive: true });
    window.addEventListener('resize', favSyncNav);
  }
  // Уведомление об активном фильтре или остановленном проигрывателе: без него отфильтрованный список выглядит как потеря регионов
  var fnote = document.getElementById('fnote'), fnoteText = document.getElementById('fnoteText'), fnoteBtn = document.getElementById('fnoteBtn');
  function syncNote() {
    if (!fnote) return;
    var msg = '', btn = 'Сбросить';
    if (idx < N) { msg = 'Показаны страны до поездки ' + (idx + 1) + ' из ' + N; btn = 'Показать все'; }
    else if (state.year) msg = 'Показаны страны ' + state.year + ' года';
    else if (state.fo) {
      var fb = document.querySelector('.chip[data-v="' + state.fo + '"]');
      msg = 'Показана часть света: ' + (fb ? fb.textContent : state.fo);
    }
    fnote.hidden = !msg;
    if (msg) { fnoteText.textContent = msg; fnoteBtn.textContent = btn; }
  }
  if (fnote) fnoteBtn.addEventListener('click', function () {
    stopPlay(); resetFilters(); picked = null; mark(''); idx = N; draw(); apply();
  });
  // поиск по названию и столице; строка поиска в атрибуте data-q уже строчная и с «е» вместо «ё»
  var find = document.getElementById('find'), none = document.getElementById('none');
  find.addEventListener('input', function () {
    state.q = find.value.trim().toLowerCase().replace(/ё/g, 'е');
    stopPlay(); idx = N; draw(); apply();
  });
  var filterBtns = [].slice.call(document.querySelectorAll('.chip, .ychip'));
  filterBtns.forEach(function (c) {
    c.addEventListener('click', function () {
      var k = c.dataset.k;
      // год в легенде — переключатель: повторное нажатие возвращает все годы
      state[k] = (k === 'year' && state.year === c.dataset.v) ? '' : c.dataset.v;
      filterBtns.forEach(function (x) {
        if (x.dataset.k === k) x.setAttribute('aria-pressed', x.dataset.v === state[k] ? 'true' : 'false');
      });
      stopPlay(); idx = N; draw();
      apply();
      if (k === 'fo') zoomTo(c.dataset.v ? fit(foBox(c.dataset.v)) : FULL);
    });
  });

  // «Посмотреть маршрут»: шаг — одна поездка из data/trips.json (build.py кладёт их в data-trips у блока карты).
  // Регионы поездки загораются вместе. Дом и регионы без поездки в списке горят с первого шага.
  var steps = JSON.parse(box.dataset.trips || '[]');
  var N = steps.length;                     // значение ползунка N = «все поездки»
  var firstStep = {};
  steps.forEach(function (t, i) { t[2].forEach(function (c) { if (!(c in firstStep)) firstStep[c] = i; }); });
  function stepOf(code) { return code in firstStep ? firstStep[code] : -1; }
  var track = document.getElementById('track'), tdate = document.getElementById('tdate'), tnote = document.getElementById('tnote');
  var playBtn = document.getElementById('play'), tall = document.getElementById('tall'), mapdate = document.getElementById('mapdate');
  var idx = N, playing = false, timer = null, STEP = 1500;   // 23 поездки × 1,5 с ≈ 35 с
  var MON1 = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
  var MON = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
  function span(a, b) {                     // «19–20 февраля 2022», «30 июля – 7 августа 2025»
    var x = a.split('-'), y = b.split('-');
    if (a === b) return +x[2] + ' ' + MON[x[1] - 1] + ' ' + x[0];
    if (x[0] !== y[0]) return +x[2] + ' ' + MON[x[1] - 1] + ' ' + x[0] + ' – ' + +y[2] + ' ' + MON[y[1] - 1] + ' ' + y[0];
    if (x[1] !== y[1]) return +x[2] + ' ' + MON[x[1] - 1] + ' – ' + +y[2] + ' ' + MON[y[1] - 1] + ' ' + y[0];
    return +x[2] + '–' + +y[2] + ' ' + MON[x[1] - 1] + ' ' + x[0];
  }
  track.min = 0; track.max = N; track.step = 1; track.value = N;
  // Шкала по поездкам: засечка на каждую, подпись года — у первой поездки года
  var ruler = document.getElementById('ruler'), lastY = '';
  steps.forEach(function (t, i) {
    var pos = i / N * 100 + '%', y = t[0].slice(0, 4);
    var tick = document.createElement('i'); tick.style.left = pos; ruler.appendChild(tick);
    if (y === lastY) return;
    lastY = y;
    var s = document.createElement('span'), c = document.createElement('b');
    c.textContent = y.slice(0, 2);            // «20» прячется на узком экране: остаётся «’22»
    s.appendChild(c); s.appendChild(document.createTextNode(y.slice(2)));
    s.style.left = pos;
    ruler.appendChild(s);
  });
  function fitRuler() { ruler.classList.toggle('short', ruler.clientWidth < 360); }
  fitRuler();
  window.addEventListener('resize', fitRuler);
  var total = items.filter(function (li) { return li.dataset.visited; }).length;   // посещённые по списку, дом тоже
  function isOn(li, cur) { return !!li.dataset.visited && stepOf(li.dataset.code) <= cur; }
  function nameOf(code) { var li = byCode[code], n = li && li.querySelector('.nm, a:not(.code)'); return n ? n.textContent : code; }

  function draw() {
    var cur = idx < N ? idx : null, trip = cur === null ? null : steps[cur];
    paths.forEach(function (p) {
      var li = byCode[p.dataset.code], vis = !!(li && li.dataset.visited);
      p.classList.toggle('later', cur !== null && vis && stepOf(p.dataset.code) > cur);
      p.classList.toggle('arr', !!trip && trip[2].indexOf(p.dataset.code) >= 0);
    });
    items.forEach(function (li) { li.hidden = (cur !== null && !!li.dataset.visited && !isOn(li, cur)) || !okFilter(li); });
    secs.forEach(function (s) { s.hidden = !s.querySelector('li.reg:not([hidden])'); });
    syncFav();
    syncNote();
    track.value = idx; tall.hidden = idx >= N;
    playBtn.classList.toggle('playing', playing);
    playBtn.setAttribute('aria-label', playing ? 'Посмотреть маршрут: пауза' : 'Посмотреть маршрут: воспроизвести');
    mapdate.hidden = !trip;
    document.getElementById('tprev').disabled = idx <= 0;
    document.getElementById('tnext').disabled = idx >= N;
    var chain = document.getElementById('tchain');
    if (!trip) {
      tdate.textContent = 'Все поездки'; tnote.textContent = 'На карте все посещённые страны.'; tnote.hidden = false;
      chain.hidden = true; chain.innerHTML = '';
      if (!picked) card.innerHTML = hint; return;
    }
    var shown = items.filter(function (li) { return isOn(li, cur); }).length;
    var a = trip[0].split('-');
    mapdate.textContent = MON1[a[1] - 1] + ' ' + a[0];
    var sm = document.createElement('small'); sm.textContent = shown + ' из ' + total + ' ' + plural(total, 'страны', 'стран', 'стран');
    mapdate.appendChild(sm);
    // Подпись шага — про поездку целиком: номер и даты крупно, ниже регионы по порядку, каждый — ссылка на отчёт
    tdate.textContent = 'Поездка ' + (cur + 1) + ' из ' + N + ' · ' + span(trip[0], trip[1]);
    var li0 = byCode[trip[2][0]], tr = li0 && TR[li0.dataset.tr];
    tnote.textContent = tr ? 'Туда ' + tr.text : '';
    tnote.hidden = !tr;
    chain.innerHTML = '';
    trip[2].forEach(function (c, i) {
      if (i) { var ar = document.createElement('span'); ar.className = 'ar'; ar.setAttribute('aria-hidden', 'true'); ar.textContent = '→'; chain.appendChild(ar); }
      var href = linkOf(c), el = document.createElement(href ? 'a' : 'span');
      if (href) el.href = href;
      el.className = 'st';
      var b = document.createElement('b'); b.textContent = c;
      el.appendChild(b); el.appendChild(document.createTextNode(nameOf(c)));
      chain.appendChild(el);
    });
    chain.hidden = false;
    if (!picked) card.innerHTML = hint;
  }
  function okFilter(el) {
    var li = byCode[el.dataset.code];          // у контура на карте строки поиска нет — берётся из строки списка
    return (!state.fo || el.dataset.fo === state.fo) && (!state.year || el.dataset.year === state.year)
      && (!state.q || (li && li.dataset.q.indexOf(state.q) >= 0));
  }
  function setIdx(n) { idx = Math.max(0, Math.min(N, n)); draw(); }
  function stopPlay() { playing = false; clearTimeout(timer); }
  function loop() {
    if (!playing) return;
    timer = setTimeout(function () {
      if (idx >= N - 1) { stopPlay(); idx = N; draw(); return; }   // после последней поездки — вся карта
      idx++; draw(); loop();
    }, STEP);
  }
  playBtn.addEventListener('click', function () {
    if (playing) { stopPlay(); draw(); return; }
    if (idx >= N - 1) idx = 0;                    // с конца начинаем заново
    resetFilters(); picked = null; mark('');
    playing = true; draw(); loop();
  });
  track.addEventListener('input', function () { stopPlay(); resetFilters(); picked = null; mark(''); setIdx(+track.value); });
  document.getElementById('tprev').addEventListener('click', function () { stopPlay(); resetFilters(); setIdx(idx - 1); });
  document.getElementById('tnext').addEventListener('click', function () { stopPlay(); resetFilters(); setIdx(idx + 1); });
  tall.addEventListener('click', function () { stopPlay(); setIdx(N); });
  function resetFilters() {
    var hadFo = state.fo;
    state.fo = ''; state.year = '';
    filterBtns.forEach(function (x) { x.setAttribute('aria-pressed', x.dataset.v === '' ? 'true' : 'false'); });
    paths.forEach(function (p) { p.classList.remove('dim'); });
    if (hadFo) zoomTo(FULL);   // округ снят — снимается и его увеличение; «Европейскую часть» хронология не трогает
  }
  draw();
})();
