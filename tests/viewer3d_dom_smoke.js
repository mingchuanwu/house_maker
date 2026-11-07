// Run by tests/test_viewer3d.py: JSDOM_PATH=... node viewer3d_dom_smoke.js <page.html>
// jsdom has no WebGL: the page must say so, and everything that does not draw (outliner, selection by click,
// visibility, toolbar state) must still work.
const assert = require('assert');
const fs = require('fs');
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_PATH);

const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', (e) => { if (!/getContext|HTMLCanvasElement/.test(String(e.message || e))) errors.push(e); });
const dom = new JSDOM(fs.readFileSync(process.argv[2], 'utf8'), { runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc });
const { window } = dom;
const doc = window.document;
const v = window.__viewer;
assert.ok(v, 'the app started');
assert.deepStrictEqual(errors, [], 'no script errors');

assert.ok(!doc.querySelector('#msg').hidden && /WebGL/.test(doc.querySelector('#msg').textContent), 'no-WebGL message');
// with WebGL the message is hidden - and must then not cover the canvas (it would swallow every pointer/wheel event)
doc.querySelector('#msg').hidden = true;
assert.strictEqual(window.getComputedStyle(doc.querySelector('#msg')).display, 'none', 'hidden message box is gone');
doc.querySelector('#msg').hidden = false;

const rows = doc.querySelectorAll('.row.part');
assert.strictEqual(rows.length, v.parts.length, 'one outliner row per part');
assert.ok(doc.querySelectorAll('.row.head').length >= 3, 'groups');

// select from the outliner
const name = 'gable_wall_front';
const row = doc.querySelector(`.row.part[data-name="${name}"]`);
row.click();
assert.strictEqual(v.state.selected, name);
assert.ok(row.classList.contains('sel'));
assert.ok(doc.querySelector('#selinfo').textContent.includes(name));
row.click();
assert.strictEqual(v.state.selected, null, 'clicking again deselects');

// hide / isolate / group / show all
row.querySelector('.eye').click();
assert.ok(v.state.hidden.has(name) && row.classList.contains('off'));
row.querySelector('.solo').click();
assert.strictEqual(v.state.solo, name);
assert.strictEqual(v.parts.filter(v.visible).length, 1, 'isolate shows one part');
row.querySelector('.solo').click();
assert.strictEqual(v.state.solo, null);
const casings = doc.querySelector('.row.head[data-group="casings"] .eye');
casings.click();
assert.ok(v.parts.filter((p) => p.group === 'casings').every((p) => !v.visible(p)), 'group hidden');
v.showAll();
assert.strictEqual(v.parts.filter(v.visible).length, v.parts.length, 'show all');

// keys and toolbar
const key = (code, o = {}) => doc.dispatchEvent(new window.KeyboardEvent('keydown', { code, bubbles: true, ...o }));
key('Digit3');
assert.strictEqual(v.cam.yaw, 90, 'right view');
key('Digit3', { ctrlKey: true });
assert.strictEqual(v.cam.yaw, -90, 'left view');
key('Digit5');
assert.strictEqual(v.cam.ortho, true, 'orthographic');
const explode = doc.querySelector('#explode');
explode.value = '6';
explode.dispatchEvent(new window.Event('input'));
assert.strictEqual(v.state.explode, 6);
const section = doc.querySelector('#section');
section.checked = true;
section.dispatchEvent(new window.Event('change'));
assert.strictEqual(v.state.section.on, true);

console.log('dom smoke test passed');
