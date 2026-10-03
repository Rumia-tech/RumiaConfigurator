# Recipes

Step-by-step instructions for the most common changes. Each recipe ends with
the checks to run; before committing, always run the full set:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
```

and update this guide if what you changed is described here.

- [Add a setting](#add-a-setting)
- [Add a translated text](#add-a-translated-text)
- [Add a button to a view](#add-a-button-to-a-view)
- [Add a tab to the work area](#add-a-tab-to-the-work-area)
- [Add an icon](#add-an-icon)
- [Add or change a color](#add-or-change-a-color)
- [Add a command-line option](#add-a-command-line-option)
- [Regenerate icons and logos](#regenerate-icons-and-logos)
- Add a simulated product: see
  [Simulator and demo mode](simulator.md#add-a-simulated-product)
- Add a CAN backend: see [Connection](connection.md#add-a-backend)
- [Add an operation that asks for confirmation](#add-an-operation-that-asks-for-confirmation)

## Add a setting

Example: a boolean `confirm_on_quit`, default `True`.

1. In `src/rumia_configurator/core/settings.py`, add the field to `Settings`
   with its default and a short comment:

   ```python
   confirm_on_quit: bool = True  # ask before closing the main window
   ```

   Use simple types: `str`, `int`, `bool`. The loader checks the type exactly,
   so `1` is refused where a `bool` is expected.
2. If only some values are allowed, declare them:
   - a choice among strings: a tuple constant (like `THEMES`) and an entry in
     `_ALLOWED_VALUES`;
   - a number that must be greater than zero: add the name to `_POSITIVE_INTS`.
3. In `tests/test_settings.py`, add the field to
   `test_save_and_load_round_trip` with a non-default value, and add a test
   for an invalid value if the field has limits.
4. Use it in the interface through the settings the main window holds:
   read `self._settings.confirm_on_quit`, change it and call `self._save()`
   (see [User interface](gui.md#what-mainwindow-offers)).
5. Add a row to the table in [Core services](core.md#fields).

Old settings files do not need migrating: a missing field gets its default.
Bump `SCHEMA_VERSION` only if you change the meaning or format of an existing
field.

Check: `uv run pytest tests/test_settings.py`.

## Add a translated text

1. Write the English text with `self.tr()` **inside `retranslate()`** of the
   widget (see [Translations](translations.md#the-retranslate-pattern)):

   ```python
   def retranslate(self) -> None:
       ...
       self.scan_button.setToolTip(self.tr("Look for the nodes on the network"))
   ```

   Values go in placeholders (`"%1"` + `.replace("%1", value)`), counts in
   plurals (`self.tr("%n node(s)", "", count)`).
2. Extract the new texts into the `.ts` files:

   ```bash
   uv run python scripts/i18n.py update
   ```

3. Translate. In `src/rumia_configurator/gui/translations/rumia_configurator_it.ts`
   find the new `<message>`, write the Italian text in `<translation>` and
   remove `type="unfinished"`. In `rumia_configurator_en.ts` do the same with
   the English source text (for plurals, write both forms). Qt Linguist does
   this with a form: `uv run pyside6-linguist <file.ts>`.
4. Compile:

   ```bash
   uv run python scripts/i18n.py compile
   ```

5. Check, then try both languages in the app with the IT/EN button:

   ```bash
   uv run python scripts/i18n.py check
   uv run rumia-configurator
   ```

Commit the code, the two `.ts` files and the two `.qm` files together.

## Add a button to a view

Example: a *Disconnect* button in the top bar that asks the main window to do
something.

1. In the view (`src/rumia_configurator/gui/views/top_bar.py`), declare a
   signal on the class and create the button in `__init__`, with an empty
   text:

   ```python
   class TopBar(QFrame):
       disconnect_requested = Signal()

       def __init__(...):
           ...
           self.disconnect_button = make_button("", size="bar", icon="x", parent=self)
           self.disconnect_button.clicked.connect(self.disconnect_requested)
           layout.addWidget(self.disconnect_button)
   ```

   Choose `variant` (`"primary"` only for the main action of an area) and
   `size` (`"bar"` in toolbars, `"compact"` in the side panel). Never set
   colors or sizes on the button: see [Theme](theme.md#brand-components).
2. Set its text and tooltip in `retranslate()` with `self.tr()`, then follow
   [Add a translated text](#add-a-translated-text).
3. In `src/rumia_configurator/gui/main_window.py`, connect the signal to a
   method of `MainWindow` that does the work:

   ```python
   self.top_bar.disconnect_requested.connect(self.disconnect_bus)
   ```

   Do not reuse names of Qt methods for your own methods: `disconnect`,
   `close`, `show`, `update`, `event` already exist on every widget, and
   redefining them breaks Qt in subtle ways.

   Views emit signals; the main window applies changes and saves settings.
   If the action is destructive, ask for confirmation first
   ([Architecture](architecture.md#rules-that-are-never-broken), rule 5).
4. Add a test in `tests/test_main_window.py` that clicks the button
   (`window.top_bar.disconnect_button.click()`) and checks the result.
5. Something added to the top bar makes the window wider, and the top bar has
   only about 100 px left in Italian. The test
   `test_fits_1366x768_without_horizontal_scrolling` tells you if it no longer
   fits. Trying this very recipe, a *Disconnetti* button with text made the
   window 1383 px wide; the same button with only the icon fits (1313 px). If it
   does not fit, make the button icon-only, keep the text as tooltip and
   accessible name (`setToolTip`, `setAccessibleName`), or put the action in
   the menu.

Check: `uv run pytest tests/test_main_window.py` and look at it in both themes
and languages.

## Add a tab to the work area

Example: a *Diagnostics* tab, shown only in Expert mode.

1. In `src/rumia_configurator/gui/views/workspace.py`:
   - add the key to `TAB_KEYS`, in the position the tab should have:
     `TAB_KEYS = ("overview", ..., "monitor", "log", "diagnostics")`;
   - add it to `BASE_TABS` too if it must be visible in Base mode;
   - give it an icon in the `icons` dictionary of `Workspace.__init__`;
   - give it a title and a placeholder text in the `texts` dictionary of
     `retranslate()`.
2. Follow [Add a translated text](#add-a-translated-text) for the new texts.
3. Update the expected list in `test_base_mode_shows_overview_and_plots_only`
   (`tests/test_main_window.py`).
4. When the real page exists, replace the `PlaceholderPage` for that key with
   the new widget.

Check: `uv run pytest tests/test_main_window.py`, and that the tab bar still
fits at 1366 px in Expert mode.

## Add an icon

Icons come from [Lucide](https://lucide.dev/icons/). Find the name on the
website (for example `plug`), then:

1. Download the SVG into the icons folder:

   ```bash
   curl -sSfL -o src/rumia_configurator/gui/theme/icons/plug.svg \
     https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/plug.svg
   ```

   Do not edit the file: the icon is recolored at run time through its
   `currentColor`.
2. Use it by name:

   ```python
   make_button(self.tr("Connect"), "primary", "bar", icon="plug")
   # or, for a label or an existing button:
   theme_manager().bind_icon(widget, "plug", role="link")
   ```

   `role` is a palette role ([Theme](theme.md#colors)); the icon is repainted
   when the theme changes.

Check: `uv run pytest tests/test_theme_qt.py` (every bundled icon must render).

## Add or change a color

Colors are only in `src/rumia_configurator/gui/theme/tokens.py`. Ask first:
the brand palette is decided, and a new color must be agreed.

To **change** a value, edit it in `LIGHT` and/or `DARK`, upper case
(`"#0B2326"`).

To **add** a role, for example `warning_bg`:

1. Add the field to the `Palette` dataclass with a comment on its use, and a
   value in **both** `LIGHT` and `DARK` (the code does not start otherwise).
2. Use it in `src/rumia_configurator/gui/theme/qss.py` as `{p.warning_bg}`,
   usually with a new `role` or `kind` value.
3. Declare every text/background combination it creates in `TEXT_PAIRS` (4.5:1)
   and every graphic one in `GRAPHIC_PAIRS` (3:1).
4. Run the tests: they fail if a pair is below its minimum in either theme.

   ```bash
   uv run pytest tests/test_theme_tokens.py tests/test_theme_qt.py
   ```

5. Look at the result in both themes with `uv run rumia-configurator --theme-demo`.
6. Update the color table in [Theme](theme.md#colors).

Never write a hex color in a widget: `test_no_hardcoded_colors_in_gui_code`
fails. If code must set a color itself (for example a table item), take it
from `theme_manager().color("role")` and repaint it when `ThemeManager.changed`
is emitted.

## Add a command-line option

Example: `--safe-mode`.

1. In `src/rumia_configurator/cli.py`, add the option in `build_parser()`:

   ```python
   parser.add_argument(
       "--safe-mode",
       action="store_true",
       help="start without restoring the saved window layout",
   )
   ```

   For a command with its own options (like `export-logs`), add a sub-parser
   with `commands.add_parser(...)`.
2. Handle it in `main()`, before the GUI starts. Import Qt modules only inside
   the branch that needs them, never at the top of `cli.py`: `--version` and
   the other commands must work without a display.
3. Command-line messages are in English and are not translated. Errors go to
   stderr in three parts (what, why, what to do) and return exit code 1.
4. Add a test in `tests/test_cli.py`, for example
   `build_parser().parse_args(["--safe-mode"]).safe_mode is True`.
5. Add the option to the table in [Environment](environment.md#everyday-commands).

Check: `uv run pytest tests/test_cli.py` and `uv run rumia-configurator --help`.

## Add an operation that asks for confirmation

Rule 5 of the [Architecture](architecture.md#rules-that-are-never-broken): an
operation that can stop a machine or lose settings asks first. Example: *Store
parameters* (write "save" into 0x1010).

1. In the method of `MainWindow` (or of the view) that starts the operation,
   ask with `dialogs.confirm_action()` from `src/rumia_configurator/gui/dialogs.py`
   and stop if the answer is no:

   ```python
   if not dialogs.confirm_action(
       self,
       self.tr("Store parameters · Node %1").replace("%1", str(node_id)),
       self.tr("Store the current parameters in node %1?").replace("%1", str(node_id)),
       self.tr("The node keeps them after a restart; the stored values are replaced."),
       self.tr("Confirm only if the parameters have been checked."),
       self.tr("Store in the node"),
   ):
       return
   ```

   Call it through the module (`dialogs.confirm_action`), not with
   `from ... import confirm_action`: the tests replace it there.
2. Write the three parts: **what** will happen (a question), **what it
   causes** (concrete consequences, also for nodes not in the list), **what
   to check** first. The confirm button says the action in words ("Reset all
   nodes"), never just "OK". Cancel is the default button: Enter and Esc do
   not confirm.
3. Run the operation in a worker and report the outcome in the status bar,
   with a warning callout if it did not succeed.
4. Tests (see `tests/test_nmt_gui.py`): replace `dialogs.confirm_action` with
   a function that records the question and answers no, and check that
   **nothing** reached the bus or the node; then answer yes and check the
   outcome.
5. Follow [Add a translated text](#add-a-translated-text) for the new texts.

## Regenerate icons and logos

The window icon, the top bar logos and the executables' icons are generated by
`packaging/make_icons.py` from two sources:

| Source | Generates |
| --- | --- |
| `packaging/icons/rumia_mark.svg` (vector Rumia mark) | `packaging/icons/rumia.ico`, `rumia.icns`, `rumia.png`, `src/rumia_configurator/gui/assets/app_icon.png` |
| `packaging/icons/rumia_logo.png` (mark + RUMIA wordmark) | `src/rumia_configurator/gui/assets/logo_light.png`, `logo_dark.png` |

1. Replace the source file, keeping its name.
2. Run:

   ```bash
   uv run python packaging/make_icons.py
   ```

   The mark is cropped to its outline and centred with an 8% margin. For the
   dark logo, every grey pixel (the wordmark) becomes white, so the wordmark
   must stay neutral grey and the mark colored.
3. Look at the result: `uv run rumia-configurator`, in both themes.
4. Commit the sources and the generated files: building the application does
   not need Pillow.
