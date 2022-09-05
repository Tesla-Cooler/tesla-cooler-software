"""
Uses a PIO state machine to characterize an input square wave, resulting in the frequency,
pulse width and duty cycle.

This approach is synchronous meaning the pulses are only measured on-demand, and the caller must
block while the waveform is measured.

The following represents the different parts of a square waveform that are measured with this
program.

              ----- Timer starts here.
             |
             |
1  ******    ******    ******
        *    ^    *    ^    *
0       ******    ******    ******
t       a    b    c    d


              ----- Timer starts here.
             |
             |
1            ******    ******
             ^    *    ^    *
0 ************    ******    ******
t       a    b    c    d
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

    # Point 'a'.
    # Wait for a rising edge. ~2 cycles per loop.
    label("init high check")  # type: ignore
    jmp(pin, "init high found")  # type: ignore
    jmp(x_dec, "init high check")  # type: ignore
    label("init high found")  # type: ignore
    mov(x, y)  # type: ignore

    # Point 'b'.
    # Wait for a falling edge. ~2 cycles per loop.
    label("decrement")  # type: ignore
    jmp(x_dec, "decremented")  # type: ignore
    jmp("never low")  # type: ignore
    label("decremented")  # type: ignore
    jmp(pin, "decrement")  # type: ignore
    label("never low")  # type: ignore

    # Point 'c'.
    # Wait for another rising edge. ~3 cycles per loop.
    label("still low")  # type: ignore
    jmp(y_dec, "pin check")  # type: ignore
    jmp("high found")  # type: ignore
    label("pin check")  # type: ignore
    jmp(pin, "high found")  # type: ignore
    jmp("still low")  # type: ignore
    label("high found")  # type: ignore
    # Point 'd'.

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
    Sends the timeout in clock cycles into the state machine, and waits for the two reply bytes.
    Converts these response into the wave properties, and returns the result to user.
    :param state_machine: The `rp2.StateMachine` running the `synchronous_measure_pulse_pio` program
    this function assumes that the SM is running.
    :param timeout_seconds: The amount of time in seconds to wait for a wave to complete two cycles.
    Internally, the PIO reads the waveform ~2 times, so the timeout must be long enough to cover
    this whole operation. For example, you're reading waveforms at 1 Hz, you'll want to set the
    timeout to >2s. Experimentally, doubling the expected period is a safe bet, so for reading a
    1 Hz square wave, a safe timeout would be three seconds.
    :param clock_period:
    :return: The Pulse's Properties as a NamedTuple. Contains frequency, period and duty cycle.
    """

    # The `5` here comes from the max amount of loops it could take to get through the PIO
    # in the 100%/0% duty cycle cases. In both cases, blocking completely on side of the
    # measurement always sums to 5 cycles per loop.
    timeout_pulses = int((timeout_seconds // clock_period) // 5)

    state_machine.put(timeout_pulses)

    c_raw = state_machine.get()
    d_raw = state_machine.get()

    if (c_raw == MAX_32_BIT_VALUE) and (d_raw == timeout_pulses - 1):
        return PulseProperties(frequency=None, pulse_width=None, duty_cycle=1)
    elif (d_raw == MAX_32_BIT_VALUE) and (c_raw == timeout_pulses - 1):
        return PulseProperties(frequency=None, pulse_width=None, duty_cycle=0)
    else:
        c_unpacked = (timeout_pulses - c_raw) * 2
        d_unpacked = (timeout_pulses - d_raw) * 3
        total_clock_cycles = c_unpacked + d_unpacked
        total_period = total_clock_cycles * clock_period
        return PulseProperties(
            frequency=(1 / total_period),
            pulse_width=c_unpacked * clock_period,
            duty_cycle=c_unpacked / total_clock_cycles,
        )
