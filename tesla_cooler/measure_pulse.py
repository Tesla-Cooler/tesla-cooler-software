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


PICO_CLOCK_FREQUENCY_HZ = 1.25e8
PICO_CLOCK_PERIOD_SECONDS = 1 / PICO_CLOCK_FREQUENCY_HZ
PICO_CLOCK_PERIOD_MICROSECONDS = PICO_CLOCK_PERIOD_SECONDS / 1e-6


@asm_pio(sideset_init=(rp2.PIO.OUT_LOW))
def pulse_properties_pio() -> None:  # pylint: disable=all
    """
    PIO program to read pulse length.

    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Set the x scratch register to 0
    set(x, 0)  # type: ignore
    set(y, 0)  # type: ignore

    # Wait for the input pin to go low, then to go high.
    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    label("wait_for_low")  # type: ignore

    # Decrease the value of x by a single count.
    # If this value is non-zero, go to the loop x_decremented.
    # If this value is zero, do nothing.
    # We never actually expect this to become zero, but we have to do a `jmp` here because it's
    # the only way to change the value of x.
    jmp(x_dec, "x_decremented").side(1)  # type: ignore
    label("x_decremented")  # type: ignore

    # If the pin is still high, loop back around to wait_for_low
    # This means we'll keep counting down x until the pin goes low.
    # Once the pin goes low, we'll move onto the next instruction.
    jmp(pin, "wait_for_low").side(0)  # type: ignore

    # Pin is now low, we need to wait for it to go high again

    label("pin_still_low")  # type: ignore

    jmp(pin, "pin_high_again")  # type: ignore

    jmp(y_dec, "y_decrement")  # type: ignore
    label("y_decrement")  # type: ignore

    jmp("pin_still_low")  # type: ignore

    label("pin_high_again")  # type: ignore

    # The pin has gone low, and x represents how many clock cycles it took to complete.
    # Push the current value of x onto the input shift register.
    # The input shift register is connected to the RX FIFO, so this value will be transferred
    # out from the state machine to the CPU.
    mov(isr, x)  # type: ignore

    # Push the contents of the contents of the ISR into the RX FIFO
    # Because `noblock` is used, new counts will be written to RX FIFO as often as pulses
    # are detected, and older pulse durations will be overwritten.
    push()  # type: ignore

    mov(isr, y)
    push()

    wrap()  # type: ignore


@asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def wavelength_pio() -> None:  # pylint: disable=all
    """
    PIO program to read pulse length.

    Records the amount of time between rising edges

    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Set the x scratch register to 0
    set(x, 0)  # type: ignore
    set(y, 0)  # type: ignore

    # Wait for the input pin to go high.
    wait(1, pin, 0).side(1)  # type: ignore

    label("wait_for_low")  # type: ignore

    jmp(x_dec, "x_decremented_1")  # type: ignore
    label("x_decremented_1")  # type: ignore

    jmp(pin, "wait_for_low") # type: ignore

    # Pin is now low, we need to wait for it to go high again

    label("pin_still_low")  # type: ignore

    jmp(pin, "pin_high_again")  # type: ignore
    jmp(x_dec, "pin_still_low")  # type: ignore

    label("pin_high_again")  # type: ignore

    # The pin has gone high again, and x represents how many clock cycles it took to complete.
    # Push the current value of x onto the input shift register.
    # The input shift register is connected to the RX FIFO, so this value will be transferred
    # out from the state machine to the CPU.
    mov(isr, x).side(0)  # type: ignore

    # Push the contents of the contents of the ISR into the RX FIFO
    # Because `noblock` is used, new counts will be written to RX FIFO as often as pulses
    # are detected, and older pulse durations will be overwritten.
    push(noblock)  # type: ignore

    wrap()  # type: ignore


def fifo_count_timeout(fifo_callable: "t.Callable[[], int]", timeout_us: int, min_values: int = 1) -> int:
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
        if output >= min_values:
            return output


def measure_pulse_properties(
    data_pin: Pin, counter_pin: Pin, state_machine_index: int
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
        state_machine_index, pulse_properties_pio, in_base=data_pin, sideset_base=counter_pin
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
            fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us, min_values=2
        )

        if not words_in_fifo:
            return None

        high_time = 0xFFFFFFFF - state_machine.get()
        low_time = 0xFFFFFFFF - state_machine.get()

        return high_time, low_time, high_time + low_time

    return measure


def measure_wavelength(
    data_pin: Pin, counter_pin: Pin, state_machine_index: int
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
        state_machine_index, wavelength_pio, in_base=data_pin, sideset_base=counter_pin
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

        return float((int(0xFFFFFFFF - state_machine.get()) * 2) * PICO_CLOCK_PERIOD_MICROSECONDS)

    return measure


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    read_wavelength = measure_pulse_properties(data_pin=Pin(0, Pin.IN), counter_pin=Pin(1, Pin.OUT), state_machine_index=0)
    # read_pulse = measure_pulse_duration(data_pin=Pin(0, Pin.IN), counter_pin=Pin(1, Pin.OUT), state_machine_index=1)

    while True:

        wavelength = read_wavelength()
        # pulse = read_pulse()

        print(f"Value: {wavelength}")
        # print(f"High side pulse of: {pulse} microseconds detected.")

        # print(f"Duty Cycle: {((pulse/wavelength) * 100)}%")

        utime.sleep(0.1)


if __name__ == "__main__":
    main()
