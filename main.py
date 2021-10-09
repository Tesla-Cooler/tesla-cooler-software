"""
Main module, gets run on boot by the pico.
"""

import utime

from tesla_cooler import fan_controller, thermistor
from tesla_cooler.pcb_constants import (
    COOLER_A_FAN_PINS,
    COOLER_A_THERMISTOR,
    COOLER_B_FAN_PINS,
    COOLER_B_THERMISTOR,
)

try:
    from typing import Callable, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

COOLER_NAME_BY_INDEX = ["A", "B"]

LOG_MSG = "Cooler: {name} is {temperature} degrees. Setting fan: {fan} to duty: {duty}."


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    functions: "List[Tuple[Callable[[], float], List[Callable[[float], int]]]]" = [
        (
            thermistor.thermistor_temperature(thermistor_pin),
            [fan_controller.set_fan_speed(fan_pin) for fan_pin in fan_pins],
        )
        for thermistor_pin, fan_pins in [
            (COOLER_A_THERMISTOR, COOLER_A_FAN_PINS),
            (COOLER_B_THERMISTOR, COOLER_B_FAN_PINS),
        ]
    ]

    while True:
        try:
            for cooler_index, (temp_function, speed_functions) in enumerate(functions):
                cooler_temp = temp_function()
                for fan_index, speed_function in enumerate(speed_functions):
                    new_speed = speed_function(cooler_temp)
                    print(
                        LOG_MSG.format(
                            name=COOLER_NAME_BY_INDEX[cooler_index],
                            temperature=cooler_temp,
                            fan=fan_index,
                            duty=new_speed,
                        )
                    )
        except Exception as e:  # pylint: disable=broad-except
            print(f"Ran into exception in main loop: {e}")

        print("sleeping...")
        utime.sleep(0.5)


if __name__ == "__main__":
    main()
