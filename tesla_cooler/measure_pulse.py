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
    import typing as t
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore


PICO_CLOCK_FREQUENCY_HZ = int(1.25e8)


PulseProperties = namedtuple(
    "PulseProperties",
    [
        # The pulse's period (time from rising edge to rising edge) in Nanoseconds as a float.
        "period_ns",
        # The duration of the high side of the pulse in Nanoseconds as a float.
        "width_ns",
        # Pulse's width / pulse's period. If the period is 0, or any other divide by zero situation
        # occurs, this value will be None, otherwise it will be a float.
        "duty_cycle",
    ],
)


@asm_pio()
def pulse_properties_pio() -> None:  # pylint: disable=all
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.
    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Set the `x` scratch register to 0
    set(x, 0)  # type: ignore

    # Wait for the input `pin` to go low, then to go high.
    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    label("wait_for_low")  # type: ignore

    # Decrease the value of `x` by a single count.
    # If this value is non-zero, go to `x_decremented`.
    # If this value is zero, do nothing.
    # We never actually expect this to become zero, but we have to do a `jmp` here because it's
    # the only way to change the value of `x`.
    jmp(x_dec, "x_decremented")  # type: ignore
    label("x_decremented")  # type: ignore

    # If the `pin` is still high, loop back around to `wait_for_low`
    # This means we'll keep decrementing `x` until the pin goes low.
    # Once the `pin` goes low, we'll move onto the next instruction.
    jmp(pin, "wait_for_low")  # type: ignore

    # `pin` is now low, save the counts it was high into `y`.
    mov(y, x)  # type: ignore

    # Wait around until pin goes high again, decrementing `x` for each count it isn't high.
    label("pin_still_low")  # type: ignore
    jmp(pin, "pin_high_again")  # type: ignore
    jmp(x_dec, "pin_still_low")  # type: ignore
    label("pin_high_again")  # type: ignore

    # The `pin` has gone low for the second time.
    # `x` represents the total number of clock cycles it took to complete a period,
    # `y` represents how many clock cycles the pulse was high.

    # In order to get both of these values out to the CPU in a single `push`, we truncate
    # the counts to the first 16 bits worth of data. `in` automatically shifts data over per
    # invocation, so by the time both of these complete, the `ISR` contains a single 32 bit word
    # made up of the period and pulse width.
    in_(x, 16)  # type: ignore
    in_(y, 16)  # type: ignore

    # Push the contents of the contents of the `ISR` into the `RX FIFO`
    # Because `noblock` is used, new counts will be written to `RX FIFO` as often as pulses
    # are detected, and older pulse durations will be overwritten. This gives the CPU the ability
    # to always get the most recent reading decoupled from how often it's able to pull data.
    push(noblock)  # type: ignore

    wrap()  # type: ignore


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))


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


def measure_pulse_properties(
    data_pin: Pin, state_machine_index: int, clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ
) -> "t.Callable[[], t.Optional[PulseProperties]]":
    """
    Creates a callable to measure the length of a square-wave pulse on a GPIO pin.
    Calling the returned callable will measure the most recent pulse period/width in microseconds.

    :param data_pin: `Pin` object, represents which physical pin to read pulses from.
    :param state_machine_index: The PIO state machine index to be used to make the measurements.
    :param clock_freq_hz: The frequency to drive the state machine at. Note that this will effect
    the range of measurable frequencies. Both Period and Pulse width are sent back to the CPU from
    the state machine as 16 bit numbers, and therefore have a maximum value of 65535. If the
    pulse lasts longer than can be encoded into this 16 bit value, the result will not make any
    sense. The formula for the min/max frequency given the clock frequency is as follows:

    min_freq_hz = 1/(1/(c*2) * 65535)
    max_freq_hz = 1/(1/(c*2) * 1)

    Given c = input clock frequency in hz. By default, the fastest possible clock frequency on the
    pico is used, so this range is between ~3815 Hz - ~250 MHz. If you wanted to measure waveforms
    in the 100-500 Hz range, you could set `clock_freq_hz` to 2949075, resulting in a measurable
    range from ~90 Hz - ~5.898 MHz.

    :return: Callable that returns the pulse duration in microseconds.
    """

    clock_period_seconds = 1 / clock_freq_hz
    clock_period_microseconds = clock_period_seconds / 1e-6

    state_machine = rp2.StateMachine(
        state_machine_index, prog=pulse_properties_pio, in_base=data_pin, freq=clock_freq_hz
    )

    state_machine.active(1)

    def cycles_to_periods_ns(cycles: float) -> float:
        """
        Converts the number of clock cycles as returned by the PIO to the period elapsed in
        Nanoseconds.
        :param cycles: Number of cycles.
        :return: Period in Nanoseconds.
        """

        return cycles * clock_period_microseconds * 2

    def measure(
        timeout_us: int = 10000,
    ) -> "t.Optional[PulseProperties]":
        """
        Output Callable. Pulls all available data from the StateMachine's RX FIFO, unpacks each
        value, takes the average across each of the entries in the RX FIFO, and returns the result
        as a NamedTuple.

        :param timeout_us: If a pulse doesn't occur within this amount of time, `None` will be
        returned.
        :return: If a pulse or pulses occur, their period and pulse with are returned as a
        NamedTuple. If no pulses occur None will be returned.
        """

        words_in_fifo = fifo_count_timeout(
            fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us
        )

        if not words_in_fifo:
            return None

        packed_values = (state_machine.get() for _ in range(words_in_fifo))
        unpacked_values = (((packed >> 16) & 0xFFFF, packed & 0xFFFF) for packed in packed_values)

        # These are both in clock cycles
        periods_cs, widths_cs = map(
            lambda values: list(map(lambda value: int(0xFFFF - value), values)),
            zip(*unpacked_values),
        )

        average_period_cs = list_mean(periods_cs)
        average_width_cs = list_mean(widths_cs)

        try:
            duty_cycle = average_width_cs / average_period_cs
        except ZeroDivisionError:
            duty_cycle = None

        return PulseProperties(
            period_ns=cycles_to_periods_ns(average_period_cs),
            width_ns=cycles_to_periods_ns(average_width_cs),
            duty_cycle=duty_cycle,
        )

    return measure


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    latest_properties = measure_pulse_properties(data_pin=Pin(0, Pin.IN), state_machine_index=0)

    while True:

        print(f"Properties: {latest_properties()}")
        utime.sleep(0.1)


if __name__ == "__main__":
    main()
