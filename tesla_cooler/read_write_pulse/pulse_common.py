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
