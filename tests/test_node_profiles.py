"""Profiles of the nodes: automatic, chosen by hand, from a file (FR-NET-08, FR-SDO-01)."""

from pathlib import Path

import pytest

from rumia_configurator.core.network import NodeInfo, SeenBy
from rumia_configurator.profiles.association import ProfileRegistry, ProfileSource
from rumia_configurator.profiles.catalog import RecognitionRule, product_by_key
from rumia_configurator.profiles.eds import EdsLoadError, EdsWarningCode, bundled_eds

SMART_IMU = NodeInfo(29, SeenBy.SCAN, name="Smart IMU")
NAMELESS = NodeInfo(42, SeenBy.HEARTBEAT, vendor_id=0, product_code=0)


def test_recognised_node_gets_the_eds_of_its_product() -> None:
    registry = ProfileRegistry()
    profile = registry.on_identity(SMART_IMU)
    assert profile.source == ProfileSource.RECOGNIZED
    assert profile.rule == RecognitionRule.DEVICE_NAME
    assert profile.product is product_by_key("smart_imu")
    assert profile.eds_path == bundled_eds("smart_imu")
    assert 0x6001 in profile.od
    assert profile.od[0x1800][1].default == 0x40000180 + 29  # $NODEID of this node
    assert profile.is_rumia and not profile.manual
    assert EdsWarningCode.EMPTY_DEVICE_INFO in {w.code for w in profile.warnings}
    assert registry.profile(29) is profile


def test_unrecognised_node_gets_the_minimal_dictionary() -> None:
    profile = ProfileRegistry().on_identity(NAMELESS)
    assert profile.source == ProfileSource.NONE
    assert profile.product is None and not profile.is_rumia
    assert sorted(profile.od) == [0x1000, 0x1001, 0x1017, 0x1018]


def test_choice_by_hand_wins_over_recognition() -> None:
    registry = ProfileRegistry()
    registry.on_identity(NAMELESS)
    chosen = registry.associate_product(42, product_by_key("smart_imu"))
    assert chosen.source == ProfileSource.MANUAL_PRODUCT and chosen.is_rumia and chosen.manual
    assert registry.on_identity(NAMELESS) is chosen  # a new identity read keeps it


def test_back_to_automatic() -> None:
    registry = ProfileRegistry()
    registry.associate_product(42, product_by_key("incli_sense"))
    profile = registry.clear(42, NAMELESS)
    assert profile is not None and profile.source == ProfileSource.NONE


def test_no_profile_chosen_by_hand() -> None:
    registry = ProfileRegistry()
    profile = registry.associate_none(29)
    assert profile.manual and profile.product is None
    assert registry.on_identity(SMART_IMU).source == ProfileSource.MANUAL_NONE  # kept


def test_choices_last_for_the_session() -> None:
    """A new registry is created at every connection: the choice is gone."""
    first = ProfileRegistry()
    first.associate_product(42, product_by_key("smart_imu"))
    assert ProfileRegistry().on_identity(NAMELESS).source == ProfileSource.NONE


def test_eds_from_a_file(tmp_path: Path) -> None:
    path = tmp_path / "third_party.eds"
    path.write_bytes(bundled_eds("smart_imu").read_bytes())
    profile = ProfileRegistry().associate_file(42, path)
    assert profile.source == ProfileSource.MANUAL_FILE
    assert profile.eds_path == path and profile.product is None
    assert profile.warnings  # the warnings of the file travel with the profile


def test_bad_file_keeps_the_previous_profile(tmp_path: Path) -> None:
    registry = ProfileRegistry()
    before = registry.on_identity(SMART_IMU)
    path = tmp_path / "broken.eds"
    path.write_text("not an EDS", encoding="ascii")
    with pytest.raises(EdsLoadError):
        registry.associate_file(29, path)
    assert registry.profile(29) is before
