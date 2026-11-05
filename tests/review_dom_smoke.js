// DOM smoke test of the review page in jsdom. usage: node review_dom_smoke.js <review.html>
// jsdom has no SVG layout or canvas, so the CTM is stubbed (identity + the outer group's 10mm margin);
// the canvas-based overlap analysis is exercised only in a real browser.
const fs = require('fs');
const assert = require('assert');
const { JSDOM } = require(process.env.JSDOM_PATH || 'jsdom');

const html = fs.readFileSync(process.argv[2], 'utf8');
const downloads = [];
const dom = new JSDOM(html, {
  url: 'http://localhost/review.html', runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(win) {
    const mat = (e, f) => ({ a: 1, b: 0, c: 0, d: 1, e, f, inverse() { return mat(-e, -f); } });
    win.SVGElement.prototype.getScreenCTM = function () { return this.id === 'house_box_panels' ? mat(10, 10) : mat(0, 0); };
    win.SVGSVGElement.prototype.createSVGPoint = function () {
      return { x: 0, y: 0, matrixTransform(m) { return { x: this.x + m.e, y: this.y + m.f }; } };
    };
    win.SVGElement.prototype.setPointerCapture = function () {};
    win.URL.createObjectURL = (blob) => { downloads.push({ blob }); return 'blob:x'; };
    const realClick = win.HTMLAnchorElement.prototype.click;
    win.HTMLAnchorElement.prototype.click = function () {
      if (this.download) downloads[downloads.length - 1].name = this.download; else realClick.call(this);
    };
    win.confirm = () => true; win.alert = (m) => { throw new Error('alert: ' + m); };
    win.addEventListener('error', (e) => { throw e.error || new Error(e.message); });
  },
});
const { window: win } = dom, doc = win.document;
const $ = (id) => doc.getElementById(id);
const fire = (target, type, init = {}) =>
  target.dispatchEvent(new win.MouseEvent(type, Object.assign({ bubbles: true, cancelable: true, button: 0 }, init)));
const key = (k, extra = {}) => doc.dispatchEvent(new win.KeyboardEvent('keydown', Object.assign({ key: k, bubbles: true }, extra)));
const state = () => JSON.parse(win.localStorage.getItem([...Object.keys(win.localStorage)].find((k) => k.startsWith('house_review:'))));
const pose = (name) => { const m = /matrix\(([^)]+)\)/.exec(doc.getElementById(name).getAttribute('transform')); return m[1].split(' ').map(Number); };

const data = JSON.parse($('review-data').textContent);
assert.ok(data.cases.length >= 5, 'cases embedded');
assert.ok(doc.querySelectorAll('.case').length === data.cases.length, 'sidebar lists every case');

function open(name) {
  const i = data.cases.findIndex((c) => c.case === name);
  assert.ok(i >= 0, 'no case ' + name);
  $('case' + i).click();
  return data.cases[i];
}

// ---- select + drag
const c1 = open('floor_to_side_wall_a30');
assert.ok($('stage').querySelector('svg'), 'svg injected');
assert.ok(doc.querySelectorAll('.hitfill').length === c1.panels.length, 'hit areas created');
const floorFill = doc.querySelector('g[id="floor"] .hitfill');
const before = pose('floor');
fire(floorFill, 'pointerdown', { clientX: 50, clientY: 50 });
assert.ok(doc.getElementById('floor').classList.contains('sel'), 'floor selected');
fire(win.document.querySelector('#stage svg'), 'pointermove', { clientX: 70, clientY: 65 });
fire(win.document.querySelector('#stage svg'), 'pointerup', { clientX: 70, clientY: 65 });
const after = pose('floor');
assert.ok(Math.abs(after[4] - before[4] - 20) < 1e-6 && Math.abs(after[5] - before[5] - 15) < 1e-6, `dragged by (20,15): ${before} -> ${after}`);
assert.ok(Object.keys(state().poses['box_seams/floor_to_side_wall_a30']).includes('floor'), 'pose persisted');

// ---- keyboard rotate / flip / nudge
key('r');
assert.ok(Math.abs(pose('floor')[1] - 1) < 1e-9, 'rotated 90°');   // b = sin(90°)
key('ArrowRight', { shiftKey: true });
key('x');
assert.ok(state().poses['box_seams/floor_to_side_wall_a30'].floor.flip === true, 'flip stored');
key('x'); key('R');                                              // back to rot 0
assert.ok(Math.abs(pose('floor')[1]) < 1e-9, 'rotated back');

// ---- snap to mate: reset first, then snap the side wall onto the floor
$('resetlayout').click();
fire(doc.querySelector('g[id="side_wall_left"] .hitfill'), 'pointerdown', { clientX: 5, clientY: 5 });
const mateButtons = [...doc.querySelectorAll('button.mate')];
assert.ok(mateButtons.length >= 1, 'mate button listed');
mateButtons[0].click();
const HR = require(require('path').resolve(__dirname, '../review/viewer_core.js'));
const mate = c1.mates.find((m) => m.kind === 'edge');
const A = c1.panels.find((p) => p.name === mate.a[0]), B = c1.panels.find((p) => p.name === mate.b[0]);
const st = state().poses['box_seams/floor_to_side_wall_a30'];
const mv = st[B.name] || st[A.name];
assert.ok(mv, 'snapped panel has a stored pose');
assert.ok($('overlaps'), 'overlap readout present');
assert.ok(/kerf-expected/.test($('overlaps').textContent), 'snapped fingers report kerf-expected overlap: ' + $('overlaps').textContent);
assert.ok(doc.querySelectorAll('rect.overlap').length > 0, 'overlap drawn');
assert.ok(Math.abs(mv.rot - 0) > 1e-6 || Math.abs(mv.tx) + Math.abs(mv.ty) > 1, 'snapped pose differs from original');

// ---- note (pin) on an edge
key('Escape'); key('p');
const wallFill = doc.querySelector('g[id="floor"] .hitfill');
const poseNow = pose('floor');
// click near the floor's bottom edge: local (width/2, 0) -> F = matrix * local
const m = HR.panelMatrix({ tx: 0, ty: 0, rot: 0, flip: false }, [0, 0]);
fire(wallFill, 'pointerdown', { clientX: 0, clientY: 0 });
assert.ok(!$('form').hidden, 'note form opened');
const ta = $('form').querySelector('textarea'); ta.value = 'finger 2 looks 0.3mm too narrow';
$('form').querySelector('select').value = 'bug';
[...$('form').querySelectorAll('button')].find((b) => b.textContent === 'Save').click();
assert.strictEqual(state().pins.length, 1, 'pin saved');
assert.strictEqual(state().pins[0].text, 'finger 2 looks 0.3mm too narrow');
assert.ok(state().pins[0].target && state().pins[0].case === 'box_seams/floor_to_side_wall_a30');
assert.ok(doc.querySelectorAll('.pin').length === 1 && doc.querySelectorAll('.pinrow').length === 1, 'pin drawn and listed');

// ---- export
$('export').click();
assert.strictEqual(downloads.length, 1);
assert.ok(/^house_review_.*\.json$/.test(downloads[0].name), downloads[0].name);
const reader = new win.FileReader();
reader.onload = () => {
  const out = JSON.parse(reader.result);
  const c = out.cases['box_seams/floor_to_side_wall_a30'];
  assert.strictEqual(out.schema, 'house-review/1');
  assert.strictEqual(c.pins.length, 1);
  assert.ok(Object.keys(c.poses).length >= 1, 'arrangement exported');
  assert.ok(c.svg_snapshot.includes('<svg') && !c.svg_snapshot.includes('hitfill'), 'clean svg snapshot');
  assert.ok(c.house.dimensions && c.material.kerf !== undefined, 'case parameters exported');
  console.log('ok: dom smoke test passed (' + data.cases.length + ' cases)');
  win.close();
};
reader.readAsText(downloads[0].blob);
