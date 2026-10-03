"""Profiles in the window: RUMIA badge, "Associate profile…", header, EDS warnings."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from rumia_configurator.core import paths
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import IncliSenseNode, Simulator, SmartImuNode
from rumia_configurator.gui.connection import ConnectionController
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme import manager as theme_module
from rumia_configurator.gui.theme.manager import ThemeManager, install_theme
from rumia_configurator.gui.views import profile_dialog
from rumia_configurator.gui.views.profile_dialog import ChoiceKind, ProfileChoice
from rumia_configurator.profiles.association import NodeProfile
from rumia_configurator.profiles.catalog import product_by_key


@pytest.fixture
def managers(qapp: QApplication) -> Iterator[tuple[ThemeManager, LanguageManager]]:
    theme_manager, _fonts = install_theme(qapp, "light")
    language_manager = LanguageManager(qapp, "en")
    yield theme_manager, language_manager
    language_manager.uninstall()
    qapp.setStyleSheet("")
    theme_module._reset_for_tests()


@pytest.fixture
def network(sim_channel: str) -> Iterator[Simulator]:
    """INCLI Sense 10 (recognised) and a Smart IMU 42 without 0x1008, like today's sensor."""
    nameless = SmartImuNode(42)
    del nameless.local.object_dictionary[0x1008]
    with Simulator([IncliSenseNode(), nameless], channel=sim_channel) as sim:
        yield sim


@pytest.fixture
def window(
    qtbot: QtBot,
    managers: tuple[ThemeManager, LanguageManager],
    network: Simulator,
    sim_channel: str,
) -> MainWindow:
    theme_manager, language_manager = managers
    store = SettingsStore(paths.settings_path())
    main = MainWindow(
        store,
        store.load().settings,
        theme_manager,
        language_manager,
        [("INCLI Sense", 10), ("Smart IMU", 42)],
        ConnectionController(lister=lambda: []),
    )
    qtbot.addWidget(main)
    main.resize(1366, 768)
    main.show()
    main.start_demo_connection(sim_channel)
    rows = main.node_panel.rows
    qtbot.waitUntil(
        lambda: sorted(rows) == [10, 42] and all(r.profile is not None for r in rows.values()),
        timeout=5000,
    )
    return main


def choose(monkeypatch: pytest.MonkeyPatch, choice: ProfileChoice | None) -> list[int]:
    asked: list[int] = []

    def fake(parent: object, node_id: int, current: NodeProfile | None) -> ProfileChoice | None:
        asked.append(node_id)
        return choice

    monkeypatch.setattr(profile_dialog, "choose_profile", fake)
    return asked


def test_recognised_node_has_the_rumia_badge(window: MainWindow) -> None:
    incli, nameless = window.node_panel.rows[10], window.node_panel.rows[42]
    assert incli.badge.isVisible() and incli.badge.text() == "RUMIA"
    assert not incli.profile_link.isVisible()
    assert not nameless.badge.isVisible()
    assert nameless.profile_link.isVisible()
    assert nameless.profile_link.text() == "Associate profile…"
    assert nameless.name_label.text() == "Node without name"


def test_associate_a_product_by_hand(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked = choose(monkeypatch, ProfileChoice(ChoiceKind.PRODUCT, product_by_key("smart_imu")))
    row = window.node_panel.rows[42]
    row.profile_link.click()
    assert asked == [42]
    qtbot.waitUntil(lambda: row.badge.isVisible(), timeout=3000)
    assert not row.profile_link.isVisible()
    assert row.detail.text().endswith("· chosen by hand")
    window.node_panel.select(42)
    header = window.workspace
    assert header.profile_label.text() == (
        "Profile: Smart IMU · smart_imu.eds · chosen by hand until disconnection"
    )
    assert header.warnings_link.isVisible()
    assert header.warnings_link.text() == "3 EDS warnings"


def test_recognised_profile_in_the_header(window: MainWindow) -> None:
    window.node_panel.select(10)
    header = window.workspace
    assert header.profile_label.text() == (
        "Profile: INCLI Sense · incli_sense.eds · recognised by its name"
    )
    assert not header.warnings_link.isVisible()  # the INCLI Sense EDS has no warnings
    assert header.change_profile_link.isVisible()


def test_cancelled_choice_changes_nothing(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    choose(monkeypatch, None)
    window.node_panel.rows[42].profile_link.click()
    qtbot.wait(200)
    assert not window.node_panel.rows[42].badge.isVisible()


def test_bad_file_is_explained(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "wrong.eds"
    path.write_text("not an EDS", encoding="ascii")
    choose(monkeypatch, ProfileChoice(ChoiceKind.FILE, path=path))
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, t, text: shown.append((t, text)))
    window.choose_profile(42)
    qtbot.waitUntil(lambda: bool(shown), timeout=3000)
    title, text = shown[0]
    what, why, todo = text.split("\n\n")
    assert title == "EDS not loaded"
    assert what == "The file wrong.eds could not be used for node 42."
    assert why.startswith("Cause: the file is not a valid EDS or DCF (")
    assert "keeps its previous profile" in todo
    assert not window.node_panel.rows[42].badge.isVisible()


def test_eds_warnings_are_listed_in_plain_words(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    choose(monkeypatch, ProfileChoice(ChoiceKind.PRODUCT, product_by_key("smart_imu")))
    window.choose_profile(42)
    qtbot.waitUntil(lambda: window.node_panel.rows[42].badge.isVisible(), timeout=3000)
    profile = window.node_panel.rows[42].profile
    assert profile is not None
    texts = [profile_dialog.warning_text(w) for w in profile.warnings]
    assert texts[0] == "Field VendorNumber of [DeviceInfo] is empty: read as 0"
    assert texts[2].startswith("17 objects without a default value (0x1003:00, ")
    assert texts[2].endswith("…)")


def test_profile_dialog_offers_the_products_and_the_alternatives(qapp: QApplication) -> None:
    dialog = profile_dialog.ProfileDialog(42, None)
    labels = [button.text() for button in dialog.options]
    assert labels == [
        "Smart IMU · smart_imu.eds",
        "INCLI Sense · incli_sense.eds",
        "EDS or DCF file…",
        "No profile (only the CiA 301 objects)",
    ]
    assert dialog.choice().kind == ChoiceKind.PRODUCT  # first option checked
    dialog.deleteLater()


@pytest.mark.parametrize("language", ["it", "en"])
def test_panel_still_fits(qtbot: QtBot, window: MainWindow, language: str) -> None:
    window.set_language(language)
    window.splitter.setSizes([272, 1366 - 272])
    QApplication.processEvents()
    assert window.node_panel.minimumSizeHint().width() <= 272
