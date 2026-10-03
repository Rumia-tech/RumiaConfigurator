# Testing

The tests use [pytest](https://docs.pytest.org) and, for the interface,
[pytest-qt](https://pytest-qt.readthedocs.io). They live in `tests/` and need
no hardware, no network and no screen. Run them with `uv run pytest`; the
options for running only some tests are in
[Environment](environment.md#running-some-of-the-tests).

## What is tested where

| File | Covers |
| --- | --- |
| `tests/test_settings.py` | settings load and save, every kind of invalid value, corrupt file kept aside, newer schema |
| `tests/test_app_log.py` | log file, levels, rotation, noisy libraries, ZIP export, `export-logs` command |
| `tests/test_cli.py` | `--version`, no arguments opens the GUI, `--demo` and `--theme-demo` options, `adapters` command, nothing imports `legacy/` |
| `tests/test_connection_errors.py` | real python-can exceptions of every backend and system → `ErrorKind` |
| `tests/test_adapters.py` | adapter detection: Rumia first, CANable, SocketCAN, backends per system |
| `tests/test_connection_service.py` | open errors never become a virtual bus, SLCAN check, one bus at a time, lost adapter, controller state |
| `tests/test_connection_gui.py` | adapter and bitrate menus, Connect/Disconnect, settings saved, error dialogs in three parts, demo connection, top bar width |
| `tests/test_frame_buffer.py` | ring buffer: fields, cursors, wrap-around, lost frames, search by time |
| `tests/test_traffic_stats.py` | bits per frame, bus load of a known traffic, one-second window, error and sent frames |
| `tests/test_traffic_load.py` | acceptance of T1.3: 5000 frames/s for 30 s on the virtual bus, nothing lost (takes 30 s) |
| `tests/test_live_data.py` | 30 Hz timer: frames reach the GUI within 100 ms, tick under 5 ms, sent frames recorded, status bar |
| `tests/test_node_registry.py` | scan, passive discovery, identity, NMT state, heartbeat alarm, no nodes from PDOs |
| `tests/test_node_panel.py` | acceptance of T1.4: network panel in demo mode, heartbeat alarm on the row, selection, width |
| `tests/test_nmt.py` | NMT frames and the check of each command on the heartbeat |
| `tests/test_nmt_gui.py` | confirmation (cancel sends nothing), node menu, network buttons, outcome in the status bar |
| `tests/test_simulator.py` | simulated nodes on the virtual bus: scan, identity, NMT and heartbeat, store/restore, SDO aborts, PDO content and rate, PDO reconfiguration, INCLI Sense CiA 410 logic |
| `tests/test_signals.py` | generated measurements: repeatable, plausible ranges |
| `tests/test_eds.py` | tolerant EDS/DCF import: warnings, `$NODEID` defaults, every load error, minimal dictionary |
| `tests/test_catalog.py` | product recognition: one case per rule |
| `tests/test_node_profiles.py` | profile of a node: automatic, by hand, from a file, session only |
| `tests/test_profile_gui.py` | RUMIA badge, *Associate profile…*, header, EDS warnings, file errors |
| `tests/test_demo_mode.py` | demo banner in both languages, simulator started and stopped, start failure reported |
| `tests/test_theme_tokens.py` | contrast of every color pair in both themes, waivers, plot series, brand colors (no Qt) |
| `tests/test_theme_qt.py` | fonts load, style sheet uses only token colors and parses, no hex colors in GUI code, button heights, theme switching, icons follow the theme, theme demo |
| `tests/test_main_window.py` | window fits 1366×768 in both languages, live language and theme switch, Base/Expert tabs, layout saved and restored, translations complete |
| `tests/test_docs.py` | this guide: every module is documented, every internal link works |
| `tests/test_qt_smoke.py` | Qt can create a widget in this environment |

## Configuration

The pytest settings are in `pyproject.toml` under `[tool.pytest.ini_options]`:

- `testpaths = ["tests"]`: `uv run pytest` looks only in `tests/`.
- `--strict-markers` and `xfail_strict`: a typo in a marker, or a test marked
  "expected to fail" that passes, is an error.
- `qt_api = "pyside6"`: pytest-qt uses PySide6.

## Fixtures

`tests/conftest.py` applies to every test:

- It sets `QT_QPA_PLATFORM=offscreen` (unless already set), so Qt creates
  windows in memory: tests run the same on a laptop, on a server and in CI.
- The `user_dirs` fixture is **automatic**: it replaces `core.paths.config_dir`
  and `core.paths.log_dir` with folders inside the test's temporary folder.
  No test ever reads or writes your real settings or logs. It also closes the
  log handlers at the end, because on Windows an open file cannot be deleted.

It also defines the fixtures for CANopen tests (`sim_channel`, `recorder`,
`app_network`, `simulator`): a private virtual bus with the simulated nodes on
it. They are described in
[Simulator and demo mode](simulator.md#using-it-in-tests).

Fixtures from pytest and pytest-qt used often:

| Fixture | What it gives |
| --- | --- |
| `tmp_path` | a new empty folder for the test |
| `monkeypatch` | temporary changes to attributes and environment variables, undone after the test |
| `capsys` | what the code printed on stdout and stderr |
| `qapp` | the `QApplication`, created once for the whole run |
| `qtbot` | registers widgets (closed after the test) and simulates clicks and keys |

`make_window()` in the GUI tests passes a `ConnectionController` whose adapter
list is fixed (often empty), so that no test depends on the serial ports of
the machine it runs on.

Test modules that need the theme or the translations define their own fixture
that calls `install_theme()` / `LanguageManager` and **undoes** it afterwards
(empty style sheet, `_reset_for_tests()`, `uninstall()`), because the
`QApplication` is shared by all tests. See the `manager` fixture in
`tests/test_theme_qt.py` and `managers` in `tests/test_main_window.py`.

## Writing a test

A test is a function whose name starts with `test_`, in a file whose name
starts with `test_`. Name it after the behaviour it checks.

A service test, without Qt:

```python
from pathlib import Path

from rumia_configurator.core.settings import Settings, SettingsStore


def test_theme_is_saved(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(Settings(theme="dark"))
    assert store.load().settings.theme == "dark"
```

An interface test, written in `tests/test_main_window.py` where the `managers`
fixture and the `make_window()` helper are defined:

```python
from pytestqt.qtbot import QtBot


def test_base_mode_hides_parameters(qtbot: QtBot, managers) -> None:
    window = make_window(qtbot, managers)
    window.top_bar.base_button.click()
    assert "parameters" not in window.workspace.visible_tabs()
```

Tips for interface tests:

- Always `qtbot.addWidget(widget)`, so the widget is closed at the end.
- After a language switch or a resize, let Qt process its events before
  checking texts or sizes: the tests call `QApplication.processEvents()` a few
  times (`settle()` in `tests/test_main_window.py`).
- Call the methods the user would trigger (`button.click()`,
  `action.trigger()`), not private methods, when possible.
- The offscreen screen is only 800×600: Qt shrinks restored windows to fit it,
  so a test about saved geometry checks the saved data, not the window size.
- Qt reports some problems only as printed messages (for example "Could not
  parse application stylesheet"). To fail on them, install a message handler:
  see the `qt_messages` fixture in `tests/test_theme_qt.py`.

## Annotations

Tests are annotated like the rest of the code (`-> None`, typed fixtures).
Mypy runs on `src/` only, but annotations make tests easier to read and let
the editor help you.
