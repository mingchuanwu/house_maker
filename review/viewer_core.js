/* Pure geometry for the review page (no DOM) - unit-tested with node.
 * Matrices use the SVG convention [a, b, c, d, e, f]: x' = a*x + c*y + e, y' = b*x + d*y + f. */
const HR = (() => {
  const RAD = Math.PI / 180;
  const mul = (m, n) => [
    m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
    m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
  const translate = (x, y) => [1, 0, 0, 1, x, y];
  const rotate = (deg) => { const c = Math.cos(deg * RAD), s = Math.sin(deg * RAD); return [c, s, -s, c, 0, 0]; };
  const scaleX = (k) => [k, 0, 0, 1, 0, 0];
  const apply = (m, p) => [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]];
  const invert = (m) => {
    const det = m[0] * m[3] - m[1] * m[2];
    const a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det;
    return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
  };
  const css = (m) => `matrix(${m.map((v) => +v.toFixed(6)).join(' ')})`;

  /* A panel's pose: {tx, ty, rot, flip}. With rot=0, flip=false the matrix is translate(tx, ty), the
   * form the generated SVG uses; rotation / flip happen about the centre c of the panel's bbox. */
  const centre = (meta) => [(meta.bbox[0] + meta.bbox[2]) / 2, (meta.bbox[1] + meta.bbox[3]) / 2];
  const panelMatrix = (pose, c) =>
    mul(translate(pose.tx + c[0], pose.ty + c[1]),
        mul(rotate(pose.rot), mul(scaleX(pose.flip ? -1 : 1), translate(-c[0], -c[1]))));

  const norm = (a) => Math.hypot(a[0], a[1]);
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];

  const edgeOf = (meta, name) => {
    const i = meta.edges.indexOf(name);
    if (i < 0) return null;
    const a = meta.corners[i], b = meta.corners[(i + 1) % meta.corners.length];
    return { a, b, len: norm(sub(b, a)), index: i };
  };

  /* Move panel B so that its edge `edgeB` lies on A's edge `edgeA` (opposite direction), the fingers
   * lining up: B's point s_b (from its edge start) meets A's point shift + len_b - s_b.
   * Returns B's new pose (rotation about its centre, no flip) or null when an edge is missing. */
  const snapPose = (metaA, poseA, edgeA, metaB, edgeB, shift) => {
    const ea = edgeOf(metaA, edgeA), eb = edgeOf(metaB, edgeB);
    if (!ea || !eb) return null;
    const MA = panelMatrix(poseA, centre(metaA));
    const a0 = apply(MA, ea.a), a1 = apply(MA, ea.b);
    const u = [(a1[0] - a0[0]) / norm(sub(a1, a0)), (a1[1] - a0[1]) / norm(sub(a1, a0))];
    const target = [a0[0] + u[0] * (shift + eb.len), a0[1] + u[1] * (shift + eb.len)];
    const db = [(eb.b[0] - eb.a[0]) / eb.len, (eb.b[1] - eb.a[1]) / eb.len];
    let rot = (Math.atan2(-u[1], -u[0]) - Math.atan2(db[1], db[0])) / RAD;
    rot = ((rot % 360) + 360) % 360;
    if (Math.abs(rot - 360) < 1e-9) rot = 0;
    const c = centre(metaB);
    const r = apply(rotate(rot), [eb.a[0] - c[0], eb.a[1] - c[1]]);
    return { tx: target[0] - c[0] - r[0], ty: target[1] - c[1] - r[1], rot, flip: false };
  };

  /* The same mate seen from the other panel. */
  const swapShift = (shift, lenA, lenB) => shift + lenB - lenA;

  const segDist = (p, a, b) => {
    const ab = sub(b, a), ap = sub(p, a);
    const L2 = ab[0] * ab[0] + ab[1] * ab[1];
    const t = L2 === 0 ? 0 : Math.max(0, Math.min(1, (ap[0] * ab[0] + ap[1] * ab[1]) / L2));
    return { d: norm(sub(p, [a[0] + ab[0] * t, a[1] + ab[1] * t])), s: t * Math.sqrt(L2) };
  };

  /* What is at local point p on a panel? -> {type: 'slot'|'finger'|'edge'|'panel', ...} */
  const nearestTarget = (meta, p, tol = 2.5) => {
    for (let i = 0; i < (meta.slots || []).length; i++) {
      const s = meta.slots[i];
      const hx = (s.orientation === 'horizontal' ? s.length : s.thickness) / 2 + tol;
      const hy = (s.orientation === 'horizontal' ? s.thickness : s.length) / 2 + tol;
      if (Math.abs(p[0] - s.cx) <= hx && Math.abs(p[1] - s.cy) <= hy) return { type: 'slot', slot: i };
    }
    let best = null;
    meta.edges.forEach((name) => {
      const e = edgeOf(meta, name);
      const { d, s } = segDist(p, e.a, e.b);
      // fingers protrude by up to ~depth beyond the nominal edge: allow for it
      const depth = meta.joints[name] ? meta.joints[name].depth : 0;
      if (d <= tol + depth && (!best || d < best.d)) best = { d, s, name };
    });
    if (best) {
      const j = meta.joints[best.name];
      let finger = null;
      if (j) j.fingers.forEach((f, k) => { if (best.s >= f[0] - 0.5 && best.s <= f[1] + 0.5) finger = k; });
      return finger === null ? { type: 'edge', edge: best.name, s: best.s }
                             : { type: 'finger', edge: best.name, finger, s: best.s };
    }
    return { type: 'panel' };
  };

  /* Expected overlap (mm^2) when a fingered edge pair is laid together: kerf makes every tab
   * (depth t+k) longer than its groove (depth t-k) by 2k. */
  const kerfInterference = (metaA, edgeA, metaB, edgeB) => {
    const ja = metaA.joints[edgeA], jb = metaB.joints[edgeB];
    if (!ja || !jb) return 0;
    const male = ja.role === 'male' ? ja : jb, female = ja.role === 'male' ? jb : ja;
    const sum = (j) => j.fingers.reduce((s, f) => s + (f[1] - f[0]), 0);
    // drawn tabs are wider than drawn notches by 2*kerf per finger; the laser removes exactly that
    return Math.max(0, sum(male) - sum(female)) * Math.min(Math.abs(male.depth), Math.abs(female.depth));
  };

  /* Cross-section of the tab that passes through slot k (for the "ghost" drawing). */
  const tabGhost = (metaTab, edge, metaSlot, slotIndex, thickness) => {
    const j = metaTab.joints[edge], s = metaSlot.slots[slotIndex];
    if (!j || !s) return null;
    const f = (j.nominal && j.nominal.length ? j.nominal : j.fingers)[0];     // physical (kerf-free) tab
    const width = f[1] - f[0];
    const horizontal = s.orientation === 'horizontal';
    return { cx: s.cx, cy: s.cy, w: horizontal ? width : thickness, h: horizontal ? thickness : width,
             slotW: horizontal ? s.length : s.thickness, slotH: horizontal ? s.thickness : s.length };
  };


  /* ---- overlap analysis without canvas: flatten -> even-odd scanline mask -> intersect -> rectangles */
  const flatten = (d, curveSteps = 10) => {
    const polys = []; let cur = null, last = [0, 0];
    const toks = d.match(/[MLCQZ]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/g) || [];
    let i = 0;
    const num = () => parseFloat(toks[i++]);
    while (i < toks.length) {
      const c = toks[i++];
      if (c === 'M') { cur = []; polys.push(cur); last = [num(), num()]; cur.push(last); }
      else if (c === 'L') { last = [num(), num()]; cur.push(last); }
      else if (c === 'Q' || c === 'C') {
        const pts = [last]; const n = c === 'Q' ? 2 : 3;
        for (let k = 0; k < n; k++) pts.push([num(), num()]);
        for (let s = 1; s <= curveSteps; s++) {
          const t = s / curveSteps; let p = pts.slice();
          while (p.length > 1) p = p.slice(1).map((q, j) => [p[j][0] + (q[0] - p[j][0]) * t, p[j][1] + (q[1] - p[j][1]) * t]);
          cur.push(p[0]);
        }
        last = pts[pts.length - 1];
      } else if (c === 'Z') { /* closed implicitly */ }
    }
    return polys.filter((p) => p.length > 2);
  };

  /* Rasterise polygons (already in world mm) into a mask over `box` = [x0, y0, x1, y1] at `scale` px/mm. */
  const rasterMask = (polys, box, scale) => {
    const w = Math.max(1, Math.ceil((box[2] - box[0]) * scale)), h = Math.max(1, Math.ceil((box[3] - box[1]) * scale));
    const data = new Uint8Array(w * h);
    for (let row = 0; row < h; row++) {
      const y = box[1] + (row + 0.5) / scale, xs = [];
      for (const poly of polys) {
        for (let k = 0; k < poly.length; k++) {
          const a = poly[k], b = poly[(k + 1) % poly.length];
          if ((a[1] > y) !== (b[1] > y)) xs.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
        }
      }
      xs.sort((p, q) => p - q);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const c0 = Math.max(0, Math.ceil((xs[k] - box[0]) * scale - 0.5)), c1 = Math.min(w - 1, Math.floor((xs[k + 1] - box[0]) * scale - 0.5));
        for (let c = c0; c <= c1; c++) data[row * w + c] = 1;
      }
    }
    return { w, h, data, box, scale };
  };

  const worldPolys = (d, matrix) => flatten(d).map((poly) => poly.map((p) => apply(matrix, p)));
  const polysBox = (polys) => {
    const xs = polys.flat().map((p) => p[0]), ys = polys.flat().map((p) => p[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  };

  /* Overlap of two panels given their cut path data and world matrices. -> {area (mm^2), rects} */
  const overlap = (dA, MA, dB, MB, scale = 20) => {
    const pa = worldPolys(dA, MA), pb = worldPolys(dB, MB);
    if (!pa.length || !pb.length) return { area: 0, rects: [] };
    const A = polysBox(pa), B = polysBox(pb);
    const box = [Math.max(A[0], B[0]), Math.max(A[1], B[1]), Math.min(A[2], B[2]), Math.min(A[3], B[3])];
    if (box[2] <= box[0] || box[3] <= box[1]) return { area: 0, rects: [] };
    const ma = rasterMask(pa, box, scale), mb = rasterMask(pb, box, scale);
    let n = 0; const rects = []; let open = new Map();
    for (let row = 0; row < ma.h; row++) {
      const next = new Map();
      let c = 0;
      while (c < ma.w) {
        if (ma.data[row * ma.w + c] && mb.data[row * ma.w + c]) {
          let c1 = c; while (c1 + 1 < ma.w && ma.data[row * ma.w + c1 + 1] && mb.data[row * ma.w + c1 + 1]) c1++;
          n += c1 - c + 1;
          const k = c + ':' + c1, prev = open.get(k);
          if (prev) { prev.rows++; next.set(k, prev); }
          else { const r = { c0: c, c1, row0: row, rows: 1 }; rects.push(r); next.set(k, r); }
          c = c1 + 1;
        } else c++;
      }
      open = next;
    }
    return { area: n / (scale * scale),
             rects: rects.map((r) => [box[0] + r.c0 / scale, box[1] + r.row0 / scale, (r.c1 - r.c0 + 1) / scale, r.rows / scale]) };
  };

  return { flatten, rasterMask, overlap, mul, translate, rotate, scaleX, apply, invert, css, centre, panelMatrix, edgeOf, snapPose,
           swapShift, nearestTarget, kerfInterference, tabGhost, segDist };
})();
if (typeof module !== 'undefined') module.exports = HR;
