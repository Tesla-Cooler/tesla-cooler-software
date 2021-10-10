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
        "pwm_freq",  # Should be the slowest possible pwm frequency that produces no coil whine.
        "duty_ranges",  # Ranges of duty cycles (at `pwm_freq`) that the fan can be driven at.
    ],
)


# I got mine off of amazon, in the description it says that is a replacement for
# the Maglev GM1204PQV1-8A. The name of the fan that I'm using in the build is: `Twinkle Bay
# 40x28mm Cooling Fan, Replacement for Maglev Cooling Fan, 40 x 40 x 28mm with 3 Pin 3 Wire
# onnector (12V DC, 2.8 W)`.
GM1204PQV1_8A = FanConstants(
    pwm_freq=30_000,
    duty_ranges=(  # TODO: actually measure these.
        (1000, 20_000),  # Makes no noise.
        (20_001, 30_000),
        (30_001, 40_000),  # Makes some noise.
        (40_001, 50_000),  # Makes a lot of noise.
        (50_001, 60_000),  # Makes a lot of noise.
        (60_001, MAX_DUTY),
    ),
)
