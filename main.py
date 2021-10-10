"""
Main module, gets run on boot by the pico.
"""

import _thread

from tesla_cooler import thermistor
from tesla_cooler.cooler_fan_manager import CoolerFanManager
from tesla_cooler.fan_constants import GM1204PQV1_8A
from tesla_cooler.fan_speed_control import DEFAULT_POWER_MAX, DEFAULT_POWER_MIN
from tesla_cooler.pcb_constants import (
    COOLER_A_FAN_PINS,
    COOLER_A_THERMISTOR,
    COOLER_B_FAN_PINS,
    COOLER_B_THERMISTOR,
)
from tesla_cooler.pid import PID

try:
    from typing import Callable, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


LOG_MSG = "Cooler: {name} is {temperature} degrees C. Setting fans: {duty_cycles}"


def cooler_loop(cooler_name: str, thermistor_pin: int, fan_pins: Tuple[int, ...]) -> None:
    """
    Uses a PID control loop to make sure the GPU stays cool.
    This is the main loop of the whole program.
    :param cooler_name: For logging.
    :param thermistor_pin: Temp values from this pin will feed into fan speed.
    :param fan_pins: These fans will be driven.
    :return: None
    """

    # Tries to keep the cooler at 80 degrees C
    # Note: The internal temp of the card (as reported by `nvidia-smi`) is typically 20 degC
    # lower than the case temperature, so the true target temp here is 60 degrees.
    pid_controller = PID(
        1, 0.1, 0.05, setpoint=80.0, output_limits=(DEFAULT_POWER_MIN, DEFAULT_POWER_MAX)
    )

    cooler_temp_function = thermistor.thermistor_temperature(thermistor_pin)
    cooler_fan_manager = CoolerFanManager(pin_numbers=fan_pins, fan_constants=GM1204PQV1_8A)

    cooler_fan_manager.power(new_power=0)

    while True:
        current_temp = cooler_temp_function()
        control = pid_controller(current_temp)
        fan_speeds = cooler_fan_manager.power(control)
        print(LOG_MSG.format(name=cooler_name, temperature=current_temp, duty_cycles=fan_speeds))


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    _thread.start_new_thread(
        cooler_loop,
        args=(),
        kwargs={
            "cooler_name": "A",
            "thermistor_pin": COOLER_A_THERMISTOR,
            "fan_pins": COOLER_A_FAN_PINS,
        },
    )

    cooler_loop(cooler_name="B", thermistor_pin=COOLER_B_THERMISTOR, fan_pins=COOLER_B_FAN_PINS)


if __name__ == "__main__":
    main()
