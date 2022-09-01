import rp2
from rp2 import asm_pio

try:
    import typing as t
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore

from tesla_cooler.read_write_pulse.pulse_common import (
    MAX_32_BIT_VALUE,
    OutputPIO,
    fifo_count_timeout,
)


@asm_pio(autopush=True, sideset_init=rp2.PIO.OUT_LOW)
def pulse_properties_pio_rolling_16bit() -> None:  # pylint: disable=all
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.
    :return: None
    """

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


def read_pio_rolling_16bit(
    state_machine: rp2.StateMachine, timeout_us: int, timeout_pulses: int
) -> t.Optional[OutputPIO]:
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
        output = None, None, 0
    elif packed_value == timeout_pulses:
        output = None, None, 1
    else:

        # TODO: why do I have to do this mask?
        c_point_clock_cycles = ((packed_value >> 16) & 0xFFFF) | (timeout_pulses & 0xFF0000) - 2
        d_point_clock_cycles = (packed_value & 0xFFFF) | (timeout_pulses & 0xFF0000)

        output = c_point_clock_cycles, d_point_clock_cycles, None

    return OutputPIO(*output)


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))
