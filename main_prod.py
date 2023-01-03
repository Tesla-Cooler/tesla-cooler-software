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
    "Cooler (thermistor, calc): {name} is {temperature} degrees C. "
    "Cooler Power: {power}, Target Counts: {target_counts}, Setting fans: {duty_cycles}"
)

DEFAULT_SPEEDS_PER_POWER = 30

# How often the cooler control loops will run.
DEFAULT_COOLER_UPDATE_MS = 5000


def create_cooler_callback(
    cooler_name: str,
    thermistor_pin: int,
    fan_pins: Tuple[int, ...],
    fan_constants: FanConstants,
    resistance_to_temperature: Dict[float, float],
    temperature_offset: float,
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
    :param temperature_offset: The difference between the temperature of the thermistor, and the
    temperature of the GPU. Since the thermistor is attached to the outside of the GPU, it will
    always have slightly different temperature than that measured by `nvidia-smi`.
    TODO: This assumes the relationship is linear which it probably isn't.
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

        thermistor_temperature = thermistor.rp2040_adc_thermistor_temperature(
            pin_number=thermistor_pin, resistance_to_temperature=resistance_to_temperature
        )

        current_gpu_temperature = thermistor_temperature + temperature_offset

        cooler_power = gpu_temperature_to_cooler_power(gpu_temperature=current_gpu_temperature)
        target_counts, fan_speeds = cooler_fan_manager.power(cooler_power)

        if print_activity:
            print(
                LOG_MSG.format(
                    name=cooler_name,
                    temperature=(thermistor_temperature, current_gpu_temperature),
                    power=cooler_power,
                    target_counts=target_counts,
                    duty_cycles=fan_speeds,
                )
            )

    return cooler_callback


def main() -> None:
    """
    Main entry point for tesla_cooler.
    This is very specific to my build, if you're adapting this for another configuration,
    you're probably going to want to edit this function.

    Timers:
        Attaches the two cooler control loops to timers so they can run in parallel.
        Because this function is non-blocking, you can REPL into the pico and interact with it while
        the coolers are running.

    :return: None
    """

    resistance_to_temperature = thermistor.read_resistance_to_temperature(
        lookup_json_path=thermistor.B2550_3950K_10K_JSON_PATH
    )

    # "Hot side" GPU -- The underside of the card is right up against the other GPU
    Timer().init(
        period=DEFAULT_COOLER_UPDATE_MS,
        mode=Timer.PERIODIC,
        callback=create_cooler_callback(
            cooler_name="A",
            thermistor_pin=COOLER_A_THERMISTOR,
            fan_pins=COOLER_A_FAN_PINS,
            fan_constants=GM1204PQV1_8A_SHORT_WIRE,
            resistance_to_temperature=resistance_to_temperature,
            temperature_offset=5,  # determined experimentally
        ),
    )

    # "Cool side" GPU -- The underside of the card faces the motherboard and has plenty of room.
    Timer().init(
        period=DEFAULT_COOLER_UPDATE_MS,
        mode=Timer.PERIODIC,
        callback=create_cooler_callback(
            cooler_name="B",
            thermistor_pin=COOLER_B_THERMISTOR,
            fan_pins=COOLER_B_FAN_PINS,
            fan_constants=GM1204PQV1_8A_LONG_WIRE,
            resistance_to_temperature=resistance_to_temperature,
            temperature_offset=30,  # determined experimentally
        ),
    )

    print("Timers configured!")


if __name__ == "__main__":
    main()
