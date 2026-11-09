"""Build a static Bike Logger demo for GitHub Pages."""
import argparse
import json
import shutil
from pathlib import Path

import kb


def build(destination):
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit("Choose a new or empty output directory.")
    previews = sorted(kb.PREVIEW_DIR.glob("*.json"))
    required = {"box_v2", "camera_housing", "rear_box", "tray", "ultrasonic_box", "wheel_sensor"}
    missing = required - {path.stem for path in previews}
    if missing:
        raise SystemExit(f"Generate CAD previews first. Missing: {', '.join(sorted(missing))}")

    shutil.copytree(kb.UI, destination, dirs_exist_ok=True)
    (destination / ".nojekyll").touch()
    index = destination / "index.html"
    page = index.read_text().replace("<title>Hardware knowledge</title>", "<title>Hardware Knowledge Hub · Bike Logger demo</title>")
    page = page.replace(
        '<nav id="sitenav" aria-label="murathanyildirim.com">',
        '<nav id="sitenav" aria-label="Demo links">',
    ).replace(
        '<a href="/">Murathan Yıldırım</a>\n    <a href="/#bike-logger">Bike Logger</a>\n    <a href="../">3D showcase</a>',
        '<a href="https://github.com/murathany7/hardware-knowledge-hub">Hardware Knowledge Hub</a>',
    ).replace('>Build notes</span>', '>Bike Logger demo</span>')
    page = page.replace(
        "</header>",
        '</header>\n<p class="demo-intro">New to hardware? Explore a real build. Start with where the parts go, '
        'then see how they connect and what changed along the way.</p>',
    )
    index.write_text(page)
    with (destination / "style.css").open("a") as css:
        css.write("\n.demo-intro { margin: 0; padding: 8px 20px; color: var(--muted); }\n")

    api = destination / "api"
    (api / "preview").mkdir(parents=True)
    (api / "config").write_text(json.dumps({"readonly": True}))
    shutil.copyfile(kb.DATA, api / "knowledge")
    shutil.copyfile(kb.PARAMS, api / "parameters")
    (api / "context").write_text(json.dumps([
        {"path": "hardware/CLAUDE.md", "text": kb.render(kb.load())},
    ]))
    for path in previews:
        shutil.copyfile(path, api / "preview" / path.stem)
    meshes = sorted(kb.PRINT.glob("*.stl"))
    (api / "models").write_text(json.dumps([
        {"name": path.name, "mtime": path.stat().st_mtime, "size": path.stat().st_size} for path in meshes
    ]))
    stl = destination / "stl"
    stl.mkdir()
    for path in meshes:
        shutil.copyfile(path, stl / path.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    build(parser.parse_args().destination)
