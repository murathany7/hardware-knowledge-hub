# Contributing

Hardware Knowledge Hub is small on purpose: one Python file serves the editor, the editor is plain JavaScript with no build step, and nothing needs installing to run it. That makes it a good first project to contribute to. You do not need to own a 3D printer or a Raspberry Pi.

## Ways to help

| If you like | You could |
|---|---|
| Trying things out | Run the quick start on your machine and [report](https://github.com/murathany7/hardware-knowledge-hub/issues/new/choose) anything confusing or broken |
| Building hardware | Use the hub for your own build and tell us what the Notes could not hold |
| Python | Add an operating system or a desktop app to **Open model**, or extend the tests |
| JavaScript, SVG, WebGL | Improve the Bike, Wiring and 3D views, keyboard use and small screens |
| CadQuery | Improve the example parts or their fit checks |
| Writing | Make the README, the starter project's instructions and the landing page clearer |

Open issues marked [good first issue](https://github.com/murathany7/hardware-knowledge-hub/labels/good%20first%20issue) are sized for a first pull request, and [ROADMAP.md](ROADMAP.md) lists the larger directions. For anything bigger than a fix, open an issue first so we can agree on the shape before you write it.

## Set up

You need Python 3.10 or newer. Node.js is optional (it is only used to syntax-check the editor scripts and to test the npm installer).

```sh
git clone https://github.com/murathany7/hardware-knowledge-hub
cd hardware-knowledge-hub
python3 hardware/knowledge/kb.py serve
```

Open http://127.0.0.1:8765. You are now editing the Bike Logger example that ships to every new user. Reload the page after changing a file in `hardware/knowledge/ui/`; restart the command after changing `kb.py`.

## Where things are

`hardware/` at the top of the repository is a link to `hub_package/template/hardware/`, the folder that `hardware-knowledge-hub init` copies to a new user. Edit either path; they are the same files.

| Path | What it is |
|---|---|
| `hub_package/__init__.py`, `cli.cjs` | The `init` command, for pip and for npm |
| `hub_package/template/` | The starter project every new user receives |
| `hardware/knowledge/kb.py` | The local server, the notes generator and the `build`, `check` and `serve` commands |
| `hardware/knowledge/knowledge.json` | The project's notes as data. The editor reads and writes this file |
| `hardware/CLAUDE.md` | The notes an AI assistant reads. Generated from the JSON: never edit it by hand |
| `hardware/knowledge/ui/` | The editor: `app.js` (Notes), `bike.js`, `wiring.js`, `viewer.js` (3D parts) |
| `hardware/cad/` | CadQuery scripts for the example parts, and `parameters.json` with their dimensions |
| `hardware/print/` | Generated STL, STEP and 3MF files |
| `hardware/knowledge/build_demo.py` | Builds the static, read-only copy of the editor |
| `docs/` | The landing page and `docs/demo/`, the static copy that GitHub Pages serves |
| `tests/` | The tests. Standard library only |

## Before you open a pull request

```sh
python3 hardware/knowledge/kb.py check
python3 -m unittest discover -s tests
```

The same checks run on every pull request, on Linux and macOS.

If you changed `knowledge.json`, run `python3 hardware/knowledge/kb.py build` to regenerate `hardware/CLAUDE.md`.

If you changed anything under `hardware/knowledge/ui/`, the notes, the dimensions or the print files, rebuild the published demo, otherwise the test `test_committed_demo_matches_the_template` fails:

```sh
rm -rf docs/demo
python3 hardware/knowledge/build_demo.py docs/demo
```

To try the static demo the way visitors see it, serve `docs/` over HTTP (`python3 -m http.server -d docs`) and open `/demo/`.

Changing the 3D parts themselves needs CadQuery, which is the one heavy dependency:

```sh
python3 -m venv .venv-cad
.venv-cad/bin/pip install -r hardware/requirements.txt
```

After that, **Rebuild 3D files** in the editor regenerates `hardware/print/` and the 3D view.

## Ground rules

- **No new runtime dependencies.** The editor runs on the Python standard library, and the local editor loads nothing from the network. A user on a workshop laptop with no internet must be able to run it.
- **No build step for the editor.** Plain JavaScript and CSS that a beginner can read in the browser's developer tools.
- **The server stays local and careful.** It listens on 127.0.0.1 only, refuses writes from other websites, serves only its own folders and opens only allowlisted desktop apps. Changes to `kb.py` that touch files, requests or `subprocess` need a test.
- **Add a test with a behavior change.** `tests/test_hub.py` shows how: each test works on a throwaway project, never on the repository.
- **Plain words.** The audience is someone on their first hardware build. Explain a term the first time it appears.
- **Keep measured and estimated values apart** in the example's notes, and say which is which.

## Pull requests

Keep a pull request to one change. Say what you changed and how you tried it; add a screenshot for anything visible. Contributions are released under the project's [MIT license](LICENSE).

## Releases

Maintainers bump the version in `pyproject.toml` and `package.json` (a test keeps them equal), add the changes to [CHANGELOG.md](CHANGELOG.md) run the **Publish to PyPI** workflow, and run `npm publish` for npm.
