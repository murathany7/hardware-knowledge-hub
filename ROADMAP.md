# Roadmap

Where Hardware Knowledge Hub is going, in rough order. Most items link to an issue; comment there to pick it up or to shape it. Nothing here is promised by a date.

## Now: work for any build, not only the example

The Notes view already holds any project. The Bike and Wiring views and the 3D part list are drawn for the Bike Logger example.

- **A blank starter.** `hardware-knowledge-hub init --blank` creates a project with empty notes and no example parts. ([#3](https://github.com/murathany7/hardware-knowledge-hub/issues/3))
- **Views that follow the data.** Show the Bike view only when the notes have a bike section; let a project name its own CAD scripts instead of the list in `kb.py`. ([#4](https://github.com/murathany7/hardware-knowledge-hub/issues/4))
- **Wiring for other boards.** Describe a board's header as data, so the Wiring view can draw an Arduino Uno, an ESP32 or a Pico as well as the Raspberry Pi 5. ([#5](https://github.com/murathany7/hardware-knowledge-hub/issues/5))

## Next: every desktop

- **Open model on Linux and Windows.** Today the button works on macOS. ([#1](https://github.com/murathany7/hardware-knowledge-hub/issues/1))
- **More desktop apps.** Cura, Fusion, Blender and others, added to the allowlist in `kb.py`. ([#2](https://github.com/murathany7/hardware-knowledge-hub/issues/2))
- **Windows.** Run the checks on Windows and remove what stops the repository from working there. ([#7](https://github.com/murathany7/hardware-knowledge-hub/issues/7))

## Later: more ways in and out

- **Parts list export.** Download a table from the notes as CSV, for ordering parts. ([#6](https://github.com/murathany7/hardware-knowledge-hub/issues/6))
- **More example builds.** A second, smaller example next to Bike Logger, and a gallery of builds that use the hub.
- **Keyboard and screen reader use** of the drawings and the 3D view. ([#8](https://github.com/murathany7/hardware-knowledge-hub/issues/8))
- **Translations** of the editor.

## Not planned

- A hosted service or accounts. The hub is a folder on your computer.
- A JavaScript framework or a bundler for the editor.
