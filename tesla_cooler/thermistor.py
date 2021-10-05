"""
Functions for reading temperature values off of a 10K 3950 NTC thermistor.
The resistor is attached to 3.3V and a 10K pulldown resistor which is attached to ground.
See schematic for more details.
"""

import json

from machine import ADC

from tesla_cooler.cooler_common import U_16_MAX, closest_to_value

try:
    from typing import Callable, Dict, List  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

RESISTANCE_OF_PULLDOWN = 10_000

DEFAULT_JSON_PATH = "./tesla_cooler/temperature_lookup.json"


def _thermistor_resistance(
    pin: ADC, pulldown_resistance: int = RESISTANCE_OF_PULLDOWN, vin_count: int = U_16_MAX
) -> float:
    """
    Compute the resistance of the thermistor at the given PIN.
    :param pin: The ADC interface that is associated with the pin connected to the thermistor.
    :param pulldown_resistance: The value of the pulldown resistor in ohms.
    :param vin_count: The ADC count (in the u16 number space) for V_in, the max value that could
    be read from the ADC.
    :return: The resistance in Ohms as a float.
    """
    return float((pulldown_resistance * (vin_count / pin.read_u16())) - pulldown_resistance)


def thermistor_temperature(
    pin_number: int, lookup_json_path: str = DEFAULT_JSON_PATH
) -> "Callable[[], float]":
    """
    Create a function to read the temperature off of a thermistor attached the given pin.
    :param pin_number: The pin connected to the thermistor.
    :param lookup_json_path: Path to the json file that maps temperature to resistance.
    :return: A function that when called returns the current temperature of the thermistor.
    """

    pin = ADC(pin_number)

    with open(lookup_json_path) as f:
        lookup_dict: "Dict[str, str]" = json.load(f)

        # Need to multiply by 1000 because file is in kOhm
        resistance_to_temperature: "Dict[float, float]" = {
            float(resistance_str) * 1000: float(temperature_str)
            for temperature_str, resistance_str in lookup_dict.items()
        }

    resistances = list(resistance_to_temperature.keys())

    def current_temperature() -> float:
        """
        :return: The current temperature detected by the attached resistor in degrees centigrade.
        """
        current_resistance = _thermistor_resistance(pin=pin)
        return resistance_to_temperature[closest_to_value(current_resistance, resistances)]

    return current_temperature
