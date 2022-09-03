"""
Common functionality for reading/writing pulses.
"""

import utime

try:
    import typing as t  # pylint: disable=unused-import
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore

MAX_32_BIT_VALUE = 0xFFFFFFFF


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


def cycles_to_periods_us(
    cycles: float, clock_period_microseconds: int, cycles_per_read: int
) -> float:
    """
    Converts the number of clock cycles as returned by the PIO to the period elapsed in
    microseconds. We multiply the output by 2 because it takes two clock cycles to decrement
    the counter, and then `jmp` based on the pin's value.
    :param cycles: Number of cycles.
    :return: Period in microseconds.
    """

    return cycles * clock_period_microseconds * cycles_per_read


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