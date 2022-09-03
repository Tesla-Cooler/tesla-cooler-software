"""
PIO/Python interface for the 32bit/blocking reads approach pulse measurement.
"""


import rp2
from rp2 import asm_pio

from tesla_cooler.read_write_pulse.pulse_common import (
    MAX_32_BIT_VALUE,
    OutputPIO,
    PulseProperties,
    fifo_count_timeout, convert_pio_output, cycles_to_periods_us
)

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    # we're probably on the pico if this occurs.
    pass


@asm_pio(sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def pulse_properties_pio_blocking_32bit() -> None:
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.
    :return: None
    """
    # pylint: disable=undefined-variable

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Block forever until the CPU sets the timeout count
    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    # Pin's value is currently unknown.
    # We wait for the pin's value to be high.

    wait(1, pin, 0).side(0b00)  # pin 0 goes high when the input signal goes high for the first time
    wait(0, pin, 0).side(0b01)

    # Falling edge has occurred. Start the countdown timer.
    # From here on we will actually be measuring the waveform.

    # Wait for a rising edge.
    # Wait around until pin goes high again, decrementing `x` for each count it isn't high.
    label("pin_still_low")  # type: ignore
    jmp(pin, "pin_high_again")  # type: ignore
    jmp(x_dec, "pin_still_low")  # type: ignore
    label("pin_high_again")  # type: ignore

    # Point C
    in_(x, 32).side(0b11)  # type: ignore
    push(noblock)  # type: ignore

    # Wait for another falling edge, pin is currently high
    label("dec")
    jmp(x_dec, "check_pin_high")
    label("check_pin_high")
    jmp(pin, "dec")

    # Point D
    in_(x, 32).side(0b00)  # type: ignore
    push(noblock)  # type: ignore

    wrap()  # type: ignore


def read_pio_blocking_32bit(
    state_machine: rp2.StateMachine, timeout_us: int, timeout_pulses: int, clock_period_microseconds: int,
) -> "t.Optional[PulseProperties]":
    """
    Read the rx_fifo of a given state machine, convert the resulting values to c/d clock cycle
    values to eventually be converted to period/duty cycle.
    This should only be used in conjunction with PIOs running `pulse_properties_pio_blocking_32bit`.
    :param state_machine: To read.
    :param timeout_us: Amount of time in microseconds to wait for values to arrive.
    :param timeout_pulses: The timeout in clock cycles.
    :return: None if no values arrive in the `rx_fifo`, an NT containing the read result
    """

    words_in_fifo = fifo_count_timeout(fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us)

    if not words_in_fifo:
        return None

    def read_pio() -> OutputPIO:
        """

        :return:
        """

        output: "t.List[t.Optional[int]]" = []

        for _ in range(2):

            value = state_machine.get()

            if value == MAX_32_BIT_VALUE:
                return OutputPIO(None, None, 0)
            elif value == timeout_pulses:
                return OutputPIO(None, None, 1)

            output.append(value)

        return OutputPIO(*list(output + [None]))

    pio_read = read_pio()

    if pio_read.duty_cycle_override is not None:
        return PulseProperties(
            period_us=None,
            width_us=None,
            duty_cycle=pio_read.duty_cycle_override,
            c_cs=pio_read.c_clock_cycles,
            d_cs=pio_read.d_clock_cycles,
        )

    c_cs = pio_read.c_clock_cycles
    d_cs = pio_read.d_clock_cycles

    period_cs = timeout_pulses - d_cs
    width_cs = c_cs - d_cs

    try:
        duty_cycle = width_cs / period_cs
    except ZeroDivisionError:
        duty_cycle = None

    return PulseProperties(
        period_us=cycles_to_periods_us(
            cycles=period_cs,
            clock_period_microseconds=clock_period_microseconds,
            cycles_per_read=2,
        ),
        width_us=cycles_to_periods_us(
            cycles=width_cs,
            clock_period_microseconds=clock_period_microseconds,
            cycles_per_read=2,
        ),
        duty_cycle=duty_cycle,
        c_cs=c_cs,
        d_cs=d_cs,
    )