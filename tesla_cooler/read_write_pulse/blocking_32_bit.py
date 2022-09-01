"""
PIO/Python interface for the 32bit/blocking reads approach pulse measurement.
"""


import rp2
from rp2 import asm_pio

from tesla_cooler.read_write_pulse.pulse_common import (
    MAX_32_BIT_VALUE,
    OutputPIO,
    fifo_count_timeout,
)

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    # we're probably on the pico if this occurs.
    pass


@asm_pio(sideset_init=rp2.PIO.OUT_LOW)
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
    mov(y, x)  # type: ignore

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
    in_(y, 32)  # type: ignore
    push(block)  # type: ignore

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
    in_(y, 32)  # type: ignore

    label("write_output")  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def read_pio_blocking_32bit(
    state_machine: rp2.StateMachine, timeout_us: int, timeout_pulses: int
) -> "t.Optional[OutputPIO]":
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

    output: "t.List[t.Optional[int]]" = []

    for _ in range(2):

        value = state_machine.get()

        if value == MAX_32_BIT_VALUE:
            return OutputPIO(None, None, 0)
        elif value == timeout_pulses:
            return OutputPIO(None, None, 1)

        output.append(value)

    return OutputPIO(*list(output + [None]))
