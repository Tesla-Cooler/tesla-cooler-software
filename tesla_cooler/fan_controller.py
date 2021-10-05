"""
Functions for controlling the speed of fans.
TODO: add more docs here
"""

from machine import PWM, Pin

try:
    from typing import Callable, Dict, List  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

from tesla_cooler import cooler_common

# Determined both of these through experimentation.
PWM_FREQ = 30_000
SLOWEST_POSSIBLE_SPEED_DUTY = 39000


def set_fan_speed(pin_number: int) -> "Callable[[int], int]":
    """
    Creates a function that accepts a temperature and sets the given fan to the best value to
    handle that temperature.
    :param pin_number: the pin the fan is attached to.
    :return: The function to make the conversion and write the value. Returns the resulting duty
    cycle.
    """

    pwm = PWM(Pin(pin_number))
    pwm.freq(PWM_FREQ)

    temperature_to_duty = {
        26.0: SLOWEST_POSSIBLE_SPEED_DUTY,
        70: SLOWEST_POSSIBLE_SPEED_DUTY
        + (cooler_common.U_16_MAX - SLOWEST_POSSIBLE_SPEED_DUTY) // 2,
        80: cooler_common.U_16_MAX,
    }

    temperatures = list(temperature_to_duty.keys())

    def set_speed_for_temperature(temperature: float) -> int:
        """
        Use a lookup table to go from temperature to fan speed, then set the fan speed to the
        best value for the input.
        :param temperature: Temp read by thermistor, the temp of the card.
        :return: None
        """

        duty = temperature_to_duty[
            cooler_common.closest_to_value(value=temperature, list_of_values=temperatures)
        ]

        pwm.duty_u16(duty)

        return duty

    return set_speed_for_temperature
