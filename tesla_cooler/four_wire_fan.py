"""
Library to interface with the four wire fan interfaces commonly present on PCs.
"""

from machine import Pin

from tesla_cooler.read_write_pulse import measure_pulse_properties, write_square_wave

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def mimic_fan(
    pwm_input_pin_index: int,
    tachometer_output_pin_index: int,
    state_machine_indices: "t.Tuple[int, int]",
) -> None:
    """
    Sample entrypoint. Prints pulse duration periodically.
    :return: None
    """

    state_machine_index_source = iter(state_machine_indices)

    measure_pulse = measure_pulse_properties(
        data_pin=Pin(pwm_input_pin_index, Pin.IN),
        state_machine_index=next(state_machine_index_source),
    )

    set_frequency_hz = write_square_wave(
        output_pin=Pin(tachometer_output_pin_index, Pin.OUT),
        state_machine_index=next(state_machine_index_source),
    )

    while True:
        latest_properties = measure_pulse(0.01)
        if latest_properties is not None:
            duty = round(latest_properties.duty_cycle, 2)
            output = duty * 100
            if set_frequency_hz(output):
                print(f"Input Duty: {duty}, Set output frequency to: {output} Hz")
        else:
            print("No pulse detected.")


def main() -> None:
    """
    Example usage of the `mimic_fan` function.
    :return: None
    """
    mimic_fan(pwm_input_pin_index=0, tachometer_output_pin_index=1, state_machine_indices=(0, 1))


if __name__ == "__main__":
    main()
