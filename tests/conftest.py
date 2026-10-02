"""Shared pytest configuration."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from rumia_configurator.core import app_log, paths

# Run Qt headless unless the caller chose a platform plugin explicitly.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def user_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect the per-user folders to a temporary folder for every test.

    Also closes the log handlers afterwards: on Windows an open log file
    cannot be deleted.
    """
    home = tmp_path / "user"
    monkeypatch.setattr(paths, "config_dir", lambda: home / "config")
    monkeypatch.setattr(paths, "log_dir", lambda: home / "logs")
    yield home
    app_log.shutdown_logging()
