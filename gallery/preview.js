/* Gallery previews: one shared WebGL canvas renders every house into its own 2D canvas (browsers allow only ~16 WebGL
 * contexts per page). Orbit only - drag to turn, double-click to reset; no pan, no zoom. Each preview turns slowly
 * while it is on screen until it is touched. Maths from viewer_core.js (V3). */
(() => {
  const V = V3;
  document.querySelectorAll('button.copy').forEach((b) => b.addEventListener('click', () => {
    const done = () => { b.textContent = 'Copied'; b.classList.add('done'); setTimeout(() => { b.textContent = 'Copy'; b.classList.remove('done'); }, 1200); };
    if (navigator.clipboard) navigator.clipboard.writeText(b.dataset.cmd).then(done, () => {});
    else { const t = document.createElement('textarea'); t.value = b.dataset.cmd; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); done(); }
  }));
  const houses = JSON.parse(document.getElementById('gallery-data').textContent || '[]');
  const canvases = [...document.querySelectorAll('canvas.preview')];
  const shared = document.createElement('canvas');
  let gl = null;
  try { gl = shared.getContext('webgl', { antialias: true, preserveDrawingBuffer: true }); } catch (e) { gl = null; }
  if (!gl) { document.getElementById('nogl').hidden = false; return; }

  const VS = `attribute vec3 aPos; attribute vec3 aNor; attribute vec3 aCol; uniform mat4 uMVP;
    varying vec3 vNor; varying vec3 vCol;
    void main() { vNor = aNor; vCol = aCol; gl_Position = uMVP * vec4(aPos, 1.0); }`;
  const FS = `precision highp float; uniform vec3 uLight; varying vec3 vNor; varying vec3 vCol;
    void main() { float d = max(dot(normalize(vNor), uLight), 0.0); gl_FragColor = vec4(vCol * (0.45 + 0.55 * d), 1.0); }`;
  const LVS = `attribute vec3 aPos; uniform mat4 uMVP; void main() { gl_Position = uMVP * vec4(aPos, 1.0); }`;
  const LFS = `precision highp float; void main() { gl_FragColor = vec4(0.12, 0.12, 0.12, 1.0); }`;
  const program = (vs, fs) => {
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
    return p;
  };
  const mesh = program(VS, FS), lines = program(LVS, LFS);
  const buffer = (arr) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW); return b; };

  // per house: GPU buffers (built on first draw), bounds and its own camera
  const models = houses.map((h) => ({ parts: h.parts, gpu: null, bounds: V.bounds(h.parts), cam: null, auto: true }));
  const resetCamera = (m) => {
    m.cam = V.camera(m.bounds.centre, 1);
    V.setView(m.cam, 'iso');
    V.frame(m.cam, m.bounds.centre, m.bounds.radius * 0.92);
  };
  models.forEach(resetCamera);
  const upload = (m) => {
    const pos = [], nor = [], col = [], edges = [];
    for (const p of m.parts) {
      const f = V.flatten(p.vertices, p.triangles), c = p.color.map((v) => v / 255);
      pos.push(...f.positions); nor.push(...f.normals);
      for (let i = 0; i < f.positions.length / 3; i++) col.push(...c);
      edges.push(...V.featureEdges(p.vertices, p.triangles));
    }
    m.gpu = { pos: buffer(pos), nor: buffer(nor), col: buffer(col), count: pos.length / 3, edges: buffer(edges), edgeCount: edges.length / 3 };
  };

  function draw(i) {
    const m = models[i], target = canvases[i];
    if (!m.gpu) upload(m);
    const dpr = window.devicePixelRatio || 1, w = target.clientWidth || target.width, h = target.clientHeight || target.height;
    const W = Math.round(w * dpr), H = Math.round(h * dpr);
    if (shared.width !== W || shared.height !== H) { shared.width = W; shared.height = H; }
    if (target.width !== W || target.height !== H) { target.width = W; target.height = H; }
    gl.viewport(0, 0, W, H);
    gl.clearColor(0.914, 0.925, 0.902, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 1);
    const mvp = new Float32Array(V.mul(V.projMatrix(m.cam, w / h, m.bounds.radius), V.viewMatrix(m.cam)));
    gl.useProgram(mesh);
    gl.uniformMatrix4fv(gl.getUniformLocation(mesh, 'uMVP'), false, mvp);
    gl.uniform3fv(gl.getUniformLocation(mesh, 'uLight'), V.norm(V.add(V.viewDir(m.cam), [0.2, 0.1, 0.6])));
    for (const [name, buf] of [['aPos', m.gpu.pos], ['aNor', m.gpu.nor], ['aCol', m.gpu.col]]) {
      const loc = gl.getAttribLocation(mesh, name);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 3, gl.FLOAT, false, 0, 0);
    }
    gl.drawArrays(gl.TRIANGLES, 0, m.gpu.count);
    for (const name of ['aNor', 'aCol']) gl.disableVertexAttribArray(gl.getAttribLocation(mesh, name));
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.useProgram(lines);
    gl.uniformMatrix4fv(gl.getUniformLocation(lines, 'uMVP'), false, mvp);
    const lp = gl.getAttribLocation(lines, 'aPos');
    gl.bindBuffer(gl.ARRAY_BUFFER, m.gpu.edges); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.LINES, 0, m.gpu.edgeCount);
    const ctx = target.getContext('2d');
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(shared, 0, 0);
  }

  // which previews are on screen (only those turn); interaction: orbit only
  const visible = new Set();
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
    for (const e of entries) { const i = +e.target.dataset.index; if (e.isIntersecting) { visible.add(i); draw(i); } else visible.delete(i); }
  }) : null;
  canvases.forEach((c, i) => {
    if (io) io.observe(c); else { visible.add(i); }
    let drag = null;
    c.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY }; models[i].auto = false; if (c.setPointerCapture) c.setPointerCapture(e.pointerId); });
    c.addEventListener('pointermove', (e) => {
      if (!drag) return;
      V.orbit(models[i].cam, e.clientX - drag.x, e.clientY - drag.y);
      drag = { x: e.clientX, y: e.clientY };
      draw(i);
    });
    c.addEventListener('pointerup', () => { drag = null; });
    c.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });       // no zoom, and no page jump
    c.addEventListener('dblclick', () => { resetCamera(models[i]); models[i].auto = true; draw(i); });
  });
  if (!io) canvases.forEach((_, i) => draw(i));

  let last = 0;
  const spin = (t) => {
    if (t - last > 33) {                                           // ~30 fps is plenty for a slow turn
      for (const i of visible) if (models[i].auto) { models[i].cam.yaw += 0.4; draw(i); }
      last = t;
    }
    requestAnimationFrame(spin);
  };
  requestAnimationFrame(spin);

  window.__gallery = { models, draw };
})();
