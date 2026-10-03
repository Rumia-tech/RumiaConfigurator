# Core services

`src/rumia_configurator/core/` contains services written in pure Python. They
never import Qt, so they can be used from the command line and tested without a
display. Mypy checks this folder in strict mode.

Today there are three modules: user folders, settings and the application log.

Source files:

- `src/rumia_configurator/core/paths.py`
- `src/rumia_configurator/core/settings.py`
- `src/rumia_configurator/core/app_log.py`

## User folders: `core/paths.py`

The application stores its files in the folders each operating system expects,
found with the `platformdirs` library:

| Function | Windows | Linux | macOS |
| --- | --- | --- | --- |
| `config_dir()` | `%LOCALAPPDATA%\Rumia\RumiaConfigurator` | `~/.config/RumiaConfigurator` | `~/Library/Application Support/RumiaConfigurator` |
| `log_dir()` | `%LOCALAPPDATA%\Rumia\RumiaConfigurator\Logs` | `~/.local/state/RumiaConfigurator/log` | `~/Library/Logs/RumiaConfigurator` |
| `settings_path()` | `config_dir()/settings.json` | same | same |

The functions only compute paths; folders are created when a file is written.
The tests replace `config_dir` and `log_dir` with temporary folders, so they
never touch your real settings (see [Testing](testing.md#fixtures)).

## Settings: `core/settings.py`

The user's preferences are a dataclass saved as JSON in `settings.json`
(FR-APP-01).

### Fields

| Field | Type | Default | Allowed values | Used by |
| --- | --- | --- | --- | --- |
| `schema_version` | int | `1` | | file format version |
| `language` | str | `""` | `""` (system), `"it"`, `"en"` | language of the interface |
| `ui_mode` | str | `"base"` | `"base"`, `"expert"` | Base/Expert switch |
| `theme` | str | `"system"` | `"system"`, `"light"`, `"dark"` | theme |
| `log_level` | str | `"INFO"` | `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` | log file detail |
| `window_geometry` | str | `""` | base64 text, `""` = default size | main window position and size |
| `node_panel_width` | int | `272` | > 0 | width of the network panel |
| `connection.backend` | str | `"slcan"` | | last CAN adapter type |
| `connection.channel` | str | `""` | | last port or channel |
| `connection.bitrate` | int | `1000000` | > 0 | last bitrate, in bit/s |

`connection` is a nested dataclass, `ConnectionSettings`, saved as a JSON
object. A saved file looks like this:

```json
{
  "schema_version": 1,
  "language": "it",
  "ui_mode": "base",
  "theme": "system",
  "log_level": "INFO",
  "window_geometry": "AdnQywADAAA...",
  "node_panel_width": 272,
  "connection": {
    "backend": "slcan",
    "channel": "",
    "bitrate": 1000000
  }
}
```

### Loading: tolerant but never silent

`SettingsStore(path).load()` returns a `LoadResult` with the `settings` and a
list of `warnings`. Each warning is also written to the log. Loading never
fails:

- **Missing file**: default settings, no warning (first start).
- **Unreadable file** (not JSON, not a JSON object, wrong encoding): the file is
  renamed to `settings.json.corrupt-<date-time>` so it can be inspected, the
  defaults are used and a warning says where the old file went.
- **Unknown key**: ignored, with a warning.
- **Wrong type or value**: only that field goes back to its default, with a
  warning that names the field, the bad value and the allowed values. The type
  check is exact: `true` is not accepted where a number is expected, even though
  Python treats `bool` as a kind of `int`.
- **File written by a newer version** (`schema_version` higher than the one the
  code knows): loaded anyway, with a warning that some preferences may be lost.

The checks are in `_check_value()`. Which values are allowed is declared in
two places at the top of the module: `_ALLOWED_VALUES` (field → tuple of
accepted strings) and `_POSITIVE_INTS` (fields that must be greater than zero).

When the interface starts with warnings, the status bar says that some settings
were reset (`MainWindow.report_settings_reset()`).

### Saving: atomic

`SettingsStore.save(settings)` writes the JSON to a temporary file in the same
folder and then replaces `settings.json` with it (`os.replace`). If the
computer stops in the middle, the old file is still complete: a settings file
is never half-written.

The interface saves at the moment the user changes a choice, and once more when
the main window closes (for geometry and panel width).

To add a setting, follow [Recipes](recipes.md#add-a-setting).

## Application log: `core/app_log.py`

`configure_logging(log_dir, level)` (FR-APP-02) sets up Python's standard
`logging` for the whole application:

- **File** `app.log` in the log folder, rotating: when it reaches 1 MB it is
  renamed `app.log.1` and a new one starts; at most five old files are kept.
  Every line has date, level, thread, logger name and message.
- **Console** (stderr): only warnings and errors.
- The `can` and `canopen` libraries are limited to warnings, because at debug
  level they write a line for every CAN frame.
- The first line after start-up records the version, Python and the operating
  system.

It is called once by `cli.main()` before any command runs, with the level from
the settings. If the log folder cannot be written, the application tells the
user on stderr and goes on without a log file. The handlers it installs carry
a marker attribute, so a second call (or `shutdown_logging()`) replaces exactly
those and nothing else.

In the code, each module gets its own logger and writes to it:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Connected to %s", channel)  # normal events
logger.warning("EDS has no default for %s", name)  # problems the user may need to know
logger.exception("Log export failed")  # inside an except block: adds the traceback
```

Pass values as arguments (`"%s", value`), not with f-strings: the text is built
only if the message is actually written.

### Exporting the logs

`export_logs(log_dir, settings_file, dest)` creates a ZIP to attach to a
support request:

```
logs/app.log, logs/app.log.1, ...   all log files
settings.json                       the user settings
system_info.txt                     version, Python, OS, versions of the key packages
```

Missing files are skipped. It is used by the command
`rumia-configurator export-logs [-o file.zip]` and by the menu item
*Export logs…* of the main window (see [User interface](gui.md#menu-actions)).
`default_export_name()` suggests a file name with date and time.
