// Run by tests/test_review_tool.py: node review_core_test.js <viewer_core.js> < cases.json
const assert = require('assert');
const HR = require(process.argv[2]);
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));

const near = (a, b, tol = 1e-6, msg = '') => assert.ok(Math.abs(a - b) <= tol, `${msg} ${a} vs ${b}`);
const pose0 = (meta) => ({ tx: 0, ty: 0, rot: 0, flip: false });

// matrices
{
  const m = HR.panelMatrix({ tx: 5, ty: -3, rot: 90, flip: true }, [10, 20]);
  const p = [3, 4], q = HR.apply(HR.invert(m), HR.apply(m, p));
  near(q[0], p[0]); near(q[1], p[1]);
  const id = HR.panelMatrix({ tx: 7, ty: 8, rot: 0, flip: false }, [1, 2]);
  assert.deepStrictEqual(id.map((v) => +v.toFixed(9)), [1, 0, 0, 1, 7, 8]);   // == translate(7,8)
}

// cut path data of one panel, taken from the case's SVG
const cutPath = (c, name) => {
  const g = new RegExp('<g id="' + name + '"[^>]*>([\\s\\S]*?)</g>').exec(c.svg)[1];
  return [...g.matchAll(/class="cut-line" d="([^"]+)"/g)].map((m) => m[1]).join(' ');
};

// overlap primitives
{
  const sq = (x, y, w, h) => `M ${x},${y} L ${x + w},${y} L ${x + w},${y + h} L ${x},${y + h} Z`;
  const I = [1, 0, 0, 1, 0, 0];
  near(HR.overlap(sq(0, 0, 10, 10), I, sq(6, 4, 10, 10), I).area, 4 * 6, 0.2, 'rect overlap');
  near(HR.overlap(sq(0, 0, 10, 10) + ' ' + sq(2, 2, 6, 6), I, sq(0, 0, 10, 10), I).area, 100 - 36, 0.3, 'hole is not material');
  assert.strictEqual(HR.overlap(sq(0, 0, 5, 5), I, sq(5.5, 0, 5, 5), I).area, 0);
  const rot = HR.panelMatrix({ tx: 0, ty: 0, rot: 90, flip: false }, [5, 5]);                // same square, rotated about centre
  near(HR.overlap(sq(0, 0, 10, 10), I, sq(0, 0, 10, 10), rot).area, 100, 1.5, 'rotated overlap');
  near(HR.overlap('M 0,0 Q 5,10 10,0 Z', I, sq(0, -1, 10, 3), I).area > 0 ? 1 : 0, 1, 0, 'curve flattened');
}

let snaps = 0, withFingers = 0, overlapChecked = 0;
for (const c of cases) {
  const by = Object.fromEntries(c.panels.map((p) => [p.name, p]));
  for (const m of c.mates.filter((m) => m.kind === 'edge')) {
    const A = by[m.a[0]], B = by[m.b[0]];
    // A sits at an arbitrary pose; B must land on it
    const poseA = { tx: 12.5, ty: -7, rot: 37, flip: false };
    const poseB = HR.snapPose(A, poseA, m.a[1], B, m.b[1], m.shift);
    assert.ok(poseB, `${c.case}: snap failed for ${JSON.stringify(m)}`);
    const MA = HR.panelMatrix(poseA, HR.centre(A)), MB = HR.panelMatrix(poseB, HR.centre(B));
    const ea = HR.edgeOf(A, m.a[1]), eb = HR.edgeOf(B, m.b[1]);
    // every point of B's edge meets A's edge at s_a = shift + len_b - s_b
    for (const sb of [0, eb.len * 0.3, eb.len]) {
      const pb = [eb.a[0] + (eb.b[0] - eb.a[0]) * sb / eb.len, eb.a[1] + (eb.b[1] - eb.a[1]) * sb / eb.len];
      const sa = m.shift + eb.len - sb;
      const pa = [ea.a[0] + (ea.b[0] - ea.a[0]) * sa / ea.len, ea.a[1] + (ea.b[1] - ea.a[1]) * sa / ea.len];
      const X = HR.apply(MB, pb), Y = HR.apply(MA, pa);
      near(X[0], Y[0], 1e-6, `${c.case} ${m.a}↔${m.b} x`); near(X[1], Y[1], 1e-6, `${c.case} ${m.a}↔${m.b} y`);
    }
    // the two bodies are on opposite sides of the shared edge line
    const a0 = HR.apply(MA, ea.a), a1 = HR.apply(MA, ea.b);
    const side = (pt) => (a1[0] - a0[0]) * (pt[1] - a0[1]) - (a1[1] - a0[1]) * (pt[0] - a0[0]);
    const cent = (meta, M) => { const cs = meta.corners.map((p) => HR.apply(M, p));
      return [cs.reduce((s, p) => s + p[0], 0) / cs.length, cs.reduce((s, p) => s + p[1], 0) / cs.length]; };
    assert.ok(side(cent(A, MA)) * side(cent(B, MB)) < 0, `${c.case}: ${m.a}↔${m.b} bodies overlap, not adjacent`);
    // swapping roles gives the same arrangement
    const back = HR.snapPose(B, poseB, m.b[1], A, m.a[1], HR.swapShift(m.shift, ea.len, eb.len));
    const MA2 = HR.panelMatrix(back, HR.centre(A));
    const t0 = HR.apply(MA, ea.a), t1 = HR.apply(MA2, ea.a);
    near(t0[0], t1[0], 1e-6, 'swap x'); near(t0[1], t1[1], 1e-6, 'swap y');
    snaps++;
    // End-to-end fit check: with the panels snapped, the material that overlaps is exactly the
    // kerf interference of the fingers (tab depth t+k vs notch depth t-k) - nothing more.
    if (A.joints[m.a[1]] && c.svg) {
      const ov = HR.overlap(cutPath(c, A.name), MA, cutPath(c, B.name), MB);
      const exp = HR.kerfInterference(A, m.a[1], B, m.b[1]);
      assert.ok(Math.abs(ov.area - exp) <= Math.max(0.12 * exp, 0.2), `${c.case} ${m.a}↔${m.b}: overlap ${ov.area.toFixed(3)} vs kerf-expected ${exp.toFixed(3)}`);
      overlapChecked++;
    }
    if (A.joints[m.a[1]]) {
      withFingers++;
      const ki = HR.kerfInterference(A, m.a[1], B, m.b[1]);
      const male = A.joints[m.a[1]].role === 'male' ? A : B;
      const mj = male.joints[male === A ? m.a[1] : m.b[1]];
      const expect = mj.fingers.length * 2 * c.material.kerf * Math.abs(mj.depth);   // 2k wider tab x depth, per finger
      near(ki, expect, 1e-6, 'kerf interference');
    }
  }
}
assert.ok(overlapChecked >= 15, `too few overlap checks: ${overlapChecked}`);
assert.ok(snaps >= 20 && withFingers >= 15, `too few mates exercised: ${snaps}/${withFingers}`);

// hit testing on a real wall panel
{
  const c = cases.find((x) => x.case.includes('gable_wall_to_roof'));
  const roof = c.panels.find((p) => p.name === 'roof_panel_left');
  const s = roof.slots[0];
  assert.strictEqual(HR.nearestTarget(roof, [s.cx, s.cy]).type, 'slot');
  const j = roof.joints.ridge, f = j.fingers[0];
  const t = HR.nearestTarget(roof, [(f[0] + f[1]) / 2, -1]);       // just inside a ridge notch region
  assert.ok(['finger', 'edge'].includes(t.type), JSON.stringify(t));
  assert.strictEqual(HR.nearestTarget(roof, [roof.nominal_size[0] / 2, roof.nominal_size[1] / 2]).type, 'panel');
  const g = HR.tabGhost(c.panels.find((p) => p.name === 'gable_wall_front'), 'roof_left', roof, 0, c.material.thickness);
  near(g.w, c.material.thickness); near(g.h, 15);
}
console.log(`ok: ${snaps} edge mates snapped, ${withFingers} with fingers, ${overlapChecked} overlap-verified`);
