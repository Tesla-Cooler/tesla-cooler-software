"""
Common constants and data types used across approaches of pulse reading.
"""

from collections import namedtuple

MAX_32_BIT_VALUE = 0xFFFFFFFF

PulseProperties = namedtuple(
    "PulseProperties",
    [
        "frequency",
        "pulse_width",
        "duty_cycle",
    ],
)
