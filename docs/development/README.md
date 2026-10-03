# Developer guide

This guide explains how RumiaConfigurator is built, so that you can read the
code, change it and add to it on your own. It describes the code as it is in
this version of the repository and is updated together with the code.

The public wiki of the project is generated from these files at every release:
edit the files here, never the wiki.

## Reading order

If you are new to the project, read the pages in this order:

1. [Architecture](architecture.md): the layers, the rules that are never broken
   and what happens from the command line to the window on screen.
2. [Environment](environment.md): install the tools, run the app, the tests and
   the checks, and understand what the CI does.
3. [Core services](core.md): user folders, settings and the application log.
4. [User interface](gui.md): the main window, its views and how they talk to
   each other.
5. [Theme](theme.md): colors, fonts, icons, the generated style sheet and the
   brand components.
6. [Translations](translations.md): how texts are translated and switched at
   run time.
7. [Connection](connection.md): adapters, opening the CAN bus, explained
   errors.
8. [Data flow](data-flow.md): from the receive thread to the screen, frame
   buffer, frames per second and bus load.
9. [Network](network.md): finding the nodes, their identity, NMT state and
   heartbeat alarm, the network panel.
10. [EDS and products](eds-and-products.md): loading EDS and DCF files,
    recognising the Rumia products, the profile of each node.
11. [Simulator and demo mode](simulator.md): simulated CANopen nodes for the
    tests and for `--demo`.
12. [Testing](testing.md): how the tests are organised and how to write one.
13. [Recipes](recipes.md): step-by-step instructions for the most common changes.

## Pages

| Page | Covers |
| --- | --- |
| [Architecture](architecture.md) | layers, rules, start-up sequence, folder layout |
| [Environment](environment.md) | uv, commands, ruff, mypy, CI |
| [Core services](core.md) | `paths`, `settings`, `app_log` |
| [User interface](gui.md) | `app.py`, `MainWindow`, top bar, network panel, work area, status bar |
| [Theme](theme.md) | tokens, style sheet, `ThemeManager`, fonts, icons, brand widgets, theme demo |
| [Translations](translations.md) | `tr()`, `retranslate()`, `LanguageManager`, `.ts` and `.qm` files |
| [Connection](connection.md) | `ConnectionService`, states, adapter detection, `ErrorKind` and messages, Linux permissions, adding a backend |
| [Data flow](data-flow.md) | receive thread, `FrameBuffer` and cursors, `LiveData` at 30 Hz, frames/s and bus load |
| [Network](network.md) | scan, passive listening, identity, NMT states, heartbeat alarm, `NodeRegistry`, `NodePanel` |
| [EDS and products](eds-and-products.md) | tolerant EDS/DCF loader and its warnings, minimal CiA 301 dictionary, recognition rules, `ProfileRegistry`, adding a product |
| [Simulator and demo mode](simulator.md) | `Simulator`, simulated Smart IMU and INCLI Sense, EDS loader, test fixtures, `--demo` banner |
| [Testing](testing.md) | test layout, fixtures, Qt tests, writing a new test |
| [Recipes](recipes.md) | common changes, one checklist each |

## Conventions used in this guide

- File paths are written from the root of the repository, for example
  `src/rumia_configurator/core/settings.py`.
- Requirement codes such as `FR-APP-01` or `UI-COL-02` refer to the project
  requirements; they also appear in commit messages and docstrings, so you can
  search the code for them.
- Code, names, comments and this guide are in English. The user interface is in
  Italian and English.

## Writing pages for the wiki

The wiki is generated from these files, so a few rules keep it working (a
test checks them):

- Every page starts with a `# Title` line. The title becomes the name of the
  wiki page (`# Core services` → page *Core services*); changing a title
  renames the page.
- All pages live in this folder, without subfolders, and link to each other
  with relative links: `[Theme](theme.md#colors)`.
- Write paths of the code from the repository root, in backticks:
  `` `src/rumia_configurator/core/settings.py` ``. In the wiki they become
  links to the code of the release.
- Every new page must be linked from the list in this file.
