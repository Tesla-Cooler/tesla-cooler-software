"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342

The following represents the different parts of a square waveform that are measured with this
program. Note that the 'timer' always starts at point 'b', because we only measure one pulse at a
time.

            ----- Timer starts here.
           |
           |
    a      b      c     d
     ******       ******
     ^    *       ^    *
******    *********    ******


    a      b      c     d
***********       ******
          *       ^    *
          *********    ******

"""

import rp2
import utime
from machine import Pin, mem32

from tesla_cooler.read_write_pulse.blocking_32_bit import (
    pulse_properties_pio_blocking_32bit,
    read_pio_blocking_32bit,
)
from tesla_cooler.read_write_pulse.pulse_common import MAX_32_BIT_VALUE, PulseProperties
from tesla_cooler.read_write_pulse.rolling_16_bit import (
    pulse_properties_pio_rolling_16bit,
    read_pio_rolling_16bit,
)
from tesla_cooler.read_write_pulse.write_square_wave import slow_square_pio, square_waver

try:
    import typing as t
    from collections import namedtuple
except ImportError:
    # we're probably on the pico if this occurs.
    from ucollections import namedtuple  # type: ignore


PICO_CLOCK_FREQUENCY_HZ = int(1.25e8)

_PIO0_BASE = 0x50200000
_INPUT_SYNC_BYPASS_OFFSET = 0x038
INPUT_SYNC_ENABLE_ADDRESS = _PIO0_BASE | _INPUT_SYNC_BYPASS_OFFSET


def pprint_pulse_properties(pulse_properties: PulseProperties) -> str:
    """

    :param pulse_properties:
    :return:
    """

    period_seconds = pulse_properties.period_us * 1 * 10e-7 if pulse_properties.period_us is not None else None
    frequency_khz = (1 / period_seconds) * 0.001 if period_seconds is not None else None

    c_cs = int(pulse_properties.c_cs) if pulse_properties.c_cs is not None else None
    d_cs = int(pulse_properties.d_cs) if pulse_properties.d_cs is not None else None
    period = "{:.5f}".format(pulse_properties.period_us) if pulse_properties.period_us is not None else None
    frequency = "{:.5f}".format(frequency_khz) if frequency_khz is not None else None
    duty_cycle = "{:.10f}".format(pulse_properties.duty_cycle) if pulse_properties.duty_cycle is not None else None

    return (
        f"C-CS: {c_cs}, D-CS: {d_cs}, Period (us): {period} "
        + f"Frequency (kHz): {frequency}, Duty Cycle: {duty_cycle}%"
    )


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

    # mem32[INPUT_SYNC_ENABLE_ADDRESS] = 0

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
        sideset_base=Pin(1),
        freq=clock_freq_hz,
    )

    state_machine.active(1)

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

        return pio_read_function(
            state_machine=state_machine,
            timeout_us=timeout_us,
            timeout_pulses=timeout_pulses,
            clock_period_microseconds=clock_period_microseconds,
        )

    return measure


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
            utime.sleep(0.025)


if __name__ == "__main__":
    main()
