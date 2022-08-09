"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342

The following represents the different parts of a square waveform that are measured with this
program. Note that the 'timer' always starts at point 'b', because we only measure one pulse at a
time.

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
from machine import PWM, Pin, Timer, mem32
from rp2 import PIO, asm_pio

try:
    import typing as t
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore


MAX_32_BIT_VALUE = 0xFFFFFFFF

PICO_CLOCK_FREQUENCY_HZ = int(1.25e8)

_PIO0_BASE = 0x50200000
_INPUT_SYNC_BYPASS_OFFSET = 0x038
INPUT_SYNC_ENABLE_ADDRESS = _PIO0_BASE | _INPUT_SYNC_BYPASS_OFFSET

PulseProperties = namedtuple(
    "PulseProperties",
    [
        # The pulse's period (time from rising edge to rising edge) in microseconds as a float.
        "period_us",
        # The duration of the high side of the pulse in microseconds as a float.
        "width_us",
        # Pulse's width / pulse's period. If the period is 0, or any other divide by zero situation
        # occurs, this value will be None, otherwise it will be a float.
        "duty_cycle",
        # C-Point Clock Cycles, consumed by debugging and will be removed.
        "c_cs",
        # D-Point Clock Cycles, consumed by debugging and will be removed.
        "d_cs",
    ],
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


def pprint_pulse_properties(pulse_properties: PulseProperties) -> str:
    """

    :param pulse_properties:
    :return:
    """

    period_seconds = pulse_properties.period_us * 1 * 10e-7
    frequency_khz = (1 / period_seconds) * 0.001

    return f"C-CS: {hex(pulse_properties.c_cs)}, D-CS: {hex(pulse_properties.d_cs)}, Period (us): {'{:.10f}'.format(pulse_properties.period_us)}, Frequency (kHz): {'{:.10f}'.format(frequency_khz)}, Duty Cycle: {'{:.10f}'.format(pulse_properties.duty_cycle)}%"


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


@asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def pulse_properties_pio_blocking_32bit() -> None:  # pylint: disable=all
    """
    PIO program to measure pulse width and period.
    Width and period are truncated to 16 bits, packed into RX FIFO, and shifted out in a single
    operation.
    :return: None
    """

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


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))


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
        c_point_clock_cycles = ((packed_value >> 16) & 0xFFFF) | (timeout_pulses & 0xFF0000)
        d_point_clock_cycles = (packed_value & 0xFFFF) | (timeout_pulses & 0xFF0000)

        output = c_point_clock_cycles, d_point_clock_cycles, None

    return OutputPIO(*output)


def read_pio_blocking_32bit(
    state_machine: rp2.StateMachine, timeout_us: int, timeout_pulses: int
) -> t.Optional[OutputPIO]:
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


def measure_pulse_properties(
    data_pin: Pin,
    state_machine_index: int,
    clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ,
    rolling_average_approach: bool = False,
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

    mem32[INPUT_SYNC_ENABLE_ADDRESS] = 0

    clock_period_seconds = 1 / clock_freq_hz
    clock_period_microseconds = clock_period_seconds / 1e-6

    prog, pio_read_function = (
        (pulse_properties_pio_rolling_16bit, read_pio_rolling_16bit)
        if rolling_average_approach
        else (pulse_properties_pio_blocking_32bit, read_pio_blocking_32bit)
    )

    state_machine = rp2.StateMachine(
        state_machine_index,
        prog=prog,
        jmp_pin=data_pin,
        sideset_base=Pin(2),
        freq=clock_freq_hz,
    )

    state_machine.active(1)

    def cycles_to_periods_us(cycles: float) -> float:
        """
        Converts the number of clock cycles as returned by the PIO to the period elapsed in
        microseconds. We multiply the output by 2 because it takes two clock cycles to decrement
        the counter, and then `jmp` based on the pin's value.
        :param cycles: Number of cycles.
        :return: Period in microseconds.
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

        pio_read = pio_read_function(
            state_machine=state_machine, timeout_us=timeout_us, timeout_pulses=timeout_pulses
        )

        if pio_read is None:
            return None

        c_cs, d_cs, duty_cycle_override = pio_read

        if duty_cycle_override is not None:
            return PulseProperties(
                period_us=None,
                width_us=None,
                duty_cycle=duty_cycle_override,
                c_cs=c_cs,
                d_cs=d_cs,
            )

        period_cs = timeout_pulses - d_cs
        width_cs = c_cs - d_cs

        try:
            duty_cycle = width_cs / period_cs
        except ZeroDivisionError:
            duty_cycle = None

        return PulseProperties(
            period_us=cycles_to_periods_us(period_cs),
            width_us=cycles_to_periods_us(width_cs),
            duty_cycle=duty_cycle,
            c_cs=c_cs,
            d_cs=d_cs,
        )

    return measure


@asm_pio(set_init=(PIO.OUT_LOW,), fifo_join=PIO.JOIN_TX)
def slow_square_pio() -> None:  # pylint: disable=all
    """

    :return: None
    """

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    wrap_target()  # type: ignore

    pull(noblock)  # type: ignore
    mov(x, osr)  # type: ignore

    mov(y, osr)  # type: ignore
    label("high_side_wait")  # type: ignore
    set(pins, 1)  # type: ignore
    jmp(y_dec, "high_side_wait")  # type: ignore

    mov(y, osr)  # type: ignore
    label("low_side_wait")  # type: ignore
    set(pins, 0)  # type: ignore
    jmp(y_dec, "low_side_wait")  # type: ignore

    wrap()  # type: ignore


def square_waver(
    output_pin: Pin,
    state_machine_index: int,
) -> "t.Callable[[int], None]":
    """

    :param output_pin:
    :param state_machine_index:
    :return:
    """

    state_machine = rp2.StateMachine(
        state_machine_index, prog=slow_square_pio, set_base=output_pin, freq=50_000
    )

    state_machine.active(1)

    def change_frequency(t: int) -> None:
        """

        :param t:
        :return:
        """
        state_machine.put(t - 2)

    return change_frequency


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    rolling_average_approach = False

    latest_properties = measure_pulse_properties(
        data_pin=Pin(0, Pin.IN),
        state_machine_index=0,
        rolling_average_approach=rolling_average_approach,
    )

    while True:
        properties = latest_properties()

        if properties is not None:
            pretty = pprint_pulse_properties(properties)
            print(f"Rolling Avg. Approach: {rolling_average_approach} - {pretty}")
            utime.sleep(0.01)


def main_poc() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    latest_properties = measure_pulse_properties(data_pin=Pin(0), state_machine_index=0)
    change_frequency = square_waver(output_pin=Pin(1), state_machine_index=7)

    hz_100_side_length = 125

    while True:

        duty = latest_properties().duty_cycle
        counts = int(hz_100_side_length - 50 * ((duty) + 0.1))

        print(f"Writing counts: {counts}, duty: {duty}")

        change_frequency(counts)


def main_test() -> None:
    """

    :return:
    """

    state_machine = rp2.StateMachine(
        1, prog=slow_square_pio, set_base=Pin(1), sideset_base=Pin(2), freq=50_000
    )

    state_machine.active(1)

    hz_100_side_length = 125
    hz_1250_side_length = 10

    while True:

        for target_side_length in range(hz_1250_side_length, hz_100_side_length + 23, 23):
            print(f"Writing: {target_side_length}")
            input_value = target_side_length - 2
            state_machine.put(input_value)

        for target_side_length in range(hz_100_side_length - 23, hz_1250_side_length, -23):
            print(f"Writing: {target_side_length}")
            input_value = target_side_length - 2
            state_machine.put(input_value)


if __name__ == "__main__":
    main()
