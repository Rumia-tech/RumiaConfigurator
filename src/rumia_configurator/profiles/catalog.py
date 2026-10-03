"""Rumia products the application knows, and how a node is recognised (FR-NET-03, FR-NET-08).

Rumia has no CANopen Vendor-ID yet (it must be requested from CAN in
Automation) and its products have no Product codes yet. Today a product is
recognised by its device name (0x1008). When the Vendor-ID and the codes
exist, set :data:`RUMIA_VENDOR_ID` and the ``product_codes`` of each product:
the rule by code then comes first.

A node is never recognised from its Node-ID, its PDOs or a guess on its
objects: a wrong product would show wrong units and wrong parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rumia_configurator.core.network.nodes import NodeInfo
from rumia_configurator.profiles.eds import bundled_eds

RUMIA_VENDOR_ID: int | None = None  # not assigned yet by CAN in Automation


@dataclass(frozen=True)
class Product:
    """A Rumia product: its EDS and how to recognise it on the bus."""

    key: str  # folder under profiles/data/
    name: str
    device_names: tuple[str, ...]  # accepted values of 0x1008
    product_codes: tuple[int, ...] = ()  # accepted values of 0x1018:02, when assigned

    @property
    def eds(self) -> Path:
        """The EDS shipped with the application."""
        return bundled_eds(self.key)


PRODUCTS: tuple[Product, ...] = (
    Product("smart_imu", "Smart IMU", ("Smart IMU",)),
    Product("incli_sense", "INCLI Sense", ("INCLI Sense",)),
)


class RecognitionRule(StrEnum):
    """Why a node was recognised as a product."""

    VENDOR_AND_CODE = "vendor_and_code"
    DEVICE_NAME = "device_name"


@dataclass(frozen=True)
class Recognition:
    """The product of a node, and the rule that found it; ``product`` is None if unknown."""

    product: Product | None
    rule: RecognitionRule | None = None


def product_by_key(key: str) -> Product:
    """The product with ``key`` (``KeyError`` if there is none)."""
    for product in PRODUCTS:
        if product.key == key:
            return product
    raise KeyError(key)


def _normalised(name: str) -> str:
    """Compare names without case, NUL padding and repeated spaces."""
    return " ".join(name.replace("\0", " ").split()).casefold()


def recognize(info: NodeInfo, products: tuple[Product, ...] = PRODUCTS) -> Recognition:
    """The product of ``info``, by these rules in order.

    1. Rumia Vendor-ID and a known Product code (only once the Vendor-ID exists).
    2. Device name (0x1008) equal to one of the product's names. If the product
       has Product codes and the node reports a different, non-zero one, the
       two disagree and the node is not recognised: the user chooses.
    3. Otherwise no product.
    """
    if RUMIA_VENDOR_ID is not None and info.vendor_id == RUMIA_VENDOR_ID:
        for product in products:
            if info.product_code is not None and info.product_code in product.product_codes:
                return Recognition(product, RecognitionRule.VENDOR_AND_CODE)
    if info.name:
        name = _normalised(info.name)
        for product in products:
            if name not in (_normalised(n) for n in product.device_names):
                continue
            code = info.product_code
            if product.product_codes and code and code not in product.product_codes:
                return Recognition(None)  # name and code disagree
            return Recognition(product, RecognitionRule.DEVICE_NAME)
    return Recognition(None)
