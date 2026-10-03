"""CAN connection: adapters, opening the bus, explained errors (FR-CON)."""

from rumia_configurator.core.connection.adapters import (
    BACKENDS,
    BITRATES,
    KNOWN_USB_IDS,
    AdapterInfo,
    Backend,
    backends_for,
    list_adapters,
)
from rumia_configurator.core.connection.errors import (
    ConnectionFailure,
    ErrorKind,
    classify_open_error,
)
from rumia_configurator.core.connection.service import (
    ConnectionConfig,
    ConnectionService,
    ConnectionState,
    ControllerStatus,
)

__all__ = [
    "BACKENDS",
    "BITRATES",
    "KNOWN_USB_IDS",
    "AdapterInfo",
    "Backend",
    "ConnectionConfig",
    "ConnectionFailure",
    "ConnectionService",
    "ConnectionState",
    "ControllerStatus",
    "ErrorKind",
    "backends_for",
    "classify_open_error",
    "list_adapters",
]
