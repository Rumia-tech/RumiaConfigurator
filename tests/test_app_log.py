"""Tests for the application log and its export (FR-APP-02)."""

import logging
import zipfile
from pathlib import Path

import pytest

from rumia_configurator import __version__
from rumia_configurator.cli import main
from rumia_configurator.core import app_log
from rumia_configurator.core.settings import Settings, SettingsStore


def test_log_file_receives_messages(tmp_path: Path) -> None:
    log_file = app_log.configure_logging(tmp_path, "INFO")
    logging.getLogger("rumia_configurator.test").info("hello log")
    app_log.shutdown_logging()
    text = log_file.read_text(encoding="utf-8")
    assert f"RumiaConfigurator {__version__} started" in text
    assert "hello log" in text


def test_level_filters_debug(tmp_path: Path) -> None:
    log_file = app_log.configure_logging(tmp_path, "INFO")
    logging.getLogger("rumia_configurator.test").debug("hidden")
    app_log.shutdown_logging()
    assert "hidden" not in log_file.read_text(encoding="utf-8")


def test_noisy_libraries_are_limited_to_warning(tmp_path: Path) -> None:
    app_log.configure_logging(tmp_path, "DEBUG")
    assert logging.getLogger("can").level == logging.WARNING
    assert logging.getLogger("canopen").level == logging.WARNING


def test_reconfiguring_does_not_duplicate_handlers(tmp_path: Path) -> None:
    root = logging.getLogger()
    before = len(root.handlers)
    app_log.configure_logging(tmp_path, "INFO")
    app_log.configure_logging(tmp_path, "DEBUG")
    assert len(root.handlers) == before + 2
    assert root.level == logging.DEBUG


def test_log_rotates(tmp_path: Path) -> None:
    app_log.configure_logging(tmp_path, "INFO", max_bytes=2_000, backup_count=2)
    logger = logging.getLogger("rumia_configurator.test")
    for i in range(200):
        logger.info("line %d %s", i, "x" * 50)
    app_log.shutdown_logging()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["app.log", "app.log.1", "app.log.2"]


def test_export_contains_logs_settings_and_system_info(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    app_log.configure_logging(log_dir, "INFO")
    logging.getLogger("rumia_configurator.test").info("exported line")
    settings_file = tmp_path / "settings.json"
    SettingsStore(settings_file).save(Settings(language="it"))

    dest = app_log.export_logs(log_dir, settings_file, tmp_path / "out" / "logs.zip")

    with zipfile.ZipFile(dest) as archive:
        names = set(archive.namelist())
        assert names == {"logs/app.log", "settings.json", "system_info.txt"}
        assert "exported line" in archive.read("logs/app.log").decode("utf-8")
        info = archive.read("system_info.txt").decode("utf-8")
    assert f"RumiaConfigurator {__version__}" in info
    assert "python-can:" in info


def test_export_without_logs_or_settings(tmp_path: Path) -> None:
    dest = app_log.export_logs(tmp_path / "missing", None, tmp_path / "logs.zip")
    with zipfile.ZipFile(dest) as archive:
        assert archive.namelist() == ["system_info.txt"]


def test_cli_export_logs(
    user_dirs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "support.zip"
    assert main(["export-logs", "--output", str(dest)]) == 0
    assert f"Logs exported to {dest}" in capsys.readouterr().out
    with zipfile.ZipFile(dest) as archive:
        assert "logs/app.log" in archive.namelist()
    assert (user_dirs / "logs" / "app.log").is_file()


def test_cli_export_logs_default_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "cwd"
    out_dir.mkdir()
    monkeypatch.chdir(out_dir)
    assert main(["export-logs"]) == 0
    assert len(list(out_dir.glob("rumia-configurator-logs-*.zip"))) == 1


def test_cli_export_logs_reports_unwritable_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    assert main(["export-logs", "--output", str(blocker / "logs.zip")]) == 1
    err = capsys.readouterr().err
    assert "Could not write the log archive" in err
    assert "--output" in err
