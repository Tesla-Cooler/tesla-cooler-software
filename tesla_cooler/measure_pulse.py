"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342


    a      b      c     d
     ******       ******
     *    *       *    *
******    *********    ******


    a      b      c     d
***********       ******
          *       *    *
          *********    ******

"""

import rp2
import utime
from machine import PWM, Pin
from rp2 import PIO, asm_pio

try:
    import typing as t
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore


MAX_32_BIT_VALUE = 0xFFFFFFFF

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


@asm_pio(autopush=True)
def pulse_properties_pio() -> None:  # pylint: disable=all
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.

    TODO: cannot handle a duty cycle of O% or 100% at all.
    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Load the OSR from the CPU
    pull(block)  # type: ignore

    # Copy the value in the OSR to y
    mov(y, osr)  # type: ignore

    # Set the value in y (so the value from the OSR) as the initial value for x.
    # This is to be able to time out, not to actually count the values.
    mov(x, y)  # type: ignore

    # Pin's value is currently unknown.
    # We wait for the pin's value to be high.

    label("init_pin_low")  # type: ignore
    jmp(pin, "init_pin_high")  # type: ignore
    # TODO: needs a zero detection
    jmp(x_dec, "init_pin_low")  # type: ignore
    label("init_pin_high")  # type: ignore

    # The pin has become high, or it started out as high.

    # Reset the timeout counter to the value given by user, which is stored in `y`.
    mov(x, y)  # type: ignore

    # Wait for a falling edge.

    label("wait_for_low")  # type: ignore
    # TODO: needs a zero detection
    jmp(x_dec, "x_decremented")  # type: ignore
    label("x_decremented")  # type: ignore
    jmp(pin, "wait_for_low")  # type: ignore

    # Falling edge has occurred. Start the countdown timer.

    # Reset the timeout counter to the value given by user, which is stored in `y`.
    # Point B
    mov(x, y)  # type: ignore

    # Wait for a rising edge.

    # Wait around until pin goes high again, decrementing `x` for each count it isn't high.
    label("pin_still_low")  # type: ignore
    jmp(pin, "pin_high_again")  # type: ignore
    # TODO: needs a zero detection
    jmp(x_dec, "pin_still_low")  # type: ignore
    label("pin_high_again")  # type: ignore

    # Point C
    in_(x, 16)  # type: ignore

    # Wait for another falling edge.

    label("wait_for_low_2")  # type: ignore
    # TODO: needs a zero detection
    jmp(x_dec, "x_decremented_2")  # type: ignore
    label("x_decremented_2")  # type: ignore
    jmp(pin, "wait_for_low_2")  # type: ignore

    # Point D
    in_(x, 16)  # type: ignore

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
    data_pin: Pin,
    state_machine_index: int,
    clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ,
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
        state_machine_index,
        prog=pulse_properties_pio,
        jmp_pin=data_pin,
        freq=clock_freq_hz,
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

        timeout_pulses = (MAX_32_BIT_VALUE // 2) // 10000

        # TODO: need to convert timeout in US to pulses
        state_machine.put(timeout_pulses)

        words_in_fifo = fifo_count_timeout(
            fifo_callable=state_machine.rx_fifo, timeout_us=timeout_us
        )

        if not words_in_fifo:
            return None

        packed_value = state_machine.get()

        if packed_value == MAX_32_BIT_VALUE:
            return PulseProperties(
                period_ns=None,
                width_ns=None,
                duty_cycle=0,
            )
        elif packed_value == timeout_pulses:
            return PulseProperties(
                period_ns=None,
                width_ns=None,
                duty_cycle=1,
            )
        
        else:

            c = ((packed_value >> 16) & 0xFFFF) | (timeout_pulses & 0xFF0000)
            d = (packed_value & 0xFFFF) | (timeout_pulses & 0xFF0000)

            period_cs = timeout_pulses - d
            width_cs = c - d

            try:
                duty_cycle = width_cs / period_cs
            except ZeroDivisionError:
                duty_cycle = None

            print(
                f"Packed (hex): {hex(packed_value) if packed_value is not None else ''} // C - Int: {c}, Hex: {hex(c)}, D - Int: {d}, Hex: {hex(d)}. Duty Cycle: {duty_cycle}"
            )

            return PulseProperties(
                period_ns=cycles_to_periods_ns(period_cs),
                width_ns=cycles_to_periods_ns(width_cs),
                duty_cycle=duty_cycle,
            )

    return measure


def main_properties() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    latest_properties = measure_pulse_properties(data_pin=Pin(0, Pin.IN), state_machine_index=0)

    while True:

        print(f"Properties: {latest_properties()}")
        utime.sleep(0.1)


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    # pwm = PWM(Pin(1, Pin.OUT))  # create a PWM object on a pin
    # f_base = 100
    # pwm.duty_u16(32768)
    # pwm.freq(int(f_base))

    latest_properties = measure_pulse_properties(
        data_pin=Pin(0), state_machine_index=0
    )

    while True:

        latest_properties()


if __name__ == "__main__":
    main()
