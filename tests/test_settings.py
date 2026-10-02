"""Tests for persistent settings (FR-APP-01)."""

import json
from pathlib import Path

from rumia_configurator.core import paths
from rumia_configurator.core.settings import (
    ConnectionSettings,
    Settings,
    SettingsStore,
)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_missing_file_gives_defaults_without_warnings(tmp_path: Path) -> None:
    result = SettingsStore(tmp_path / "settings.json").load()
    assert result.settings == Settings()
    assert result.warnings == []


def test_default_bitrate_is_1_mbit() -> None:
    assert Settings().connection.bitrate == 1_000_000


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "nested" / "settings.json")
    settings = Settings(
        language="it",
        ui_mode="expert",
        theme="dark",
        log_level="DEBUG",
        window_geometry="AdnQywADAAA=",
        node_panel_width=320,
        connection=ConnectionSettings(backend="pcan", channel="PCAN_USBBUS1", bitrate=250_000),
    )
    store.save(settings)
    result = store.load()
    assert result.settings == settings
    assert result.warnings == []


def test_non_ascii_values_survive(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(Settings(connection=ConnectionSettings(channel="/dev/ttyACM0-àèìòù-µ")))
    assert store.load().settings.connection.channel == "/dev/ttyACM0-àèìòù-µ"
    assert "àèìòù" in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_save_leaves_no_temporary_files(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(Settings())
    store.save(Settings(language="en"))
    assert [p.name for p in tmp_path.iterdir()] == ["settings.json"]


def test_unknown_keys_are_ignored_with_warning(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {"language": "en", "colour": "red", "connection": {"speed": 1}})
    result = SettingsStore(path).load()
    assert result.settings.language == "en"
    assert any("'colour'" in w for w in result.warnings)
    assert any("'connection.speed'" in w for w in result.warnings)


def test_invalid_values_fall_back_per_field(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(
        path,
        {
            "language": "fr",
            "ui_mode": "expert",
            "log_level": 10,
            "connection": {"backend": "socketcan", "bitrate": True, "channel": "can0"},
        },
    )
    result = SettingsStore(path).load()
    defaults = Settings()
    assert result.settings.language == defaults.language
    assert result.settings.ui_mode == "expert"
    assert result.settings.log_level == defaults.log_level
    assert result.settings.connection == ConnectionSettings(backend="socketcan", channel="can0")
    assert len(result.warnings) == 3


def test_theme_defaults_to_system_and_rejects_unknown_values(tmp_path: Path) -> None:
    assert Settings().theme == "system"
    path = tmp_path / "settings.json"
    write_json(path, {"theme": "sepia"})
    result = SettingsStore(path).load()
    assert result.settings.theme == "system"
    assert len(result.warnings) == 1


def test_non_positive_panel_width_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {"node_panel_width": 0})
    result = SettingsStore(path).load()
    assert result.settings.node_panel_width == Settings().node_panel_width
    assert len(result.warnings) == 1


def test_non_positive_bitrate_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {"connection": {"bitrate": 0}})
    result = SettingsStore(path).load()
    assert result.settings.connection.bitrate == 1_000_000
    assert len(result.warnings) == 1


def test_connection_not_an_object(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {"connection": "slcan"})
    result = SettingsStore(path).load()
    assert result.settings.connection == ConnectionSettings()
    assert len(result.warnings) == 1


def test_corrupt_file_is_kept_aside_and_reported(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    result = SettingsStore(path).load()
    assert result.settings == Settings()
    assert len(result.warnings) == 1
    backups = list(tmp_path.glob("settings.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not json"
    assert str(backups[0]) in result.warnings[0]
    assert not path.exists()


def test_top_level_not_an_object_is_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, [1, 2, 3])
    result = SettingsStore(path).load()
    assert result.settings == Settings()
    assert len(list(tmp_path.glob("settings.json.corrupt-*"))) == 1


def test_newer_schema_version_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {"schema_version": 99, "language": "it"})
    result = SettingsStore(path).load()
    assert result.settings.language == "it"
    assert any("newer version" in w for w in result.warnings)


def test_settings_path_is_in_config_dir(user_dirs: Path) -> None:
    assert paths.settings_path() == user_dirs / "config" / "settings.json"
