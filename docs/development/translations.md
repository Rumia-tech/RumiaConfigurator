# Translations

The interface is in Italian and English (FR-APP-03) and the user can switch
language while the application runs. The Qt translation system is used:
source texts are written in English inside `self.tr(...)`, translations live in
`.ts` files, and the application loads compiled `.qm` files.

What is translated and what is not:

| Translated | Not translated |
| --- | --- |
| every text the user sees in the window: labels, buttons, menus, tooltips, dialogs, status messages | log messages (for developers and support) |
| | command-line messages |
| | the theme demo window (developer tool) |
| | language names in the language menu (*Italiano*, *English*: each in its own language) |
| | units (`kbit/s`, `mg`) and technical identifiers |

Source files:

- `src/rumia_configurator/gui/i18n.py`: `LanguageManager`
- `src/rumia_configurator/gui/translations/`: `.ts` and `.qm` catalogs
- `scripts/i18n.py`: update, compile and check the catalogs

## Writing translatable text

Inside any Qt class, wrap the text in `self.tr()`:

```python
self.connect_button.setText(self.tr("Connect"))
```

Rules:

- **Write the source in English.** It is also the text shown when no
  translation exists.
- **Never build the text before `tr()`.** `self.tr(f"Saved to {path}")` cannot
  be translated, because the translation file would need one entry per path.
  Use a numbered placeholder and fill it afterwards:

  ```python
  self.tr("Logs exported to %1").replace("%1", filename)
  ```

  The translator sees `%1` and can move it where the language needs it.
- **Plurals**: pass the number as third argument and write `%n`:

  ```python
  self.tr("Network · %n node(s)", "", count)
  ```

  Each language file holds the right forms ("1 nodo" / "2 nodi",
  "1 node" / "2 nodes").
- **Error messages have three parts**: what happened, why, what to do
  (UI-I18N-02). For example: "The logs could not be saved to %1. Cause: %2.
  Choose a folder where you can write, for example Documents, and try again."
- `tr()` uses the class name as **context**: the same English word can be
  translated differently in two classes. Text written outside a class is not
  found by the extraction tool; keep user texts inside the widget classes.

## The retranslate pattern

When the language changes, Qt does not rewrite texts by itself: each widget
must set them again. Every view follows the same structure:

```python
class NodePanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scan_button = make_button("", size="compact", icon="refresh-cw")
        ...  # build widgets with empty texts
        self.retranslate()  # then set every text once

    def retranslate(self) -> None:
        self.scan_button.setText(self.tr("Scan"))
        self.scan_button.setToolTip(self.tr("Look for the nodes on the network"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
```

**Every** `self.tr()` call that produces a visible text must be inside
`retranslate()` (or in a method it calls). A text set only in `__init__`
stays in the old language after a switch.

A text that the code sets later, such as the last event in the status bar, is
translated at the moment it is shown and is not changed by a later language
switch.

## Switching language: `gui/i18n.py`

`LanguageManager` installs the translations into the `QApplication`:

- `set_language(setting)` takes `""` (follow the system), `"it"` or `"en"`.
- `resolve_language()` turns `""` into the first supported language among the
  system's preferred ones, falling back to English.
- It removes the translators it installed before, then installs:
  - `gui/translations/rumia_configurator_<language>.qm`, the application texts
    (loaded for English too, because it holds the English plural forms);
  - Qt's own `qtbase_<language>.qm`, which translates the standard buttons and
    file dialogs (*Annulla*, *Salva*, …), for every language except English.
- It sets the default `QLocale`, so numbers and dates will follow the language.
- Installing or removing a translator makes Qt send `LanguageChange` to every
  widget, which triggers the `retranslate()` methods above.
- `language` is the language in use, `setting` the user's choice; `changed` is
  emitted after a switch. `uninstall()` removes its translators (used by tests).

If a catalog cannot be loaded, the problem is logged and the interface shows
the English source texts.

## Translation files

```
src/rumia_configurator/gui/translations/
  rumia_configurator_it.ts    Italian translations (XML, edited by people)
  rumia_configurator_en.ts    English: source texts and plural forms
  rumia_configurator_it.qm    compiled, loaded by the application
  rumia_configurator_en.qm
```

Both `.ts` and `.qm` files are committed, so a fresh clone runs in both
languages without a build step. `.gitattributes` marks `.qm` files as binary.

A `.ts` entry looks like this:

```xml
<context>
    <name>NodePanel</name>
    <message>
        <source>Scan</source>
        <translation>Scansiona</translation>
    </message>
</context>
```

## Tool: `scripts/i18n.py`

| Command | What it does |
| --- | --- |
| `uv run python scripts/i18n.py update` | runs `pyside6-lupdate` on every Python file of `gui/` (except the theme demo) and adds new texts to both `.ts` files; texts no longer in the code are removed |
| `uv run python scripts/i18n.py compile` | runs `pyside6-lrelease` and writes the `.qm` files |
| `uv run python scripts/i18n.py check` | fails if a `.ts` file is out of date, a text has no translation, or a `.qm` does not match its `.ts` |

`check` is run by `tests/test_main_window.py`, so `uv run pytest` fails when a
new text was not translated or not compiled.

To translate, open a `.ts` file with Qt Linguist:

```bash
uv run pyside6-linguist src/rumia_configurator/gui/translations/rumia_configurator_it.ts
```

or edit the XML in a text editor: fill `<translation>` and remove
`type="unfinished"`. For the English file, the translation is the source text
itself, except for plurals where both forms must be written.

The full sequence is in [Recipes](recipes.md#add-a-translated-text).
