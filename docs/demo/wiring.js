// Wiring page: the Pi 5's 40-pin header and ports next to the breadboard, with every wire from the "wiring" table in
// knowledge.json drawn between them. Endpoints: "Pi 16" (header pin), "Pi USB2" (port), "BB j8" (breadboard hole),
// "BB 5V:4" (rail, optional column), anything else "Device: terminal". Click a wire, a pin or a hole: it opens on the
// right, edit it there.
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const svg = $("wsvg");
  let sel = null; // null | {kind: "row", i} | {kind: "pin", pin} | {kind: "hole", key}

  const table = () => data && data.sections.find((x) => x.id === "wiring");
  const s = (tag, attrs = {}, ...kids) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    e.append(...kids);
    return e;
  };

  // Physical pin -> name, Raspberry Pi 5 header.
  const PINS = [null, "3V3", "5V", "GPIO2 SDA", "5V", "GPIO3 SCL", "GND", "GPIO4", "GPIO14 TXD", "GND", "GPIO15 RXD",
    "GPIO17", "GPIO18", "GPIO27", "GND", "GPIO22", "GPIO23", "3V3", "GPIO24", "GPIO10 MOSI", "GND", "GPIO9 MISO",
    "GPIO25", "GPIO11 SCLK", "GPIO8 CE0", "GND", "GPIO7 CE1", "ID_SD", "ID_SC", "GPIO5", "GND", "GPIO6", "GPIO12",
    "GPIO13", "GND", "GPIO19", "GPIO16", "GPIO26", "GPIO20", "GND", "GPIO21"];
  const pinKind = (n) => /^GND/.test(PINS[n]) ? "gnd" : PINS[n] === "5V" ? "p5" : PINS[n] === "3V3" ? "p3" : "io";

  // ---- geometry (drawing units). Pi drawn top view as you hold it with the USB and Ethernet ports at the top (USB
  // left, Ethernet right): the 40-pin header runs down the left edge, pin 1 at the bottom (far from the USB ports) in
  // the inner column, even pins along the board edge; USB-C, HDMI and the camera connectors on the right edge. The
  // breadboard sits to the left of the Pi, next to the header. Not to scale.
  const PI = { x: 1260, y: 30, w: 460, h: 600 };
  const PR = PI.x + PI.w; // right edge
  const pinXY = (n) => [PI.x + (n % 2 ? 52 : 26), PI.y + PI.h - 34 - ((n - 1) >> 1) * 24];
  const PORTS = { // name -> [x, y, w, h, label, out direction]
    USB2: [PI.x + 100, PI.y, 70, 58, "USB 2", [0, -1]],
    USB3: [PI.x + 200, PI.y, 70, 58, "USB 3", [0, -1]],
    ETH: [PI.x + 330, PI.y, 80, 64, "Ethernet", [0, -1]],
    CAM0: [PR - 18, 260, 14, 60, "CAM/DISP 0", [1, 0]],
    CAM1: [PR - 18, 340, 14, 60, "CAM/DISP 1", [1, 0]],
    HDMI1: [PR - 26, 450, 26, 30, "HDMI 1", [1, 0]],
    HDMI0: [PR - 26, 500, 26, 30, "HDMI 0", [1, 0]],
    "USB-C": [PR - 30, 556, 30, 34, "USB-C power", [1, 0]],
  };
  const portXY = (p) => { const [x, y, w, h, , d] = PORTS[p]; return [x + w / 2 + d[0] * w / 2, y + h / 2 + d[1] * h / 2]; };

  const BB = { x: 400, y: 40, cols: 30, pitch: 22 };
  // Mirrored: column 1 sits at the right end, next to the Pi's header, so the Pi's wires stay short.
  const colX = (c) => BB.x + 30 + (BB.cols - c) * BB.pitch;
  const ROWY = { j: 130, i: 152, h: 174, g: 196, f: 218, e: 262, d: 284, c: 306, b: 328, a: 350 };
  const RAILS = { "5V": [64, "p5", "+5V"], GND5: [86, "gnd", "GND"], "3V3": [396, "p3", "+3V3"], GND3: [418, "gnd", "GND"] };
  const BBW = BB.cols * BB.pitch + 40, BBH = 410;

  // ---- parsing the table
  function parse(t) {
    t = String(t || "").trim();
    let m;
    if ((m = /^Pi\s+(\d{1,2})$/i.exec(t)) && +m[1] >= 1 && +m[1] <= 40) return { type: "pin", pin: +m[1] };
    if ((m = /^Pi\s+(USB-?C|USB2|USB3|CAM0|CAM1|HDMI0|HDMI1|ETH)$/i.exec(t))) {
      const p = m[1].toUpperCase().replace("USBC", "USB-C");
      return { type: "port", port: p };
    }
    if ((m = /^BB\s+([a-j])(\d{1,2})$/i.exec(t)) && +m[2] >= 1 && +m[2] <= BB.cols) return { type: "hole", row: m[1].toLowerCase(), col: +m[2] };
    if ((m = /^BB\s+(5V|GND5|3V3|GND3)(?::(\d{1,2}))?$/i.exec(t))) {
      const rail = Object.keys(RAILS).find((k) => k.toLowerCase() === m[1].toLowerCase());
      const col = m[2] ? Math.min(BB.cols, Math.max(1, +m[2])) : null;
      return { type: "rail", rail, col };
    }
    if (/^(Pi|BB)\b/i.test(t)) return null; // looks like one but does not parse
    if ((m = /^([^:]+):\s*(.+)$/.exec(t))) return { type: "dev", dev: m[1].trim(), term: m[2].trim() };
    return null;
  }

  const COLORS = ["red", "black", "orange", "yellow", "green", "blue", "white", "purple", "brown", "grey", "gray"];
  const wireColor = (w) => {
    const c = COLORS.find((k) => new RegExp("\\b" + k + "\\b", "i").test(w || ""));
    return c ? "var(--w-" + (c === "gray" ? "grey" : c) + ")" : "var(--w-other)";
  };
  const isResistor = (w) => /resistor/i.test(w || "");

  // ---- layout: endpoints -> positions, devices placed next to what they connect to
  function layout(rows) {
    const conns = rows.map((r, i) => ({ i, row: r, a: parse(r[0]), b: parse(r[1]), wire: r[2] || "", why: r[3] || "" }));
    const devs = new Map(); // name -> {name, terms: [], links: [[x,y]...]}
    const fixedXY = (e) => e.type === "pin" ? pinXY(e.pin) : e.type === "port" ? portXY(e.port)
      : e.type === "hole" ? [colX(e.col), ROWY[e.row]] : e.type === "rail" ? [colX(e.col || 1), RAILS[e.rail][0]] : null;
    for (const c of conns) {
      for (const [e, o] of [[c.a, c.b], [c.b, c.a]]) {
        if (!e || e.type !== "dev") continue;
        if (!devs.has(e.dev)) devs.set(e.dev, { name: e.dev, terms: [], links: [], target: {}, toPi: true });
        const d = devs.get(e.dev);
        if (!d.terms.includes(e.term)) d.terms.push(e.term);
        const p = o && o.type !== "dev" ? fixedXY(o) : null;
        if (p) { d.links.push(p); d.target[e.term] = { p, pin: o.type === "pin" }; }
        if (!o || (o.type !== "pin" && o.type !== "port")) d.toPi = false;
        if (o && o.type === "port") d.port = PORTS[o.port][5];
      }
    }
    // Rows: a row above everything (top ports, sensors on the breadboard's upper half or the header's upper end), a row
    // below (lower half / lower end of the header), and a column right of the Pi for its side ports. Devices in the
    // rows are wide, with their terminals along the edge facing what they connect to, ordered so wires do not cross.
    const TERM = 52;
    const cols = { top: [], bottom: [], pside: [] };
    for (const d of devs.values()) {
      const my = d.links.length ? d.links.reduce((t, p) => t + p[1], 0) / d.links.length : 300;
      const mx = d.links.length ? d.links.reduce((t, p) => t + p[0], 0) / d.links.length : 0;
      d.side = d.port ? (d.port[1] ? "top" : "pside") : my < (d.toPi ? PI.y + PI.h / 2 : 240) ? "top" : "bottom";
      if (d.side === "pside") { d.w = 170; d.h = 30 + d.terms.length * 22; } else { d.w = Math.max(130, d.terms.length * TERM + 16); d.h = 54; }
      d.want = d.side === "pside" ? my : mx;
      cols[d.side].push(d);
    }
    const stack = (list, key, start, gap) => {
      list.sort((p, q) => p.want - q.want);
      let next = start;
      for (const d of list) { d[key] = Math.max(next, d.want - (key === "y" ? d.h : d.w) / 2); next = d[key] + (key === "y" ? d.h : d.w) + gap; }
    };
    stack(cols.pside, "y", 20, 16); cols.pside.forEach((d) => (d.x = PR + 90));
    stack(cols.top, "x", BB.x - 120, 24); cols.top.forEach((d) => (d.y = -50 - d.h));
    stack(cols.bottom, "x", BB.x - 120, 24); cols.bottom.forEach((d) => (d.y = PI.y + PI.h + 60));
    // Terminal dot positions and out directions
    for (const d of devs.values()) {
      d.dot = {};
      if (d.side === "pside") {
        d.terms.forEach((t, k) => (d.dot[t] = [[d.x, d.y + 38 + k * 22], [-1, 0]]));
        continue;
      }
      // Header pins are entered from the left: the leftmost terminal takes the pin furthest from this row.
      const key = (t) => { const g = d.target[t]; return !g ? 1e9 : g.pin ? (d.side === "bottom" ? g.p[1] : -g.p[1]) : g.p[0]; };
      d.terms.sort((p, q) => key(p) - key(q));
      d.terms.forEach((t, k) => {
        const x = d.x + d.w / 2 + (k - (d.terms.length - 1) / 2) * TERM;
        d.dot[t] = d.side === "top" ? [[x, d.y + d.h], [0, 1]] : [[x, d.y], [0, -1]];
      });
    }
    // Final endpoint positions; rails without a column take the one nearest the other end.
    const where = (e, other) => {
      if (!e) return null;
      if (e.type === "dev") { const [p, dir] = devs.get(e.dev).dot[e.term]; return { p, dir }; }
      if (e.type === "pin") return { p: pinXY(e.pin), dir: [-1, 0] };
      if (e.type === "port") return { p: portXY(e.port), dir: PORTS[e.port][5] };
      if (e.type === "hole") return { p: [colX(e.col), ROWY[e.row]], dir: ROWY[e.row] < 240 ? [0, -1] : [0, 1] };
      let col = e.col;
      if (!col) {
        const o = other && where(other, null);
        col = o ? Math.min(BB.cols, Math.max(1, Math.round((o.p[0] - colX(1)) / BB.pitch) + 1)) : 1;
        e.col = col;
      }
      const y = RAILS[e.rail][0];
      return { p: [colX(col), y], dir: y < 240 ? [0, -1] : [0, 1] };
    };
    for (const c of conns) { c.pa = where(c.a, c.b); c.pb = where(c.b, c.a); }
    return { conns, devs: [...devs.values()] };
  }

  // Which breadboard strip a hole or rail end belongs to (holes in one strip are connected).
  const strip = (e) => !e ? null : e.type === "hole" ? (e.row <= "e" ? "L" : "U") + e.col : e.type === "rail" ? "R" + e.rail : null;
  const endLabel = (e) => !e ? "?" : e.type === "pin" ? `pin ${e.pin} (${PINS[e.pin]})` : e.type === "port" ? PORTS[e.port][4]
    : e.type === "hole" ? `hole ${e.row}${e.col}` : e.type === "rail" ? `${RAILS[e.rail][2]} rail` : `${e.dev} ${e.term}`;

  // ---- drawing
  function draw() {
    const t = table();
    if (!t) { svg.replaceChildren(); return; }
    const { conns, devs } = layout(t.rows);
    const selRow = sel && sel.kind === "row" ? conns[sel.i] : null;
    const hotStrips = new Set();
    const hotPins = new Set();
    const lit = (c) => selRow ? c === selRow : sel && sel.kind === "pin" ? [c.a, c.b].some((e) => e && e.type === "pin" && e.pin === sel.pin)
      : sel && sel.kind === "hole" ? [c.a, c.b].some((e) => strip(e) === sel.key) : false;
    for (const c of conns) if (lit(c)) for (const e of [c.a, c.b]) { if (strip(e)) hotStrips.add(strip(e)); if (e && e.type === "pin") hotPins.add(e.pin); }
    if (sel && sel.kind === "hole") hotStrips.add(sel.key);
    if (sel && sel.kind === "pin") hotPins.add(sel.pin);
    const used = new Set(conns.flatMap((c) => [c.a, c.b]).filter((e) => e && e.type === "pin").map((e) => e.pin));

    const kids = [];
    // Pi board
    kids.push(s("rect", { x: PI.x, y: PI.y, width: PI.w, height: PI.h, rx: 14, class: "pcb" }),
      s("text", { x: PI.x + 190, y: PI.y + 180, class: "boardname" }, "Raspberry Pi 5"),
      s("text", { x: PI.x + 190, y: PI.y + 200, class: "small" }, "top view, ports approx. Pin 1 = square pad"));
    for (const [name, [x, y, w, h, label, d]] of Object.entries(PORTS)) {
      const g = s("g", { class: "port" }, s("rect", { x, y, width: w, height: h, rx: 3 }), s("title", {}, label));
      g.append(d[0] ? s("text", { x: x - 6, y: y + h / 2 + 4, class: "small", "text-anchor": "end" }, label)
        : s("text", { x: x + w / 2, y: y + h + 14, class: "small", "text-anchor": "middle" }, label));
      g.dataset.port = name;
      kids.push(g);
    }
    const hy = pinXY(40)[1] - 14;
    kids.push(s("rect", { x: PI.x + 14, y: hy, width: 50, height: pinXY(1)[1] + 14 - hy, rx: 4, class: "header" }));
    const pinLabels = []; // drawn after the wires, so wires leaving the header never hide them
    for (let n = 1; n <= 40; n++) {
      const [x, y] = pinXY(n);
      const cls = "pin " + pinKind(n) + (used.has(n) ? " used" : "") + (hotPins.has(n) ? " sel" : "");
      const g = s("g", { class: cls });
      g.append(s("rect", { x: x - 8, y: y - 8, width: 16, height: 16, rx: n === 1 ? 0 : 8, class: "pad" }),
        s("title", {}, `Pin ${n}: ${PINS[n]}`));
      g.dataset.pin = n;
      kids.push(g);
      const lg = s("g", { class: cls }, s("text", { x: n % 2 ? x + 14 : x - 14, y: y + 4, "text-anchor": n % 2 ? "start" : "end", class: "pinlabel" },
        n % 2 ? `${n} ${PINS[n]}` : `${PINS[n]} ${n}`), s("title", {}, `Pin ${n}: ${PINS[n]}`));
      lg.dataset.pin = n;
      pinLabels.push(lg);
    }

    // Breadboard
    kids.push(s("rect", { x: BB.x, y: BB.y, width: BBW, height: BBH, rx: 10, class: "bb" }),
      s("rect", { x: BB.x + 10, y: BB.y + 192, width: BBW - 20, height: 14, rx: 3, class: "gap" }),
      s("text", { x: BB.x, y: BB.y - 10, class: "boardname" }, "Breadboard (half size, 30 columns)"));
    for (const [rail, [dy, kind, label]] of Object.entries(RAILS)) {
      const y = dy;
      const hot = hotStrips.has("R" + rail);
      const ly = y + (kind === "gnd" ? 11 : -11); // red line above +, blue line below -
      kids.push(s("line", { x1: colX(1) - 14, x2: colX(BB.cols) + 14, y1: ly, y2: ly, class: "railline " + kind }),
        s("text", { x: BB.x + 4, y: y + 4, class: "raillabel " + kind }, label === "GND" ? "−" : "+"),
        s("text", { x: BB.x + BBW + 6, y: y + 4, class: "raillabel " + kind }, label));
      for (let c = 1; c <= BB.cols; c++) {
        const h = s("rect", { x: colX(c) - 4, y: y - 4, width: 8, height: 8, rx: 1.5, class: "hole" + (hot ? " hot" : "") });
        h.dataset.hole = "R" + rail;
        h.append(s("title", {}, `${label} rail, column ${c}`));
        kids.push(h);
      }
    }
    for (const [r, y] of Object.entries(ROWY)) {
      kids.push(s("text", { x: BB.x + 12, y: y + 4, class: "small", "text-anchor": "middle" }, r),
        s("text", { x: BB.x + BBW - 12, y: y + 4, class: "small", "text-anchor": "middle" }, r));
      for (let c = 1; c <= BB.cols; c++) {
        const key = (r <= "e" ? "L" : "U") + c;
        const h = s("rect", { x: colX(c) - 4, y: y - 4, width: 8, height: 8, rx: 1.5, class: "hole" + (hotStrips.has(key) ? " hot" : "") });
        h.dataset.hole = key;
        h.append(s("title", {}, `${r}${c}: joined with ${r <= "e" ? "a-e" : "f-j"}${c}`));
        kids.push(h);
      }
    }
    for (let c = 1; c <= BB.cols; c++) {
      if (c !== 1 && c % 5) continue;
      kids.push(s("text", { x: colX(c), y: ROWY.j - 14, class: "small", "text-anchor": "middle" }, c),
        s("text", { x: colX(c), y: ROWY.a + 22, class: "small", "text-anchor": "middle" }, c));
    }

    // Devices
    for (const d of devs) {
      const ny = d.side === "bottom" ? d.y + d.h - 10 : d.y + 20;
      const g = s("g", { class: "dev" }, s("rect", { x: d.x, y: d.y, width: d.w, height: d.h, rx: 8 }),
        s("text", { x: d.x + d.w / 2, y: ny, "text-anchor": "middle", class: "devname" }, d.name));
      d.terms.forEach((t) => {
        const [[x, y], dir] = d.dot[t];
        g.append(s("circle", { cx: x, cy: y, r: 4, class: "term" }), dir[0]
          ? s("text", { x: x - dir[0] * 10, y: y + 4, "text-anchor": dir[0] > 0 ? "end" : "start", class: "pinlabel" }, t)
          : s("text", { x, y: y - dir[1] * 14 + 4, "text-anchor": "middle", class: "pinlabel" }, t));
      });
      kids.push(g);
    }

    // Wires, the selected ones last so they sit on top
    const order = conns.filter((c) => c.pa && c.pb).sort((p, q) => lit(p) - lit(q));
    for (const c of order) {
      const [a, b] = [c.pa.p, c.pb.p];
      const on = lit(c);
      const g = s("g", { class: "wire" + (on ? " sel" : sel ? " dim" : "") });
      g.dataset.row = c.i;
      if (isResistor(c.wire)) {
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        const ang = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI;
        const val = (/(\d+(\.\d+)?\s*[kM]?)/.exec(c.wire) || [""])[0].replace(/\s/g, "");
        g.append(s("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "lead" }),
          s("g", { transform: `translate(${mx} ${my}) rotate(${Math.abs(ang) > 90 ? ang + 180 : ang})` },
            s("rect", { x: -16, y: -6, width: 32, height: 12, rx: 5, class: "resistor" }),
            s("text", { x: 0, y: -10, "text-anchor": "middle", class: "rlabel" }, val)));
      } else {
        const k = Math.max(40, Math.min(160, Math.hypot(b[0] - a[0], b[1] - a[1]) / 2.5));
        const da = c.pa.dir, db = c.pb.dir;
        const bothBB = strip(c.a) && strip(c.b);
        const d = bothBB
          ? ((o) => `M${a[0]},${a[1]} C${a[0] + o},${a[1] + 10} ${b[0] + o},${b[1] - 10} ${b[0]},${b[1]}`)(a[0] < BB.x + BBW / 2 ? -26 : 26)
          : `M${a[0]},${a[1]} C${a[0] + da[0] * k},${a[1] + da[1] * k} ${b[0] + db[0] * k},${b[1] + db[1] * k} ${b[0]},${b[1]}`;
        g.append(s("path", { d, class: "casing" }), s("path", { d, class: "core", stroke: wireColor(c.wire) }));
        if (/ribbon|usb/i.test(c.wire)) g.classList.add("cable");
      }
      for (const p of [a, b]) g.append(s("circle", { cx: p[0], cy: p[1], r: 3.5, class: "end", fill: wireColor(c.wire) }));
      g.append(s("title", {}, `${c.row[0]} → ${c.row[1]} (${c.wire})\n${c.why}`));
      kids.push(g);
    }
    svg.replaceChildren(...kids, ...pinLabels);
    const bb = svg.getBBox();
    svg.setAttribute("viewBox", `${bb.x - 20} ${bb.y - 20} ${bb.width + 40} ${bb.height + 40}`);
  }

  svg.onclick = (e) => {
    const w = e.target.closest("[data-row]"), p = e.target.closest("[data-pin]"), h = e.target.closest("[data-hole]");
    sel = w ? { kind: "row", i: +w.dataset.row } : p ? { kind: "pin", pin: +p.dataset.pin } : h ? { kind: "hole", key: h.dataset.hole } : null;
    draw(); drawPanel(!!w);
  };

  // ---- the panel on the right
  const saveNote = () => el("p", { className: "hint edit", textContent: "Wiring changes are saved with Save & rebuild CLAUDE.md (top right)." });
  const rowButton = (t, i) => {
    const r = t.rows[i];
    const bad = !parse(r[0]) || !parse(r[1]);
    const b = el("button", { className: "item" + (bad ? " bad" : "") }, el("b", { textContent: `${r[0]} → ${r[1]}` }),
      el("small", { textContent: (bad ? "Not drawn: an endpoint does not parse. " : "") + (r[2] ? r[2] + ". " : "") + (r[3] || "") }));
    b.onclick = () => { sel = { kind: "row", i }; draw(); drawPanel(true); };
    return b;
  };

  function drawPanel(focus) {
    const t = table();
    const box = $("wpanel");
    if (!t) { box.replaceChildren(el("p", { className: "hint", textContent: "No section with id \"wiring\" in knowledge.json." })); return; }
    const back = el("button", { textContent: "← All wires", className: "ghost" });
    back.onclick = () => { sel = null; draw(); drawPanel(); };
    const add = el("button", { textContent: "+ Add wire", className: "edit" });
    add.onclick = () => { t.rows.push(["", "", "", ""]); sel = { kind: "row", i: t.rows.length - 1 }; changed(); draw(); drawPanel(true); };

    if (!sel) {
      const groups = new Map();
      t.rows.forEach((r, i) => {
        const a = parse(r[0]), b = parse(r[1]);
        const dev = [a, b].find((e) => e && e.type === "dev");
        const key = dev ? dev.dev : "Pi to breadboard";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(i);
      });
      box.replaceChildren(el("h2", { textContent: t.title }),
        el("p", { className: "hint", textContent: "Click a wire, a Pi pin or a breadboard hole. Holes light up with everything they are joined to." }),
        ...(readonly && t.intro ? [el("p", { className: "hint", textContent: "Pin numbers are the Pi's physical header numbers. Ultrasonic echo goes through a 1k/2k divider, because the board answers at 5 V and the Pi takes 3.3 V." })] : []),
        ...[...groups].flatMap(([k, list]) => [el("h3", { textContent: k }), ...list.map((i) => rowButton(t, i))]),
        el("div", { className: "actions" }, add), el("h3", { className: "edit", textContent: "How to write an endpoint" }),
        el("p", { className: "hint edit", textContent: t.intro || "" }), saveNote());
      freeze(box);
      return;
    }
    if (sel.kind === "row") {
      const r = t.rows[sel.i];
      if (!r) { sel = null; return drawPanel(); }
      const fields = ["From", "To", "Wire", "Why"].map((label, k) => {
        const input = k === 3 ? el("textarea", { value: r[k] || "", rows: 3 }) : el("input", { value: r[k] || "" });
        const msg = el("small", { className: "parse" });
        const check = () => {
          if (k > 1) return;
          const e = parse(input.value);
          msg.textContent = e ? endLabel(e) : "Does not parse: Pi 16, Pi USB2, BB j8, BB 5V:4 or Device: terminal";
          msg.className = "parse" + (e ? "" : " bad");
        };
        input.oninput = () => { r[k] = input.value; check(); changed(); draw(); };
        check();
        return el("div", {}, el("label", { textContent: label }), input, ...(readonly ? [] : [msg]));
      });
      const del = el("button", { textContent: "Delete this wire", className: "edit" });
      del.onclick = () => { t.rows.splice(sel.i, 1); sel = null; changed(); draw(); drawPanel(); };
      box.replaceChildren(back, el("h2", { textContent: `${r[0] || "?"} → ${r[1] || "?"}` }), ...fields,
        el("div", { className: "actions" }, del, add), saveNote());
      if (focus && !readonly) fields[0].querySelector("input").focus({ preventScroll: true });
      freeze(box);
      return;
    }
    // A pin or a breadboard strip: what is connected to it
    const hits = t.rows.map((r, i) => i).filter((i) => [parse(t.rows[i][0]), parse(t.rows[i][1])].some((e) =>
      e && (sel.kind === "pin" ? e.type === "pin" && e.pin === sel.pin : strip(e) === sel.key)));
    let title, hint;
    if (sel.kind === "pin") {
      title = `Pin ${sel.pin}: ${PINS[sel.pin]}`;
      hint = pinKind(sel.pin) === "io" ? "GPIO pins take 3.3 V at most: anything at 5 V needs a divider." : "Power pin.";
    } else if (sel.key[0] === "R") {
      const [, , label] = RAILS[sel.key.slice(1)];
      title = `${label} rail`; hint = "Every hole along this line is joined.";
    } else {
      const c = sel.key.slice(1);
      title = `Column ${c}, ${sel.key[0] === "L" ? "a-e" : "f-j"}`; hint = "These five holes are joined.";
    }
    box.replaceChildren(back, el("h2", { textContent: title }), el("p", { className: "hint", textContent: hint }),
      el("h3", { textContent: hits.length ? "Connected" : "Nothing connected" }), ...hits.map((i) => rowButton(t, i)),
      el("div", { className: "actions" }, add), saveNote());
    freeze(box);
  }

  views.wiring = { enter() { draw(); drawPanel(); } };
})();
