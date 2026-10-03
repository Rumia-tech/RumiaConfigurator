"""Plausible measurement signals for the simulated products.

Every generator is a pure function of the time in seconds: the same time
always gives the same values, so tests are repeatable. The "noise" is a sum
of fast sines with unrelated frequencies, which looks random on a chart but
is fully deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

INT16_MIN = -32768
INT16_MAX = 32767
GRAVITY_MG = 1000.0


def clamp_int16(value: float) -> int:
    """Round ``value`` and clamp it to the INT16 range."""
    return max(INT16_MIN, min(INT16_MAX, round(value)))


def _noise(t: float, amplitude: float, phase: float) -> float:
    """Deterministic jitter in ``[-amplitude, amplitude]``."""
    return amplitude * (
        0.5 * math.sin(2 * math.pi * 7.3 * t + phase)
        + 0.3 * math.sin(2 * math.pi * 19.1 * t + 2.1 * phase)
        + 0.2 * math.sin(2 * math.pi * 31.7 * t + 3.7 * phase)
    )


@dataclass(frozen=True)
class ImuSample:
    """One Smart IMU reading: accelerations in mg, angular rates in mdps."""

    acc_x: int
    acc_y: int
    acc_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int


@dataclass(frozen=True)
class ImuMotion:
    """Slow tilting of the sensor plus a machine vibration.

    Pitch and roll swing like a sine; the accelerometer sees gravity in the
    tilted frame and the gyroscope sees the derivative of the angles.
    """

    pitch_amplitude_deg: float = 15.0
    pitch_frequency_hz: float = 0.05
    roll_amplitude_deg: float = 10.0
    roll_frequency_hz: float = 0.031
    yaw_rate_amplitude_dps: float = 2.0
    yaw_frequency_hz: float = 0.02
    vibration_mg: float = 20.0
    vibration_hz: float = 12.5
    acc_noise_mg: float = 4.0
    gyro_noise_mdps: float = 50.0

    def sample(self, t: float) -> ImuSample:
        """Reading at time ``t`` (seconds)."""
        w_pitch = 2 * math.pi * self.pitch_frequency_hz
        w_roll = 2 * math.pi * self.roll_frequency_hz
        pitch = math.radians(self.pitch_amplitude_deg) * math.sin(w_pitch * t)
        roll = math.radians(self.roll_amplitude_deg) * math.sin(w_roll * t + 1.0)
        pitch_rate_dps = self.pitch_amplitude_deg * w_pitch * math.cos(w_pitch * t)
        roll_rate_dps = self.roll_amplitude_deg * w_roll * math.cos(w_roll * t + 1.0)
        yaw_rate_dps = self.yaw_rate_amplitude_dps * math.sin(
            2 * math.pi * self.yaw_frequency_hz * t
        )
        vibration = self.vibration_mg * math.sin(2 * math.pi * self.vibration_hz * t)

        acc_x = -GRAVITY_MG * math.sin(pitch) + _noise(t, self.acc_noise_mg, 0.1)
        acc_y = GRAVITY_MG * math.sin(roll) * math.cos(pitch) + _noise(t, self.acc_noise_mg, 0.7)
        acc_z = (
            GRAVITY_MG * math.cos(roll) * math.cos(pitch)
            + vibration
            + _noise(t, self.acc_noise_mg, 1.3)
        )
        return ImuSample(
            acc_x=clamp_int16(acc_x),
            acc_y=clamp_int16(acc_y),
            acc_z=clamp_int16(acc_z),
            gyro_x=clamp_int16(roll_rate_dps * 1000 + _noise(t, self.gyro_noise_mdps, 1.9)),
            gyro_y=clamp_int16(pitch_rate_dps * 1000 + _noise(t, self.gyro_noise_mdps, 2.3)),
            gyro_z=clamp_int16(yaw_rate_dps * 1000 + _noise(t, self.gyro_noise_mdps, 2.9)),
        )


@dataclass(frozen=True)
class InclinationMotion:
    """Two slow, independent swings of the longitudinal and lateral slope."""

    longitudinal_amplitude_deg: float = 5.0
    longitudinal_frequency_hz: float = 0.04
    lateral_amplitude_deg: float = 3.0
    lateral_frequency_hz: float = 0.027
    noise_deg: float = 0.02

    def sample(self, t: float) -> tuple[float, float]:
        """Longitudinal and lateral slope in degrees at time ``t`` (seconds)."""
        longitudinal = self.longitudinal_amplitude_deg * math.sin(
            2 * math.pi * self.longitudinal_frequency_hz * t
        ) + _noise(t, self.noise_deg, 0.4)
        lateral = self.lateral_amplitude_deg * math.sin(
            2 * math.pi * self.lateral_frequency_hz * t + 0.5
        ) + _noise(t, self.noise_deg, 1.1)
        return longitudinal, lateral
