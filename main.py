"""Main module."""

import utime

from tesla_cooler import fan_controller, thermistor

try:
    from typing import Callable, Dict, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

COOLER_A_THERMISTOR = 26
COOLER_B_THERMISTOR = 27

COOLER_A_FAN_PINS = (1, 3, 5)
COOLER_B_FAN_PINS = (7, 9, 11)

RESISTANCE_OF_PULLDOWN = 10_000

COOLER_NAME_BY_INDEX = ["A", "B"]


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    functions: "List[Tuples[Callable[[], float], Tuple[Callable[[int], int]]]]" = [
        (
            thermistor.thermistor_temperature(thermistor_pin),
            (fan_controller.set_fan_speed(fan_pin) for fan_pin in fan_pins),
        )
        for thermistor_pin, fan_pins in zip(
            [
                (COOLER_A_THERMISTOR, COOLER_A_FAN_PINS),
                (COOLER_B_THERMISTOR, COOLER_B_FAN_PINS),
            ]
        )
    ]

    while True:

        for cooler_index, (temp_function, speed_functions) in enumerate(functions):
            cooler_temp = temp_function()

            for fan_index, speed_function in enumerate(speed_functions):
                new_speed = speed_function(cooler_temp)

                print(
                    f"Set Cooler: {COOLER_NAME_BY_INDEX[cooler_index]} "
                    f"fan: {fan_index} "
                    f"to duty: {new_speed}."
                )

        utime.sleep(0.5)


if __name__ == "__main__":
    main()
