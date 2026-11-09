// Bike page: a side view of the user's bike drawn from the geometry in the "bike" section of knowledge.json, with every
// logger part where it sits. Click a tube: its geometry opens on the right. Click a part: where it sits, and the CAD
// dimensions of its model (the same parameters.json values as the 3D parts view). Drag a part to move it on the drawing.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const svg = $("bsvg");
  let sel = null; // null (overview) | {kind: "geo", keys, label} | {kind: "mount", id}
  let drag = null;
  let status = "";
  const previews = {}; // component model key -> {title, components, general} from /api/preview/<key>

  const bike = () => data && data.sections.find((s) => s.type === "bike");
  const s = (tag, attrs = {}, ...kids) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    e.append(...kids);
    return e;
  };
  // Drawing coordinates are millimetres from the rear axle, x forward, y up; SVG's y points down.
  const P = (p) => `${p[0].toFixed(1)},${(-p[1]).toFixed(1)}`;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const mul = (a, k) => [a[0] * k, a[1] * k];
  const rad = (d) => (d * Math.PI) / 180;

  function geom(b) {
    const g = Object.fromEntries(b.geometry.map((x) => [x.key, x.value]));
    const R = [0, 0];
    const BB = [Math.sqrt(Math.max(0, g.chainstay ** 2 - g.bb_drop ** 2)), -g.bb_drop];
    const F = [g.wheelbase, 0];
    const up = [-Math.cos(rad(g.seat_angle)), Math.sin(rad(g.seat_angle))]; // up the seat tube
    const S = add(BB, mul(up, g.seat_tube));
    const down = [Math.cos(rad(g.head_angle)), -Math.sin(rad(g.head_angle))]; // down the steering axis
    const HT = add(BB, [g.reach, g.stack]);
    const HB = add(HT, mul(down, g.head_tube));
    return { g, R, BB, F, S, up, down, HT, HB, rw: g.rim_bsd / 2 + g.tyre_width };
  }

  function arc(c, r, a0, a1) {
    const p = (a) => [c[0] + r * Math.cos(rad(a)), c[1] + r * Math.sin(rad(a))];
    return `M${P(p(a0))} A${r},${r} 0 ${Math.abs(a1 - a0) > 180 ? 1 : 0} 0 ${P(p(a1))}`;
  }

  // ---- drawing
  function draw() {
    const b = bike();
    if (!b) { svg.replaceChildren(); return; }
    const { g, R, BB, F, S, up, down, HT, HB, rw } = geom(b);
    const on = (keys) => sel && sel.kind === "geo" && keys.some((k) => sel.keys.includes(k));
    const hit = (label, keys, el) => {
      el.classList.add("hit");
      if (on(keys)) el.classList.add("sel");
      el.dataset.geo = JSON.stringify({ label, keys });
      el.append(s("title", {}, label));
      return el;
    };
    const tube = (a, z, w, label, keys) => hit(label, keys, s("line", { x1: a[0], y1: -a[1], x2: z[0], y2: -z[1], "stroke-width": w, class: "tube" }));

    const saddleAt = add(S, mul(up, g.seatpost_out));
    const stemTop = add(HT, mul(down, -70));
    const bar = add(stemTop, [-150, 30]);
    const top = Math.max(saddleAt[1] + 60, bar[1] + 40, ...b.mounts.map((m) => m.y + m.h / 2 + 50));
    const left = Math.min(-rw, -g.rack_rear, ...b.mounts.map((m) => m.x - m.w / 2 - (m.lp === "left" ? 22 * (m.short || m.label).length : 0))) - 40;
    const right = F[0] + rw + 40;
    const bottom = rw + 110;
    svg.setAttribute("viewBox", `${left} ${-top} ${right - left} ${top + bottom}`);

    const wheel = (c, label) => {
      const grp = s("g", {}, s("circle", { cx: c[0], cy: -c[1], r: rw - g.tyre_width / 2, "stroke-width": g.tyre_width, class: "tyre" }),
        s("circle", { cx: c[0], cy: -c[1], r: g.rim_bsd / 2 - 8, class: "rim" }), s("circle", { cx: c[0], cy: -c[1], r: 30, class: "hub" }));
      for (let i = 0; i < 18; i++) {
        const a = rad(i * 20);
        grp.append(s("line", { x1: c[0], y1: -c[1], x2: c[0] + (g.rim_bsd / 2 - 10) * Math.cos(a), y2: -c[1] - (g.rim_bsd / 2 - 10) * Math.sin(a), class: "spoke" }));
      }
      return hit(label, ["rim_bsd", "tyre_width", "wheelbase"], grp);
    };

    // rack: platform at rack_height, a strut down to the axle and a tie forward to the seatstays
    const stayTop = add(S, mul(up, -30));
    const rackFront = [g.rack_front, g.rack_height];
    const onStay = g.rack_height < stayTop[1] ? mul(stayTop, g.rack_height / stayTop[1]) : stayTop;

    svg.replaceChildren(
      s("line", { x1: left, y1: rw, x2: right, y2: rw, class: "ground" }),
      wheel(R, "Rear wheel"), wheel(F, "Front wheel"),
      s("path", { d: arc(R, rw + 14, 25, 200), class: "guard" }), s("path", { d: arc(F, rw + 14, -15, 150), class: "guard" }),
      hit("Chain case (drive side) and chainstay", ["chainstay", "bb_drop"],
        s("line", { x1: R[0], y1: -R[1], x2: BB[0], y2: -BB[1], "stroke-width": 150, class: "case" })),
      tube(R, BB, 22, "Chainstay", ["chainstay", "bb_drop"]),
      tube(R, stayTop, 20, "Seatstay", ["chainstay", "seat_tube", "seat_angle"]),
      tube(BB, S, 32, "Seat tube", ["seat_tube", "seat_angle"]),
      tube(add(S, mul(up, -25)), add(HT, mul(down, 30)), 32, "Top tube", ["top_tube", "reach", "stack"]),
      tube(BB, add(HB, mul(down, -40)), 42, "Down tube", ["reach", "stack", "head_angle"]),
      tube(HT, HB, 46, "Head tube", ["head_tube", "head_angle", "stack", "reach"]),
      hit("Fork", ["fork_length", "fork_offset", "head_angle", "wheelbase"],
        s("path", { d: `M${P(HB)} L${P(add(HB, mul(down, 60)))} Q${P(add(F, mul(down, -120)))} ${P(F)}`, "stroke-width": 26, class: "tube fork" })),
      tube(S, saddleAt, 26, "Seatpost", ["seatpost_out"]),
      hit("Saddle", ["seatpost_out"], s("path", { d: `M${P(add(saddleAt, [-150, 20]))} Q${P(add(saddleAt, [0, 60]))} ${P(add(saddleAt, [110, 30]))} L${P(add(saddleAt, [110, 10]))} Q${P(add(saddleAt, [0, 0]))} ${P(add(saddleAt, [-150, 0]))} Z`, class: "saddle" })),
      s("path", { d: `M${P(HT)} L${P(stemTop)} Q${P(add(stemTop, [-30, 40]))} ${P(bar)}`, "stroke-width": 24, class: "tube bar" }),
      s("circle", { cx: BB[0], cy: -BB[1], r: 90, class: "ring" }),
      hit("Rear rack", ["rack_height", "rack_rear", "rack_front"], s("g", {},
        s("line", { x1: -g.rack_rear, y1: -g.rack_height, x2: rackFront[0], y2: -rackFront[1], "stroke-width": 16, class: "rack" }),
        s("line", { x1: -g.rack_rear + 30, y1: -g.rack_height, x2: -8, y2: -15, "stroke-width": 12, class: "rack" }),
        s("line", { x1: rackFront[0], y1: -rackFront[1], x2: onStay[0], y2: -onStay[1], "stroke-width": 12, class: "rack" }))),
      hit("Wheelbase", ["wheelbase"], s("g", {},
        s("line", { x1: R[0], y1: rw + 55, x2: F[0], y2: rw + 55, class: "dim" }),
        s("line", { x1: R[0], y1: rw + 35, x2: R[0], y2: rw + 75, class: "dim" }),
        s("line", { x1: F[0], y1: rw + 35, x2: F[0], y2: rw + 75, class: "dim" }),
        s("text", { x: (R[0] + F[0]) / 2, y: rw + 45, class: "dimt" }, `wheelbase ${g.wheelbase} mm`))),
      s("text", { x: left + 20, y: -top + 50, class: "title" }, `${b.title.replace(/^The bike: /, "")}, size ${b.size}`),
      ...b.mounts.map(drawMount),
    );
  }

  function drawMount(m) {
    const x0 = m.x - m.w / 2, y0 = -(m.y + m.h / 2);
    const pad = Math.max(0, (50 - Math.min(m.w, m.h)) / 2); // small parts get a bigger click area
    const isSel = sel && sel.kind === "mount" && sel.id === m.id;
    const lp = m.lp || "above";
    const tx = lp === "left" ? x0 - 18 : lp === "right" ? x0 + m.w + 18 : m.x;
    const ty = lp === "below" ? y0 + m.h + 38 : lp === "above" ? y0 - 16 : y0 + m.h / 2 + 9;
    const anchor = lp === "left" ? "end" : lp === "right" ? "start" : "middle";
    const grp = s("g", { class: "mount" + (isSel ? " sel" : "") + (m.model ? "" : " nomodel") },
      s("rect", { x: x0 - pad, y: y0 - pad, width: m.w + 2 * pad, height: m.h + 2 * pad, class: "pad" }),
      s("rect", { x: x0, y: y0, width: m.w, height: m.h, rx: 6, class: "body" + (m.side === "left" ? " left" : "") }),
      s("text", { x: tx, y: ty, "text-anchor": anchor, class: "label" }, m.short || m.label),
      s("title", {}, `${m.label}\n${m.where}`));
    grp.dataset.mount = m.id;
    return grp;
  }

  // ---- clicking and dragging
  const toMM = (e) => {
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
    return [p.x, -p.y];
  };
  svg.onpointerdown = (e) => {
    const mg = e.target.closest("[data-mount]");
    const gg = e.target.closest("[data-geo]");
    if (mg && readonly) {
      sel = { kind: "mount", id: mg.dataset.mount };
      draw(); drawPanel();
    } else if (mg) {
      const m = bike().mounts.find((q) => q.id === mg.dataset.mount);
      const p = toMM(e);
      drag = { m, dx: m.x - p[0], dy: m.y - p[1], sx: e.clientX, sy: e.clientY, moved: false };
      svg.setPointerCapture(e.pointerId);
    } else if (gg) {
      sel = { kind: "geo", ...JSON.parse(gg.dataset.geo) };
      draw(); drawPanel(true);
    } else if (sel) {
      sel = null; draw(); drawPanel();
    }
  };
  svg.onpointermove = (e) => {
    if (!drag) return;
    if (!drag.moved && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) < 4) return;
    drag.moved = true;
    const p = toMM(e);
    drag.m.x = Math.round(p[0] + drag.dx);
    drag.m.y = Math.round(p[1] + drag.dy);
    draw();
  };
  svg.onpointerup = () => {
    if (!drag) return;
    const { m, moved } = drag;
    drag = null;
    if (moved) changed();
    sel = { kind: "mount", id: m.id };
    draw(); drawPanel(!moved);
  };

  // ---- the panel on the right
  function numRow(label, value, unit, help, onInput) {
    const input = el("input", { type: "number", step: "any", value, className: "num" });
    input.oninput = () => { const v = parseFloat(input.value); if (!Number.isNaN(v)) onInput(v); };
    return el("label", { className: "prow", title: help || "" }, el("span", { className: "pl", textContent: label }), input,
      el("span", { className: "pu", textContent: unit }));
  }

  function sizePicker(b) {
    const pick = el("select", {}, ...Object.keys(b.sizes).map((k) => el("option", { value: k, textContent: k, selected: k === b.size })));
    pick.onchange = () => {
      b.size = pick.value;
      for (const gm of b.geometry) if (gm.key in b.sizes[b.size]) gm.value = b.sizes[b.size][gm.key];
      changed(); draw(); drawPanel();
    };
    return el("label", { className: "prow" }, el("span", { className: "pl", textContent: "Frame size" }), pick, el("span"));
  }

  const saveNote = () => el("p", { className: "hint edit", textContent: "Bike changes are saved with Save & rebuild CLAUDE.md (top right)." });

  function drawPanel(focus) {
    const b = bike();
    const box = $("bpanel");
    if (!b) { box.replaceChildren(el("p", { className: "hint", textContent: "No bike section in knowledge.json." })); return; }
    if (!sel) {
      box.replaceChildren(el("h2", { textContent: b.title }), el("p", { className: "hint", textContent: "Click a part or a tube in the drawing." }),
        sizePicker(b), el("h3", { textContent: "Parts on the bike" }),
        ...b.mounts.map((m) => {
          const btn = el("button", { className: "item" }, el("b", { textContent: m.label }), el("small", { textContent: m.status }));
          btn.onclick = () => { sel = { kind: "mount", id: m.id }; draw(); drawPanel(); };
          return btn;
        }),
        el("h3", { textContent: "About the bike" }), el("p", { className: "hint", textContent: b.intro }), saveNote());
      freeze(box);
      return;
    }
    const back = el("button", { textContent: "← Whole bike", className: "ghost" });
    back.onclick = () => { sel = null; draw(); drawPanel(); };
    if (sel.kind === "geo") {
      const rows = b.geometry.map((gm) => {
        const r = numRow(gm.label, gm.value, gm.unit, gm.help, (v) => { gm.value = v; changed(); draw(); });
        if (sel.keys.includes(gm.key)) r.classList.add("hl");
        return r;
      });
      box.replaceChildren(back, el("h2", { textContent: sel.label }), el("p", { className: "hint", textContent: "Highlighted: the numbers that shape it. Picking a frame size fills in Gazelle's numbers for that size." }),
        sizePicker(b), ...rows, saveNote());
      freeze(box);
      const first = box.querySelector(".prow.hl");
      if (first) {
        first.scrollIntoView({ block: "nearest" });
        box.querySelectorAll(".prow.hl").forEach((r) => { r.classList.remove("flash"); void r.offsetWidth; r.classList.add("flash"); });
        if (focus) { const i = first.querySelector("input"); i.focus({ preventScroll: true }); i.select(); }
      }
      return;
    }
    const m = b.mounts.find((q) => q.id === sel.id);
    const where = el("textarea", { value: m.where, rows: 3 });
    where.oninput = () => { m.where = where.value; changed(); };
    const st = el("input", { value: m.status });
    st.oninput = () => { m.status = st.value; changed(); };
    const pos = (k, label) => numRow(label, m[k], "mm", "", (v) => { m[k] = v; changed(); draw(); });
    const cad = el("div", {});
    box.replaceChildren(back, el("h2", { textContent: m.label }),
      el("label", { textContent: "Where it sits" }), where, el("label", { textContent: "Status" }), st,
      el("h3", { textContent: "On the drawing (from the rear axle)" }),
      pos("x", "Forward"), pos("y", "Up"), pos("w", "Length"), pos("h", "Height"), saveNote(), cad);
    if (focus && !readonly) where.focus({ preventScroll: true });
    freeze(box);
    drawCad(cad, m);
  }

  async function drawCad(box, m) {
    if (!m.model) {
      box.replaceChildren(el("h3", { textContent: "Dimensions" }), el("p", { className: "hint", textContent: "No CAD model for this part yet." }));
      return;
    }
    box.replaceChildren(el("p", { className: "hint", textContent: "Loading dimensions..." }));
    if (!params) params = await (await fetch("api/parameters")).json();
    if (!previews[m.model]) {
      let r = await fetch("api/preview/" + m.model);
      if (!r.ok) { await post("api/preview/build", {}); r = await fetch("api/preview/" + m.model); }
      if (!r.ok) { box.replaceChildren(el("p", { className: "hint", textContent: "Could not build the parts view: the Dimensions page's Rebuild 3D files shows the error." })); return; }
      const j = await r.json();
      previews[m.model] = { title: j.title, general: j.general, components: j.components.map(({ id, label, kind, hint, params: ps }) => ({ id, label, kind, hint, params: ps })) };
    }
    if (!sel || sel.id !== m.id) return; // moved on while loading
    const pv = previews[m.model];
    const byKey = Object.fromEntries(params.parameters.map((p) => [p.key, p]));
    const msg = el("div", { className: "hint log", textContent: status });
    const groups = [...pv.components, ...(pv.general ? [{ id: "_general", label: pv.general.label, params: pv.general.params }] : [])]
      .filter((c) => c.params.some((k) => byKey[k]))
      .map((c) => {
        const d = el("details", { className: "grp" }, el("summary", {}, el("b", { textContent: c.label }), c.kind === "ghost" ? el("small", { textContent: " not printed" }) : ""));
        d.append(...c.params.filter((k) => byKey[k]).map((k) => {
          const p = byKey[k];
          return numRow(p.label, p.value, p.unit, "code name: " + p.key + "\n" + p.help, (v) => { p.value = v; paramsDirty = true; msg.textContent = "Changed: press Save dimensions"; });
        }));
        const open = el("button", { textContent: "Show in 3D", className: "ghost" });
        open.onclick = () => window.open3D(m.model, c.id === "_general" ? null : c.id);
        d.append(open);
        return d;
      });
    const save = el("button", { textContent: "Save dimensions", className: "primary edit" });
    save.onclick = async () => {
      save.disabled = true;
      msg.textContent = status = "Saving, then rebuilding the print files in the background...";
      const r = await post("api/parameters", { values: Object.fromEntries(params.parameters.map((p) => [p.key, p.value])) });
      if (r.error) { msg.textContent = status = "Error: " + r.error; save.disabled = false; return; }
      paramsDirty = false;
      delete previews[m.model];
      for (;;) {
        const st = await (await fetch("api/rebuild/status")).json();
        if (!st.running) { status = st.ok ? "Saved. Print files and the 3D view are up to date." : "Saved, but the print files failed:\n" + st.log; break; }
        await new Promise((res) => setTimeout(res, 2000));
      }
      msg.textContent = status;
      save.disabled = false;
    };
    const open3d = el("button", { textContent: "Open in 3D" });
    open3d.onclick = () => window.open3D(m.model);
    box.replaceChildren(el("h3", { textContent: "Dimensions: " + pv.title }),
      el("p", { className: "hint", textContent: readonly ? "The numbers each part is built from. Open a component to see them." : "The same numbers as the 3D parts view (hardware/cad/parameters.json). Open a component to edit it." }),
      ...groups, el("div", { className: "actions" }, save, open3d), msg);
    freeze(box);
  }

  views.bike = { enter() { draw(); drawPanel(); } };
})();
