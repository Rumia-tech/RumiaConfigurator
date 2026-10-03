"""Tolerant import of EDS and DCF files (FR-SDO-01, FR-SDO-12).

The ``canopen`` library refuses some EDS files that are good enough to work
with: an empty ``VendorNumber=`` in ``[DeviceInfo]``, for example, stops the
import. This module repairs those fields in memory, imports the file and
returns the object dictionary together with a list of warnings, so that an
incomplete EDS loads anyway instead of blocking the application.

Warnings are structured (:class:`EdsWarning`): the interface translates and
groups them, the log keeps the technical text. A file that cannot be imported
at all raises :class:`EdsLoadError`; there is never an empty dictionary in
its place.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import canopen
from canopen import objectdictionary
from canopen.objectdictionary import ObjectDictionary, ODVariable

DATA_DIR = Path(__file__).resolve().parent / "data"
SUFFIXES = (".eds", ".dcf")
MANDATORY_OBJECTS = (0x1000, 0x1001, 0x1018)  # CiA 301

# Numeric [DeviceInfo] keys that canopen parses with int(): an empty value fails.
_NUMERIC_DEVICE_INFO = re.compile(
    r"^(VendorNumber|ProductNumber|RevisionNumber|BaudRate_\d+|SimpleBootUp(?:Master|Slave)"
    r"|Granularity|DynamicChannelsSupported|GroupMessaging|NrOfRXPDO|NrOfTXPDO"
    r"|LSS_Supported)[ \t]*=[ \t]*(\r?)$",
    re.MULTILINE,
)
_SECTION = re.compile(r"^\[([^\]]+)\]", re.MULTILINE)


class EdsWarningCode(StrEnum):
    """Kinds of problem found in a file that still loads."""

    EMPTY_DEVICE_INFO = "empty_device_info"  # a numeric [DeviceInfo] field is empty
    MISSING_MANDATORY = "missing_mandatory"  # 0x1000, 0x1001 or 0x1018 is missing
    MISSING_DEFAULTS = "missing_defaults"  # objects without DefaultValue
    EMPTY_PRODUCT_NAME = "empty_product_name"
    LIBRARY = "library"  # a warning logged by canopen while importing


@dataclass(frozen=True)
class EdsWarning:
    """One problem of the file; ``objects`` lists what it concerns (keys or ``0x1003:01``)."""

    code: EdsWarningCode
    text: str  # technical text, in English, for the log and for support
    objects: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.text


@dataclass
class EdsLoadResult:
    """Object dictionary imported from an EDS or DCF, with what had to be repaired."""

    od: ObjectDictionary
    warnings: list[EdsWarning] = field(default_factory=list)


class EdsLoadErrorKind(StrEnum):
    """Why a file could not be loaded; the interface explains each one."""

    UNREADABLE = "unreadable"  # missing, no permission
    WRONG_TYPE = "wrong_type"  # not .eds or .dcf
    INVALID = "invalid"  # the library refused it
    EMPTY = "empty"  # no objects


class EdsLoadError(ValueError):
    """The file cannot be read or is not an EDS/DCF that can be imported.

    ``reason`` is the technical text, in English, for the log and for support.
    """

    def __init__(self, path: Path, kind: EdsLoadErrorKind, reason: str) -> None:
        super().__init__(f"{path.name}: {reason}")
        self.path = path
        self.kind = kind
        self.reason = reason


class _NamedStringIO(io.StringIO):
    """Text stream with a file name: canopen picks the format from it."""

    def __init__(self, text: str, name: str) -> None:
        super().__init__(text)
        self.name = name


class _CollectWarnings(logging.Handler):
    """Collect the warnings canopen logs while it imports a file."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def bundled_eds(product: str) -> Path:
    """Path of the EDS shipped for ``product`` (a folder name under ``data/``)."""
    folder = DATA_DIR / product
    matches = sorted(folder.glob("*.eds"))
    if not matches:
        raise FileNotFoundError(f"No EDS file in {folder}")
    return matches[0]


def _read_text(path: Path) -> str:
    """EDS files are ASCII in theory; accept UTF-8 and fall back to Latin-1."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise EdsLoadError(
            path, EdsLoadErrorKind.UNREADABLE, f"the file cannot be read ({exc})"
        ) from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _repair_device_info(text: str, warnings: list[EdsWarning]) -> str:
    """Set empty numeric fields of ``[DeviceInfo]`` to 0, with one warning each."""
    sections = list(_SECTION.finditer(text))
    for position, section in enumerate(sections):
        if section.group(1).strip().lower() != "deviceinfo":
            continue
        start = section.end()
        end = sections[position + 1].start() if position + 1 < len(sections) else len(text)
        body = text[start:end]
        for match in _NUMERIC_DEVICE_INFO.finditer(body):
            key = match.group(1)
            warnings.append(
                EdsWarning(
                    EdsWarningCode.EMPTY_DEVICE_INFO,
                    f"[DeviceInfo] {key} is empty: read as 0",
                    (key,),
                )
            )
        body = _NUMERIC_DEVICE_INFO.sub(r"\1=0\2", body)
        return text[:start] + body + text[end:]
    return text


def _variables(od: ObjectDictionary) -> list[ODVariable]:
    """Every variable of the dictionary, sub-entries included."""
    found: list[ODVariable] = []
    for obj in od.values():
        if isinstance(obj, ODVariable):
            found.append(obj)
        else:
            found.extend(obj.values())
    return found


def _check(od: ObjectDictionary) -> list[EdsWarning]:
    """Problems that do not stop the import but the user should know."""
    warnings: list[EdsWarning] = []
    missing = [f"0x{index:04X}" for index in MANDATORY_OBJECTS if index not in od]
    if missing:
        warnings.append(
            EdsWarning(
                EdsWarningCode.MISSING_MANDATORY,
                f"Mandatory CiA 301 objects missing: {', '.join(missing)}",
                tuple(missing),
            )
        )
    no_default = tuple(
        f"0x{var.index:04X}:{var.subindex:02X}"
        for var in _variables(od)
        # ``default_raw`` keeps "$NODEID+0x80" when no Node-ID was given: not missing.
        if var.index >= 0x1000
        and var.default is None
        and not getattr(var, "default_raw", None)
        and var.readable
    )
    if no_default:
        warnings.append(
            EdsWarning(
                EdsWarningCode.MISSING_DEFAULTS,
                f"{len(no_default)} objects without DefaultValue: {', '.join(no_default)}",
                no_default,
            )
        )
    if not (od.device_information.product_name or "").strip():
        warnings.append(EdsWarning(EdsWarningCode.EMPTY_PRODUCT_NAME, "ProductName is empty"))
    return warnings


def load_object_dictionary(path: Path, node_id: int | None = None) -> EdsLoadResult:
    """Import the EDS or DCF at ``path`` for ``node_id``, repairing what canopen would refuse.

    Raises :class:`EdsLoadError` if the file cannot be read or imported even
    after the repairs.
    """
    if path.suffix.lower() not in SUFFIXES:
        raise EdsLoadError(
            path, EdsLoadErrorKind.WRONG_TYPE, "only .eds and .dcf files can be loaded"
        )
    warnings: list[EdsWarning] = []
    text = _repair_device_info(_read_text(path), warnings)
    collector = _CollectWarnings()
    canopen_log = logging.getLogger("canopen.objectdictionary")
    canopen_log.addHandler(collector)
    try:
        od = canopen.import_od(_NamedStringIO(text, path.name), node_id)
    except Exception as exc:  # canopen raises many types for a malformed file
        raise EdsLoadError(
            path, EdsLoadErrorKind.INVALID, f"not a valid EDS or DCF file ({exc})"
        ) from exc
    finally:
        canopen_log.removeHandler(collector)
    if len(od) == 0:
        raise EdsLoadError(path, EdsLoadErrorKind.EMPTY, "the file defines no objects")
    warnings.extend(EdsWarning(EdsWarningCode.LIBRARY, text) for text in collector.messages)
    warnings.extend(_check(od))
    return EdsLoadResult(od, warnings)


def minimal_object_dictionary(node_id: int | None = None) -> ObjectDictionary:
    """The objects every CiA 301 node has, for nodes without an EDS (FR-SDO-01).

    0x1000 Device type, 0x1001 Error register, 0x1017 Producer heartbeat time
    and 0x1018 Identity. Other objects are read raw by index and sub-index.
    """
    od = ObjectDictionary()
    od.node_id = node_id
    od.add_object(_var("Device type", 0x1000, 0, objectdictionary.UNSIGNED32, "ro"))
    od.add_object(_var("Error register", 0x1001, 0, objectdictionary.UNSIGNED8, "ro"))
    od.add_object(_var("Producer heartbeat time", 0x1017, 0, objectdictionary.UNSIGNED16, "rw"))
    identity = objectdictionary.ODRecord("Identity object", 0x1018)
    identity.add_member(
        _var("Highest sub-index supported", 0x1018, 0, objectdictionary.UNSIGNED8, "ro")
    )
    for subindex, name in enumerate(
        ("Vendor-ID", "Product code", "Revision number", "Serial number"), start=1
    ):
        identity.add_member(_var(name, 0x1018, subindex, objectdictionary.UNSIGNED32, "ro"))
    od.add_object(identity)
    return od


def _var(name: str, index: int, subindex: int, data_type: int, access: str) -> ODVariable:
    var = ODVariable(name, index, subindex)
    var.data_type = data_type
    var.access_type = access
    return var
