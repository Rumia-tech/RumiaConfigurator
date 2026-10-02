"""Per-user folders for settings and logs, following each OS convention (FR-APP-01)."""

from pathlib import Path

import platformdirs

APP_NAME = "RumiaConfigurator"
APP_AUTHOR = "Rumia"
SETTINGS_FILE_NAME = "settings.json"


def config_dir() -> Path:
    """Folder that holds the user settings (not created here)."""
    return Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR, roaming=False))


def log_dir() -> Path:
    """Folder that holds the application log files (not created here)."""
    return Path(platformdirs.user_log_dir(APP_NAME, APP_AUTHOR))


def settings_path() -> Path:
    """Default location of the settings file."""
    return config_dir() / SETTINGS_FILE_NAME
