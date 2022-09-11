"""
Uses PIO state machines to characterize and create square waves.

* `measure_pulse_properties` is able to surmise changing duty cycles from waveforms that are
changing in frequency, something that the micropython library function `time_pulse_us` wasn't able
to do accurately.

* `write_square_wave` is able to create square waves as low as 1 Hz, which was not possible with the
library function. It should also be possible to go slower with this approach but this has not been
implemented yet.
"""

import rp2
from machine import Pin

from tesla_cooler.read_write_pulse.read_write_pulse_common import MAX_32_BIT_VALUE, PulseProperties
from tesla_cooler.read_write_pulse.synchronous_measure_pulse import (
    read_synchronous_measure_pulse_pio,
    synchronous_measure_pulse_pio,
)
from tesla_cooler.read_write_pulse.write_square_wave import (
    square_waver_pio,
    square_waver_pio_frequency_to_counts,
)

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
    Converts a `PulseProperty` namedtuple to a string for printing.
    :param pulse_properties: To convert.
    :return: To read.
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

    :param data_pin: `machine.Pin` object, represents which physical pin to read pulses from.
    :param state_machine_index: The PIO state machine index to be used to make the measurements.
    :param clock_freq_hz: The frequency to drive the state machine at. Note that this will effect
    the range of measurable frequencies. Both Period and Pulse width are sent back to the CPU from
    the state machine as 32 bit numbers, and therefore have a maximum value of 4,294,967,295. If the
    pulse lasts longer than can be encoded into this 32 bit value, the result will not make any
    sense. The formula for the min/max frequency given the clock frequency is as follows:

    min_freq_hz = 1/(1/(c*2) * 4,294,967,295)
    max_freq_hz = 1/(1/(c*2) * 1)

    Given c = input clock frequency in hz. By default, the fastest possible clock frequency on the
    pico is used.

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

    state_machine.active(True)

    return lambda timeout_seconds: read_synchronous_measure_pulse_pio(
        state_machine=state_machine, timeout_seconds=timeout_seconds, clock_period=clock_period
    )


def write_square_wave(
    output_pin: Pin,
    state_machine_index: int,
    init_frequency_hz: int = 0,
    clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ,
) -> "t.Callable[[int], bool]":
    """
    Writes 50% duty cycle square waves at a given frequency to an output pin.
    :param output_pin: Waves will be written to this Pin.
    :param state_machine_index: State machine to use, make sure there's noone using this already.
    :param init_frequency_hz: Initial frequency to drive the output at.
    :param clock_freq_hz: Modify the frequency the statemachine runs at for more granular control
    of output. By default runs as fast as possible.
    :return: A callable that accepts the target frequency in hz as an argument, and returns whether
    or not the state machine was written to. If you send the same frequency twice in a row, the
    state machine's state will be exactly the same and the write will be skipped. Float frequencies
    (ie. 10.5Hz) are not supported. Note: This call will block until the CPU is able to `.put` the
    input value into the state machine. If you are changing between low frequencies, this call can
    block until the state machine has had time to clock out the output and ingest the input. This
    guarantees that each unique input will get converted to output, all desired frequencies will
    occur.
    """

    state_machine = rp2.StateMachine(
        state_machine_index, prog=square_waver_pio, set_base=output_pin, freq=clock_freq_hz
    )

    # Used to prevent unneeded writes.
    previous_frequency: "t.Optional[int]" = None

    def write_frequency_if_active(frequency_hz: int) -> bool:
        """
        Accepts the target frequency in hz as an argument, and returns whether or not the state
        machine was written to. If you send the same frequency twice in a row, the state machine's
        state will be exactly the same and the write will be skipped. Float frequencies (ie. 10.5Hz)
        are not supported.
        :param frequency_hz: Desired frequency in Hertz.
        :return: True if the state machine was modified, false if the input was ignored because the
        state machine would not change. Note: This call will block until the CPU is able to `.put`
        the input value into the state machine. If you are changing between low frequencies, this
        call can block until the state machine has had time to clock out the output and ingest the
        input. This guarantees that each unique input will get converted to output, all desired
        frequencies will occur.
        """
        nonlocal previous_frequency
        if frequency_hz != previous_frequency:
            if frequency_hz == 0:
                state_machine.active(False)
                output_pin.off()
            else:
                if not state_machine.active():  # pylint: disable=no-value-for-parameter
                    state_machine.active(True)
                state_machine.put(
                    square_waver_pio_frequency_to_counts(
                        state_machine_frequency_hz=clock_freq_hz, frequency_hz=frequency_hz
                    )
                )
            previous_frequency = frequency_hz
            return True
        return False

    write_frequency_if_active(init_frequency_hz)

    return write_frequency_if_active
