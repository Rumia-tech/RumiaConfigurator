"""Tolerant EDS and DCF import (FR-SDO-01, FR-SDO-12)."""

from pathlib import Path

import pytest

from rumia_configurator.profiles.eds import (
    EdsLoadError,
    EdsLoadErrorKind,
    EdsWarningCode,
    bundled_eds,
    load_object_dictionary,
    minimal_object_dictionary,
)


def codes(result: object) -> list[EdsWarningCode]:
    return [w.code for w in result.warnings]  # type: ignore[attr-defined]


def incli_text() -> str:
    return bundled_eds("incli_sense").read_text(encoding="ascii").replace("\r\n", "\n")


def test_smart_imu_eds_loads_with_warnings() -> None:
    """Acceptance of T1.6: the provisional Smart IMU EDS loads, with its warnings listed."""
    result = load_object_dictionary(bundled_eds("smart_imu"), 29)
    assert len(result.od) == 37
    assert result.od.device_information.product_name == "Smart IMU"
    assert result.od.device_information.vendor_number == 0
    empty = [w.objects[0] for w in result.warnings if w.code == EdsWarningCode.EMPTY_DEVICE_INFO]
    assert empty == ["VendorNumber", "ProductNumber"]
    defaults = next(w for w in result.warnings if w.code == EdsWarningCode.MISSING_DEFAULTS)
    assert "0x1003:01" in defaults.objects  # the error history has no default values
    assert all(obj.startswith("0x1003") for obj in defaults.objects)
    assert str(defaults) == defaults.text  # technical text for the log
    assert result.od[0x1800][1].default == 0x40000180 + 29  # $NODEID resolved


def test_incli_sense_eds_loads_cleanly() -> None:
    result = load_object_dictionary(bundled_eds("incli_sense"), 10)
    assert result.warnings == []
    assert result.od[0x1008].default == "INCLI Sense"
    assert [result.od[0x1A00][i].default for i in (1, 2)] == [0x60100010, 0x60200010]


def test_nodeid_defaults_are_not_missing_without_a_node_id() -> None:
    """``$NODEID+0x80`` has no value until a Node-ID is given: it is not a missing default."""
    assert load_object_dictionary(bundled_eds("incli_sense")).warnings == []


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_empty_numeric_fields_are_repaired_with_any_line_ending(
    tmp_path: Path, newline: str
) -> None:
    text = incli_text().replace("ProductNumber=0", "ProductNumber=").replace("\n", newline)
    path = tmp_path / "device.eds"
    path.write_bytes(text.encode("ascii"))
    result = load_object_dictionary(path)
    assert [str(w) for w in result.warnings] == ["[DeviceInfo] ProductNumber is empty: read as 0"]
    assert result.od.device_information.product_name == "INCLI Sense"


def test_dcf_files_are_accepted(tmp_path: Path) -> None:
    path = tmp_path / "configured.dcf"
    path.write_text(incli_text(), encoding="ascii")
    assert len(load_object_dictionary(path, 10).od) == 24


def test_missing_mandatory_objects_and_product_name(tmp_path: Path) -> None:
    text = incli_text().replace("ProductName=INCLI Sense", "ProductName=")
    start = text.index("[1001]")
    end = text.index("[1018]")  # drop 0x1001 and 0x1008..0x1017 that follow it
    text = text[:start] + text[end:]
    path = tmp_path / "partial.eds"
    path.write_text(text, encoding="ascii")
    result = load_object_dictionary(path)
    warnings = {w.code: w for w in result.warnings}
    assert warnings[EdsWarningCode.MISSING_MANDATORY].objects == ("0x1001",)
    assert EdsWarningCode.EMPTY_PRODUCT_NAME in warnings


@pytest.mark.parametrize(
    ("name", "content", "kind"),
    [
        ("broken.eds", "this is not an EDS file", EdsLoadErrorKind.INVALID),
        ("notes.txt", "[FileInfo]", EdsLoadErrorKind.WRONG_TYPE),
        ("empty.eds", "[FileInfo]\nFileName=empty.eds\n", EdsLoadErrorKind.EMPTY),
    ],
)
def test_files_that_cannot_be_loaded(
    tmp_path: Path, name: str, content: str, kind: EdsLoadErrorKind
) -> None:
    path = tmp_path / name
    path.write_text(content, encoding="ascii")
    with pytest.raises(EdsLoadError) as error:
        load_object_dictionary(path)
    assert error.value.path == path
    assert error.value.kind == kind
    assert error.value.reason  # technical text for the log
    assert isinstance(error.value, ValueError)


def test_missing_file_is_a_load_error(tmp_path: Path) -> None:
    with pytest.raises(EdsLoadError) as error:
        load_object_dictionary(tmp_path / "missing.eds")
    assert error.value.kind == EdsLoadErrorKind.UNREADABLE


def test_minimal_dictionary_has_the_cia_301_objects() -> None:
    od = minimal_object_dictionary(42)
    assert sorted(od) == [0x1000, 0x1001, 0x1017, 0x1018]
    assert [od[0x1018][i].name for i in (1, 2, 3, 4)] == [
        "Vendor-ID",
        "Product code",
        "Revision number",
        "Serial number",
    ]
    assert od[0x1017].writable and not od[0x1000].writable


def test_unknown_product_has_no_bundled_eds() -> None:
    with pytest.raises(FileNotFoundError):
        bundled_eds("no_such_product")
