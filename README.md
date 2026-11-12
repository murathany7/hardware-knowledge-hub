# Hardware Knowledge Hub

[![Checks](https://github.com/murathany7/hardware-knowledge-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/murathany7/hardware-knowledge-hub/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/hardware-knowledge-hub)](https://pypi.org/project/hardware-knowledge-hub/) [![npm](https://img.shields.io/npm/v/hardware-knowledge-hub)](https://www.npmjs.com/package/hardware-knowledge-hub) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/murathany7/hardware-knowledge-hub/blob/main/LICENSE)

**Give your AI assistant the whole build, one time.**

A hardware project comes with dozens of facts an assistant needs to make a good suggestion. Which parts are on hand? Which GPIO pins are already taken? What actually fits in the enclosure? Keep those details in one editable project notebook, then let your coding assistant read the same notes each time you work together.

[Explore the live Bike Logger demo](https://murathany7.github.io/hardware-knowledge-hub/) · [Source on GitHub](https://github.com/murathany7/hardware-knowledge-hub)

## Try it in a few minutes

```sh
pip install hardware-knowledge-hub
hardware-knowledge-hub init my-first-build
cd my-first-build
python3 hardware/knowledge/kb.py serve
```

If you have Node.js, `npx hardware-knowledge-hub init my-first-build` creates the same folder without installing anything. The editor itself needs Python 3.10 or newer.

Open [the local editor](http://127.0.0.1:8765). Your new folder starts with Bike Logger, a real Raspberry Pi project with a rear camera, sensors, and a printed enclosure.

1. **Explore the build.** Find where parts sit in **Bike**, trace connections in **Wiring**, and inspect the enclosure in **3D Parts**.
2. **Record what you learn.** Edit **Notes** when a component, dimension, or design decision changes. Saving updates the project notes your assistant reads.
3. **Ask about the build.** Open the project folder in Codex or Claude Code. The starter project points both assistants to the generated hardware notes.

> Read the hardware notes. Where is the rear camera mounted, how is its cable routed, and which dimensions should I measure before changing the bracket?

You can ask the next question in a fresh chat. The project folder carries the measurements, parts list, print log, and decisions forward.

## From the 3D view to your slicer

In the local editor on macOS, select a finished print in **3D Parts**, choose an app, and click **Open model**. The app needs to be installed.

| Application | File opened |
|---|---|
| Bambu Studio | Matching 3MF when available, otherwise STL |
| OrcaSlicer | Matching 3MF when available, otherwise STL |
| PrusaSlicer | Matching 3MF when available, otherwise STL |
| FreeCAD | Matching STEP when available, otherwise STL |

You can also open the files directly from `hardware/print/`. The hosted demo runs in the browser. The local editor is where you save changes and launch desktop apps.

## Make it yours

Use **Notes** for your own parts, measurements, decisions, and build log. The Bike Logger diagrams and CAD controls are examples configured for that build. Project data lives in `hardware/knowledge/knowledge.json`, with the generated assistant-readable notes in `hardware/CLAUDE.md`.

## Contributing

The hub is one Python file and a few plain JavaScript files, with no dependencies and no build step, so it is quick to get into. You do not need a 3D printer or a Raspberry Pi to help.

- **Try it and tell us.** [Report a problem, share an idea, or describe your build](https://github.com/murathany7/hardware-knowledge-hub/issues/new/choose).
- **Pick something small.** Issues marked [good first issue](https://github.com/murathany7/hardware-knowledge-hub/labels/good%20first%20issue) are sized for a first pull request.
- **See where it is going.** The [roadmap](https://github.com/murathany7/hardware-knowledge-hub/blob/main/ROADMAP.md) lists the larger directions: a blank starter, other boards in the Wiring view, Linux and Windows.

[CONTRIBUTING.md](https://github.com/murathany7/hardware-knowledge-hub/blob/main/CONTRIBUTING.md) covers setup, where things are, and the checks to run. The project is MIT-licensed.
