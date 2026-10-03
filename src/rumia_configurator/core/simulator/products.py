"""Simulated Rumia products: Smart IMU and INCLI Sense."""

from __future__ import annotations

import struct
from functools import partial

from canopen.objectdictionary import ODVariable
from canopen.sdo.exceptions import SdoAbortedError

from rumia_configurator.core.simulator.node import ABORT_VALUE_RANGE_EXCEEDED, SimulatedNode
from rumia_configurator.core.simulator.signals import (
    ImuMotion,
    ImuSample,
    InclinationMotion,
    clamp_int16,
)
from rumia_configurator.profiles.eds import bundled_eds

SMART_IMU_NODE_ID = 29
INCLI_SENSE_NODE_ID = 10

# Smart IMU measurement objects and the sample field each one carries. The
# firmware sends them as INT16 little-endian (the provisional EDS says UNSIGNED16).
IMU_OBJECTS: dict[int, str] = {
    0x6001: "acc_x",
    0x6002: "acc_y",
    0x6003: "acc_z",
    0x6004: "gyro_x",
    0x6005: "gyro_y",
    0x6006: "gyro_z",
}

# CiA 410 objects, by axis: slope, operating parameters, preset, offset, differential offset.
LONGITUDINAL = 0x6010
LATERAL = 0x6020
OPERATING_PARAMETERS = 1
PRESET = 2
OFFSET = 3
DIFFERENTIAL_OFFSET = 4
RESOLUTION = 0x6000
INVERSION_BIT = 0x01
SCALING_BIT = 0x02  # offset and differential offset are applied
RESOLUTIONS_MILLIDEG = (1, 10, 100, 1000)


def _int16_bytes(value: float) -> bytes:
    return struct.pack("<h", clamp_int16(value))


class SmartImuNode(SimulatedNode):
    """Smart IMU: accelerations in mg (TPDO1) and angular rates in mdps (TPDO2)."""

    def __init__(
        self,
        node_id: int = SMART_IMU_NODE_ID,
        motion: ImuMotion | None = None,
        *,
        auto_start: bool = True,
    ) -> None:
        super().__init__(node_id, bundled_eds("smart_imu"), auto_start=auto_start)
        self.motion = motion or ImuMotion()
        for index, field in IMU_OBJECTS.items():
            self.provide(index, 0, partial(self._measurement, field))

    def sample(self) -> ImuSample:
        """Reading at the current simulation time."""
        return self.motion.sample(self.now())

    def _measurement(self, field: str) -> bytes:
        value: int = getattr(self.sample(), field)
        return _int16_bytes(value)


class IncliSenseNode(SimulatedNode):
    """INCLI Sense: longitudinal and lateral slope as in CiA 410 (TPDO1).

    The output of each axis, in units of the resolution 0x6000, is
    ``sign * slope``, plus offset and differential offset when the scaling
    bit of the operating parameters is set. Writing the preset computes the
    offset so that the output equals the preset (plus the differential
    offset) at that moment.
    """

    def __init__(
        self,
        node_id: int = INCLI_SENSE_NODE_ID,
        motion: InclinationMotion | None = None,
        *,
        auto_start: bool = True,
    ) -> None:
        super().__init__(node_id, bundled_eds("incli_sense"), auto_start=auto_start)
        self.motion = motion or InclinationMotion()
        for axis in (LONGITUDINAL, LATERAL):
            self.provide(axis, 0, partial(self._output_bytes, axis))
        self.local.add_write_callback(self._write_parameter)

    def slope_degrees(self, axis: int) -> float:
        """Physical slope of ``axis`` (``LONGITUDINAL`` or ``LATERAL``) now, in degrees."""
        longitudinal, lateral = self.motion.sample(self.now())
        return longitudinal if axis == LONGITUDINAL else lateral

    def output(self, axis: int) -> int:
        """Value of 0x6010 or 0x6020 now, in units of the resolution."""
        value = self._signed_slope(axis)
        if self._int(axis + OPERATING_PARAMETERS) & SCALING_BIT:
            value += self._int(axis + OFFSET) + self._int(axis + DIFFERENTIAL_OFFSET)
        return value

    def _output_bytes(self, axis: int) -> bytes:
        return _int16_bytes(self.output(axis))

    def _int(self, index: int) -> int:
        return int(self.read(index))

    def _signed_slope(self, axis: int) -> int:
        """Slope in resolution units with the inversion applied, before offsets."""
        units = self.slope_degrees(axis) * 1000.0 / self._int(RESOLUTION)
        if self._int(axis + OPERATING_PARAMETERS) & INVERSION_BIT:
            units = -units
        return round(units)

    def _write_parameter(self, index: int, subindex: int, od: ODVariable, data: bytes) -> None:
        if index == RESOLUTION and od.decode_raw(data) not in RESOLUTIONS_MILLIDEG:
            raise SdoAbortedError(ABORT_VALUE_RANGE_EXCEEDED)
        for axis in (LONGITUDINAL, LATERAL):
            if index == axis + PRESET:
                preset = int(od.decode_raw(data))
                self.store(axis + OFFSET, 0, clamp_int16(preset - self._signed_slope(axis)))
