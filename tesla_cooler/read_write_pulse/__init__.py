"""
Use a PIO state machine to accurately measure the frequency, pulse width, and duty cycle of a
square wave.

Adapted from a post by `danjperrorn` on the micropython forum:
    * https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342
"""

import rp2
from machine import Pin

from tesla_cooler.read_write_pulse.read_write_pulse_common import (
    MAX_32_BIT_VALUE,
    PulseProperties,
    SquareWaveController,
)
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
    init_enabled: bool = True,
    init_frequency_hz: int = 1_000,
    clock_freq_hz: int = PICO_CLOCK_FREQUENCY_HZ,
) -> SquareWaveController:
    """
    Writes 50% duty cycle square waves at a given frequency to an output pin.
    :param output_pin: Waves will be written to this Pin.
    :param state_machine_index: State machine to use, make sure there's noone using this already.
    :param init_enabled: If the output should be initially enabled or not.
    :param init_frequency_hz: Initial frequency to drive the output at.
    :param clock_freq_hz: Modify the frequency the statemachine runs at for more granular control
    of output. By default runs as fast as possible.
    :return: A NamedTuple with property callables to be able to change the frequency of the output
    as well as enable/disable the output all together.
    """

    state_machine = rp2.StateMachine(
        state_machine_index, prog=square_waver_pio, set_base=output_pin, freq=clock_freq_hz
    )

    def write_frequency_if_active(frequency_hz: int) -> None:
        """
        If the state machine is active, convert the input frequency to count and send it to the
        SM via the RX fifo. If the state machine is not active, do nothing.
        :param frequency_hz: Desired frequency in Hertz.
        :return: None
        """
        if state_machine.active():  # pylint: disable=no-value-for-parameter
            state_machine.put(
                square_waver_pio_frequency_to_counts(
                    state_machine_frequency_hz=clock_freq_hz, frequency_hz=frequency_hz
                )
            )

    state_machine.active(init_enabled)
    write_frequency_if_active(init_frequency_hz)

    return SquareWaveController(
        set_frequency_hz=write_frequency_if_active,
        enable=lambda: state_machine.active(True),
        disable=lambda: state_machine.active(False),
    )


def main() -> None:
    """
    Sample entrypoint. Prints pulse duration periodically.
    :return: None
    """

    wave_controller = write_square_wave(
        output_pin=Pin(0, Pin.OUT),
        state_machine_index=0,
        init_enabled=False,
    )

    wave_controller.enable()
    wave_controller.set_frequency_hz(10_000.5)

    while True:
        pass


if __name__ == "__main__":
    main()
