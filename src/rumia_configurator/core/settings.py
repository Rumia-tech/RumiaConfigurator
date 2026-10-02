"""Persistent user preferences stored as JSON in the user folder (FR-APP-01).

Loading is tolerant but never silent: every value that cannot be used is
replaced by its default and reported as a warning, so the caller can log it
and show it to the user.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

LANGUAGES = ("", "it", "en")
UI_MODES = ("base", "expert")
THEMES = ("system", "light", "dark")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass
class ConnectionSettings:
    """Last used CAN adapter settings."""

    backend: str = "slcan"
    channel: str = ""
    bitrate: int = 1_000_000


@dataclass
class Settings:
    """All user preferences."""

    schema_version: int = SCHEMA_VERSION
    language: str = ""  # "" follows the system language
    ui_mode: str = "base"
    theme: str = "system"  # "system" follows the operating system (UI-COL-03)
    log_level: str = "INFO"
    window_geometry: str = ""  # base64 of the main window geometry; "" = default size
    node_panel_width: int = 272
    connection: ConnectionSettings = field(default_factory=ConnectionSettings)


_ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "language": LANGUAGES,
    "ui_mode": UI_MODES,
    "theme": THEMES,
    "log_level": LOG_LEVELS,
}


_POSITIVE_INTS = ("connection.bitrate", "node_panel_width")


@dataclass
class LoadResult:
    """Settings read from disk plus the problems found while reading them."""

    settings: Settings
    warnings: list[str] = field(default_factory=list)


def _check_value(name: str, value: Any, default: Any, warnings: list[str]) -> Any:
    """Return ``value`` if it has the type and range of ``default``, else ``default``."""
    # Exact type check: bool is a subclass of int and must not pass as one.
    if type(value) is not type(default):
        warnings.append(
            f"Setting '{name}' has an invalid value {value!r}: using the default {default!r}."
        )
        return default
    allowed = _ALLOWED_VALUES.get(name)
    if allowed is not None and value not in allowed:
        choices = ", ".join(repr(a) for a in allowed)
        warnings.append(
            f"Setting '{name}' has an unsupported value {value!r} (allowed: {choices}): "
            f"using the default {default!r}."
        )
        return default
    if name in _POSITIVE_INTS and value <= 0:
        warnings.append(
            f"Setting '{name}' must be a positive number, got {value!r}: "
            f"using the default {default!r}."
        )
        return default
    return value


def _connection_from_dict(data: dict[str, Any], warnings: list[str]) -> ConnectionSettings:
    defaults = ConnectionSettings()
    known = [f.name for f in fields(ConnectionSettings)]
    for key in sorted(data.keys() - set(known)):
        warnings.append(f"Unknown setting 'connection.{key}' ignored.")
    values: dict[str, Any] = {}
    for name in known:
        if name in data:
            values[name] = _check_value(
                f"connection.{name}", data[name], getattr(defaults, name), warnings
            )
    return ConnectionSettings(**values)


def settings_from_dict(data: dict[str, Any], warnings: list[str]) -> Settings:
    """Build :class:`Settings` from parsed JSON, appending problems to ``warnings``."""
    defaults = Settings()
    known = [f.name for f in fields(Settings)]
    for key in sorted(data.keys() - set(known)):
        warnings.append(f"Unknown setting '{key}' ignored.")

    version = data.get("schema_version", SCHEMA_VERSION)
    if type(version) is int and version > SCHEMA_VERSION:
        warnings.append(
            f"The settings file was written by a newer version (schema {version}, "
            f"this version reads schema {SCHEMA_VERSION}): some preferences may be lost."
        )

    values: dict[str, Any] = {}
    for name in known:
        if name in ("schema_version", "connection") or name not in data:
            continue
        values[name] = _check_value(name, data[name], getattr(defaults, name), warnings)

    if "connection" in data:
        connection = data["connection"]
        if isinstance(connection, dict):
            values["connection"] = _connection_from_dict(connection, warnings)
        else:
            warnings.append("Setting 'connection' is not an object: using the defaults.")
    return Settings(**values)


class SettingsStore:
    """Reads and writes :class:`Settings` at a fixed path."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> LoadResult:
        """Read the settings; a missing file gives the defaults without warnings."""
        if not self.path.exists():
            return LoadResult(Settings())
        warnings: list[str] = []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("the top level is not a JSON object")
        except (OSError, ValueError) as exc:  # UnicodeDecodeError is a ValueError
            backup = self._move_aside()
            warnings.append(
                f"The settings file {self.path} could not be read ({exc}). "
                f"Default settings are in use; the old file was kept as {backup}."
            )
            settings = Settings()
        else:
            settings = settings_from_dict(data, warnings)
        for message in warnings:
            logger.warning(message)
        return LoadResult(settings, warnings)

    def save(self, settings: Settings) -> None:
        """Write the settings atomically (temporary file, then replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as tmp:
                tmp.write(text)
            os.replace(tmp_name, self.path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        logger.debug("Settings saved to %s", self.path)

    def _move_aside(self) -> Path:
        """Rename an unreadable settings file so it is kept but no longer used."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        try:
            os.replace(self.path, backup)
        except OSError:
            logger.exception("Could not move the unreadable settings file aside")
            return self.path
        return backup
