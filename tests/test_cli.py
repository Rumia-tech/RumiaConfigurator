"""Tests for the command-line entry point."""

import ast
from pathlib import Path

import pytest

from rumia_configurator import __version__
from rumia_configurator.cli import main

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "rumia_configurator"


def test_version_prints_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"rumia-configurator {__version__}"


def test_no_arguments_opens_the_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    from rumia_configurator.gui import app

    calls: list[bool] = []
    monkeypatch.setattr(app, "run_gui", lambda demo: calls.append(demo) or 0)
    assert main([]) == 0
    assert calls == [False]


def test_demo_option_opens_the_gui_in_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from rumia_configurator.gui import app

    calls: list[bool] = []
    monkeypatch.setattr(app, "run_gui", lambda demo: calls.append(demo) or 0)
    assert main(["--demo"]) == 0
    assert calls == [True]


def test_package_does_not_import_legacy() -> None:
    for source in PACKAGE_DIR.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert name.split(".")[0] != "legacy", f"{source} imports {name}"


def test_theme_demo_option_is_parsed() -> None:
    from rumia_configurator.cli import build_parser

    assert build_parser().parse_args(["--theme-demo"]).theme_demo is True
    assert build_parser().parse_args([]).theme_demo is False


def test_adapters_command_lists_rumia_first(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from rumia_configurator.core import connection

    found = [
        connection.AdapterInfo("slcan", "COM5", "Rumia CAN Interface", "rumia", 0x17D0, 0x118E),
        connection.AdapterInfo("slcan", "COM3", "Bluetooth link", "serial"),
    ]
    monkeypatch.setattr(connection, "list_adapters", lambda: found)
    assert main(["adapters"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split()[:3] == ["rumia", "slcan", "COM5"]
    assert lines[0].endswith("USB 17D0:118E")
    assert "COM3" in lines[1]


def test_adapters_command_without_adapters(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from rumia_configurator.core import connection

    monkeypatch.setattr(connection, "list_adapters", lambda: [])
    assert main(["adapters"]) == 0
    assert "No adapter found" in capsys.readouterr().out
