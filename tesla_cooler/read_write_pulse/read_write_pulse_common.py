"""
Common constants and data types used across approaches of pulse reading.
"""

from collections import namedtuple

MAX_32_BIT_VALUE = 0xFFFFFFFF

PulseProperties = namedtuple(
    "PulseProperties",
    [
        # The frequency of the input waveform in Hertz.
        # Will be set to `None` in the 0/1 duty cycle cases.
        "frequency",
        # The amount of time in seconds the input waveform is high.
        # Will be set to `None` in the 0/1 duty cycle cases.
        "pulse_width",
        # The ratio of pulse high to pulse low.
        # If the waveform is always high, this value will be set to 1.
        # If the waveform is always low, this value will be set to 0.
        "duty_cycle",
    ],
)

SquareWaveController = namedtuple(
    "SquareWaveController",
    [
        # Function that takes the frequency in HZ to drive the output square wave at.
        "set_frequency_hz",
        # Callable, starts creating waves if they're not being created already.
        "enable",
        # Callable, stops creating waves. Pin will be set high once disabled.
        "disable",
    ],
)
