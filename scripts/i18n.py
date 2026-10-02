"""Maintain the interface translations (UI-I18N-01).

    uv run python scripts/i18n.py update   # extract tr() strings into the .ts files
    uv run python scripts/i18n.py compile  # build the .qm files the app loads
    uv run python scripts/i18n.py check    # fail if .ts or .qm are out of date

Translate the .ts files with Qt Linguist (``pyside6-linguist``) or a text
editor, then run ``compile``. Both .ts and .qm files are committed.
The theme demo window is a developer tool and is not translated.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUI = ROOT / "src" / "rumia_configurator" / "gui"
TRANSLATIONS = GUI / "translations"
CATALOG = "rumia_configurator"
LANGUAGES = ("it", "en")
EXCLUDED = {GUI / "theme_demo.py"}


def tool(name: str) -> str:
    """Path of a PySide6 tool, also when the virtual environment is not activated."""
    found = shutil.which(name)
    if found:
        return found
    folder = Path(sys.executable).parent
    for candidate in (folder / name, folder / f"{name}.exe"):
        if candidate.is_file():
            return str(candidate)
    raise SystemExit(f"{name} not found: run `uv sync` to install PySide6.")


def sources() -> list[Path]:
    return sorted(p for p in GUI.rglob("*.py") if p not in EXCLUDED)


def ts_path(language: str, folder: Path = TRANSLATIONS) -> Path:
    return folder / f"{CATALOG}_{language}.ts"


def update(folder: Path = TRANSLATIONS) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    targets = [str(ts_path(lang, folder)) for lang in LANGUAGES]
    command = [tool("pyside6-lupdate"), *map(str, sources()), "-no-obsolete", "-locations", "none"]
    subprocess.run([*command, "-ts", *targets], check=True, capture_output=True)


def compile_qm(folder: Path = TRANSLATIONS, out: Path = TRANSLATIONS) -> None:
    for language in LANGUAGES:
        qm = out / f"{CATALOG}_{language}.qm"
        command = [tool("pyside6-lrelease"), str(ts_path(language, folder)), "-qm", str(qm)]
        subprocess.run(command, check=True, capture_output=True)


def unfinished(language: str) -> list[str]:
    """Source texts without a finished translation."""
    tree = ET.parse(ts_path(language))
    missing = []
    for message in tree.iter("message"):
        translation = message.find("translation")
        source = message.findtext("source", "")
        if translation is None or translation.get("type") in ("unfinished", "obsolete"):
            missing.append(source)
            continue
        forms = translation.findall("numerusform")
        complete = all(f.text for f in forms) if forms else bool(translation.text)
        if not complete:
            missing.append(source)
    return missing


def _text(path: Path) -> str:
    """File content with line endings normalized (Git may convert them on Windows)."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def check() -> int:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for language in LANGUAGES:
            shutil.copy(ts_path(language), ts_path(language, folder))
        update(folder)
        for language in LANGUAGES:
            if _text(ts_path(language, folder)) != _text(ts_path(language)):
                problems.append(
                    f"{ts_path(language).name} is out of date: run `scripts/i18n.py update`, "
                    "translate the new strings and run `scripts/i18n.py compile`."
                )
        compile_qm(TRANSLATIONS, folder)
        for language in LANGUAGES:
            name = f"{CATALOG}_{language}.qm"
            committed = TRANSLATIONS / name
            if not committed.is_file() or committed.read_bytes() != (folder / name).read_bytes():
                problems.append(f"{name} is out of date: run `scripts/i18n.py compile`.")
    for language in LANGUAGES:
        for source in unfinished(language):
            problems.append(f"{ts_path(language).name}: no translation for {source!r}")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    if argv == ["update"]:
        update()
        return 0
    if argv == ["compile"]:
        compile_qm()
        return 0
    if argv == ["check"]:
        return check()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
