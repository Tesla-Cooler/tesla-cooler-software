"""
Main module, gets run on boot by the pico.
"""

from machine import Timer

from tesla_cooler import thermistor
from tesla_cooler.cooler_fan_manager import CoolerFanManager
from tesla_cooler.fan_constants import (
    GM1204PQV1_8A_LONG_WIRE,
    GM1204PQV1_8A_SHORT_WIRE,
    FanConstants,
)
from tesla_cooler.gpu_temperature_to_cooler_power import gpu_temperature_to_cooler_power
from tesla_cooler.pcb_constants import (
    COOLER_A_FAN_PINS,
    COOLER_A_THERMISTOR,
    COOLER_B_FAN_PINS,
    COOLER_B_THERMISTOR,
)

try:
    from typing import Callable, Dict, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


LOG_MSG = (
    "Cooler: {name} is {temperature} degrees C. "
    "Cooler Power: {power}, Setting fans: {duty_cycles}"
)

DEFAULT_SPEEDS_PER_POWER = 35

# How often the cooler control loops will run.
DEFAULT_COOLER_UPDATE_MS = 2500


def create_cooler_callback(
    cooler_name: str,
    thermistor_pin: int,
    fan_pins: Tuple[int, ...],
    fan_constants: FanConstants,
    resistance_to_temperature: Dict[float, float],
    print_activity: bool = False,
) -> Callable[[Timer], None]:
    """
    Creates a function to be called by the timer.
    :param cooler_name: For logging.
    :param thermistor_pin: Temp values from this pin will feed into fan speed.
    :param fan_pins: These fans will be driven.
    :param fan_constants: Contains information on electrical properties of the fan. See the
    docs in the type for more.
    :param resistance_to_temperature: A dictionary mapping electrical resistance to the
    corresponding temperature of a resistor. Used to figure out what temperature the GPU is.
    :param print_activity: If True, each time the timer runs a log will be printed to the console.
    Makes it hard to work in a repl alongside operation but good for debugging otherwise.
    :return: None
    """

    cooler_fan_manager = CoolerFanManager(
        pin_numbers=fan_pins, fan_constants=fan_constants, speeds_per_power=DEFAULT_SPEEDS_PER_POWER
    )

    def cooler_callback(timer: Timer) -> None:  # pylint: disable=unused-argument
        """
        This function will be called by the timer. This function does the following:
        1. Read the current temperature off of the thermistor.
        2. Converts that current temperature to cooler power.
        3. Converts cooler power into the actual PWM duty cycle values to be written to the fans
        and actually writes the values to the fans.
        4. Logs status (if configured)
        :param timer: Provided by the timer interface but not consumed.
        :return: None
        """

        current_gpu_temperature = thermistor.thermistor_temperature(
            pin_number=thermistor_pin, resistance_to_temperature=resistance_to_temperature
        )

        cooler_power = gpu_temperature_to_cooler_power(current_temperature=current_gpu_temperature)
        fan_speeds = cooler_fan_manager.power(cooler_power)

        if print_activity:
            print(
                LOG_MSG.format(
                    name=cooler_name,
                    temperature=current_gpu_temperature,
                    power=cooler_power,
                    duty_cycles=fan_speeds,
                )
            )

    return cooler_callback


def main() -> None:
    """
    Main entry point for tesla_cooler.

    Timers:
        Attaches the two cooler control loops to timers so they can run in parallel.
        Because this function is non-blocking, you can REPL into the pico and interact with it while
        the coolers are running.

    :return: None
    """

    resistance_to_temperature = thermistor.read_resistance_to_temperature()

    Timer().init(
        period=DEFAULT_COOLER_UPDATE_MS,
        mode=Timer.PERIODIC,
        callback=create_cooler_callback(
            cooler_name="A",
            thermistor_pin=COOLER_A_THERMISTOR,
            fan_pins=COOLER_A_FAN_PINS,
            fan_constants=GM1204PQV1_8A_SHORT_WIRE,
            resistance_to_temperature=resistance_to_temperature,
        ),
    )

    Timer().init(
        period=DEFAULT_COOLER_UPDATE_MS,
        mode=Timer.PERIODIC,
        callback=create_cooler_callback(
            cooler_name="B",
            thermistor_pin=COOLER_B_THERMISTOR,
            fan_pins=COOLER_B_FAN_PINS,
            fan_constants=GM1204PQV1_8A_LONG_WIRE,
            resistance_to_temperature=resistance_to_temperature,
        ),
    )


if __name__ == "__main__":
    pass
    # main()
