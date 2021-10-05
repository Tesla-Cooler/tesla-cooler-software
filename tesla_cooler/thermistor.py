"""
Functions for reading temperature values off of a 10K 3950 NTC thermistor.
The resistor is attached to 3.3V and a 10K pulldown resistor which is attached to ground.
See schematic for more details.
"""

import json

from machine import ADC

try:
    from typing import Callable, Dict, List  # pylint: disable=unused-import
except ImportError:
    pass

U_16_MAX = 65535
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


def _closest_to_value(value: float, list_of_values: "List[float]") -> float:
    """
    Given a value, and a list of values, find the closest value in the list to the input.
    :param value: Value to find in list.
    :param list_of_values: Candidate output values.
    :return: The value closest to `value` in `list_of_values`.
    """
    return list_of_values[
        min(range(len(list_of_values)), key=lambda i: abs(list_of_values[i] - value))
    ]


def thermistor_temperature(
    pin: ADC, lookup_json_path: str = DEFAULT_JSON_PATH
) -> "Callable[[], float]":
    """

    :param pin: The ADC interface that is associated with the pin connected to the thermistor.
    :param lookup_json_path: Path to the json file that maps temperature to resistance.
    :return: A function that when called returns the current temperature of the thermistor.
    """

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
        return resistance_to_temperature[_closest_to_value(current_resistance, resistances)]

    return current_temperature
