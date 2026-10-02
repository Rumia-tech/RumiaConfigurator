"""Application log: rotating file plus export for support requests (FR-APP-02)."""

from __future__ import annotations

import logging
import platform
import sys
import zipfile
from datetime import datetime
from importlib import metadata
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rumia_configurator import __version__

LOG_FILE_NAME = "app.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(threadName)s] %(name)s: %(message)s"

# Libraries that log every frame or SDO transfer at DEBUG/INFO level.
_NOISY_LOGGERS = ("can", "canopen")
_REPORTED_PACKAGES = ("canopen", "python-can", "pyside6", "pyqtgraph", "numpy", "scipy")

# Marks the handlers installed here, so a later call can replace exactly those.
_HANDLER_TAG = "_rumia_configurator_handler"


def configure_logging(
    log_dir: Path,
    level: str = "INFO",
    *,
    max_bytes: int = MAX_BYTES,
    backup_count: int = BACKUP_COUNT,
) -> Path:
    """Send the root logger to a rotating file in ``log_dir`` and warnings to stderr.

    Safe to call again (for example after the log level changes): the handlers
    installed by a previous call are closed and replaced. Returns the log file path.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILE_NAME
    shutdown_logging()

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    for handler in (file_handler, console_handler):
        setattr(handler, _HANDLER_TAG, True)
        root.addHandler(handler)
    root.setLevel(level)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "RumiaConfigurator %s started (Python %s, %s)",
        __version__,
        platform.python_version(),
        platform.platform(),
    )
    return log_file


def shutdown_logging() -> None:
    """Close and remove the handlers installed by :func:`configure_logging`."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_TAG, False):
            root.removeHandler(handler)
            handler.close()


def system_info() -> str:
    """Plain-text summary of the application and its environment."""
    lines = [
        f"RumiaConfigurator {__version__}",
        f"Created: {datetime.now().isoformat(timespec='seconds')}",
        f"Python: {platform.python_version()} ({sys.executable})",
        f"OS: {platform.platform()}",
        f"Machine: {platform.machine()}",
        "",
        "Packages:",
    ]
    for package in _REPORTED_PACKAGES:
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            version = "not installed"
        lines.append(f"  {package}: {version}")
    return "\n".join(lines) + "\n"


def default_export_name() -> str:
    """File name suggested for an exported log archive."""
    return f"rumia-configurator-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"


def export_logs(log_dir: Path, settings_file: Path | None, dest: Path) -> Path:
    """Write a ZIP with the log files, the settings and system information.

    Missing log files or settings are left out. Returns ``dest``.
    """
    for handler in logging.getLogger().handlers:
        handler.flush()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if log_dir.is_dir():
            for log_file in sorted(log_dir.glob(f"{LOG_FILE_NAME}*")):
                archive.write(log_file, f"logs/{log_file.name}")
        if settings_file is not None and settings_file.is_file():
            archive.write(settings_file, settings_file.name)
        archive.writestr("system_info.txt", system_info())
    logging.getLogger(__name__).info("Logs exported to %s", dest)
    return dest
