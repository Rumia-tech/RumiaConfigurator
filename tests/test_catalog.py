"""Recognition of the Rumia products (FR-NET-03, FR-NET-08), one test per case."""

import pytest

from rumia_configurator.core.network import NodeInfo, SeenBy
from rumia_configurator.profiles import catalog
from rumia_configurator.profiles.catalog import (
    PRODUCTS,
    Product,
    RecognitionRule,
    product_by_key,
    recognize,
)
from rumia_configurator.profiles.eds import load_object_dictionary


def node(**fields: object) -> NodeInfo:
    return NodeInfo(42, SeenBy.SCAN, **fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Smart IMU", "smart_imu"),
        ("INCLI Sense", "incli_sense"),
        ("smart imu", "smart_imu"),  # case
        ("  Smart   IMU ", "smart_imu"),  # spaces
        ("Smart IMU\0\0\0", "smart_imu"),  # NUL padding of a VISIBLE_STRING
    ],
)
def test_recognised_by_device_name(name: str, key: str) -> None:
    result = recognize(node(name=name))
    assert result.product is product_by_key(key)
    assert result.rule == RecognitionRule.DEVICE_NAME


@pytest.mark.parametrize("name", [None, "", "Smart IMU 2", "PCAN-Router", "IMU"])
def test_not_recognised(name: str | None) -> None:
    """Today's Smart IMU has no 0x1008: it is not recognised and is chosen by hand."""
    assert recognize(node(name=name, vendor_id=0, product_code=0)).product is None


def test_name_and_product_code_must_agree() -> None:
    products = (Product("smart_imu", "Smart IMU", ("Smart IMU",), (0x0101,)),)
    assert recognize(node(name="Smart IMU", product_code=0x0101), products).product
    assert recognize(node(name="Smart IMU", product_code=0), products).product  # code not set
    assert recognize(node(name="Smart IMU", product_code=0x0999), products).product is None


def test_vendor_and_product_code_when_the_vendor_id_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    products = (Product("incli_sense", "INCLI Sense", ("INCLI Sense",), (0x0202,)),)
    info = node(vendor_id=0x0000ABCD, product_code=0x0202)  # no name
    assert recognize(info, products).product is None  # no Vendor-ID assigned yet
    monkeypatch.setattr(catalog, "RUMIA_VENDOR_ID", 0x0000ABCD)
    result = recognize(info, products)
    assert result.product is products[0]
    assert result.rule == RecognitionRule.VENDOR_AND_CODE
    other_vendor = node(vendor_id=0x00000123, product_code=0x0202)
    assert recognize(other_vendor, products).product is None


def test_no_product_codes_are_assigned_yet() -> None:
    assert catalog.RUMIA_VENDOR_ID is None
    assert all(product.product_codes == () for product in PRODUCTS)


@pytest.mark.parametrize("product", PRODUCTS, ids=lambda p: p.key)
def test_every_product_has_an_eds_that_loads(product: Product) -> None:
    result = load_object_dictionary(product.eds, 1)
    assert len(result.od) > 0
    assert product.name in product.device_names


def test_unknown_key() -> None:
    with pytest.raises(KeyError):
        product_by_key("router")
