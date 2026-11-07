// Run by tests/test_viewer3d.py: node viewer3d_core_test.js <viewer_core.js>
const assert = require('assert');
const V = require(process.argv[2]);

const near = (a, b, tol = 1e-6, msg = '') => assert.ok(Math.abs(a - b) <= tol, `${msg} ${a} vs ${b}`);
const nearV = (a, b, tol = 1e-6, msg = '') => a.forEach((v, i) => near(v, b[i], tol, `${msg}[${i}]`));

// matrices: invert(m) * m = I, transform round-trips
{
  const m = V.mul(V.perspective(0.6, 1.5, 0.1, 500), V.lookAt([30, -40, 25], [1, 2, 3], [0, 0, 1]));
  const id = V.mul(V.invert(m), m);
  nearV(id, V.identity(), 1e-9, 'inverse');
  const p = [3, -7, 11];
  nearV(V.transform(V.invert(m), V.transform(m, p)), p, 1e-6, 'round trip');
}

// orbit camera: the eye sits dist away from the target along viewDir; pitch is clamped; yaw wraps
{
  const cam = V.camera([10, 20, 30], 50);
  near(V.len(V.sub(V.eye(cam), cam.target)), 50, 1e-9, 'distance');
  const t0 = cam.target.slice();
  V.orbit(cam, 0, 1e6);
  near(cam.pitch, V.PITCH_LIMIT, 1e-9, 'pitch clamp');
  V.orbit(cam, 0, -1e7);
  near(cam.pitch, -V.PITCH_LIMIT, 1e-9, 'pitch clamp low');
  V.orbit(cam, 1000, 0);
  assert.ok(cam.yaw >= -180 && cam.yaw < 180, 'yaw wraps');
  nearV(cam.target, t0, 0, 'orbit keeps the target');
}

// standard views look along the documented axes; the front view has +Y to the right, top has +Y right too
{
  const cam = V.camera([0, 0, 0], 10);
  const looks = { front: [-1, 0, 0], back: [1, 0, 0], right: [0, -1, 0], left: [0, 1, 0], top: [0, 0, -1], bottom: [0, 0, 1] };
  for (const [name, dir] of Object.entries(looks)) {
    V.setView(cam, name);
    nearV(V.scale(V.viewDir(cam), -1), dir, 1e-3, name);
  }
  V.setView(cam, 'front');
  nearV(V.screenAxes(cam)[0], [0, 1, 0], 1e-9, 'front: right is +Y');
  nearV(V.screenAxes(cam)[1], [0, 0, 1], 1e-9, 'front: up is +Z');
  V.setView(cam, 'top');
  nearV(V.screenAxes(cam)[0], [0, 1, 0], 1e-3, 'top: right is +Y');
  nearV(V.screenAxes(cam)[1], [-1, 0, 0], 1e-3, 'top: the front (+X) is at the bottom');
}

// picking ray through the screen centre passes through the target (perspective and ortho)
for (const ortho of [false, true]) {
  const cam = V.camera([5, 6, 7], 80);
  cam.ortho = ortho;
  const r = V.ray(cam, 1.6, 40, 0, 0);
  const toTarget = V.sub(cam.target, r.origin);
  nearV(V.cross(r.dir, V.norm(toTarget)), [0, 0, 0], 1e-6, `centre ray ortho=${ortho}`);
  nearV(V.focalPoint(cam, r), cam.target, 1e-6, `focal point ortho=${ortho}`);
}

// pan moves the target in the screen plane; zoomAbout keeps the pivot's screen position
{
  const cam = V.camera([0, 0, 0], 100);
  V.setView(cam, 'front');
  V.pan(cam, 10, 0, 500);
  assert.ok(cam.target[1] < 0 && Math.abs(cam.target[0]) < 1e-9 && Math.abs(cam.target[2]) < 1e-9, 'drag right: target moves -Y');
  const p = [0, 15, 8], aspect = 1.5, R = 50;
  const screen = (c) => V.transform(V.mul(V.projMatrix(c, aspect, R), V.viewMatrix(c)), p);
  for (const ortho of [false, true]) {
    cam.ortho = ortho;
    const before = screen(cam);
    V.zoomAbout(cam, 0.5, p);
    const after = screen(cam);
    near(after[0], before[0], 1e-6, `zoom x ortho=${ortho}`);
    near(after[1], before[1], 1e-6, `zoom y ortho=${ortho}`);
  }
}

// pivotAbout keeps the eye where it is
{
  const cam = V.camera([0, 0, 0], 100);
  const e0 = V.eye(cam);
  V.pivotAbout(cam, [10, -5, 3]);
  nearV(V.eye(cam), e0, 1e-6, 'pivot keeps the eye');
  nearV(cam.target, [10, -5, 3], 0, 'pivot target');
}

// a unit cube as the model's flat vertex/triangle lists (outward CCW)
const cube = (() => {
  const v = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1];
  const t = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7];
  return { vertices: v, triangles: t, explode: [0, 0, 1] };
})();

// edges: a cube has 12 feature edges (the face diagonals are flat), 18 triangle edges
assert.strictEqual(V.featureEdges(cube.vertices, cube.triangles).length / 6, 12, 'cube feature edges');
assert.strictEqual(V.wireEdges(cube.vertices, cube.triangles).length / 6, 18, 'cube wire edges');
{
  const f = V.flatten(cube.vertices, cube.triangles);
  assert.strictEqual(f.positions.length, 36 * 3);
  nearV(f.normals.slice(0, 3), [0, 0, -1], 1e-9, 'bottom face normal points out');
}

// picking hits the nearest face, honours offsets and the section plane
{
  const r = { origin: [0.5, 0.5, 10], dir: [0, 0, -1] };
  const hit = V.pick(r, [cube]);
  near(hit.point[2], 1, 1e-9, 'top face');
  const moved = V.pick(r, [cube], (p) => V.explodeOffset(p, 2));
  near(moved.point[2], 3, 1e-9, 'exploded by 2 along +Z');
  const cut = V.sectionPlane(2, 0.5);                          // keep z <= 0.5
  const below = V.pick(r, [cube], undefined, (pt) => V.keeps(cut, pt));
  near(below.point[2], 0, 1e-9, 'section: the top face is cut away, the bottom one is hit');
  assert.strictEqual(V.pick({ origin: [5, 5, 10], dir: [0, 0, -1] }, [cube]), null, 'miss');
}

// section plane: which side is kept
{
  const p = V.sectionPlane(0, 10);
  assert.ok(V.keeps(p, [9, 0, 0]) && V.keeps(p, [10, 0, 0]) && !V.keeps(p, [11, 0, 0]));
  const f = V.sectionPlane(0, 10, true);
  assert.ok(!V.keeps(f, [9, 0, 0]) && V.keeps(f, [11, 0, 0]));
}

// bounds with offsets; frame fits the sphere
{
  const b = V.bounds([{ vertices: cube.vertices, offset: [10, 0, 0] }]);
  nearV(b.min, [10, 0, 0]); nearV(b.max, [11, 1, 1]); near(b.radius, Math.sqrt(3) / 2);
  const cam = V.camera();
  V.frame(cam, b.centre, b.radius);
  assert.ok(cam.dist * Math.sin(cam.fovy / 2) >= b.radius, 'framed');
}

// colours are valid and differ between neighbours
for (let i = 0; i < 30; i++) {
  const c = V.distinctColor(i), d = V.distinctColor(i + 1);
  c.forEach((v) => assert.ok(v >= 0 && v <= 1));
  assert.ok(V.len(V.sub(c, d)) > 0.1, `colour ${i} vs ${i + 1}`);
}

// wheel: pinch zooms, shift pans, mouse-like steps zoom, trackpad swipes orbit; the mode overrides the guess
{
  const w = (o) => ({ deltaMode: 0, deltaX: 0, deltaY: 3, ctrlKey: false, shiftKey: false, ...o });
  assert.strictEqual(V.wheelAction(w({ ctrlKey: true })), 'pinch');
  assert.strictEqual(V.wheelAction(w({ shiftKey: true })), 'pan');
  assert.strictEqual(V.wheelAction(w({ deltaY: 100 })), 'zoom');
  assert.strictEqual(V.wheelAction(w({ deltaMode: 1 })), 'zoom');
  assert.strictEqual(V.wheelAction(w({ deltaX: 2.5, deltaY: 1.5 })), 'orbit');
  assert.strictEqual(V.wheelAction(w({ deltaY: 100 }), 'trackpad'), 'orbit');
  assert.strictEqual(V.wheelAction(w({ deltaY: 3 }), 'mouse'), 'zoom');
}

console.log('ok: viewer3d core');
