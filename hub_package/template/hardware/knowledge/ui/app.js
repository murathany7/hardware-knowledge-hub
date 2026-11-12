// Hardware knowledge editor. Plain JS, no build step, talks to hardware/knowledge/kb.py.
let data = null;
let current = 0; // index into data.sections; -1 = the Dimensions page
let params = null; // hardware/cad/parameters.json
let paramsDirty = false;
let dirty = false;
let tab = "claude"; // "claude" = generated hardware/CLAUDE.md; otherwise a path from /api/context
let context = [];
let generated = "";
let timer = null;
let readonly = false; // the public copy (kb.py with KB_READONLY=1): nothing is saved

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...kids) => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};
// Dark mode: the OS setting, unless the page set html.dark / html.light (the public copy is always dark, like
// murathanyildirim.com).
const isDark = () => {
  const c = document.documentElement.classList;
  return c.contains("dark") || (!c.contains("light") && matchMedia("(prefers-color-scheme: dark)").matches);
};
const post = (url, body) =>
  readonly && url !== "api/render"
    ? Promise.resolve({ error: "This is a read-only copy: changes are not saved." })
    : fetch(url, { method: "POST", body: JSON.stringify(body) }).then((r) => r.json());

// The pages: "bike" (bike.js), "wiring" (wiring.js), "kb" (this file), "3d" (viewer.js). Each may register enter/leave hooks.
// The address keeps the page (#bike, #wiring, #notes, #3d), so links can open one directly.
const views = {};
const HASH = { bike: "bike", wiring: "wiring", kb: "notes", "3d": "3d" };
let view = null;
function showView(v) {
  history.replaceState(null, "", "#" + HASH[v]);
  if (view && views[view] && views[view].leave) views[view].leave();
  view = v;
  document.querySelector("main").hidden = v !== "kb";
  $("viewer").hidden = v !== "3d";
  $("bike").hidden = v !== "bike";
  $("wiring").hidden = v !== "wiring";
  for (const k of ["bike", "wiring", "kb", "3d"]) $("view-" + k).className = k === v ? "on" : "";
  if (views[v] && views[v].enter) views[v].enter();
}
for (const k of ["bike", "wiring", "kb", "3d"]) $("view-" + k).onclick = () => showView(k);

function setDirty(v) {
  dirty = v;
  $("save").disabled = !v;
  $("status").textContent = readonly ? (v ? "Read-only: changes are not saved" : "Read-only copy") : v ? "Unsaved changes" : "Saved";
  $("status").className = v ? "dirty" : "";
}

function changed() {
  setDirty(true);
  clearTimeout(timer);
  timer = setTimeout(refreshPreview, 250);
}

async function refreshPreview() {
  const r = await post("api/render", data);
  generated = r.markdown ?? `Error: ${r.error}`;
  drawPreview();
}

function drawPreview() {
  const files = [{ path: "hardware/CLAUDE.md (generated: what Claude loads for hardware work)", key: "claude" }]
    .concat(context.filter((f) => !f.path.startsWith("hardware/")).map((f) => ({ path: f.path, key: f.path })));
  const tabs = $("tabs");
  tabs.replaceChildren(
    ...files.map((f) => {
      const short = f.key === "claude" ? "hardware/CLAUDE.md" : f.path;
      const b = el("button", { textContent: short, title: f.path, className: f.key === tab ? "on" : "" });
      b.onclick = () => { tab = f.key; drawPreview(); };
      return b;
    })
  );
  const text = tab === "claude" ? generated : (context.find((f) => f.path === tab) || {}).text || "";
  $("preview").textContent = text;
  $("meta").textContent = `${text.length.toLocaleString()} characters, about ${Math.round(text.length / 4).toLocaleString()} tokens` +
    (tab === "claude" ? "" : " (read-only: edit the file in the repo)");
}

function drawNav() {
  const dim = el("button", { textContent: readonly ? "Dimensions" : "Dimensions (3D model)", className: current === -1 ? "on" : "" });
  dim.onclick = () => { current = -1; drawNav(); drawEditor(); };
  // The public copy skips the notes on how to work with the editor itself.
  const shown = data.sections.map((s, i) => [s, i]).filter(([s]) => !(readonly && s.id === "rules"));
  $("nav").replaceChildren(
    ...(readonly ? [] : [dim]),
    ...shown.map(([s, i]) => {
      const b = el("button", { textContent: s.title, className: i === current ? "on" : "" });
      b.onclick = () => { current = i; drawNav(); drawEditor(); };
      return b;
    }),
    ...(readonly ? [dim] : [])
  );
}

// ---- the public copy: sections read as a document, panels show values as text
const inline = (text) => String(text).split("`").map((part, i) => (i % 2 ? el("code", { textContent: part }) : part));
const paras = (text) => String(text).split(/\n\s*\n/).filter((p) => p.trim()).map((p) => el("p", {}, ...inline(p)));

function tableCsv(s) {
  const cell = (value) => {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  };
  return [s.columns, ...s.rows].map((row) => s.columns.map((_, c) => cell(row[c])).join(",")).join("\r\n") + "\r\n";
}

function csvButton(s) {
  const button = el("button", { textContent: "Download CSV" });
  button.onclick = () => {
    // Read the current rows, including unsaved edits. The BOM helps spreadsheets read UTF-8.
    const blob = new Blob(["\ufeff", tableCsv(s)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: (s.id || "table").replace(/[^a-z0-9_-]/gi, "_") + ".csv" });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  return button;
}

function drawDoc(s) {
  const box = $("editor");
  box.replaceChildren(el("h2", { textContent: s.title }), ...(s.intro ? paras(s.intro).map((p) => ((p.className = "lead"), p)) : []));
  if (s.type === "bike") {
    const go = el("button", { textContent: "Open the Bike page", className: "primary" });
    go.onclick = () => showView("bike");
    box.append(el("p", {}, "The frame, its geometry and where each part sits are drawn on the Bike page."), el("div", { className: "actions" }, go));
  } else if (s.type === "text") {
    box.append(...paras(s.text || ""));
  } else if (s.type === "list") {
    box.append(el("ul", { className: "doclist" }, ...s.items.filter((x) => x.trim()).map((x) => el("li", {}, ...inline(x)))));
  } else {
    box.append(s.rows.length
      ? el("div", { className: "doctable" }, el("table", {}, el("tr", {}, ...s.columns.map((c) => el("th", { textContent: c }))),
        ...s.rows.map((r) => el("tr", {}, ...s.columns.map((_, c) => el("td", {}, ...inline(r[c] || "")))))))
      : el("p", { className: "hint", textContent: "Nothing here yet." }));
    box.append(el("div", { className: "actions" }, csvButton(s)));
  }
  box.scrollTop = 0;
}

// Form fields become plain text and editing controls (class "edit") go, so a panel built for the editor reads as a page.
function freeze(root) {
  if (!readonly || !root) return;
  root.querySelectorAll(".edit").forEach((e) => e.remove());
  root.querySelectorAll("input:not([type=checkbox]), textarea, select").forEach((f) => {
    const v = f.tagName === "SELECT" ? f.selectedOptions[0]?.textContent || "" : f.value;
    f.replaceWith(el("span", { className: "ro" + (f.classList.contains("num") ? " num" : ""), textContent: v }));
  });
}

function autosize(t) { t.style.height = "auto"; t.style.height = t.scrollHeight + 2 + "px"; }

function field(value, onInput) {
  const t = el("textarea", { value, rows: 1 });
  t.oninput = () => { onInput(t.value); autosize(t); changed(); };
  queueMicrotask(() => autosize(t));
  return t;
}

function drawDimensions() {
  const box = $("editor");
  box.replaceChildren();
  if (readonly) {
    box.append(el("h2", { textContent: "Dimensions" }),
      el("p", { className: "lead", textContent: "Every number the printed parts are built from, in millimetres. The CAD scripts read them, so changing one reshapes the parts and reruns the fit checks." }));
    for (const g of [...new Set(params.parameters.map((p) => p.group))]) {
      box.append(el("h3", { textContent: g }), el("div", { className: "doctable" }, el("table", {},
        el("tr", {}, el("th", { textContent: "What" }), el("th", { textContent: "Value" }), el("th", { textContent: "What it means" })),
        ...params.parameters.filter((q) => q.group === g).map((p) => el("tr", {}, el("td", { textContent: p.label }),
          el("td", { className: "val", textContent: `${p.value} ${p.unit}` }), el("td", { className: "help", textContent: p.help }))))));
    }
    box.scrollTop = 0;
    return;
  }
  box.append(
    el("h2", { textContent: "Dimensions" }),
    el("p", { className: "hint", textContent: "Every number the camera housing, wheel sensor and the v1 parts (tray, ultrasonic box) are built from, in millimetres. Box v2, the main box, keeps its sizes in the PARAMETERS block of hardware/cad/box_v2.py. Change a value, press Save dimensions: the STEP, STL and 3MF files regenerate automatically (Rebuild 3D files forces it) in the STEP, STL and 3MF in hardware/print/. The build runs the fit checks and stops with a message if parts clash." })
  );
  const groups = [...new Set(params.parameters.map((p) => p.group))];
  for (const g of groups) {
    box.append(el("h3", { textContent: g }));
    const table = el("table", { className: "dims" });
    table.append(el("tr", {}, el("th", { textContent: "What" }), el("th", { textContent: "Value" }), el("th", { textContent: "Unit" }), el("th", { textContent: "What it means" })));
    for (const p of params.parameters.filter((q) => q.group === g)) {
      const input = el("input", { type: "number", step: "any", value: p.value, className: "num" });
      input.oninput = () => {
        const v = parseFloat(input.value);
        if (Number.isNaN(v)) return;
        p.value = v; paramsDirty = true; $("saveDims").disabled = false; setDirty(dirty);
      };
      table.append(el("tr", {}, el("td", { textContent: p.label, title: "code name: " + p.key }), el("td", {}, input), el("td", { className: "unit", textContent: p.unit }), el("td", { className: "help", textContent: p.help })));
    }
    box.append(table);
  }
  const save = el("button", { id: "saveDims", textContent: "Save dimensions", className: "primary", disabled: !paramsDirty });
  save.onclick = async () => {
    const values = Object.fromEntries(params.parameters.map((p) => [p.key, p.value]));
    const r = await post("api/parameters", { values });
    $("buildlog").textContent = r.error ? "Error: " + r.error : "Saved to " + r.saved + ". Rebuilding the print files in the background (about a minute); press Rebuild 3D files to watch the result.";
    if (!r.error) { paramsDirty = false; save.disabled = true; }
  };
  const build = el("button", { textContent: "Rebuild 3D files" });
  build.onclick = async () => {
    if (paramsDirty) { $("buildlog").textContent = "Save dimensions first."; return; }
    $("buildlog").textContent = "Building, about a minute...";
    build.disabled = true;
    const r = await post("api/rebuild", {});
    build.disabled = false;
    $("buildlog").textContent = (r.ok ? "Done.\n" : "Failed:\n") + r.log;
  };
  box.append(el("div", { className: "actions" }, save, build), el("pre", { id: "buildlog", className: "log" }));
}

function drawEditor() {
  if (current === -1) return drawDimensions();
  const s = data.sections[current];
  if (readonly) return drawDoc(s);
  const box = $("editor");
  box.replaceChildren();

  box.append(el("label", { textContent: "Section title" }));
  const title = el("input", { value: s.title });
  title.oninput = () => { s.title = title.value; changed(); drawNav(); };
  box.append(title);

  box.append(el("label", { textContent: "Intro (optional)" }), field(s.intro || "", (v) => (s.intro = v)));

  if (s.type === "bike") {
    const go = el("button", { textContent: "Open the Bike page", className: "primary" });
    go.onclick = () => showView("bike");
    box.append(el("p", { className: "hint", textContent: "The frame size, geometry and where each part sits are edited on the Bike page: click a tube or a part in the drawing." }),
      el("div", { className: "actions" }, go));
  } else if (s.type === "text") {
    box.append(el("label", { textContent: "Text" }), field(s.text || "", (v) => (s.text = v)));
  } else if (s.type === "list") {
    box.append(el("label", { textContent: "Items" }));
    s.items.forEach((item, i) => {
      const del = el("button", { textContent: "✕", className: "ghost", title: "Remove" });
      del.onclick = () => { s.items.splice(i, 1); changed(); drawEditor(); };
      box.append(el("div", { className: "row" }, field(item, (v) => (s.items[i] = v)), del));
    });
    const add = el("button", { textContent: "+ Add item" });
    add.onclick = () => { s.items.push(""); changed(); drawEditor(); };
    box.append(el("div", { className: "actions" }, add));
  } else {
    const table = el("table");
    table.append(el("tr", {}, ...s.columns.map((c) => el("th", { textContent: c })), el("th")));
    s.rows.forEach((row, r) => {
      while (row.length < s.columns.length) row.push("");
      const del = el("button", { textContent: "✕", className: "ghost", title: "Remove row" });
      del.onclick = () => { s.rows.splice(r, 1); changed(); drawEditor(); };
      table.append(el("tr", {}, ...s.columns.map((_, c) => el("td", {}, field(row[c], (v) => (row[c] = v)))), el("td", {}, del)));
    });
    box.append(el("label", { textContent: "Rows" }), table);
    const add = el("button", { textContent: "+ Add row" });
    add.onclick = () => { s.rows.push(s.columns.map(() => "")); changed(); drawEditor(); };
    box.append(el("div", { className: "actions" }, add, csvButton(s)));
  }

  const actions = el("div", { className: "actions" });
  const addSection = el("button", { textContent: "+ New section (list)" });
  addSection.onclick = () => {
    data.sections.push({ id: "s" + Date.now(), title: "New section", type: "list", items: [""] });
    current = data.sections.length - 1;
    changed(); drawNav(); drawEditor();
  };
  const delSection = el("button", { textContent: "Delete this section" });
  delSection.onclick = () => {
    if (!confirm(`Delete "${s.title}"? Decisions should normally be kept.`)) return;
    data.sections.splice(current, 1);
    current = Math.max(0, current - 1);
    changed(); drawNav(); drawEditor();
  };
  const up = el("button", { textContent: "↑ Move up", disabled: current === 0 });
  up.onclick = () => move(-1);
  const down = el("button", { textContent: "↓ Move down", disabled: current === data.sections.length - 1 });
  down.onclick = () => move(1);
  actions.append(up, down, addSection, delSection);
  box.append(el("hr"), actions);
}

function move(d) {
  const [s] = data.sections.splice(current, 1);
  current += d;
  data.sections.splice(current, 0, s);
  changed(); drawNav(); drawEditor();
}

$("save").onclick = async () => {
  const r = await post("api/save", data);
  if (r.error) { $("status").textContent = "Error: " + r.error; return; }
  setDirty(false);
  $("status").textContent = `Saved, rebuilt ${r.saved}`;
  context = await (await fetch("api/context")).json();
  drawPreview();
};

window.addEventListener("beforeunload", (e) => { if (!readonly && (dirty || paramsDirty)) e.preventDefault(); });

// The public copy wears murathanyildirim.com's look: its font, colours and nav pill, dark like the site (dark only for
// now; the html.site light colours in style.css are kept for when the site gets its switch back).
function siteTheme() {
  const html = document.documentElement;
  html.classList.add("site", "dark");
  document.head.append(el("link", { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" }));
  $("bhint").textContent = "Click a part or a tube: its details open on the right. Seen from the right (drive) side; dashed = on the left side.";
  $("hint").textContent = "Click a part: its dimensions open on the right. Drag: rotate · Shift/right-drag: pan · Wheel: zoom · Double-click: reset.";
  dispatchEvent(new Event("resize")); // the 3D view repaints its background
}

(async () => {
  readonly = (await (await fetch("api/config")).json()).readonly;
  document.body.classList.toggle("readonly", readonly);
  if (readonly) siteTheme();
  data = await (await fetch("api/knowledge")).json();
  params = await (await fetch("api/parameters")).json();
  context = await (await fetch("api/context")).json();
  setDirty(false);
  if (readonly) current = data.sections.findIndex((s) => s.id !== "rules");
  drawNav();
  drawEditor();
  if (!readonly) refreshPreview(); // the public copy has no "what Claude sees" pane
  addEventListener("hashchange", () => {
    const v = Object.keys(HASH).find((k) => "#" + HASH[k] === location.hash);
    if (v && v !== view) showView(v);
  });
  const asked = Object.keys(HASH).find((k) => "#" + HASH[k] === location.hash);
  showView(asked || (data.sections.some((s) => s.type === "bike") ? "bike" : "kb"));
})();
