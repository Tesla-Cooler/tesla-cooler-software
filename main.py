"""
Main module, gets run on boot by the pico.
"""

# pylint: disable=unused-variable

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

    cooler_a_temp_function = thermistor.thermistor_temperature(COOLER_A_THERMISTOR)
    cooler_a_manager = fan_controller.CoolerManager(pin_numbers=COOLER_A_FAN_PINS)

    cooler_b_temp_function = thermistor.thermistor_temperature(COOLER_B_THERMISTOR)
    cooler_b_manager = fan_controller.CoolerManager(pin_numbers=COOLER_B_FAN_PINS)

    while True:
        print("sleeping...")
        utime.sleep(0.5)


if __name__ == "__main__":
    main()
