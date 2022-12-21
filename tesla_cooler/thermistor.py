"""
Functions for reading temperature values off of a 10K 3950 NTC thermistor.
The resistor is attached to 3.3V and a 10K pulldown resistor which is attached to ground.
See schematic for more details.
"""

import json

from machine import ADC

try:
    from typing import Callable, Dict, List, Sequence, Union  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

from tesla_cooler.pure_python_itertools import float_mean

RESISTANCE_OF_PULLDOWN = 10_000
U_16_MAX = 65535

# Determined experimentally
DEFAULT_THERMISTOR_SAMPLES = 10

# These are the 'barrel' type thermistors used in the original tesla cooler.
B2550_3950K_10K_JSON_PATH = (
    "./tesla_cooler/10K_B2550_ 3950K_NTC_temperature_to_resistance_lookup.json"
)

# This works with Ring Lug type NTCALUG03A103GC.
B2585_3984K_10K_JSON_PATH = (
    "./tesla_cooler/10K_B2585_3984K_NTC_temperature_to_resistance_lookup.json"
)


def _thermistor_resistance(
    pin: ADC,
    pulldown_resistance: int = RESISTANCE_OF_PULLDOWN,
    vin_count: int = U_16_MAX,
    samples: int = DEFAULT_THERMISTOR_SAMPLES,
) -> float:
    """
    Compute the resistance of the thermistor at the given PIN.
    :param pin: The ADC interface that is associated with the pin connected to the thermistor.
    :param pulldown_resistance: The value of the pulldown resistor in ohms.
    :param vin_count: The ADC count (in the u16 number space) for V_in, the max value that could
    be read from the ADC.
    :param samples: The number of samples to take to average for the measurement.
    :return: The resistance in Ohms as a float.
    """
    return float_mean(
        [
            float((pulldown_resistance * (vin_count / pin.read_u16())) - pulldown_resistance)
            for _ in range(samples)
        ]
    )


def _closest_to_value(
    value: float, list_of_values: Union[Sequence[int], Sequence[float]]
) -> Union[int, float]:
    """
    Given a value, and a list of values, find the closest value in the list to the input.
    :param value: Value to find in list.
    :param list_of_values: Candidate output values.
    :return: The value closest to `value` in `list_of_values`.
    """
    return list_of_values[
        min(range(len(list_of_values)), key=lambda i: abs(list_of_values[i] - value))
    ]


def read_resistance_to_temperature(
    lookup_json_path: str,
) -> Dict[float, float]:
    """
    Reads a local json file that contains a series of keys mapping temperature to resistance.
    :param lookup_json_path: Path to the json file.
    :return: The mapping as a dict.
    """

    with open(lookup_json_path) as f:
        lookup_dict: Dict[str, str] = json.load(f)

        # Need to multiply by 1000 because file is in kOhm
        resistance_to_temperature: Dict[float, float] = {
            float(resistance_str): float(temperature_str)
            for temperature_str, resistance_str in lookup_dict.items()
        }

    return resistance_to_temperature


def thermistor_temperature(pin_number: int, resistance_to_temperature: Dict[float, float]) -> float:
    """
    Read the temperature off of a thermistor attached the given pin.
    :param pin_number: The pin connected to the thermistor.
    :param resistance_to_temperature: A dict mapping resistance values to their corresponding
    temperature. Units are ohms and degrees Celsius.
    :return: A function that when called returns the current temperature of the thermistor.
    """

    return resistance_to_temperature[
        _closest_to_value(
            _thermistor_resistance(pin=ADC(pin_number)), list(resistance_to_temperature.keys())
        )
    ]
