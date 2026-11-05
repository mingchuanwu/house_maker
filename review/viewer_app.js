/* House review page: move panels, check fit, annotate. Depends on HR (viewer_core.js). */
(() => {
  'use strict';
  const DATA = JSON.parse(document.getElementById('review-data').textContent);
  const KEY = 'house_review:' + DATA.run;
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    if (parent) parent.appendChild(e);
    return e;
  };
  const h = (tag, props = {}, ...kids) => {
    const e = Object.assign(document.createElement(tag), props);
    kids.forEach((k) => e.append(k));
    return e;
  };
  const CATS = { bug: ['🐞', '#d93025'], improve: ['💡', '#e8710a'], question: ['❓', '#1a73e8'], good: ['✅', '#188038'] };

  // ------------------------------------------------------------------ state
  let S;
  try { S = JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { S = null; }
  S = S || { poses: {}, pins: [], notes: {}, ui: { fit: true, grid: false } };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* private mode */ } updateCounts(); };

  let ci = -1, cur = null, svg = null, outer = null, ui = null, overlay = null;
  let panels = {};            // name -> {g, meta, init, pose, fill}
  let selected = null, tool = 'select', fullVB = null, measure = null, drag = null, pan = null;

  const key = (c) => c.group + '/' + c.case;
  const casePins = () => S.pins.filter((p) => p.case === key(cur));

  // ------------------------------------------------------------------ sidebar
  function buildSidebar() {
    const side = $('cases'); side.innerHTML = '';
    const groups = {};
    DATA.cases.forEach((c, i) => (groups[c.group] = groups[c.group] || []).push(i));
    Object.entries(groups).forEach(([g, idxs]) => {
      side.append(h('div', { className: 'grp' }, g));
      idxs.forEach((i) => {
        const a = h('a', { href: '#', className: 'case', id: 'case' + i }, DATA.cases[i].case);
        a.append(h('span', { className: 'cnt', id: 'cnt' + i }));
        a.onclick = (e) => { e.preventDefault(); openCase(i); };
        side.append(a);
      });
    });
    updateCounts();
  }
  function updateCounts() {
    DATA.cases.forEach((c, i) => {
      const n = S.pins.filter((p) => p.case === key(c) && p.status !== 'fixed').length;
      const moved = Object.keys(S.poses[key(c)] || {}).length;
      const span = $('cnt' + i);
      if (span) span.textContent = (n ? ` 📌${n}` : '') + (moved ? ' ✎' : '');
    });
  }

  // ------------------------------------------------------------------ case loading
  function parseTranslate(g) {
    const m = /translate\(\s*([-\d.eE+]+)[ ,]+([-\d.eE+]+)\s*\)/.exec(g.getAttribute('transform') || '');
    return m ? [parseFloat(m[1]), parseFloat(m[2])] : [0, 0];
  }
  function openCase(i) {
    ci = i; cur = DATA.cases[i]; selected = null; measure = null;
    document.querySelectorAll('.case').forEach((a) => a.classList.toggle('on', a.id === 'case' + i));
    $('stage').innerHTML = cur.svg;
    svg = $('stage').querySelector('svg');
    svg.removeAttribute('width'); svg.removeAttribute('height');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    outer = svg.querySelector('#house_box_panels');
    fullVB = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    panels = {};
    const saved = S.poses[key(cur)] || {};
    cur.panels.forEach((meta) => {
      const g = svg.querySelector('g[id="' + meta.name + '"]');
      if (!g) return;
      const [tx, ty] = parseTranslate(g);
      const init = { tx, ty, rot: 0, flip: false };
      const fill = el('path', { class: 'hitfill', 'fill-rule': 'evenodd', d: panelPathData(g) });
      g.insertBefore(fill, g.firstChild);
      panels[meta.name] = { g, meta, init, pose: Object.assign({}, saved[meta.name] || init), fill };
      g.classList.add('panel');
      applyPose(meta.name);
    });
    overlay = el('g', { class: 'overlay' }, outer);
    ui = el('g', { class: 'ui' }, outer);
    drawGhosts();
    $('title').textContent = cur.title || '';
    $('caseName').textContent = key(cur);
    $('notes').value = S.notes[key(cur)] || '';
    renderInfo(); renderPins(); refreshOverlaps();
    svg.classList.toggle('fit', S.ui.fit);
    svg.addEventListener('pointerdown', onDown);
    svg.addEventListener('pointermove', onMove);
    svg.addEventListener('pointerup', onUp);
    svg.addEventListener('wheel', onWheel, { passive: false });
    svg.addEventListener('dblclick', () => resetView());
  }
  function panelPathData(g) {
    return [...g.querySelectorAll('path.cut-line')].map((p) => p.getAttribute('d')).join(' ');
  }
  function applyPose(name) {
    const P = panels[name];
    P.g.setAttribute('transform', HR.css(HR.panelMatrix(P.pose, HR.centre(P.meta))));
  }
  function persistPose(name) {
    const P = panels[name], k = key(cur);
    const same = ['tx', 'ty', 'rot', 'flip'].every((f) => Math.abs(+P.pose[f] - +P.init[f]) < 1e-9);
    S.poses[k] = S.poses[k] || {};
    if (same) delete S.poses[k][name]; else S.poses[k][name] = Object.assign({}, P.pose);
    if (!Object.keys(S.poses[k]).length) delete S.poses[k];
    save();
  }

  // ------------------------------------------------------------------ coordinates
  function toF(e) {          // client -> outer-group coordinates (mm on the sheet)
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(outer.getScreenCTM().inverse());
    return [p.x, p.y];
  }
  const matrixOf = (name) => HR.panelMatrix(panels[name].pose, HR.centre(panels[name].meta));
  const toLocal = (name, f) => HR.apply(HR.invert(matrixOf(name)), f);
  const toSheet = (name, l) => HR.apply(matrixOf(name), l);

  // ------------------------------------------------------------------ pointer handling
  function panelAt(e) {
    const g = e.target.closest && e.target.closest('g.panel');
    return g ? g.id : null;
  }
  function onDown(e) {
    if (e.button === 1 || e.button === 2 || e.altKey) { startPan(e); return; }
    const pinEl = e.target.closest && e.target.closest('.pin');
    if (pinEl) { editPin(pinEl.dataset.id); return; }
    const name = panelAt(e), f = toF(e);
    if (tool === 'measure') {
      if (!measure || measure.done) measure = { a: f, b: f, done: false }; else { measure.b = f; measure.done = true; }
      drawMeasure(); return;
    }
    if (tool === 'pin') { newPin(e, name, f); return; }
    if (name) {
      select(name);
      const P = panels[name];
      drag = { name, start: f, pose: Object.assign({}, P.pose), moved: false };
      svg.setPointerCapture(e.pointerId);
    } else { select(null); startPan(e); }
  }
  function onMove(e) {
    const f = toF(e);
    $('coords').textContent = `x ${f[0].toFixed(2)}  y ${f[1].toFixed(2)} mm`;
    if (pan) { doPan(e); return; }
    if (tool === 'measure' && measure && !measure.done) { measure.b = f; drawMeasure(); return; }
    if (!drag) return;
    const P = panels[drag.name];
    let tx = drag.pose.tx + f[0] - drag.start[0], ty = drag.pose.ty + f[1] - drag.start[1];
    if (S.ui.grid) { tx = Math.round(tx * 2) / 2; ty = Math.round(ty * 2) / 2; }
    if (Math.abs(f[0] - drag.start[0]) + Math.abs(f[1] - drag.start[1]) > 0.2) drag.moved = true;
    P.pose.tx = tx; P.pose.ty = ty; applyPose(drag.name); renderPins(); clearOverlaps();
  }
  function onUp(e) {
    if (pan) { pan = null; return; }
    if (drag) { if (drag.moved) { persistPose(drag.name); renderInfo(); refreshOverlaps(); } drag = null; }
  }
  function startPan(e) { pan = { x: e.clientX, y: e.clientY, vb: svg.getAttribute('viewBox').split(/\s+/).map(Number) }; }
  function doPan(e) {
    const k = svg.getScreenCTM().a;
    const vb = pan.vb.slice();
    vb[0] -= (e.clientX - pan.x) / k; vb[1] -= (e.clientY - pan.y) / k;
    svg.setAttribute('viewBox', vb.join(' '));
  }
  function onWheel(e) {
    e.preventDefault();
    const before = toF(e);
    const vb = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    const z = Math.exp(e.deltaY * 0.0015);
    vb[2] *= z; vb[3] *= z;
    svg.setAttribute('viewBox', vb.join(' '));
    const after = toF(e);
    vb[0] += before[0] - after[0]; vb[1] += before[1] - after[1];
    svg.setAttribute('viewBox', vb.join(' '));
    renderPins();
  }
  function resetView() { svg.setAttribute('viewBox', fullVB.join(' ')); renderPins(); }

  // ------------------------------------------------------------------ selection / info panel
  function select(name) {
    selected = name;
    Object.entries(panels).forEach(([n, P]) => P.g.classList.toggle('sel', n === name));
    renderInfo(); refreshOverlaps();
  }
  function mutate(fn) {
    if (!selected) return;
    fn(panels[selected].pose); applyPose(selected); persistPose(selected);
    renderPins(); renderInfo(); refreshOverlaps();
  }
  function renderInfo() {
    const box = $('info'); box.innerHTML = '';
    if (!selected) { box.append(h('p', { className: 'hint' }, 'Click a panel to select it. Drag to move. R rotates 90°, X flips, arrows nudge (Shift = 1 mm, Alt = 0.01 mm).')); return; }
    const P = panels[selected], m = P.meta, pose = P.pose;
    box.append(h('h3', {}, m.label || m.name));
    const dims = m.nominal_size ? m.nominal_size.map((v) => v.toFixed(2)).join(' × ') + ' mm' : '';
    box.append(h('div', { className: 'kv' }, `${dims}   pos ${pose.tx.toFixed(2)}, ${pose.ty.toFixed(2)}   rot ${pose.rot.toFixed(1)}°${pose.flip ? '  flipped' : ''}`));
    const row = h('div', { className: 'btns' });
    [['⟲ −90', () => mutate((p) => { p.rot = (p.rot + 270) % 360; })], ['⟳ +90', () => mutate((p) => { p.rot = (p.rot + 90) % 360; })],
     ['⇋ flip', () => mutate((p) => { p.flip = !p.flip; })], ['↺ reset', () => mutate((p) => Object.assign(p, panels[selected].init))]]
      .forEach(([t, fn]) => { const b = h('button', {}, t); b.onclick = fn; row.append(b); });
    box.append(row);

    // mates of the selected panel
    const mates = cur.mates.filter((x) => x.a[0] === selected || x.b[0] === selected);
    if (mates.length) box.append(h('h4', {}, 'Mates'));
    mates.forEach((x) => {
      if (x.kind === 'edge') {
        const other = x.a[0] === selected ? x.b : x.a, mine = x.a[0] === selected ? x.a : x.b;
        const b = h('button', { className: 'mate' }, `snap ${mine[1]} → ${other[0]}.${other[1]}`);
        b.title = x.note;
        b.onclick = () => snapTo(x, x.a[0] === selected);
        box.append(b);
      } else {
        const tabSide = x.a[0] === selected;
        const t = HR.tabGhost(panels[x.a[0]].meta, x.a[1], panels[x.b[0]].meta, x.b[1], cur.material.thickness);
        const clr = t ? (t.slotW + cur.material.kerf - t.w) : NaN, clr2 = t ? (t.slotH + cur.material.kerf - t.h) : NaN;
        box.append(h('div', { className: 'kv' },
          `${tabSide ? 'tab' : 'slot'}: ${x.a[0]}.${x.a[1]} → ${x.b[0]} slot ${x.b[1]}` +
          (t ? `   tab ${t.w.toFixed(2)}×${t.h.toFixed(2)} in slot ${t.slotW.toFixed(2)}×${t.slotH.toFixed(2)} (+kerf ${cur.material.kerf}) clearance ${clr.toFixed(2)} / ${clr2.toFixed(2)} mm` : '')));
      }
    });
    box.append(h('h4', {}, 'Overlaps'));
    box.append(h('div', { id: 'overlaps', className: 'kv' }, '…'));
  }
  function snapTo(mate, selectedIsA) {
    // A stored mate says "B moves onto A"; when the selected panel is A we use the swapped roles.
    const fixedRef = selectedIsA ? mate.b : mate.a, movingRef = selectedIsA ? mate.a : mate.b;
    const F = panels[fixedRef[0]], M = panels[movingRef[0]];
    if (F.pose.flip || M.pose.flip) { alert('Reset the flip on both panels first.'); return; }
    const lenA = HR.edgeOf(panels[mate.a[0]].meta, mate.a[1]).len, lenB = HR.edgeOf(panels[mate.b[0]].meta, mate.b[1]).len;
    const shift = selectedIsA ? HR.swapShift(mate.shift, lenA, lenB) : mate.shift;
    const pose = HR.snapPose(F.meta, F.pose, fixedRef[1], M.meta, movingRef[1], shift);
    if (!pose) return;
    M.pose = pose; applyPose(movingRef[0]); persistPose(movingRef[0]); renderPins(); renderInfo(); refreshOverlaps();
  }

  // ------------------------------------------------------------------ overlap analysis (canvas)
  function clearOverlaps() { if (overlay) overlay.innerHTML = ''; const o = $('overlaps'); if (o) o.textContent = '…'; }
  function worldBBox(name) {
    const m = matrixOf(name), b = panels[name].meta.bbox;
    const pts = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]].map((p) => HR.apply(m, p));
    return [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
  }
  function overlapOf(a, b) {
    const A = worldBBox(a), B = worldBBox(b);
    if (A[2] <= B[0] || B[2] <= A[0] || A[3] <= B[1] || B[3] <= A[1]) return null;
    return HR.overlap(panels[a].fill.getAttribute('d'), matrixOf(a), panels[b].fill.getAttribute('d'), matrixOf(b));
  }
  function expectedKerf(a, b) {
    return cur.mates.filter((m) => m.kind === 'edge' && ((m.a[0] === a && m.b[0] === b) || (m.a[0] === b && m.b[0] === a)))
      .reduce((s, m) => s + HR.kerfInterference(panels[m.a[0]].meta, m.a[1], panels[m.b[0]].meta, m.b[1]), 0);
  }
  function refreshOverlaps() {
    if (!overlay) return;
    overlay.innerHTML = '';
    const out = $('overlaps');
    if (!selected) return;
    const lines = [];
    Object.keys(panels).filter((n) => n !== selected).forEach((n) => {
      let r; try { r = overlapOf(selected, n); } catch (e) { r = null; }
      if (!r) return;
      if (r.area > 0) {
        r.rects.slice(0, 3000).forEach((q) => el('rect', { x: q[0], y: q[1], width: q[2], height: q[3], class: 'overlap' }, overlay));
        const exp = expectedKerf(selected, n);
        lines.push(`${n}: ${r.area.toFixed(2)} mm²` + (exp ? `  (kerf-expected ${exp.toFixed(2)})` : '  ← unexpected'));
      }
    });
    if (out) out.textContent = lines.length ? lines.join('\n') : 'none';
  }

  // ------------------------------------------------------------------ ghosts (tab cross-sections)
  function drawGhosts() {
    cur.mates.filter((m) => m.kind === 'tab_slot').forEach((m) => {
      const t = HR.tabGhost(panels[m.a[0]].meta, m.a[1], panels[m.b[0]].meta, m.b[1], cur.material.thickness);
      if (!t || !panels[m.b[0]]) return;
      const g = el('g', { class: 'ghost' }, panels[m.b[0]].g);
      el('rect', { x: t.cx - t.w / 2, y: t.cy - t.h / 2, width: t.w, height: t.h, class: 'ghostrect' }, g);
    });
  }

  // ------------------------------------------------------------------ measuring
  function drawMeasure() {
    ui.querySelectorAll('.measure').forEach((n) => n.remove());
    if (!measure) return;
    const g = el('g', { class: 'measure' }, ui), k = 1 / svg.getScreenCTM().a;
    el('line', { x1: measure.a[0], y1: measure.a[1], x2: measure.b[0], y2: measure.b[1], stroke: '#9334e6', 'stroke-width': 1.5 * k }, g);
    const dx = measure.b[0] - measure.a[0], dy = measure.b[1] - measure.a[1];
    const t = el('text', { x: measure.b[0] + 4 * k, y: measure.b[1] - 4 * k, 'font-size': 12 * k, fill: '#9334e6' }, g);
    t.textContent = `${Math.hypot(dx, dy).toFixed(2)} mm  (Δx ${dx.toFixed(2)}, Δy ${dy.toFixed(2)})`;
  }

  // ------------------------------------------------------------------ pins
  function newPin(e, name, f) {
    let target = { type: 'free' }, local = null;
    if (name) { local = toLocal(name, f); target = HR.nearestTarget(panels[name].meta, local); }
    const pin = { id: 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5), case: key(cur), panel: name,
                  target, local, sheet: f, category: 'bug', severity: 'med', text: '', status: 'open', created: new Date().toISOString() };
    openForm(pin, true, e);
  }
  function editPin(id) { const pin = S.pins.find((p) => p.id === id); if (pin) openForm(pin, false); }
  function describeTarget(pin) {
    const t = pin.target || { type: 'free' };
    const where = pin.panel || 'sheet';
    if (t.type === 'finger') return `${where} · ${t.edge} · finger #${t.finger + 1}`;
    if (t.type === 'edge') return `${where} · ${t.edge}`;
    if (t.type === 'slot') return `${where} · slot #${t.slot + 1}`;
    return where;
  }
  function openForm(pin, isNew) {
    const f = $('form'); f.hidden = false; f.innerHTML = '';
    const sel = (opts, val) => { const s = h('select'); opts.forEach((o) => s.append(h('option', { value: o, selected: o === val }, o))); return s; };
    const cat = sel(Object.keys(CATS), pin.category), sev = sel(['low', 'med', 'high'], pin.severity), st = sel(['open', 'fixed', 'wontfix'], pin.status);
    const text = h('textarea', { rows: 5, placeholder: 'What is wrong / what should change? (be specific: which edge, which dimension, what you expected)' });
    text.value = pin.text;
    f.append(h('h3', {}, (isNew ? 'New note · ' : 'Edit note · ') + describeTarget(pin)),
             h('label', {}, 'Type ', cat), h('label', {}, ' Severity ', sev), h('label', {}, ' Status ', st), text);
    const row = h('div', { className: 'btns' });
    const ok = h('button', { className: 'primary' }, 'Save');
    ok.onclick = () => {
      Object.assign(pin, { category: cat.value, severity: sev.value, status: st.value, text: text.value.trim() });
      if (!S.pins.includes(pin)) S.pins.push(pin);
      f.hidden = true; save(); renderPins();
    };
    const cancel = h('button', {}, 'Cancel'); cancel.onclick = () => { f.hidden = true; };
    row.append(ok, cancel);
    if (!isNew) { const del = h('button', { className: 'danger' }, 'Delete'); del.onclick = () => { S.pins = S.pins.filter((p) => p !== pin); f.hidden = true; save(); renderPins(); }; row.append(del); }
    f.append(row); text.focus();
  }
  function renderPins() {
    if (!ui) return;
    ui.querySelectorAll('.pin').forEach((n) => n.remove());
    const k = 1 / svg.getScreenCTM().a, list = $('pinlist'); list.innerHTML = '';
    casePins().forEach((pin, i) => {
      const at = pin.panel && panels[pin.panel] ? toSheet(pin.panel, pin.local) : pin.sheet;
      const [emoji, color] = CATS[pin.category] || CATS.bug;
      const g = el('g', { class: 'pin' + (pin.status !== 'open' ? ' done' : ''), 'data-id': pin.id, transform: `translate(${at[0]},${at[1]})` }, ui);
      el('circle', { r: 9 * k, fill: color, stroke: '#fff', 'stroke-width': 1.5 * k }, g);
      const t = el('text', { 'text-anchor': 'middle', y: 3.5 * k, 'font-size': 11 * k, fill: '#fff', 'font-weight': 'bold' }, g);
      t.textContent = i + 1;
      const item = h('div', { className: 'pinrow' + (pin.status !== 'open' ? ' done' : '') },
        h('b', {}, `${i + 1} ${emoji} ${pin.severity}`), ` ${describeTarget(pin)}`, h('div', {}, pin.text || '(no text)'));
      item.onclick = () => editPin(pin.id);
      list.append(item);
    });
  }

  // ------------------------------------------------------------------ toolbar / keys
  function setTool(t) {
    tool = t; measure = null; if (ui) drawMeasure();
    document.querySelectorAll('[data-tool]').forEach((b) => b.classList.toggle('on', b.dataset.tool === t));
    $('stage').dataset.tool = t;
  }
  document.querySelectorAll('[data-tool]').forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
  $('fit').onclick = () => { S.ui.fit = !S.ui.fit; svg.classList.toggle('fit', S.ui.fit); $('fit').classList.toggle('on', S.ui.fit); save(); };
  $('grid').onclick = () => { S.ui.grid = !S.ui.grid; $('grid').classList.toggle('on', S.ui.grid); save(); };
  $('fit').classList.toggle('on', S.ui.fit); $('grid').classList.toggle('on', S.ui.grid);
  $('zoomfit').onclick = resetView;
  $('resetlayout').onclick = () => {
    if (!cur || !confirm('Reset all panels of this case to their original positions?')) return;
    delete S.poses[key(cur)]; save(); openCase(ci);
  };
  $('notes').oninput = (e) => { S.notes[key(cur)] = e.target.value; save(); };
  window.addEventListener('keydown', (e) => {
    if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    const step = e.altKey ? 0.01 : e.shiftKey ? 1 : 0.1;
    const k = e.key;
    if (k === 'v') setTool('select'); else if (k === 'p') setTool('pin'); else if (k === 'm') setTool('measure');
    else if (k === 'f') $('fit').click(); else if (k === 'g') $('grid').click();
    else if (k === 'Escape') { $('form').hidden = true; measure = null; drawMeasure(); select(null); }
    else if (k === 'r' || k === 'R') mutate((p) => { p.rot = (p.rot + (k === 'R' ? 270 : 90)) % 360; });
    else if (k === 'x') mutate((p) => { p.flip = !p.flip; });
    else if (k.startsWith('Arrow') && selected) {
      e.preventDefault();
      mutate((p) => { if (k === 'ArrowLeft') p.tx -= step; if (k === 'ArrowRight') p.tx += step; if (k === 'ArrowUp') p.ty -= step; if (k === 'ArrowDown') p.ty += step; });
    }
  });
  $('stage').addEventListener('contextmenu', (e) => e.preventDefault());

  // ------------------------------------------------------------------ export / import
  function snapshot() {
    const clone = svg.cloneNode(true);
    clone.querySelectorAll('.ui, .overlay, .hitfill, .ghost').forEach((n) => n.remove());
    return new XMLSerializer().serializeToString(clone);
  }
  function exportFeedback() {
    const cases = {};
    DATA.cases.forEach((c, i) => {
      const k = key(c), pins = S.pins.filter((p) => p.case === k), poses = S.poses[k], notes = S.notes[k];
      if (!pins.length && !poses && !notes) return;
      cases[k] = { house: c.house, material: c.material, notes: notes || '', pins, poses: poses || {} };
      if (i === ci) cases[k].svg_snapshot = snapshot();
    });
    const out = { schema: 'house-review/1', run: DATA.run, exported_at: new Date().toISOString(), cases };
    const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const a = h('a', { href: URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' })),
                      download: `house_review_${DATA.run}_${stamp}.json` });
    document.body.append(a); a.click(); a.remove();
    const n = S.pins.length;
    $('status').textContent = `Exported ${n} note(s). Move the downloaded file to the inbox: ${DATA.inbox}`;
  }
  $('export').onclick = exportFeedback;
  $('import').onchange = (e) => {
    const file = e.target.files[0]; if (!file) return;
    file.text().then((txt) => {
      const d = JSON.parse(txt);
      Object.entries(d.cases || {}).forEach(([k, c]) => {
        (c.pins || []).forEach((p) => { if (!S.pins.some((q) => q.id === p.id)) S.pins.push(p); });
        if (c.poses && Object.keys(c.poses).length) S.poses[k] = Object.assign(S.poses[k] || {}, c.poses);
        if (c.notes) S.notes[k] = c.notes;
      });
      save(); openCase(ci);
    });
  };

  buildSidebar();
  $('run').textContent = DATA.run;
  if (DATA.cases.length) openCase(0);
  setTool('select');
})();
