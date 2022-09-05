"""
Uses a PIO state machine to characterize an input square wave, resulting in the frequency,
pulse width and duty cycle.

This approach is synchronous meaning the pulses are only measured on-demand, and the caller must
block while the waveform is measured.

TODO: Needs timeouts w/ duty cycle override
"""

import rp2
from rp2 import asm_pio

from tesla_cooler.read_write_pulse.read_write_pulse_common import MAX_32_BIT_VALUE, PulseProperties

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


@asm_pio()
def synchronous_measure_pulse_pio() -> None:
    """
    Measures the duration of the high pulse, stores this in `x`, measures the duration of the low
    side of the square wave, stores this in `y`. These values are then pushed out in two successive
    `push` operations.

    Note that it takes two clock cycles to detect the wave initially going low, and then 3 for it
    going high again. This is handled in the python side of the program, but getting the true
    system clock counts needs a multiple of 2,3 respectively.
    :return: None
    """
    # pylint: disable=undefined-variable

    wrap_target()  # type: ignore

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore
    mov(y, x)  # type: ignore

    # `pin` state currently unknown

    # Wait for a falling edge, or discover pin is already low. ~3 cycles per loop.
    label("init pin check")  # type: ignore
    jmp(pin, "init decrement")  # type: ignore
    jmp("init low found")  # type: ignore
    label("init decrement")  # type: ignore
    jmp(x_dec, "init pin check")  # type: ignore
    label("init low found")  # type: ignore
    mov(x, y)  # type: ignore

    # Wait for a rising edge. ~2 cycles per loop.
    label("init high check")  # type: ignore
    jmp(pin, "init high found")  # type: ignore
    jmp(x_dec, "init high check")  # type: ignore
    label("init high found")  # type: ignore
    mov(x, y)  # type: ignore

    # Wait for a falling edge. ~2 cycles per loop.
    label("decrement")  # type: ignore
    jmp(x_dec, "decremented")  # type: ignore
    jmp("never low")  # type: ignore
    label("decremented")  # type: ignore
    jmp(pin, "decrement")  # type: ignore
    label("never low")  # type: ignore

    # Wait for another rising edge. ~3 cycles per loop.
    label("still low")  # type: ignore
    jmp(y_dec, "pin check")  # type: ignore
    jmp("high found")  # type: ignore
    label("pin check")  # type: ignore
    jmp(pin, "high found")  # type: ignore
    jmp("still low")  # type: ignore
    label("high found")  # type: ignore

    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    in_(y, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def read_synchronous_measure_pulse_pio(
    state_machine: rp2.StateMachine,
    timeout_seconds: "t.Union[int, float]",
    clock_period: "t.Union[int, float]",
) -> PulseProperties:
    """

    TODO: need to get cute there with comprehensions.
    :param state_machine:
    :param timeout_seconds:
    :param clock_period:
    :return:
    """

    # The `5` here comes from the max amount of loops it could take to get through the PIO
    # in the 100%/0% duty cycle cases. In both cases, blocking completely on side of the
    # measurement always sums to 5 cycles per loop.
    timeout_pulses = int((timeout_seconds // clock_period) // 5)

    state_machine.put(timeout_pulses)

    a_raw = state_machine.get()
    b_raw = state_machine.get()

    if (a_raw == MAX_32_BIT_VALUE) and (b_raw == timeout_pulses - 1):
        return PulseProperties(frequency=None, pulse_width=None, duty_cycle=1)
    elif (b_raw == MAX_32_BIT_VALUE) and (a_raw == timeout_pulses - 1):
        return PulseProperties(frequency=None, pulse_width=None, duty_cycle=0)
    else:
        a_unpacked = (timeout_pulses - a_raw) * 2
        b_unpacked = (timeout_pulses - b_raw) * 3
        total_clock_cycles = a_unpacked + b_unpacked
        total_period = total_clock_cycles * clock_period
        return PulseProperties(
            frequency=(1 / total_period),
            pulse_width=a_unpacked * clock_period,
            duty_cycle=a_unpacked / total_clock_cycles,
        )
