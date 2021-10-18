"""
Converts temperature to cooler power.
"""

from tesla_cooler import linear_interpolate
from tesla_cooler.fan_speed_control import COOLER_POWER_MAX, COOLER_POWER_MIN


def gpu_temperature_to_cooler_power(
    current_temperature: float,
    cooler_power_min: float = COOLER_POWER_MIN,
    cooler_power_max: float = COOLER_POWER_MAX,
) -> float:
    """
    Kind of like a fan curve, converts temperature to cooler power.
    It's up to the `CoolerFanManager` that consumes this value to convert this power to fan rotation
    speed. It is assumed though that higher power = faster fans.
    TODO: Would love to be able to pass the temp bounds here as a config file or more formal data
    structure.
    :param current_temperature: Current temperature of the GPU as read by the thermistor.
    :param cooler_power_min: Min power value.
    :param cooler_power_max: Max power value.
    :return: Cooler power as a float between the given bounds.
    """

    if current_temperature < 30:
        return cooler_power_min
    elif 30 <= current_temperature < 70:
        return linear_interpolate.linterp_float(
            x=current_temperature,
            in_min=30,
            in_max=70,
            out_min=cooler_power_min,
            out_max=cooler_power_max / 2,
        )
    elif 70 <= current_temperature < 100:
        return linear_interpolate.linterp_float(
            x=current_temperature,
            in_min=70,
            in_max=100,
            out_min=cooler_power_max / 2,
            out_max=cooler_power_max,
        )
    else:
        return cooler_power_max
