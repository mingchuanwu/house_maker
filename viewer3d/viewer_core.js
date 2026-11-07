/* Pure maths for the 3D viewer (no DOM, no WebGL) - unit-tested with node.
 * World: millimetres, Z up. Matrices are 4x4, column-major (WebGL): m[col * 4 + row]. */
const V3 = (() => {
  const RAD = Math.PI / 180;
  const PITCH_LIMIT = 89.99;

  // ------------------------------------------------------------------ vectors
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const len = (a) => Math.sqrt(dot(a, a));
  const norm = (a) => { const l = len(a); return l === 0 ? [0, 0, 0] : scale(a, 1 / l); };

  // ------------------------------------------------------------------ matrices
  const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  const mul = (a, b) => {
    const o = new Array(16).fill(0);
    for (let c = 0; c < 4; c++)
      for (let r = 0; r < 4; r++)
        for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
    return o;
  };
  const perspective = (fovy, aspect, near, far) => {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  };
  const ortho = (l, r, b, t, n, f) => [
    2 / (r - l), 0, 0, 0, 0, 2 / (t - b), 0, 0, 0, 0, -2 / (f - n), 0,
    -(r + l) / (r - l), -(t + b) / (t - b), -(f + n) / (f - n), 1];
  const lookAt = (eye, target, up) => {
    const f = norm(sub(target, eye)), s = norm(cross(f, up)), u = cross(s, f);
    return [s[0], u[0], -f[0], 0, s[1], u[1], -f[1], 0, s[2], u[2], -f[2], 0,
            -dot(s, eye), -dot(u, eye), dot(f, eye), 1];
  };
  const invert = (m) => {
    const inv = new Array(16);
    inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
    inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
    inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
    inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
    inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
    inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
    inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
    inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
    inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
    inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
    inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
    inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
    inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
    inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
    inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
    inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5];
    const det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
    return inv.map((v) => v / det);
  };
  const transform = (m, p) => {
    const x = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12];
    const y = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13];
    const z = m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14];
    const w = m[3] * p[0] + m[7] * p[1] + m[11] * p[2] + m[15];
    return [x / w, y / w, z / w];
  };

  // ------------------------------------------------------------------ orbit camera
  // yaw: degrees around +Z from +X; pitch: degrees above the XY plane; the eye sits at target + dist * dir.
  const camera = (target = [0, 0, 0], dist = 100) => ({ target, yaw: 45, pitch: 35.264, dist, ortho: false, fovy: 35 * RAD });
  const viewDir = (cam) => {
    const y = cam.yaw * RAD, p = cam.pitch * RAD;
    return [Math.cos(p) * Math.cos(y), Math.cos(p) * Math.sin(y), Math.sin(p)];
  };
  const eye = (cam) => add(cam.target, scale(viewDir(cam), cam.dist));
  const clampPitch = (p) => Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, p));
  const viewMatrix = (cam) => lookAt(eye(cam), cam.target, [0, 0, 1]);
  const halfHeight = (cam) => cam.dist * Math.tan(cam.fovy / 2);          // world units from screen centre to top
  const projMatrix = (cam, aspect, radius) => {
    const far = cam.dist + 4 * radius;
    if (cam.ortho) {
      const h = halfHeight(cam);
      return ortho(-h * aspect, h * aspect, -h, h, -4 * radius, far);
    }
    return perspective(cam.fovy, aspect, Math.max(cam.dist * 0.01, 0.01), far);
  };
  /** Screen axes in world space: [right, up]. */
  const screenAxes = (cam) => {
    const f = scale(viewDir(cam), -1), r = norm(cross(f, [0, 0, 1]));
    return [r, cross(r, f)];
  };
  /** Drag by (dx, dy) pixels (y down): the model follows the pointer. */
  const orbit = (cam, dx, dy, k = 0.4) => {
    cam.yaw = ((cam.yaw - dx * k) % 360 + 540) % 360 - 180;
    cam.pitch = clampPitch(cam.pitch + dy * k);
  };
  const pan = (cam, dx, dy, viewportHeight) => {
    const upp = 2 * halfHeight(cam) / viewportHeight, [r, u] = screenAxes(cam);
    cam.target = add(cam.target, add(scale(r, -dx * upp), scale(u, dy * upp)));
  };
  /** Scale the view by `f` (< 1 zooms in) about world point `p`, which stays put on screen. */
  const zoomAbout = (cam, f, p) => {
    cam.target = add(p, scale(sub(cam.target, p), f));
    cam.dist *= f;
  };
  /** Orbit around `p` from now on, without moving the eye. */
  const pivotAbout = (cam, p) => {
    const d = sub(eye(cam), p), l = len(d);
    if (l < 1e-9) return;
    cam.target = p.slice();
    cam.dist = l;
    cam.yaw = Math.atan2(d[1], d[0]) / RAD;
    cam.pitch = clampPitch(Math.asin(Math.max(-1, Math.min(1, d[2] / l))) / RAD);
  };
  // the front of the house is its +X face (gable_wall_front); front view looks along -X with +Y to the right
  const VIEWS = {
    front: [0, 0], back: [180, 0], right: [90, 0], left: [-90, 0],
    top: [0, PITCH_LIMIT], bottom: [0, -PITCH_LIMIT], iso: [45, 35.264],
  };
  const setView = (cam, name) => { [cam.yaw, cam.pitch] = VIEWS[name]; };
  /** Fit a sphere (centre, radius) in the view. */
  const frame = (cam, centre, radius) => {
    cam.target = centre.slice();
    cam.dist = Math.max(radius, 1e-3) / Math.sin(cam.fovy / 2) * 1.1;
  };

  // ------------------------------------------------------------------ picking
  /** World ray through normalised device coordinates (x, y in [-1, 1], y up). */
  const ray = (cam, aspect, radius, nx, ny) => {
    const inv = invert(mul(projMatrix(cam, aspect, radius), viewMatrix(cam)));
    const a = transform(inv, [nx, ny, -1]), b = transform(inv, [nx, ny, 1]);
    return { origin: a, dir: norm(sub(b, a)) };
  };
  /** Point where the ray meets the plane through the target facing the camera. */
  const focalPoint = (cam, r) => {
    const n = viewDir(cam), d = dot(r.dir, n);
    if (Math.abs(d) < 1e-12) return cam.target.slice();
    return add(r.origin, scale(r.dir, dot(sub(cam.target, r.origin), n) / d));
  };
  /** Distance along the ray to triangle (a, b, c), or null (Moller-Trumbore, both faces). */
  const hitTriangle = (r, a, b, c) => {
    const e1 = sub(b, a), e2 = sub(c, a), p = cross(r.dir, e2), det = dot(e1, p);
    if (Math.abs(det) < 1e-12) return null;
    const s = sub(r.origin, a), u = dot(s, p) / det;
    if (u < 0 || u > 1) return null;
    const q = cross(s, e1), v = dot(r.dir, q) / det;
    if (v < 0 || u + v > 1) return null;
    const t = dot(e2, q) / det;
    return t > 0 ? t : null;
  };
  /** Nearest hit among `parts` ({vertices, triangles}); offset(part) moves a part, keep(point) filters (section). */
  const pick = (r, parts, offset = () => [0, 0, 0], keep = () => true) => {
    let best = null;
    for (const part of parts) {
      const o = offset(part), v = part.vertices, t = part.triangles;
      const at = (i) => [v[3 * i] + o[0], v[3 * i + 1] + o[1], v[3 * i + 2] + o[2]];
      for (let k = 0; k < t.length; k += 3) {
        const d = hitTriangle(r, at(t[k]), at(t[k + 1]), at(t[k + 2]));
        if (d === null || (best && d >= best.t)) continue;
        const point = add(r.origin, scale(r.dir, d));
        if (keep(point)) best = { part, t: d, point };
      }
    }
    return best;
  };

  // ------------------------------------------------------------------ meshes
  const triNormal = (a, b, c) => norm(cross(sub(b, a), sub(c, a)));
  /** Flat-shaded, unindexed copy for WebGL: {positions, normals} as flat arrays (3 per vertex). */
  const flatten = (vertices, triangles) => {
    const positions = [], normals = [];
    for (let k = 0; k < triangles.length; k += 3) {
      const p = [0, 1, 2].map((j) => { const i = triangles[k + j]; return [vertices[3 * i], vertices[3 * i + 1], vertices[3 * i + 2]]; });
      const n = triNormal(p[0], p[1], p[2]);
      for (const q of p) { positions.push(...q); normals.push(...n); }
    }
    return { positions, normals };
  };
  const posKey = (v, i) => `${Math.round(v[3 * i] * 1e4)},${Math.round(v[3 * i + 1] * 1e4)},${Math.round(v[3 * i + 2] * 1e4)}`;
  /** Edges where the surface folds by more than `angleDeg` (or that border one face): flat [x,y,z, x,y,z, ...]. */
  const featureEdges = (vertices, triangles, angleDeg = 20) => {
    const ids = new Map(), id = (i) => { const k = posKey(vertices, i); if (!ids.has(k)) ids.set(k, i); return ids.get(k); };
    const edges = new Map(), cosMax = Math.cos(angleDeg * RAD), at = (i) => [vertices[3 * i], vertices[3 * i + 1], vertices[3 * i + 2]];
    for (let k = 0; k < triangles.length; k += 3) {
      const t = [id(triangles[k]), id(triangles[k + 1]), id(triangles[k + 2])];
      const n = triNormal(at(t[0]), at(t[1]), at(t[2]));
      for (let j = 0; j < 3; j++) {
        const a = t[j], b = t[(j + 1) % 3], key = a < b ? `${a}|${b}` : `${b}|${a}`;
        if (!edges.has(key)) edges.set(key, { a, b, normals: [] });
        edges.get(key).normals.push(n);
      }
    }
    const out = [];
    for (const e of edges.values()) {
      const ns = e.normals;
      if (ns.length === 1 || ns.length > 2 || dot(ns[0], ns[1]) < cosMax) out.push(...at(e.a), ...at(e.b));
    }
    return out;
  };
  /** Every triangle edge once: flat [x,y,z, x,y,z, ...]. */
  const wireEdges = (vertices, triangles) => {
    const seen = new Set(), out = [], at = (i) => [vertices[3 * i], vertices[3 * i + 1], vertices[3 * i + 2]];
    for (let k = 0; k < triangles.length; k += 3)
      for (let j = 0; j < 3; j++) {
        const a = triangles[k + j], b = triangles[k + (j + 1) % 3], key = a < b ? `${a}|${b}` : `${b}|${a}`;
        if (!seen.has(key)) { seen.add(key); out.push(...at(a), ...at(b)); }
      }
    return out;
  };
  /** {min, max, centre, radius} of flat vertex arrays, each moved by its offset. */
  const bounds = (items) => {
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (const { vertices, offset = [0, 0, 0] } of items)
      for (let i = 0; i < vertices.length; i += 3)
        for (let a = 0; a < 3; a++) {
          const c = vertices[i + a] + offset[a];
          if (c < min[a]) min[a] = c;
          if (c > max[a]) max[a] = c;
        }
    if (min[0] === Infinity) return { min: [0, 0, 0], max: [0, 0, 0], centre: [0, 0, 0], radius: 1 };
    const centre = scale(add(min, max), 0.5);
    return { min, max, centre, radius: Math.max(len(sub(max, centre)), 1e-3) };
  };
  const explodeOffset = (part, amount) => scale(part.explode || [0, 0, 0], amount);

  // ------------------------------------------------------------------ section plane
  /** Plane [a, b, c, d]: a fragment p is cut away where a*x + b*y + c*z + d > 0. Keeps p[axis] <= pos (flip: >=). */
  const sectionPlane = (axis, pos, flip = false) => {
    const p = [0, 0, 0, 0];
    p[axis] = flip ? -1 : 1;
    p[3] = flip ? pos : -pos;
    return p;
  };
  const keeps = (plane, p) => plane[0] * p[0] + plane[1] * p[1] + plane[2] * p[2] + plane[3] <= 1e-9;

  // ------------------------------------------------------------------ colours and input
  /** Distinct colour for part i (golden-angle hues), RGB in [0, 1]. */
  const distinctColor = (i) => {
    const h = (i * 137.508) % 360, s = 0.55, l = i % 2 ? 0.52 : 0.64;
    const k = (n) => (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
    const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
    return [f(0), f(8), f(4)];
  };
  /** Does a wheel event come from a mouse wheel rather than a trackpad? (line/page mode or a big pure-vertical step) */
  const looksLikeMouse = (e) => e.deltaMode !== 0 || (e.deltaX === 0 && Math.abs(e.deltaY) >= 50);
  /** What a wheel event does: 'pinch' (zoom), 'zoom', 'pan' or 'orbit'. mode: 'auto' | 'trackpad' | 'mouse'. */
  const wheelAction = (e, mode = 'auto') => {
    if (e.ctrlKey) return 'pinch';                           // trackpad pinch arrives as ctrl+wheel
    if (e.shiftKey) return 'pan';
    const mouse = mode === 'mouse' || (mode === 'auto' && looksLikeMouse(e));
    return mouse ? 'zoom' : 'orbit';
  };

  return { RAD, add, sub, scale, dot, cross, len, norm, identity, mul, perspective, ortho, lookAt, invert, transform,
           camera, viewDir, eye, viewMatrix, projMatrix, screenAxes, orbit, pan, zoomAbout, pivotAbout, VIEWS, setView,
           frame, ray, focalPoint, hitTriangle, pick, flatten, featureEdges, wireEdges, bounds, explodeOffset,
           sectionPlane, keeps, distinctColor, looksLikeMouse, wheelAction, PITCH_LIMIT };
})();
if (typeof module !== 'undefined') module.exports = V3;
