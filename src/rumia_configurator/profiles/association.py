"""Which product and object dictionary each node uses (FR-NET-03, FR-NET-08, FR-SDO-01).

A node gets a profile in one of these ways:

- ``RECOGNIZED``: its identity matches a Rumia product of the catalog, and the
  EDS of that product is loaded automatically;
- ``MANUAL_PRODUCT``: the user chose a Rumia product;
- ``MANUAL_FILE``: the user loaded an EDS or DCF file;
- ``MANUAL_NONE``: the user chose no profile;
- ``NONE``: not recognised, nothing chosen.

Without a product or file the node gets the minimal CiA 301 dictionary. A
choice of the user always wins over the automatic recognition. Choices last
for the session: a new :class:`ProfileRegistry` is created at every
connection, so they are forgotten on disconnection.

Loading a file is blocking: call :meth:`ProfileRegistry.on_identity`,
:meth:`ProfileRegistry.associate_product` and
:meth:`ProfileRegistry.associate_file` from a worker thread.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from canopen.objectdictionary import ObjectDictionary

from rumia_configurator.core.network.nodes import NodeInfo
from rumia_configurator.profiles.catalog import Product, RecognitionRule, recognize
from rumia_configurator.profiles.eds import (
    EdsWarning,
    load_object_dictionary,
    minimal_object_dictionary,
)

logger = logging.getLogger(__name__)


class ProfileSource(StrEnum):
    RECOGNIZED = "recognized"
    MANUAL_PRODUCT = "manual_product"
    MANUAL_FILE = "manual_file"
    MANUAL_NONE = "manual_none"
    NONE = "none"


MANUAL_SOURCES = (
    ProfileSource.MANUAL_PRODUCT,
    ProfileSource.MANUAL_FILE,
    ProfileSource.MANUAL_NONE,
)


@dataclass(frozen=True)
class NodeProfile:
    """Product, EDS and object dictionary of one node."""

    node_id: int
    source: ProfileSource
    od: ObjectDictionary
    product: Product | None = None
    rule: RecognitionRule | None = None  # for RECOGNIZED
    eds_path: Path | None = None
    warnings: tuple[EdsWarning, ...] = field(default_factory=tuple)

    @property
    def manual(self) -> bool:
        """Chosen by the user: the automatic recognition does not replace it."""
        return self.source in MANUAL_SOURCES

    @property
    def is_rumia(self) -> bool:
        """A Rumia product, recognised or chosen: shows the RUMIA badge."""
        return self.product is not None


class ProfileRegistry:
    """Profiles of the nodes of one connection."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._profiles: dict[int, NodeProfile] = {}

    def profile(self, node_id: int) -> NodeProfile | None:
        with self._lock:
            return self._profiles.get(node_id)

    def all(self) -> dict[int, NodeProfile]:
        with self._lock:
            return dict(self._profiles)

    def on_identity(self, info: NodeInfo) -> NodeProfile:
        """Recognise ``info`` and load the EDS of its product; a manual choice is kept."""
        current = self.profile(info.node_id)
        if current is not None and current.manual:
            return current
        recognition = recognize(info)
        if recognition.product is None:
            return self._store(self._minimal(info.node_id, ProfileSource.NONE))
        try:
            profile = self._product_profile(
                info.node_id, recognition.product, ProfileSource.RECOGNIZED
            )
        except (OSError, ValueError):  # a bundled EDS is tested: this would be a bug
            logger.exception("Bundled EDS of %s not loaded", recognition.product.name)
            return self._store(self._minimal(info.node_id, ProfileSource.NONE))
        return self._store(replace(profile, rule=recognition.rule))

    def associate_product(self, node_id: int, product: Product) -> NodeProfile:
        """The user chose a Rumia product for ``node_id``."""
        return self._store(self._product_profile(node_id, product, ProfileSource.MANUAL_PRODUCT))

    def associate_file(self, node_id: int, path: Path) -> NodeProfile:
        """The user chose an EDS or DCF file; raises ``EdsLoadError`` if it cannot be loaded.

        On error the previous profile of the node is kept.
        """
        result = load_object_dictionary(path, node_id)
        profile = NodeProfile(
            node_id,
            ProfileSource.MANUAL_FILE,
            result.od,
            eds_path=path,
            warnings=tuple(result.warnings),
        )
        return self._store(profile)

    def associate_none(self, node_id: int) -> NodeProfile:
        """The user chose no profile: minimal CiA 301 dictionary until disconnection."""
        return self._store(self._minimal(node_id, ProfileSource.MANUAL_NONE))

    def clear(self, node_id: int, info: NodeInfo | None = None) -> NodeProfile | None:
        """Forget the choice of the user; recognise again if ``info`` is given."""
        with self._lock:
            self._profiles.pop(node_id, None)
        return self.on_identity(info) if info is not None else None

    @staticmethod
    def _minimal(node_id: int, source: ProfileSource) -> NodeProfile:
        return NodeProfile(node_id, source, minimal_object_dictionary(node_id))

    @staticmethod
    def _product_profile(node_id: int, product: Product, source: ProfileSource) -> NodeProfile:
        result = load_object_dictionary(product.eds, node_id)
        return NodeProfile(
            node_id,
            source,
            result.od,
            product,
            eds_path=product.eds,
            warnings=tuple(result.warnings),
        )

    def _store(self, profile: NodeProfile) -> NodeProfile:
        with self._lock:
            self._profiles[profile.node_id] = profile
        what = profile.product.name if profile.product else (profile.eds_path or "none")
        logger.info("Node %d: profile %s (%s)", profile.node_id, what, profile.source.value)
        return profile
