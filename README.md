# Hardware Knowledge Hub

A project notebook for your first hardware build. Keep track of what you bought, where each part goes, how everything connects, and what you learned along the way.

**Start with the Bike Logger example.** Explore the bike layout, follow the wiring, read the build notes, and rotate the printed parts in 3D.

## Install from PyPI

```sh
pip install hardware-knowledge-hub
hardware-knowledge-hub init my-first-build
cd my-first-build
```

Then run the editor from that folder.

## Run the editor

With Python 3 installed, run this from the project folder.

```sh
python3 hardware/knowledge/kb.py serve
```

Open http://127.0.0.1:8765. The Notes view edits the example and saves it to `hardware/knowledge/knowledge.json`. The editor also generates `hardware/CLAUDE.md` from the same data. The Bike layout, wiring and CAD panels are configured for the included example.

## Preview the demo

```sh
python3 -m http.server 8000
```

Open http://localhost:8000/docs/ (landing page) or http://localhost:8000/docs/demo/ (interactive example). The demo is read-only and runs on static hosting. To publish it, select GitHub Actions in GitHub Pages settings and run the Publish demo workflow.

The example comes from [Bike Logger](https://murathanyildirim.com/bike-logger/).

## Install from source

Run `pip install .` or `npm install -g .`, then run
`hardware-knowledge-hub init my-first-build` to create an editable copy of the Bike Logger example.
The editor requires Python even when installed using npm.
