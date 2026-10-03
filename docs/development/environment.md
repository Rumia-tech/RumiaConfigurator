# Environment

## Tools

- **[uv](https://docs.astral.sh/uv/)** manages Python and the dependencies. It
  downloads Python 3.12 by itself if needed. Dependencies and tool settings are
  in `pyproject.toml`; the exact versions are pinned in `uv.lock`.
- **Git**.
- An editor. The project is developed in VS Code: open the repository folder
  and choose the interpreter in `.venv` (Command Palette → *Python: Select
  Interpreter*).

No Qt Designer, Qt Creator or `.ui` files are used: every window is written in
Python.

If uv fails to download with a certificate error (`invalid peer certificate:
UnknownIssuer`), your network inspects TLS traffic: set the environment
variable `UV_SYSTEM_CERTS=1` so that uv trusts the system certificates.

## First set-up

```bash
uv sync
```

This creates `.venv/` with Python 3.12, the application dependencies and the
development tools (pytest, ruff, mypy, …). Run it again whenever
`pyproject.toml` or `uv.lock` change, for example after a `git pull`.

To add a dependency use `uv add <package>` (or `uv add --dev <package>` for a
development tool). This updates `pyproject.toml` and `uv.lock`; commit both.
Check the license first: see [Architecture](architecture.md#dependencies).

## Everyday commands

| Command | What it does |
| --- | --- |
| `uv run rumia-configurator` | start the application |
| `uv run rumia-configurator --version` | print the version |
| `uv run rumia-configurator --demo` | start in demo mode: simulated Smart IMU and INCLI Sense on a virtual bus ([Simulator and demo mode](simulator.md#demo-mode)) |
| `uv run rumia-configurator --theme-demo` | open the gallery of brand components ([Theme](theme.md#theme-demo)) |
| `uv run rumia-configurator adapters` | list the CAN adapters found on this computer ([Connection](connection.md#adapters-fr-con-01-fr-con-02)) |
| `uv run rumia-configurator export-logs` | save logs, settings and system information to a ZIP file |
| `uv run pytest` | run all the tests |
| `uv run ruff check .` | lint |
| `uv run ruff format .` | format the code (`--check` only reports) |
| `uv run mypy src` | type checking |
| `uv run python scripts/i18n.py check` | check that translations are complete and compiled |
| `uv run python packaging/make_icons.py` | regenerate icons and logos ([Recipes](recipes.md#regenerate-icons-and-logos)) |

Before every commit run the same checks as the CI:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
```

## Running some of the tests

```bash
uv run pytest tests/test_settings.py                      # one file
uv run pytest tests/test_settings.py::test_save_and_load_round_trip   # one test
uv run pytest -k theme                                    # tests whose name contains "theme"
uv run pytest -x                                          # stop at the first failure
uv run pytest -q                                          # shorter output
```

More in [Testing](testing.md).

## Reading ruff messages

Ruff checks style and common mistakes. A message looks like this:

```
E501 Line too long (105 > 100)
  --> src/rumia_configurator/gui/views/top_bar.py:41:101
```

- The code (`E501`) tells which rule fired; search it on the ruff website for
  an explanation. The enabled rule families are listed in `pyproject.toml`
  under `[tool.ruff.lint]`.
- Lines may be up to 100 characters.
- Many problems are fixed automatically with `uv run ruff check --fix .`.
  Formatting is always fixed by `uv run ruff format .`.
- `# noqa: N802` at the end of a line silences one rule on that line. The code
  uses it only where Qt imposes a name, such as `changeEvent` or `closeEvent`,
  which break the snake_case naming rule. Add a short reason after it.

## Reading mypy messages

Mypy checks the type annotations. Every function must be annotated
(`disallow_untyped_defs`), and `core/` is checked in strict mode, the most
demanding one. A message looks like this:

```
src/rumia_configurator/gui/views/top_bar.py:98: error: Argument 4 to "_add_choice"
of "TopBar" has incompatible type "SignalInstance"; expected "Signal"  [arg-type]
```

It gives the file and line, what is wrong and, in brackets, the error code.
Fix the annotation or the code; use `# type: ignore[code]` only when a library
has wrong or missing type information, and always with the specific code.
`pyqtgraph`, `canopen` and `scipy` have no type information: mypy is told to
ignore them in `pyproject.toml`.

## Continuous integration

`.github/workflows/ci.yml` runs on GitHub Actions:

- On every push and pull request: Ubuntu 22.04 only.
- On version tags (`v*`) and when started by hand: Windows, Ubuntu 22.04 and
  macOS (Apple Silicon).

Steps: check out, install the system libraries Qt needs on Linux, install uv
and Python 3.12, `uv sync --locked`, then ruff (lint and format check), mypy
and pytest. `--locked` makes the job fail if `uv.lock` does not match
`pyproject.toml`: commit both files together.

The tests run with the environment variable `QT_QPA_PLATFORM=offscreen`, which
lets Qt create windows without a screen. The test configuration sets it too,
so the tests also run headless on your machine.

## Versions

The version number lives only in `src/rumia_configurator/__init__.py`
(`__version__`); `pyproject.toml` reads it from there. Between releases it has
a `.devN` suffix, for example `0.6.0.dev0`. A release sets it to the final
number (`0.6.0`) and creates the matching Git tag `v0.6.0`: the two must match.
