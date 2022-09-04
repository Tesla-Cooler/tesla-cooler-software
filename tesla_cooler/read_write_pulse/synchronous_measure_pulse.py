"""
Uses a PIO state machine to characterize an input square wave, resulting in the frequency,
pulse width and duty cycle.

This approach is synchronous meaning the pulses are only measured on-demand, and the caller must
block while the waveform is measured.
"""

import rp2
from rp2 import asm_pio

from tesla_cooler.read_write_pulse.read_write_pulse_common import PulseProperties

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    # we're probably on the pico if this occurs.
    pass


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

    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    # Wait for a falling edge.
    label("decrement")  # type: ignore
    jmp(x_dec, "decremented")  # type: ignore
    label("decremented")  # type: ignore
    jmp(pin, "decrement")  # type: ignore

    # Wait for another rising edge.
    label("still low")  # type: ignore
    jmp(y_dec, "pin check")  # type: ignore
    label("pin check")  # type: ignore
    jmp(pin, "high found")  # type: ignore
    jmp("still low")  # type: ignore
    label("high found")  # type: ignore

    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    in_(y, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))


def read_synchronous_measure_pulse_pio(
    state_machine: rp2.StateMachine, timeout_pulses: int, clock_period: float
) -> PulseProperties:
    """

    TODO: need to get cute there with comprehensions.
    :param state_machine:
    :param timeout_pulses:
    :param clock_period:
    :return:
    """

    a_readings = []
    b_readings = []

    for _ in range(10):
        state_machine.put(timeout_pulses)
        a_readings.append((timeout_pulses - state_machine.get()) * 2)
        b_readings.append((timeout_pulses - state_machine.get()) * 3)

    a_average = list_mean(a_readings)
    b_average = list_mean(b_readings)

    total_clock_cycles = a_average + b_average
    total_period = total_clock_cycles * clock_period

    return PulseProperties(
        frequency=(1 / total_period),
        pulse_width=a_average * clock_period,
        duty_cycle=a_average / total_clock_cycles,
    )
