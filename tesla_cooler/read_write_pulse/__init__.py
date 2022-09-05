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
from machine import Pin

from tesla_cooler.read_write_pulse.read_write_pulse_common import MAX_32_BIT_VALUE, PulseProperties
from tesla_cooler.read_write_pulse.rolling_16_bit import (
    pulse_properties_pio_rolling_16bit,
    read_pio_rolling_16bit,
)
from tesla_cooler.read_write_pulse.synchronous_measure_pulse import (
    read_synchronous_measure_pulse_pio,
    synchronous_measure_pulse_pio,
)
from tesla_cooler.read_write_pulse.write_square_wave import slow_square_pio, square_waver

try:
    import typing as t
except ImportError:
    pass  # we're probably on the pico if this occurs.


PICO_CLOCK_FREQUENCY_HZ = int(1.25e8)

_PIO0_BASE = 0x50200000
_INPUT_SYNC_BYPASS_OFFSET = 0x038
INPUT_SYNC_ENABLE_ADDRESS = _PIO0_BASE | _INPUT_SYNC_BYPASS_OFFSET


def pretty_print_pulse_properties(pulse_properties: PulseProperties) -> str:
    """

    :param pulse_properties:
    :return:
    """

    output = f"Frequency (hz): {pulse_properties.frequency} "
    output += f"Pulse Width (s): {pulse_properties.pulse_width} "
    output += f"Duty Cycle: {pulse_properties.duty_cycle}"

    return output


def measure_pulse_properties(
    data_pin: Pin,
    state_machine_index: int,
    clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ,
) -> "t.Callable[[int | float], t.Optional[PulseProperties]]":
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

    :return: Callable that takes a single argument, the read timeout in seconds. Internally, the
    PIO reads the waveform ~2 times, so the timeout must be long enough to cover this whole
    operation. For example, you're reading waveforms at 1 Hz, you'll want to set the timeout
    to >2s. Experimentally, doubling the expected period is a safe bet, so for reading a 1 Hz
    square wave, a safe timeout would be three seconds.
    """

    clock_period = 1 / clock_freq_hz

    state_machine = rp2.StateMachine(
        state_machine_index,
        prog=synchronous_measure_pulse_pio,
        jmp_pin=data_pin,
        freq=clock_freq_hz,
    )

    state_machine.active(1)

    return lambda timeout_seconds: read_synchronous_measure_pulse_pio(
        state_machine=state_machine, timeout_seconds=timeout_seconds, clock_period=clock_period
    )


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    latest_properties = measure_pulse_properties(
        data_pin=Pin(0, Pin.IN),
        state_machine_index=0,
    )

    while True:
        properties = latest_properties(0.1)
        if properties is not None:
            print(pretty_print_pulse_properties(properties))
            utime.sleep(0.025)


if __name__ == "__main__":
    main()
