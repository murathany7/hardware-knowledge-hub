// 3D viewer. Plain WebGL, no libraries.
//  - hardware/print/*.stl (binary STL, what the generator writes): look at a finished part, open it in Bambu Studio.
//  - "Parts + dimensions": the same models split into components (hardware/cad/preview.py). Click a component and the
//    drawer on the right jumps to the dimensions that size it and flashes them; focus a dimension and its component lights up.
(() => {
  const canvas = document.getElementById("gl");
  const gl = canvas.getContext("webgl");
  let parts = [];
  let selected = null; // STL file name, or null in component mode
  let mesh = null; // {buf, count, size:[x,y,z], center:[x,y,z]}
  let poll = null;
  let fm = null; // finished file's dimensions: {title, size, note, components:[{id,label,kind,hint,params}], general} (no meshes)
  let cm = null; // component model: {key, title, components:[{id,label,kind,visible,params,buf,count,tris,color}], general, size, center}
  let sel = null, hov = null; // selected / hovered component id
  let busy = "";
  const MODELS = [["box_v2", "Main box v2: body, lid, deck, hoods, mount"], ["camera_housing", "Camera housing: parts + dimensions"], ["wheel_sensor", "Wheel sensor: parts + dimensions"],
    ["tray", "v1 tray (reference only)"], ["ultrasonic_box", "v1 ultrasonic box (reference only)"], ["rear_box", "Rear box draft (not used)"]];
  const PALETTE = [[0.35, 0.55, 0.8], [0.45, 0.7, 0.55], [0.8, 0.6, 0.35], [0.65, 0.5, 0.8], [0.8, 0.5, 0.55], [0.5, 0.7, 0.75]];
  const GHOST = [0.9, 0.62, 0.2];
  // Which component model (hardware/cad/preview.py) holds the dimensions of a finished file.
  const modelOf = (name) => (name.startsWith("ultrasonic_") ? "ultrasonic_box" : name.startsWith("camera_") ? "camera_housing"
    : name.startsWith("box_v2") ? "box_v2" : name.startsWith("rear_box_") ? "rear_box" : name.startsWith("wheel_sensor") ? "wheel_sensor" : "tray");
  const cam = { yaw: -0.8, pitch: 0.6, dist: 1, pan: [0, 0] };

  const vs = `attribute vec3 p; attribute vec3 n; uniform mat4 m; uniform mat3 nm; varying vec3 v;
    void main(){ v = normalize(nm * n); gl_Position = m * vec4(p, 1.0); }`;
  const fs = `precision mediump float; varying vec3 v; uniform vec3 c; uniform float a;
    void main(){ float d = abs(dot(normalize(v), normalize(vec3(0.4, 0.6, 0.8)))); gl_FragColor = vec4(c * (0.35 + 0.65 * d), a); }`;
  const prog = gl && (() => {
    const mk = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const pr = gl.createProgram();
    gl.attachShader(pr, mk(gl.VERTEX_SHADER, vs));
    gl.attachShader(pr, mk(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(pr);
    return pr;
  })();

  function parse(buf) {
    const dv = new DataView(buf);
    const n = dv.getUint32(80, true);
    if (84 + n * 50 !== buf.byteLength) throw new Error("not a binary STL");
    const out = new Float32Array(n * 18);
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < n; i++) {
      const o = 84 + i * 50;
      for (let v = 0; v < 3; v++) {
        for (let k = 0; k < 3; k++) {
          const x = dv.getFloat32(o + 12 + v * 12 + k * 4, true);
          out[i * 18 + v * 6 + k] = x;
          out[i * 18 + v * 6 + 3 + k] = dv.getFloat32(o + k * 4, true);
          lo[k] = Math.min(lo[k], x); hi[k] = Math.max(hi[k], x);
        }
      }
    }
    return { data: out, count: n * 3, lo, hi };
  }

  function mat(a, b) { // 4x4 column-major multiply
    const r = new Float32Array(16);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++)
      r[j * 4 + i] = a[i] * b[j * 4] + a[4 + i] * b[j * 4 + 1] + a[8 + i] * b[j * 4 + 2] + a[12 + i] * b[j * 4 + 3];
    return r;
  }

  function inv4(m) { // 4x4 inverse (column-major), or null
    const o = new Float64Array(16), a = m;
    o[0] = a[5] * a[10] * a[15] - a[5] * a[11] * a[14] - a[9] * a[6] * a[15] + a[9] * a[7] * a[14] + a[13] * a[6] * a[11] - a[13] * a[7] * a[10];
    o[4] = -a[4] * a[10] * a[15] + a[4] * a[11] * a[14] + a[8] * a[6] * a[15] - a[8] * a[7] * a[14] - a[12] * a[6] * a[11] + a[12] * a[7] * a[10];
    o[8] = a[4] * a[9] * a[15] - a[4] * a[11] * a[13] - a[8] * a[5] * a[15] + a[8] * a[7] * a[13] + a[12] * a[5] * a[11] - a[12] * a[7] * a[9];
    o[12] = -a[4] * a[9] * a[14] + a[4] * a[10] * a[13] + a[8] * a[5] * a[14] - a[8] * a[6] * a[13] - a[12] * a[5] * a[10] + a[12] * a[6] * a[9];
    o[1] = -a[1] * a[10] * a[15] + a[1] * a[11] * a[14] + a[9] * a[2] * a[15] - a[9] * a[3] * a[14] - a[13] * a[2] * a[11] + a[13] * a[3] * a[10];
    o[5] = a[0] * a[10] * a[15] - a[0] * a[11] * a[14] - a[8] * a[2] * a[15] + a[8] * a[3] * a[14] + a[12] * a[2] * a[11] - a[12] * a[3] * a[10];
    o[9] = -a[0] * a[9] * a[15] + a[0] * a[11] * a[13] + a[8] * a[1] * a[15] - a[8] * a[3] * a[13] - a[12] * a[1] * a[11] + a[12] * a[3] * a[9];
    o[13] = a[0] * a[9] * a[14] - a[0] * a[10] * a[13] - a[8] * a[1] * a[14] + a[8] * a[2] * a[13] + a[12] * a[1] * a[10] - a[12] * a[2] * a[9];
    o[2] = a[1] * a[6] * a[15] - a[1] * a[7] * a[14] - a[5] * a[2] * a[15] + a[5] * a[3] * a[14] + a[13] * a[2] * a[7] - a[13] * a[3] * a[6];
    o[6] = -a[0] * a[6] * a[15] + a[0] * a[7] * a[14] + a[4] * a[2] * a[15] - a[4] * a[3] * a[14] - a[12] * a[2] * a[7] + a[12] * a[3] * a[6];
    o[10] = a[0] * a[5] * a[15] - a[0] * a[7] * a[13] - a[4] * a[1] * a[15] + a[4] * a[3] * a[13] + a[12] * a[1] * a[7] - a[12] * a[3] * a[5];
    o[14] = -a[0] * a[5] * a[14] + a[0] * a[6] * a[13] + a[4] * a[1] * a[14] - a[4] * a[2] * a[13] - a[12] * a[1] * a[6] + a[12] * a[2] * a[5];
    o[3] = -a[1] * a[6] * a[11] + a[1] * a[7] * a[10] + a[5] * a[2] * a[11] - a[5] * a[3] * a[10] - a[9] * a[2] * a[7] + a[9] * a[3] * a[6];
    o[7] = a[0] * a[6] * a[11] - a[0] * a[7] * a[10] - a[4] * a[2] * a[11] + a[4] * a[3] * a[10] + a[8] * a[2] * a[7] - a[8] * a[3] * a[6];
    o[11] = -a[0] * a[5] * a[11] + a[0] * a[7] * a[9] + a[4] * a[1] * a[11] - a[4] * a[3] * a[9] - a[8] * a[1] * a[7] + a[8] * a[3] * a[5];
    o[15] = a[0] * a[5] * a[10] - a[0] * a[6] * a[9] - a[4] * a[1] * a[10] + a[4] * a[2] * a[9] + a[8] * a[1] * a[6] - a[8] * a[2] * a[5];
    const det = a[0] * o[0] + a[1] * o[4] + a[2] * o[8] + a[3] * o[12];
    if (!det) return null;
    for (let i = 0; i < 16; i++) o[i] /= det;
    return o;
  }

  const bounds = () => cm || mesh;

  function matrices() {
    const w = canvas.clientWidth, h = canvas.clientHeight, b = bounds();
    const r = Math.max(...b.size) * 0.5 * Math.sqrt(3);
    const d = r * 2.6 * cam.dist;
    const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    // model: center, Z-up rotated by yaw (about Z) then pitch (about X), CAD Z-up -> screen Y-up
    const rz = [cy, sy, 0, 0, -sy, cy, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const rx = [1, 0, 0, 0, 0, sp, -cp, 0, 0, cp, sp, 0, 0, 0, 0, 1];
    const tr = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -b.center[0], -b.center[1], -b.center[2], 1];
    const asp = w / h, f = 1 / Math.tan(0.4), near = d * 0.05, far = d * 10;
    const proj = [f / asp, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, 2 * far * near / (near - far), 0];
    const view = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, cam.pan[0] * d, cam.pan[1] * d, -d, 1];
    return { m: mat(mat(mat(proj, view), rx), mat(rz, tr)), rot: mat(rx, rz) };
  }

  const accent = () => (isDark() ? [0.3, 0.64, 1] : [0.04, 0.42, 0.8]);

  function drawItem(it, m, loc, alpha, color) {
    gl.uniform3f(loc.c, ...color);
    gl.uniform1f(loc.a, alpha);
    gl.bindBuffer(gl.ARRAY_BUFFER, it.buf);
    gl.enableVertexAttribArray(loc.p); gl.vertexAttribPointer(loc.p, 3, gl.FLOAT, false, 24, 0);
    gl.enableVertexAttribArray(loc.n); gl.vertexAttribPointer(loc.n, 3, gl.FLOAT, false, 24, 12);
    gl.drawArrays(gl.TRIANGLES, 0, it.count);
  }

  function draw() {
    if (!gl) return;
    const w = canvas.clientWidth, h = canvas.clientHeight, dpr = devicePixelRatio || 1;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) { canvas.width = w * dpr; canvas.height = h * dpr; }
    gl.viewport(0, 0, canvas.width, canvas.height);
    const dark = isDark();
    const bg = (getComputedStyle($("stage")).backgroundColor.match(/[\d.]+/g) || [245, 246, 248]).slice(0, 3).map((v) => v / 255);
    gl.clearColor(...bg, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    if (!bounds()) return;
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(prog);
    const { m, rot } = matrices();
    gl.uniformMatrix4fv(gl.getUniformLocation(prog, "m"), false, m);
    gl.uniformMatrix3fv(gl.getUniformLocation(prog, "nm"), false, [rot[0], rot[1], rot[2], rot[4], rot[5], rot[6], rot[8], rot[9], rot[10]]);
    const loc = { c: gl.getUniformLocation(prog, "c"), a: gl.getUniformLocation(prog, "a"), p: gl.getAttribLocation(prog, "p"), n: gl.getAttribLocation(prog, "n") };
    if (!cm) { drawItem(mesh, m, loc, 1, dark ? [0.75, 0.82, 0.9] : [0.25, 0.5, 0.8]); return; }
    const ac = accent();
    const shade = (c, k) => c.map((v) => Math.min(1, v * k));
    gl.disable(gl.BLEND);
    for (const c of cm.components) {   // printed parts first, opaque
      if (!c.visible || c.kind === "ghost") continue;
      const base = c.id === sel ? ac : c.id === hov ? shade(c.color, 1.35) : c.color;
      drawItem(c, m, loc, 1, base);
    }
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
    for (const c of cm.components) {   // ghosts (the real part that sits in it, or a hole) translucent on top
      if (!c.visible || c.kind !== "ghost") continue;
      const on = c.id === sel, hv = c.id === hov;
      drawItem(c, m, loc, on ? 0.7 : hv ? 0.5 : 0.28, on ? ac : GHOST);
    }
    gl.depthMask(true); gl.disable(gl.BLEND);
  }

  // ---- picking: ray against the triangles of the visible components
  function pick(px, py) {
    if (!cm) return null;
    const inv = inv4(matrices().m);
    if (!inv) return null;
    const x = (px / canvas.clientWidth) * 2 - 1, y = 1 - (py / canvas.clientHeight) * 2;
    const un = (z) => {
      const v = [0, 1, 2, 3].map((i) => inv[i] * x + inv[4 + i] * y + inv[8 + i] * z + inv[12 + i]);
      return [v[0] / v[3], v[1] / v[3], v[2] / v[3]];
    };
    const o = un(-1), e = un(1), d = [e[0] - o[0], e[1] - o[1], e[2] - o[2]];
    let best = null, bt = Infinity;
    for (const c of cm.components) {
      if (!c.visible) continue;
      const T = c.tris;
      for (let i = 0; i < T.length; i += 9) {
        const e1 = [T[i + 3] - T[i], T[i + 4] - T[i + 1], T[i + 5] - T[i + 2]], e2 = [T[i + 6] - T[i], T[i + 7] - T[i + 1], T[i + 8] - T[i + 2]];
        const pv = [d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0]];
        const det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2];
        if (Math.abs(det) < 1e-9) continue;
        const s = [o[0] - T[i], o[1] - T[i + 1], o[2] - T[i + 2]];
        const u = (s[0] * pv[0] + s[1] * pv[1] + s[2] * pv[2]) / det;
        if (u < 0 || u > 1) continue;
        const q = [s[1] * e1[2] - s[2] * e1[1], s[2] * e1[0] - s[0] * e1[2], s[0] * e1[1] - s[1] * e1[0]];
        const v = (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]) / det;
        if (v < 0 || u + v > 1) continue;
        const t = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det;
        // translucent ghosts count a bit less than printed parts, so a part in front of a ghost wins ties
        const tt = c.kind === "ghost" ? t + 0.5 : t;
        if (t > 0 && tt < bt) { bt = tt; best = c.id; }
      }
    }
    return best;
  }

  // ---- loading
  async function load(name) {
    const buf = await (await fetch("stl/" + name + "?t=" + Date.now())).arrayBuffer();
    const s = parse(buf);
    const b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, s.data, gl.STATIC_DRAW);
    const size = s.hi.map((v, i) => v - s.lo[i]);
    mesh = { buf: b, count: s.count, size, center: s.hi.map((v, i) => (v + s.lo[i]) / 2) };
    $("info").textContent = `${name}\n${size.map((v) => v.toFixed(1)).join(" x ")} mm (X x Y x Z)\n${(s.count / 3).toLocaleString()} triangles`;
    $("info").style.whiteSpace = "pre";
    draw();
    await loadFileDims(name, size, s.count / 3);
  }

  async function loadFileDims(name, size, tris) {
    await ensureParams();
    const key = modelOf(name);
    let m = null;
    if (key) {
      let r = await fetch("api/preview/" + key);
      if (!r.ok) { await post("api/preview/build", {}); r = await fetch("api/preview/" + key); }
      if (r.ok) m = await r.json();
    }
    if (selected !== name || cm) return;          // the user moved on while this loaded
    fm = { name, size, tris, title: m ? m.title : name, general: m && m.general,
      note: m ? "" : "No editable dimensions yet: this part's sizes are constants at the top of its script in hardware/cad/.",
      components: m ? m.components.map(({ id, label, kind, hint, params: ps }) => ({ id, label, kind, hint, params: ps })) : [] };
    drawDrawer();
  }

  async function ensureParams() {
    if (!params) params = await (await fetch("api/parameters")).json();
  }

  async function loadModel(key, keepSel) {
    $("info").textContent = "Loading parts...";
    await ensureParams();
    let r = await fetch("api/preview/" + key);
    if (!r.ok) {
      $("info").textContent = "Building the 3D parts (about 10 s)...";
      await post("api/preview/build", {});
      r = await fetch("api/preview/" + key);
    }
    if (!r.ok) { $("info").textContent = "Could not build the parts view. Rebuild 3D files on the Dimensions page shows the error."; return; }
    const m = await r.json();
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    const prevVisible = Object.fromEntries((cm && cm.key === key ? cm.components : []).map((c) => [c.id, c.visible]));
    m.components.forEach((c, n) => {
      const out = new Float32Array(c.t.length * 6), tris = new Float32Array(c.t.length * 3);
      for (let i = 0; i < c.t.length; i += 3) {
        const P = [0, 1, 2].map((k) => [c.v[c.t[i + k] * 3], c.v[c.t[i + k] * 3 + 1], c.v[c.t[i + k] * 3 + 2]]);
        const a = [P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]], b = [P[2][0] - P[0][0], P[2][1] - P[0][1], P[2][2] - P[0][2]];
        let nx = a[1] * b[2] - a[2] * b[1], ny = a[2] * b[0] - a[0] * b[2], nz = a[0] * b[1] - a[1] * b[0];
        const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
        for (let k = 0; k < 3; k++) {
          out.set([...P[k], nx, ny, nz], (i + k) * 6);
          tris.set(P[k], (i + k) * 3);
          for (let q = 0; q < 3; q++) { lo[q] = Math.min(lo[q], P[k][q]); hi[q] = Math.max(hi[q], P[k][q]); }
        }
      }
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, out, gl.STATIC_DRAW);
      c.buf = buf; c.count = c.t.length; c.tris = tris;
      c.color = PALETTE[n % PALETTE.length];
      if (c.id in prevVisible) c.visible = prevVisible[c.id];
      delete c.v; delete c.t;
    });
    const size = hi.map((v, i) => v - lo[i]);
    cm = { key, title: m.title, components: m.components, general: m.general, size, center: hi.map((v, i) => (v + lo[i]) / 2) };
    if (!keepSel) { sel = null; hov = null; }
    $("info").textContent = `${m.title}\nclick a part to see its dimensions`;
    $("info").style.whiteSpace = "pre";
    drawDrawer();
    draw();
  }

  // ---- drawer: dimensions of the model's components
  const dm = () => cm || fm;
  const compOf = (id) => dm() && dm().components.find((c) => c.id === id);
  const groupEls = {};

  function paramRow(p, id) {
    const input = el("input", { type: "number", step: "any", value: p.value, className: "num" });
    input.oninput = () => {
      const v = parseFloat(input.value);
      if (Number.isNaN(v)) return;
      p.value = v; paramsDirty = true; busy = ""; $("drawer-status").textContent = "Changed: press Save & update 3D view";
    };
    input.onfocus = () => { if (id && sel !== id) { select(id, false); } };
    return el("label", { className: "prow", title: "code name: " + p.key + "\n" + p.help }, el("span", { className: "pl", textContent: p.label }), input,
      el("span", { className: "pu", textContent: p.unit }));
  }

  function drawDrawer() {
    const dr = $("drawer");
    const d = dm();
    $("viewer").classList.toggle("cm", !!d);
    dr.hidden = !d;
    if (!d) return;
    dr.replaceChildren(el("h2", { textContent: d.title }),
      cm ? el("p", { className: "hint", textContent: "Click a part in the 3D view, or a name here. Translucent orange items are not printed: the real part that sits there, or a hole. Values are millimetres." })
        : el("div", {}, el("p", { className: "size", textContent: `${d.name}\n${d.size.map((v) => v.toFixed(1)).join(" x ")} mm (X x Y x Z)` }),
          el("p", { className: "hint", textContent: d.note || (readonly ? "A finished print file. Click a name to see the dimensions that size it, in millimetres." : "Finished file. Click a name to edit the dimensions that size it, then Save: every print file is rebuilt. Values are millimetres.") })));
    for (const k of Object.keys(groupEls)) delete groupEls[k];
    const byKey = Object.fromEntries(params.parameters.map((p) => [p.key, p]));
    const mk = (id, label, keys, c) => {
      const on = id === sel;
      const eye = el("input", { type: "checkbox", checked: c ? c.visible : true, title: "Show in the 3D view" });
      eye.onclick = (e) => { e.stopPropagation(); if (c) { c.visible = eye.checked; draw(); } };
      const head = el("div", { className: "ghead" }, cm && c ? eye : "", el("b", { textContent: label }),
        c && c.kind === "ghost" ? el("small", { textContent: "not printed" }) : "");
      head.onclick = () => select(on ? null : id, true);
      head.onmouseenter = () => { hov = id; draw(); };
      head.onmouseleave = () => { hov = null; draw(); };
      const g = el("section", { className: "grp" + (on ? " sel" : "") }, head);
      if (c && c.hint && on) g.append(el("p", { className: "hint", textContent: c.hint }));
      if (on) keys.forEach((k) => byKey[k] && g.append(paramRow(byKey[k], id)));
      else if (!keys.length) g.append(el("p", { className: "hint", textContent: "No dimensions of its own." }));
      groupEls[id] = g;
      return g;
    };
    d.components.forEach((c) => dr.append(mk(c.id, c.label, c.params, c)));
    if (d.general) dr.append(mk("_general", d.general.label, d.general.params, null));
    const status = el("div", { id: "drawer-status", className: "hint", textContent: busy });
    const save = el("button", { textContent: cm ? "Save & update 3D view" : "Save & rebuild files", className: "primary edit" });
    const rebuildBtn = el("button", { textContent: "Rebuild print files", className: "edit" });
    const waitForFiles = async () => {
      for (;;) {                                   // the server rebuilds every print file after a save
        const s = await (await fetch("api/rebuild/status")).json();
        if (!s.running) return s.ok ? "Print files and plates are up to date." : "The print files failed:\n" + s.log;
        await new Promise((res) => setTimeout(res, 2000));
      }
    };
    save.onclick = async () => {
      $("drawer-status").textContent = cm ? "Saving, then rebuilding the view (about 10 s)..." : "Saving, then rebuilding the print files...";
      save.disabled = rebuildBtn.disabled = true;
      const r = await post("api/parameters", { values: Object.fromEntries(params.parameters.map((p) => [p.key, p.value])) });
      if (r.error) { $("drawer-status").textContent = "Error: " + r.error; save.disabled = rebuildBtn.disabled = false; return; }
      paramsDirty = false;
      if (cm) {
        await post("api/preview/build", {});
        await loadModel(cm.key, true);
        busy = "Saved. Rebuilding the print files (STEP/STL/3MF/plates) in the background...";
        $("drawer-status").textContent = busy;
      }
      busy = "Saved. " + (await waitForFiles());
      $("drawer-status").textContent = busy;
      save.disabled = rebuildBtn.disabled = false;
    };
    rebuildBtn.onclick = async () => {
      if (paramsDirty) { $("drawer-status").textContent = "Changed dimensions are not saved yet: press Save first."; return; }
      $("drawer-status").textContent = "Rebuilding the print files (STEP/STL/3MF/plates)...";
      save.disabled = rebuildBtn.disabled = true;
      const r = await post("api/rebuild", {});
      busy = r.ok ? "Rebuilt. Print files and plates are up to date." : "Rebuild failed:\n" + (r.log || r.error);
      $("drawer-status").textContent = busy;
      save.disabled = rebuildBtn.disabled = false;
    };
    dr.append(el("div", { className: "actions" }, save, rebuildBtn), status);
    freeze(dr);
    const g = groupEls[sel];
    if (g) g.scrollIntoView({ block: "nearest" });
  }

  function select(id, fromDrawer) {
    sel = id;
    draw();
    drawDrawer();
    const g = groupEls[id];
    if (g) {
      g.scrollIntoView({ block: "nearest", behavior: "smooth" });
      const rows = [...g.querySelectorAll(".prow")];
      rows.forEach((r) => { r.classList.remove("flash"); void r.offsetWidth; r.classList.add("flash"); });
      if (!fromDrawer && rows.length) { const i = rows[0].querySelector("input"); i.focus({ preventScroll: true }); i.select(); }
    }
    const c = compOf(id);
    if (cm) $("info").textContent = c ? `${cm.title}\n${c.label}${c.kind === "ghost" ? " (not printed)" : ""}` : `${cm.title}\nclick a part to see its dimensions`;
  }

  // ---- list of parts / models
  function drawList() {
    const comp = MODELS.map(([key, label]) => {
      const b = el("button", { className: cm && cm.key === key ? "on" : "" }, label, el("small", {}, readonly ? "click a part to see its dimensions" : "click a part, edit its dimensions"));
      b.onclick = async () => { selected = null; mesh = null; fm = null; $("studio").hidden = true; await loadModel(key, false); drawList(); };
      return b;
    });
    $("parts").replaceChildren(...comp, el("hr"), el("small", { className: "ptitle", textContent: "Finished files (hardware/print)" }), ...parts.map((p) => {
      const b = el("button", { className: !cm && p.name === selected ? "on" : "" }, p.name.replace(/\.stl$/, ""),
        el("small", {}, "built " + new Date(p.mtime * 1000).toLocaleString()));
      b.onclick = () => { cm = null; fm = null; sel = hov = null; drawDrawer(); $("studio").hidden = false; selected = p.name; drawList(); load(p.name); };
      return b;
    }));
  }

  async function refresh() {
    const list = await (await fetch("api/models")).json();
    const prev = parts.find((p) => p.name === selected);
    const now = list.find((p) => p.name === selected);
    parts = list;
    if (!cm && !selected && list.length) selected = (list.find((p) => p.name.startsWith("box_v2_body")) || list[0]).name;
    drawList();
    if (!cm && selected && (!prev || !now || prev.mtime !== now.mtime || !mesh)) load(selected);
  }

  views["3d"] = {
    enter() { refresh(); poll = setInterval(refresh, 3000); draw(); },
    leave() { clearInterval(poll); },
  };
  // Used by the Bike page: open a component model with one of its components selected.
  window.open3D = async (key, compId) => {
    selected = null; mesh = null; fm = null; $("studio").hidden = true;
    await loadModel(key, false);
    showView("3d");
    drawList();
    if (compId) select(compId, false);
  };
  $("studio").onclick = async () => {
    const r = await fetch("api/open-in-studio", { method: "POST", body: JSON.stringify({ name: selected }) });
    const j = await r.json();
    $("studio").textContent = r.ok ? "Opened " + j.opened : j.error;
    setTimeout(() => { $("studio").textContent = "Open in Bambu Studio"; }, 3000);
  };
  if (!gl) $("view-3d").disabled = true;

  let drag = null;
  canvas.onpointerdown = (e) => { drag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, pan: e.shiftKey || e.button === 2 }; canvas.setPointerCapture(e.pointerId); };
  canvas.onpointerup = (e) => {
    if (drag && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < 4 && cm && e.button === 0) {
      const r = canvas.getBoundingClientRect();
      const id = pick(e.clientX - r.left, e.clientY - r.top);
      if (id) select(id, false); else if (sel) { sel = null; drawDrawer(); draw(); }
    }
    drag = null;
  };
  canvas.oncontextmenu = (e) => e.preventDefault();
  canvas.onpointermove = (e) => {
    if (!drag) {
      if (cm) {
        const r = canvas.getBoundingClientRect();
        const id = pick(e.clientX - r.left, e.clientY - r.top);
        if (id !== hov) { hov = id; canvas.style.cursor = id ? "pointer" : "default"; draw(); }
      }
      return;
    }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY;
    if (drag.pan) { cam.pan[0] += dx / canvas.clientHeight * 0.9; cam.pan[1] -= dy / canvas.clientHeight * 0.9; }
    else { cam.yaw += dx * 0.01; cam.pitch = Math.max(-1.5, Math.min(1.5, cam.pitch + dy * 0.01)); }
    draw();
  };
  canvas.onpointerleave = () => { if (hov && !drag) { hov = null; draw(); } };
  canvas.onwheel = (e) => { e.preventDefault(); cam.dist = Math.max(0.1, Math.min(5, cam.dist * Math.exp(e.deltaY * 0.001))); draw(); };
  canvas.ondblclick = () => { Object.assign(cam, { yaw: -0.8, pitch: 0.6, dist: 1, pan: [0, 0] }); draw(); };
  addEventListener("resize", draw);
})();
