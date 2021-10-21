"""
Constants related to physical fans
"""


try:
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore

MAX_DUTY = 65_025  # Per Raspberry Pi Pico Docs

FanConstants = namedtuple(
    "FanConstants",
    [
        # Should be the slowest possible pwm frequency that produces no coil whine.
        "pwm_freq",
        # Ranges of duty cycles (at `pwm_freq`) that the fan can be driven at.
        "duty_ranges",
        # When this duty cycle is applied, the fan transitions from not moving at all, to it's
        # slowest possible speed.
        "min_cold_start_duty",
        # The minimum value that the fans will actually still rotate. Not currently used.
        "min_duty",
    ],
)


# I got mine off of amazon, in the description it says that is a replacement for
# the Maglev GM1204PQV1-8A. The name of the fan that I'm using in the build is: `Twinkle Bay
# 40x28mm Cooling Fan, Replacement for Maglev Cooling Fan, 40 x 40 x 28mm with 3 Pin 3 Wire
# Connector (12V DC, 2.8 W)`.
GM1204PQV1_8A_SHORT_WIRE = FanConstants(
    pwm_freq=30_000,
    duty_ranges=(
        (4_001, 5_000),
        (5_001, 10_000),
        (10_001, 30_000),
        (30_001, 50_000),
        (50_001, 60_000),
        (60_001, MAX_DUTY),
    ),
    min_cold_start_duty=8_000,
    min_duty=3_000,
)

# TODO add note in readme and here about distinction between these two
GM1204PQV1_8A_LONG_WIRE = FanConstants(
    pwm_freq=30_000,
    duty_ranges=(  # TODO: actually measure these.
        (19_000, 35_000),  # Slowest spinning speed
        (35_001, 45_000),
        (45_001, 50_000),
        (50_001, 60_000),
        (60_001, MAX_DUTY),
    ),
    min_cold_start_duty=40_000,
    min_duty=19_000,
)
