"""
PIO/Python interface for the 16bit/rolling reads approach pulse measurement.
Note: This isn't actually used anywhere, but is kept around because it's interesting.
"""

# mypy: ignore-errors
# pylint: skip-file

from collections import namedtuple

import rp2
from rp2 import asm_pio

from tesla_cooler.read_write_pulse.read_write_pulse_common import MAX_32_BIT_VALUE, PulseProperties

try:
    import typing as t
except ImportError:
    # we're probably on the pico if this occurs.
    pass


@asm_pio(autopush=True, sideset_init=rp2.PIO.OUT_LOW)
def pulse_properties_pio_rolling_16bit() -> None:
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.
    :return: None
    """
    # pylint: disable=undefined-variable

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    # Block forever until the CPU sets the timeout count
    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    wrap_target()  # type: ignore

    pull(noblock)  # type: ignore
    mov(x, osr)  # type: ignore

    # Set the value in y (so the value from the OSR) as the initial value for x.
    # This is to be able to time out, not to actually count the values.
    mov(y, x)  # type: ignore

    # Pin's value is currently unknown.
    # We wait for the pin's value to be high.

    label("init_pin_low")  # type: ignore
    jmp(pin, "init_pin_high")  # type: ignore
    jmp(y_dec, "init_pin_low")  # type: ignore
    # If this is reached, it means we've timed out waiting for it to go high.
    # Write the 0xFFFFFFFF value to the ISR
    in_(y, 32)  # type: ignore
    jmp("write_output")  # type: ignore
    label("init_pin_high")  # type: ignore

    # The pin has become high, or it started out as high.

    # Reset the timeout counter to the value given by user, which is stored in `y`.
    mov(y, x)  # type: ignore

    # Wait for a falling edge.

    # Wait for another falling edge, pin is currently high
    label("x_decremented")  # type: ignore
    jmp(pin, "wait_for_low")  # type: ignore
    jmp("falling_edge")  # type: ignore

    label("wait_for_low")  # type: ignore
    jmp(y_dec, "x_decremented")  # type: ignore
    # If this is reached, it means we've timed out waiting for it to go low again.
    # Write the input timeout count to the ISR
    in_(x, 32)  # type: ignore
    jmp("write_output")  # type: ignore
    label("falling_edge")  # type: ignore

    # Falling edge has occurred. Start the countdown timer.
    # From here on we will actually be measuring the waveform.

    # Reset the timeout counter to the value given by user, which is stored in `y`.
    # Point B
    mov(y, x).side(1)  # type: ignore

    # Wait for a rising edge.

    # Wait around until pin goes high again, decrementing `x` for each count it isn't high.
    label("pin_still_low")  # type: ignore
    jmp(pin, "pin_high_again")  # type: ignore
    jmp(y_dec, "pin_still_low")  # type: ignore
    # If this is reached, it means we've timed out waiting for it to go high.
    # Write the 0xFFFFFFFF value to the ISR
    in_(y, 32)  # type: ignore
    jmp("write_output")  # type: ignore
    label("pin_high_again")  # type: ignore

    # Point C
    in_(y, 16)  # type: ignore

    # Wait for another falling edge, pin is currently high
    label("x_decremented_2")  # type: ignore
    jmp(pin, "wait_for_low_2")  # type: ignore
    jmp("falling_edge_2")  # type: ignore

    label("wait_for_low_2")  # type: ignore
    jmp(y_dec, "x_decremented_2")  # type: ignore
    # If this is reached, it means we've timed out waiting for it to go low again.
    # Write the input timeout count to the ISR
    in_(x, 32)  # type: ignore
    jmp("write_output")  # type: ignore
    label("falling_edge_2")  # type: ignore

    # Point D
    in_(y, 16).side(0)  # type: ignore

    label("write_output")  # type: ignore

    wrap()  # type: ignore


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))


def read_pio_rolling_16bit(
    state_machine: rp2.StateMachine,
    timeout_us: int,
    timeout_pulses: int,
    clock_period_microseconds: int,
) -> t.Optional[PulseProperties]:
    """
    Read the rx_fifo of a given state machine, convert the resulting values to c/d clock cycle
    values to eventually be converted to period/duty cycle.
    This should only be used in conjunction with PIOs running `pulse_properties_pio_rolling_16bit`.
    :param state_machine: To read.
    :param timeout_us: Amount of time in microseconds to wait for values to arrive.
    :param timeout_pulses: The timeout in clock cycles.
    :return: None if no values arrive in the `rx_fifo`, an NT containing the read result
    """

    words_in_fifo = fifo_count_timeout(fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us)

    if not words_in_fifo:
        return None

    # TODO: we can now read a bunch of values out of the rx_fifo and take the average
    packed_value = state_machine.get()

    if packed_value == MAX_32_BIT_VALUE:
        pio_read = OutputPIO(None, None, 0)
    elif packed_value == timeout_pulses:
        pio_read = OutputPIO(None, None, 1)
    else:
        # TODO: why do I have to do this mask?
        c_point_clock_cycles = ((packed_value >> 16) & 0xFFFF) | (timeout_pulses & 0xFF0000)
        d_point_clock_cycles = (packed_value & 0xFFFF) | (timeout_pulses & 0xFF0000)
        pio_read = OutputPIO(c_point_clock_cycles, d_point_clock_cycles, None)

    return convert_pio_output(
        pio_read=pio_read,
        timeout_pulses=timeout_pulses,
        clock_period_microseconds=clock_period_microseconds,
        cycles_per_read=2,
    )


OutputPIO = namedtuple(
    "OutputPIO",
    [
        # These two values represent the number of clock cycles it took to reach the point in the
        # waveform as labeled by the comment at the top of the document.
        "c_clock_cycles",
        "d_clock_cycles",
        # If the PIO detects either a 100% duty cycle waveform, or a 0% duty cycle waveform, there
        # can be no valid values for c/d clock cycles. If either of these cases, this field will
        # be set to 1/0 respectively (w/ the other two  field set to None), otherwise None.
        "duty_cycle_override",
    ],
)


def cycles_to_periods_us(cycles: float, clock_period_microseconds: int) -> float:
    """
    Converts the number of clock cycles as returned by the PIO to the period elapsed in
    microseconds. We multiply the output by 2 because it takes two clock cycles to decrement
    the counter, and then `jmp` based on the pin's value.
    :param cycles: Number of cycles.
    :return: Period in microseconds.
    """

    return cycles * clock_period_microseconds


def convert_pio_output(
    pio_read: OutputPIO, timeout_pulses: int, clock_period_microseconds: int, cycles_per_read: int
) -> PulseProperties:
    """

    :param pio_read:
    :param timeout_pulses:
    :param clock_period_microseconds:
    :param cycles_per_read:
    :return:
    """

    if pio_read.duty_cycle_override is not None:
        return PulseProperties(
            period_us=None,
            width_us=None,
            duty_cycle=pio_read.duty_cycle_override,
            c_cs=pio_read.c_clock_cycles,
            d_cs=pio_read.d_clock_cycles,
        )

    period_cs = timeout_pulses - pio_read.d_clock_cycles
    width_cs = pio_read.c_clock_cycles - pio_read.d_clock_cycles

    try:
        duty_cycle = width_cs / period_cs
    except ZeroDivisionError:
        duty_cycle = None

    return PulseProperties(
        period_us=cycles_to_periods_us(
            cycles=period_cs,
            clock_period_microseconds=clock_period_microseconds,
            cycles_per_read=cycles_per_read,
        ),
        width_us=cycles_to_periods_us(
            cycles=width_cs,
            clock_period_microseconds=clock_period_microseconds,
            cycles_per_read=cycles_per_read,
        ),
        duty_cycle=duty_cycle,
        c_cs=pio_read.c_clock_cycles,
        d_cs=pio_read.d_clock_cycles,
    )


def fifo_count_timeout(
    fifo_callable: "t.Callable[[], int]", timeout_us: int, min_count: int = 0
) -> int:
    """
    Continuously calls `fifo_callable` until it reports there are values in the queue.
    If no values become available within `timeout_us`, 0 is returned.

    :param fifo_callable: Either `rp2.StateMachine.rx_fifo` or `rp2.StateMachine.tx_fifo`, or
    some other function wrapping those two.
    :param min_count: Blocks until this many bytes are ready to be read off of the pio.
    :param timeout_us: Amount of time in microseconds to wait for values to arrive.
    :return: The value returned by the callable, 0 if nothing arrives.
    """

    start = utime.ticks_us()

    while True:

        if utime.ticks_us() - start > timeout_us:
            return 0

        output = fifo_callable()
        if output >= min_count:
            return output

    return 0
