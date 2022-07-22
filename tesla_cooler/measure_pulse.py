"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342
"""

import rp2
import utime
from machine import Pin, mem32
from rp2 import PIO, asm_pio

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


PICO_CLOCK_FREQUENCY = 1.25e8
PICO_CLOCK_PERIOD_SECONDS = 1 / PICO_CLOCK_FREQUENCY
PICO_CLOCK_PERIOD_MICROSECONDS = PICO_CLOCK_PERIOD_SECONDS / 1e-6


@asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def pulse_length_pio() -> None:  # pylint: disable=all
    """
    PIO program to read pulse length.

    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Set the x scratch register to 0
    set(x, 0)  # type: ignore

    # Wait for the input pin to go low, then to go high.
    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    label("wait_for_low")  # type: ignore

    # Decrease the value of x by a single count.
    # If this value is non-zero, go to the loop 2 label.
    # If this value is zero, do nothing.
    jmp(x_dec, "x_decremented").side(1)  # type: ignore
    label("x_decremented")  # type: ignore

    # If the pin is still high, loop back around to loop1
    # This means we'll keep counting down x until the pin goes low.
    # Once the pin goes low, we'll move onto the next instruction.
    jmp(pin, "wait_for_low").side(0)  # type: ignore

    # The pin has gone low, and x represents how many clock cycles it took to complete.
    # Push the current value of x onto the input shift register.
    # The input shift register is connected to the RX FIFO, so this value will be transferred
    # out from the state machine to the CPU.
    mov(isr, x)  # type: ignore

    # Push the contents of the contents of the ISR into the RX FIFO
    # Because `noblock` is used, new counts will be written to RX FIFO as often as pulses
    # are detected, and older pulse durations will be overwritten.
    push(noblock)  # type: ignore

    wrap()  # type: ignore


def fifo_count_timeout(fifo_callable: "t.Callable[[], int]", timeout_us: int) -> int:
    """
    Continuously calls `fifo_callable` until it reports there are values in the queue.
    If no values become available within `timeout_us`, 0 is returned.

    :param fifo_callable: Either `rp2.StateMachine.rx_fifo` or `rp2.StateMachine.tx_fifo`, or
    some other function wrapping those two.
    :param timeout_us: Amount of time in microseconds to wait for values to arrive.
    :return: The value returned by the callable, 0 if nothing arrives.
    """

    start = utime.ticks_us()

    while True:

        if utime.ticks_us() - start > timeout_us:
            return 0

        output = fifo_callable()
        if output:
            return output


def measure_pulse_duration(
    data_pin: Pin, counter_pin: Pin, state_machine_index: int = 0
) -> "t.Callable[[], t.Optional[float]]":
    """
    Creates a callable to measure the length of a square-wave pulse on a GPIO pin.
    Calling the returned callable will measure the most recent pulse duration in microseconds.

    :param data_pin: Index of pin attached to the pulse source.
    :param counter_pin: Index of pin attached to the pulse source.
    :param state_machine_index: The PIO state machine index to be used to make the measurements.
    :return: Callable that returns the pulse duration in microseconds.
    """

    state_machine = rp2.StateMachine(
        state_machine_index, pulse_length_pio, in_base=data_pin, sideset_base=counter_pin
    )

    state_machine.active(1)

    def measure(timeout_us: int = 10000) -> "t.Optional[float]":  # pylint: disable=unused-argument
        """
        Output Callable.

        :param timeout_us: If a pulse doesn't occur within this amount of time, `None` will be
        returned.
        :return: The pulse duration if a pulse occurs, `None` if otherwise.
        """

        words_in_fifo = fifo_count_timeout(
            fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us
        )

        if not words_in_fifo:
            return None

        inverted_counts = (state_machine.get() for _ in range(words_in_fifo))
        high_cycle_counts = list(map(lambda value: int(0xFFFFFFFF - value), inverted_counts))
        average_counts = sum(high_cycle_counts) / len(high_cycle_counts)

        return float((average_counts * 2) * PICO_CLOCK_PERIOD_MICROSECONDS)

    return measure


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    read_pulse = measure_pulse_duration(data_pin=Pin(0, Pin.IN), counter_pin=Pin(1, Pin.OUT))

    while True:
        print(f"High side pulse of: {read_pulse()} microseconds detected.")


if __name__ == "__main__":
    main()
