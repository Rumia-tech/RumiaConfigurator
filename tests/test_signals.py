"""Measurement signals of the simulated products."""

import math

from rumia_configurator.core.simulator.signals import (
    INT16_MAX,
    INT16_MIN,
    ImuMotion,
    InclinationMotion,
    clamp_int16,
)

TIMES = [i * 0.37 for i in range(400)]  # about 150 s, several slow periods


def test_signals_are_repeatable() -> None:
    assert ImuMotion().sample(12.3) == ImuMotion().sample(12.3)
    assert InclinationMotion().sample(4.2) == InclinationMotion().sample(4.2)


def test_accelerometer_sees_about_one_g() -> None:
    for t in TIMES:
        s = ImuMotion().sample(t)
        magnitude = math.sqrt(s.acc_x**2 + s.acc_y**2 + s.acc_z**2)
        assert 950 < magnitude < 1050, t


def test_gyroscope_follows_the_tilt() -> None:
    motion = ImuMotion(gyro_noise_mdps=0, acc_noise_mg=0, vibration_mg=0)
    # Pitch rate is maximum and positive at t = 0: acc_x (= -g sin pitch) is decreasing.
    assert motion.sample(0).gyro_y > 4000
    assert motion.sample(1).acc_x < motion.sample(0).acc_x


def test_inclination_stays_in_its_amplitude() -> None:
    motion = InclinationMotion()
    for t in TIMES:
        longitudinal, lateral = motion.sample(t)
        assert abs(longitudinal) <= motion.longitudinal_amplitude_deg + motion.noise_deg
        assert abs(lateral) <= motion.lateral_amplitude_deg + motion.noise_deg


def test_clamp_int16() -> None:
    assert clamp_int16(1.6) == 2
    assert clamp_int16(1e9) == INT16_MAX
    assert clamp_int16(-1e9) == INT16_MIN
