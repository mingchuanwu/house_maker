/* The 3D viewer page: WebGL drawing, input, outliner and toolbar. All maths lives in viewer_core.js (V3). */
(() => {
  const V = V3;
  const $ = (s) => document.querySelector(s);
  const GROUPS = ['floor', 'walls', 'roof', 'casings', 'chimney', 'dormer'];
  const SELECT = [1.0, 0.62, 0.15], EDGE = [0.08, 0.08, 0.08], CAP = [0.75, 0.2, 0.2], BG = [0.17, 0.17, 0.17];

  let data = {};
  try { data = JSON.parse($('#model-data').textContent || '{}'); } catch (e) { data = {}; }
  const parts = (data.parts || []).map((p, i) => ({
    ...p, index: i, tris: p.triangles.length / 3, distinct: V.distinctColor(i), material: p.color.map((c) => c / 255),
  }));
  const byName = new Map(parts.map((p) => [p.name, p]));

  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } return null; };
  const state = {
    hidden: new Set(), solo: null, selected: null, explode: 0,
    xray: false, opacity: 0.3, edges: true, wire: false, material: false,
    section: { on: false, axis: 2, pos: 0, flip: false },
    wheel: store('viewer3d.wheel') || 'auto',
  };
  const visible = (p) => (state.solo ? p.name === state.solo : !state.hidden.has(p.name));
  const offset = (p) => V.explodeOffset(p, state.explode);
  const plane = () => V.sectionPlane(state.section.axis, state.section.pos, state.section.flip);
  const keep = (pt) => !state.section.on || V.keeps(plane(), pt);
  const model = V.bounds(parts);
  const cam = V.camera();
  V.frame(cam, model.centre, model.radius);

  // ------------------------------------------------------------------ WebGL
  const canvas = $('#gl');
  let gl = null;
  try { gl = canvas.getContext('webgl', { antialias: true }); } catch (e) { gl = null; }
  const message = (text) => { $('#msg').textContent = text; $('#msg').hidden = false; };
  if (!parts.length) message('No parts in this model');
  else if (!gl) message('WebGL is not available in this browser');

  const MESH_VS = `attribute vec3 aPos; attribute vec3 aNor; uniform mat4 uMVP; uniform vec3 uOff;
    varying vec3 vWorld; varying vec3 vNor;
    void main() { vec3 w = aPos + uOff; vWorld = w; vNor = aNor; gl_Position = uMVP * vec4(w, 1.0); }`;
  const MESH_FS = `precision highp float;
    uniform vec3 uColor; uniform float uAlpha; uniform vec4 uPlane; uniform float uClip; uniform vec3 uLight; uniform vec3 uCap;
    varying vec3 vWorld; varying vec3 vNor;
    void main() {
      if (uClip > 0.5 && dot(uPlane.xyz, vWorld) + uPlane.w > 0.0) discard;
      if (!gl_FrontFacing) { gl_FragColor = vec4(uCap, uAlpha); return; }       // inside of a cut panel
      float d = max(dot(normalize(vNor), uLight), 0.0);
      gl_FragColor = vec4(uColor * (0.42 + 0.58 * d), uAlpha);
    }`;
  const LINE_VS = `attribute vec3 aPos; uniform mat4 uMVP; uniform vec3 uOff; varying vec3 vWorld;
    void main() { vec3 w = aPos + uOff; vWorld = w; gl_Position = uMVP * vec4(w, 1.0); }`;
  const LINE_FS = `precision highp float; uniform vec3 uColor; uniform vec4 uPlane; uniform float uClip; varying vec3 vWorld;
    void main() { if (uClip > 0.5 && dot(uPlane.xyz, vWorld) + uPlane.w > 0.0) discard; gl_FragColor = vec4(uColor, 1.0); }`;

  const program = (vs, fs) => {
    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    const loc = {};
    const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const u = gl.getActiveUniform(p, i).name; loc[u] = gl.getUniformLocation(p, u); }
    loc.aPos = gl.getAttribLocation(p, 'aPos'); loc.aNor = gl.getAttribLocation(p, 'aNor');
    return { p, loc };
  };
  const buffer = (arr) => { const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW); return b; };

  let meshProg, lineProg, axes;
  if (gl && parts.length) {
    try {
      meshProg = program(MESH_VS, MESH_FS);
      lineProg = program(LINE_VS, LINE_FS);
    } catch (e) { message('WebGL error: ' + e.message); gl = null; }
  }
  if (gl) {
    for (const p of parts) {
      const f = V.flatten(p.vertices, p.triangles);
      p.gl = { pos: buffer(f.positions), nor: buffer(f.normals), count: f.positions.length / 3 };
      const e = V.featureEdges(p.vertices, p.triangles);
      p.gl.edges = buffer(e); p.gl.edgeCount = e.length / 3;
      p.gl.wire = null;                                            // built on first use
    }
    const a = model.radius * 0.35;
    axes = [[[1, 0, 0], [0.9, 0.3, 0.3]], [[0, 1, 0], [0.4, 0.8, 0.3]], [[0, 0, 1], [0.35, 0.55, 1.0]]]
      .map(([d, c]) => ({ buf: buffer([0, 0, 0, d[0] * a, d[1] * a, d[2] * a]), color: c }));
  }

  let frameQueued = false;
  const redraw = () => { if (!frameQueued) { frameQueued = true; requestAnimationFrame(draw); } };
  const size = () => {
    const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth || 1, h = canvas.clientHeight || 1;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    return { w, h, aspect: w / h };
  };
  const radius = () => model.radius + 2 * state.explode;

  function draw() {
    frameQueued = false;
    if (!gl) return;
    const { aspect } = size();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(BG[0], BG[1], BG[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const mvp = V.mul(V.projMatrix(cam, aspect, radius()), V.viewMatrix(cam));
    const light = V.norm(V.add(V.viewDir(cam), [0.2, 0.1, 0.6]));
    const clip = state.section.on ? 1 : 0, pl = plane();
    const shown = parts.filter(visible);
    const colorOf = (p) => (state.material ? p.material : p.distinct);

    // faces
    gl.useProgram(meshProg.p);
    const m = meshProg.loc;
    gl.uniformMatrix4fv(m.uMVP, false, new Float32Array(mvp));
    gl.uniform4fv(m.uPlane, pl); gl.uniform1f(m.uClip, clip);
    gl.uniform3fv(m.uLight, light);
    gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 1);           // lines win over the faces they lie on
    if (state.xray) { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); }
    else { gl.disable(gl.BLEND); gl.depthMask(true); }
    gl.uniform1f(m.uAlpha, state.xray ? state.opacity : 1);
    gl.enableVertexAttribArray(m.aPos); gl.enableVertexAttribArray(m.aNor);
    for (const p of shown) {
      const c = colorOf(p);
      const face = p.name === state.selected ? c.map((v, i) => 0.4 * v + 0.6 * SELECT[i]) : c;
      gl.uniform3fv(m.uColor, face);
      // back faces only show through a section cut (solid red) - or everywhere in X-ray, where they are just darker
      gl.uniform3fv(m.uCap, state.section.on && !state.xray ? CAP : face.map((v) => v * 0.6));
      gl.uniform3fv(m.uOff, offset(p));
      gl.bindBuffer(gl.ARRAY_BUFFER, p.gl.pos); gl.vertexAttribPointer(m.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, p.gl.nor); gl.vertexAttribPointer(m.aNor, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLES, 0, p.gl.count);
    }
    gl.disableVertexAttribArray(m.aNor);
    gl.disable(gl.POLYGON_OFFSET_FILL); gl.disable(gl.BLEND); gl.depthMask(true);

    // lines
    gl.useProgram(lineProg.p);
    const l = lineProg.loc;
    gl.uniformMatrix4fv(l.uMVP, false, new Float32Array(mvp));
    gl.uniform4fv(l.uPlane, pl); gl.uniform1f(l.uClip, clip);
    gl.enableVertexAttribArray(l.aPos);
    const lines = (buf, count, color, off) => {
      gl.uniform3fv(l.uColor, color); gl.uniform3fv(l.uOff, off);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.vertexAttribPointer(l.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.LINES, 0, count);
    };
    if (state.xray) gl.disable(gl.DEPTH_TEST);                           // see-through edges in X-ray
    for (const p of shown) {
      const sel = p.name === state.selected;
      if (state.wire) {
        if (!p.gl.wire) { const w = V.wireEdges(p.vertices, p.triangles); p.gl.wire = buffer(w); p.gl.wireCount = w.length / 3; }
        lines(p.gl.wire, p.gl.wireCount, sel ? SELECT : colorOf(p).map((v) => v * 0.55), offset(p));
      }
      if (state.edges || sel) lines(p.gl.edges, p.gl.edgeCount, sel ? SELECT : EDGE, offset(p));
    }
    gl.uniform1f(l.uClip, 0);
    gl.disable(gl.DEPTH_TEST);
    for (const ax of axes) lines(ax.buf, 2, ax.color, [0, 0, 0]);
    gl.enable(gl.DEPTH_TEST);
  }

  // ------------------------------------------------------------------ picking helpers
  const rayAt = (clientX, clientY) => {
    const r = canvas.getBoundingClientRect(), w = r.width || 1, h = r.height || 1;
    return V.ray(cam, w / h, radius(), ((clientX - r.left) / w) * 2 - 1, 1 - ((clientY - r.top) / h) * 2);
  };
  const pickAt = (x, y) => V.pick(rayAt(x, y), parts.filter(visible), offset, keep);
  const fmt = (v) => v.toFixed(2);

  // ------------------------------------------------------------------ selection, visibility
  function select(name) {
    state.selected = name && byName.has(name) ? name : null;
    const p = state.selected && byName.get(state.selected);
    $('#selinfo').textContent = p ? `${p.name}  ·  ${p.group}  ·  ${p.tris} triangles` : 'Nothing selected';
    updateOutliner(); redraw();
  }
  function toggleHidden(name) {
    if (state.hidden.has(name)) state.hidden.delete(name); else state.hidden.add(name);
    updateOutliner(); redraw();
  }
  function setSolo(name) {
    state.solo = state.solo === name ? null : name;
    updateOutliner(); redraw();
  }
  function toggleGroup(group) {
    const members = parts.filter((p) => p.group === group);
    const allHidden = members.every((p) => state.hidden.has(p.name));
    for (const p of members) { if (allHidden) state.hidden.delete(p.name); else state.hidden.add(p.name); }
    updateOutliner(); redraw();
  }
  function showAll() { state.hidden.clear(); state.solo = null; updateOutliner(); redraw(); }
  function frameView() {
    const items = (state.selected ? [byName.get(state.selected)] : parts.filter(visible)).map((p) => ({ vertices: p.vertices, offset: offset(p) }));
    const b = V.bounds(items.length ? items : parts.map((p) => ({ vertices: p.vertices, offset: offset(p) })));
    V.frame(cam, b.centre, b.radius); redraw();
  }

  // ------------------------------------------------------------------ outliner
  const outliner = $('#outliner');
  const rows = new Map();
  const css = (c) => `rgb(${c.map((v) => Math.round(v * 255)).join(',')})`;
  for (const g of GROUPS) {
    const members = parts.filter((p) => p.group === g);
    if (!members.length) continue;
    const box = document.createElement('div');
    box.className = 'group';
    const head = document.createElement('div');
    head.className = 'row head'; head.dataset.group = g;
    head.innerHTML = `<button class="eye" title="Show/hide the group">👁</button><span class="name">${g} (${members.length})</span>`;
    head.querySelector('.eye').onclick = (e) => { e.stopPropagation(); toggleGroup(g); };
    box.appendChild(head);
    for (const p of members) {
      const row = document.createElement('div');
      row.className = 'row part'; row.dataset.name = p.name; row.title = p.name;
      row.innerHTML = `<button class="eye" title="Show/hide">👁</button><span class="sw"></span>` +
                      `<span class="name"></span><button class="solo" title="Isolate (show only this)">◎</button>`;
      row.querySelector('.name').textContent = p.name;
      row.querySelector('.eye').onclick = (e) => { e.stopPropagation(); toggleHidden(p.name); };
      row.querySelector('.solo').onclick = (e) => { e.stopPropagation(); setSolo(p.name); };
      row.onclick = () => select(state.selected === p.name ? null : p.name);
      rows.set(p.name, row);
      box.appendChild(row);
    }
    outliner.appendChild(box);
  }
  function updateOutliner() {
    for (const p of parts) {
      const row = rows.get(p.name);
      row.classList.toggle('sel', p.name === state.selected);
      row.classList.toggle('off', !visible(p));
      row.querySelector('.eye').textContent = state.hidden.has(p.name) ? '–' : '👁';
      row.querySelector('.solo').classList.toggle('on', state.solo === p.name);
      row.querySelector('.sw').style.background = css(state.material ? p.material : p.distinct);
    }
    for (const head of outliner.querySelectorAll('.row.head')) {
      const members = parts.filter((p) => p.group === head.dataset.group);
      head.querySelector('.eye').textContent = members.every((p) => state.hidden.has(p.name)) ? '–' : '👁';
    }
  }
  updateOutliner();

  // ------------------------------------------------------------------ toolbar
  const setProj = (ortho) => { cam.ortho = ortho; $('#proj').textContent = ortho ? 'Ortho' : 'Persp'; redraw(); };
  const view = (name) => { V.setView(cam, name); redraw(); };
  document.querySelectorAll('[data-view]').forEach((b) => { b.onclick = () => view(b.dataset.view); });
  $('#proj').onclick = () => setProj(!cam.ortho);
  $('#fit').onclick = frameView;
  const bind = (id, fn, ev = 'input') => $(id).addEventListener(ev, (e) => { fn(e.target); redraw(); });
  bind('#xray', (el) => { state.xray = el.checked; }, 'change');
  bind('#opacity', (el) => { state.opacity = +el.value; });
  bind('#edges', (el) => { state.edges = el.checked; }, 'change');
  bind('#wire', (el) => { state.wire = el.checked; }, 'change');
  bind('#material', (el) => { state.material = el.checked; updateOutliner(); }, 'change');
  bind('#explode', (el) => { state.explode = +el.value; $('#explodeVal').textContent = `${el.value} mm`; });
  const sectionRange = () => {
    const a = state.section.axis, lo = model.min[a] - 1, hi = model.max[a] + 1, el = $('#sectionPos');
    el.min = lo.toFixed(1); el.max = hi.toFixed(1);
    if (state.section.pos < lo || state.section.pos > hi) state.section.pos = model.centre[a];
    el.value = state.section.pos;
    $('#sectionVal').textContent = `${'XYZ'[a]} ${state.section.pos.toFixed(1)}`;
  };
  state.section.pos = model.centre[2];
  sectionRange();
  bind('#section', (el) => { state.section.on = el.checked; }, 'change');
  bind('#axis', (el) => { state.section.axis = +el.value; state.section.pos = model.centre[state.section.axis]; sectionRange(); }, 'change');
  bind('#sectionPos', (el) => { state.section.pos = +el.value; sectionRange(); });
  bind('#flip', (el) => { state.section.flip = el.checked; }, 'change');
  $('#wheel').value = state.wheel;
  bind('#wheel', (el) => { state.wheel = el.value; store('viewer3d.wheel', el.value); }, 'change');

  // ------------------------------------------------------------------ pointer and wheel
  let drag = null;
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('pointerdown', (e) => {
    drag = { x: e.clientX, y: e.clientY, button: e.button, moved: false };
    if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (drag) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 3) return;
      drag.moved = true; drag.x = e.clientX; drag.y = e.clientY;
      if (drag.button === 2 || e.shiftKey) V.pan(cam, dx, dy, canvas.clientHeight || 1);
      else V.orbit(cam, dx, dy);
      redraw();
    } else hover(e);
  });
  canvas.addEventListener('pointerup', (e) => {
    if (drag && !drag.moved && drag.button === 0) {
      const hit = pickAt(e.clientX, e.clientY);
      select(hit ? hit.part.name : null);
    }
    drag = null;
  });
  canvas.addEventListener('dblclick', (e) => {
    const hit = pickAt(e.clientX, e.clientY);
    if (hit) { V.pivotAbout(cam, hit.point); redraw(); }
  });
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
    const dx = e.deltaX * unit, dy = e.deltaY * unit;
    const action = V.wheelAction(e, state.wheel);
    if (action === 'orbit') V.orbit(cam, -dx, -dy);
    else if (action === 'pan') V.pan(cam, -dx, -dy, canvas.clientHeight || 1);
    else {
      const f = Math.exp(dy * (action === 'pinch' ? 0.01 : 0.0015));
      V.zoomAbout(cam, Math.max(0.2, Math.min(5, f)), V.focalPoint(cam, rayAt(e.clientX, e.clientY)));
    }
    redraw();
  }, { passive: false });
  let hoverQueued = null;
  function hover(e) {
    if (hoverQueued) { hoverQueued = e; return; }
    hoverQueued = e;
    requestAnimationFrame(() => {
      const ev = hoverQueued; hoverQueued = null;
      const hit = pickAt(ev.clientX, ev.clientY);
      $('#cursor').textContent = hit ? `${hit.part.name}  x ${fmt(hit.point[0])}  y ${fmt(hit.point[1])}  z ${fmt(hit.point[2])} mm` : '';
    });
  }

  // ------------------------------------------------------------------ keys
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'SELECT' || (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox' && e.target.type !== 'range')) return;
    const c = e.code.replace('Numpad', 'Digit'), opposite = e.ctrlKey || e.metaKey;
    const views = { Digit1: ['front', 'back'], Digit3: ['right', 'left'], Digit7: ['top', 'bottom'] };
    if (views[c]) { view(views[c][opposite ? 1 : 0]); e.preventDefault(); }
    else if (c === 'Digit0') view('iso');
    else if (c === 'Digit5') setProj(!cam.ortho);
    else if (c === 'KeyF') frameView();
    else if (c === 'KeyH' && e.altKey) showAll();
    else if (c === 'KeyH' && state.selected) { state.hidden.add(state.selected); select(null); }
    else if (c === 'KeyX') { $('#xray').checked = !$('#xray').checked; state.xray = $('#xray').checked; redraw(); }
    else if (c === 'Escape') select(null);
  });

  window.addEventListener('resize', redraw);
  redraw();
  window.__viewer = { state, parts, cam, select, toggleHidden, setSolo, toggleGroup, showAll, frameView, visible };
})();
