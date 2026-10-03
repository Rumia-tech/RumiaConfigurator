# RumiaConfigurator

RumiaConfigurator is an open source desktop application for configuring Rumia CANopen products (Smart IMU, INCLI Sense) and for viewing data from any CANopen node on the network.

It runs on Windows 10/11, Linux (Ubuntu 22.04+) and macOS 13+ (Apple Silicon).

> **Status: in development.** The application is being rewritten and is not usable yet.

## Requirements

- [uv](https://docs.astral.sh/uv/) (it downloads Python 3.12 automatically if needed)
- A USB-CAN adapter supported by [python-can](https://python-can.readthedocs.io/) (reference adapter: CANable with SLCAN firmware)

## Getting started

```bash
uv sync                          # install dependencies (including development tools)
uv run rumia-configurator        # start the application
uv run rumia-configurator --version
uv run pytest                    # run the tests
```

## Developer guide

How the code is organised, how to change it and the rules it follows are
explained in [docs/development/](docs/development/README.md). Start there
before changing the code.

## Translations

The interface is in Italian and English. Source strings are English and pass
through Qt's `tr()`; the catalogs are in `src/rumia_configurator/gui/translations/`.

```bash
uv run python scripts/i18n.py update   # add new strings to the .ts files
uv run python scripts/i18n.py compile  # rebuild the .qm files after translating
uv run python scripts/i18n.py check    # what the tests verify
```

## Repository layout

```
src/rumia_configurator/   application package
  core/                   services (pure Python, no Qt)
  profiles/               product profiles and EDS files
  gui/                    PySide6 user interface
  cli.py                  command-line entry point
docs/development/         developer guide
tests/                    automated tests
scripts/                  developer tools (translations)
packaging/                icons and build files
legacy/                   previous prototype, kept for reference only
```
