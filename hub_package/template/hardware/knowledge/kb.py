"""Hardware knowledge base: knowledge.json -> hardware/CLAUDE.md, plus the editing UI.

    python3 hardware/knowledge/kb.py build    # regenerate hardware/CLAUDE.md
    python3 hardware/knowledge/kb.py check    # fail if hardware/CLAUDE.md is out of date
    python3 hardware/knowledge/kb.py serve    # open the editor at http://127.0.0.1:8765

KB_READONLY=1 serves a read-only copy (the public one on murathanyildirim.com/bike-logger/hardware/, deployed by
hardware/knowledge/deploy.sh): nothing can be saved or rebuilt, and Claude's context shows hardware/CLAUDE.md only.
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / "knowledge.json"
OUT = REPO / "hardware" / "CLAUDE.md"
UI = HERE / "ui"
PRINT = REPO / "hardware" / "print"
PARAMS = REPO / "hardware" / "cad" / "parameters.json"
SCRIPTS = [REPO / "hardware" / "cad" / n for n in ("box_v2.py", "enclosure.py", "ultrasonic_box.py", "camera_housing.py", "wheel_sensor.py", "rear_box.py")]
PREVIEW = REPO / "hardware" / "cad" / "preview.py"
PREVIEW_DIR = REPO / "hardware" / "cad" / "out" / "preview"
PORT = int(os.environ.get("PORT", "8765"))  # the desktop app's preview may pick another port
READONLY = os.environ.get("KB_READONLY") == "1"

HEADER = (
    "# Hardware knowledge\n\n"
    "<!-- GENERATED from hardware/knowledge/knowledge.json by hardware/knowledge/kb.py. "
    "Do not edit by hand: edit the JSON (or run `python3 hardware/knowledge/kb.py serve`), then run `build`. -->\n\n"
    "Everything Claude needs to know about the physical build. For the software, see the root `CLAUDE.md`.\n"
)


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def table(cols, rows):
    if not rows:
        return ["(none yet)", ""]
    out = ["| " + " | ".join(cell(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for row in rows:
        row = (list(row) + [""] * len(cols))[: len(cols)]
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return out + [""]


def render_bike(s):
    """The bike section: frame geometry (drives the drawing on the Bike page) and where each part sits."""
    out = [f"Frame size: {s['size']}.\n", "Frame geometry (what the Bike page drawing is built from):\n"]
    out += table(["What", "Value", "Notes"], [[g["label"], f"{g['value']:g} {g['unit']}", g.get("help", "")] for g in s["geometry"]])
    keys = [g["key"] for g in s["geometry"] if all(g["key"] in v for v in s["sizes"].values())]
    label = {g["key"]: g["label"] for g in s["geometry"]}
    out += ["Geometry by frame size (high step):\n"]
    out += table(["What", *s["sizes"]], [[label[k], *(f"{v[k]:g}" for v in s["sizes"].values())] for k in keys])
    out += ["Where each part sits on the bike:\n"]
    out += table(["Part", "Where", "Status", "CAD model"],
                 [[m["label"], m["where"], m["status"], m.get("model") or "none"] for m in s["mounts"]])
    return out


def render(data):
    out = [HEADER]
    for s in data["sections"]:
        out.append(f"## {s['title']}\n")
        if s.get("intro"):
            out.append(s["intro"] + "\n")
        kind = s.get("type", "text")
        if kind == "table":
            out.extend(table(s["columns"], s["rows"]))
        elif kind == "bike":
            out.extend(render_bike(s))
        elif kind == "list":
            out.extend(f"- {item}" for item in s["items"])
            out.append("")
        else:
            out.append(s.get("text", "") + "\n")
    return "\n".join(out).rstrip() + "\n"


def load():
    return json.loads(DATA.read_text())


def save(data):
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    OUT.write_text(render(data))


def context_files():
    """The files Claude reads for hardware work, in the order they load."""
    paths = [OUT] if READONLY else [REPO / "CLAUDE.md", OUT, *sorted((REPO / ".claude" / "skills").glob("*/SKILL.md"))]
    return [{"path": str(p.relative_to(REPO)), "text": p.read_text() if p.exists() else ""} for p in paths]


def save_params(body):
    """Write new values into parameters.json, keeping labels and help text. Rejects unknown keys and non-numbers."""
    doc = json.loads(PARAMS.read_text())
    known = {p["key"]: p for p in doc["parameters"]}
    for k, v in body["values"].items():
        if k not in known or isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"bad value for {k}")
        known[k]["value"] = v
    PARAMS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def python():
    return next((p for p in (REPO / ".venv-cad" / "bin" / "python", REPO / ".venv" / "bin" / "python") if p.exists()), None)


BUILD_LOCK = threading.RLock()                 # one build at a time (preview and print files write the same folders)
STATUS = {"running": False, "ok": None, "log": "", "finished": 0.0}
AGAIN = threading.Event()                      # parameters were saved again while a build was running


def build_preview():
    """Regenerate the meshes the 3D view shows (hardware/cad/out/preview), from the saved parameters."""
    py = python()
    if py is None:
        return {"ok": False, "log": "No .venv-cad found. Run: python3 -m venv .venv-cad && .venv-cad/bin/pip install -r hardware/requirements.txt"}
    with BUILD_LOCK:
        r = subprocess.run([str(py), str(PREVIEW)], capture_output=True, text=True, timeout=600, check=False)
    return {"ok": r.returncode == 0, "log": (r.stdout + r.stderr).strip()[-3000:]}


def rebuild():
    with BUILD_LOCK:
        return _rebuild()


def _rebuild():
    """Regenerate the STEP/STL/3MF files in hardware/print from the saved parameters, running the scripts' own fit checks, then the 3D view."""
    py = python()
    if py is None:
        return {"ok": False, "log": "No .venv-cad found. Run: python3 -m venv .venv-cad && .venv-cad/bin/pip install -r hardware/requirements.txt"}
    logs, ok = [], True
    for script in SCRIPTS:
        r = subprocess.run([str(py), str(script), "--out", str(REPO / "hardware" / "print")], capture_output=True, text=True, timeout=600, check=False)
        ok = ok and r.returncode == 0
        logs.append(f"== {script.name}\n" + (r.stdout + r.stderr).strip())
        if not ok:
            break
    if ok:
        pv = build_preview()
        ok = pv["ok"]
        logs.append("== preview.py\n" + pv["log"])
    return {"ok": ok, "log": "\n".join(logs)[-3000:]}


def rebuild_in_background():
    """After parameters are saved: regenerate every STEP/STL/3MF in the background. Saving again meanwhile queues one more run."""
    if STATUS["running"]:
        AGAIN.set()
        return
    STATUS.update(running=True, ok=None, log="")

    def work():
        while True:
            AGAIN.clear()
            r = rebuild()
            if not AGAIN.is_set():
                STATUS.update(running=False, ok=r["ok"], log=r["log"], finished=time.time())
                return
    threading.Thread(target=work, daemon=True).start()


def open_in_studio(name):
    """Open the plate (3MF) with the same name as the STL, or the STL itself, in Bambu Studio's Prepare view (macOS)."""
    stl = (PRINT / Path(name).name).resolve()
    if stl.parent != PRINT.resolve() or stl.suffix != ".stl" or not stl.is_file():
        raise ValueError("unknown model")
    target = stl.with_suffix(".3mf") if stl.with_suffix(".3mf").is_file() else stl
    r = subprocess.run(["open", "-a", "BambuStudio", str(target)], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise ValueError("could not open Bambu Studio: " + (r.stderr.strip() or "is it installed in /Applications?"))
    return {"opened": target.name}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, ctype="application/json", status=200):
        body = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/config":
            return self.send(json.dumps({"readonly": READONLY}))
        if self.path == "/api/knowledge":
            return self.send(DATA.read_bytes())
        if self.path == "/api/parameters":
            return self.send(PARAMS.read_bytes())
        if self.path == "/api/rebuild/status":
            return self.send(json.dumps(STATUS))
        if self.path.startswith("/api/preview/"):
            f = (PREVIEW_DIR / (self.path.rsplit("/", 1)[1] + ".json")).resolve()
            if f.parent != PREVIEW_DIR.resolve() or not f.is_file():
                return self.send(json.dumps({"error": "not built yet"}), status=404)
            return self.send(f.read_bytes())
        if self.path == "/api/models":
            return self.send(json.dumps([{"name": p.name, "mtime": p.stat().st_mtime, "size": p.stat().st_size}
                                         for p in sorted(PRINT.glob("*.stl"))]))
        if self.path.startswith("/stl/"):
            f = (PRINT / self.path[5:].split("?")[0]).resolve()
            if f.parent != PRINT.resolve() or f.suffix != ".stl" or not f.is_file():
                return self.send("not found", "text/plain", 404)
            return self.send(f.read_bytes(), "model/stl")
        if self.path == "/api/context":
            return self.send(json.dumps(context_files()))
        name = "index.html" if self.path == "/" else self.path.lstrip("/")
        f = (UI / name).resolve()
        if f.parent != UI or not f.is_file():
            return self.send("not found", "text/plain", 404)
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}.get(f.suffix, "text/plain")
        self.send(f.read_bytes(), ctype + "; charset=utf-8")

    def do_POST(self):
        if READONLY and self.path != "/api/render":  # rendering the preview changes nothing
            return self.send(json.dumps({"error": "This is a read-only copy: edit in the local editor"}), status=403)
        # Reject cross-site posts: only the page we serve may write.
        if not READONLY and self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            return self.send("forbidden", "text/plain", 403)
        if self.path == "/api/rebuild":
            return self.send(json.dumps(rebuild()))
        if self.path == "/api/preview/build":
            return self.send(json.dumps(build_preview()))
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size > 5_000_000:
                raise ValueError("request too large")
            data = json.loads(self.rfile.read(size))
            if self.path == "/api/open-in-studio":
                return self.send(json.dumps(open_in_studio(data["name"])))
            if self.path == "/api/parameters":
                save_params(data)
                rebuild_in_background()
                return self.send(json.dumps({"saved": str(PARAMS.relative_to(REPO))}))
            text = render(data)
        except (ValueError, KeyError, TypeError) as e:
            return self.send(json.dumps({"error": str(e)}), status=400)
        if self.path == "/api/render":
            return self.send(json.dumps({"markdown": text}))
        if self.path == "/api/save":
            save(data)
            return self.send(json.dumps({"saved": str(OUT.relative_to(REPO)), "chars": len(text)}))
        self.send("not found", "text/plain", 404)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "build"
    if cmd == "build":
        save(load())
        print(f"wrote {OUT.relative_to(REPO)}")
    elif cmd == "check":
        if not OUT.exists() or OUT.read_text() != render(load()):
            sys.exit("hardware/CLAUDE.md is out of date: run `python3 hardware/knowledge/kb.py build`")
        print("hardware/CLAUDE.md is up to date")
    elif cmd == "serve":
        try:
            server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        except OSError:
            sys.exit(f"Port {PORT} is busy: the editor may already be running at http://127.0.0.1:{PORT}")
        print(f"Knowledge editor: http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
        server.serve_forever()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
