"""
Functions for controlling the speed of fans.
TODO: add more docs here
"""

from machine import PWM, Pin

from tesla_cooler.fan_speed_control import combinations_to_sum, linear_interpolate, total_weight

try:
    from typing import Callable, Dict, List, Sequence, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


# Determined both of these through experimentation.
PWM_FREQ = 30_000

SLOWEST_POSSIBLE_SPEED_DUTY = 40_000  # Determined experimentally
MAX_DUTY = 65_025  # Per Raspberry Pi Pico Docs

POWER_MIN, POWER_MAX = (0, 1)

WEIGHT_RANGES = (
    (0, 1000),  # Makes no noise.
    (1001, 2000),  # Makes some noise.
    (2001, 3000),  # Makes a lot of noise.
)


def setup_pwm(pin_number: int) -> PWM:
    """

    :param pin_number:
    :return:
    """

    pwm = PWM(Pin(pin_number))
    pwm.freq(PWM_FREQ)
    return pwm


class CoolerManager:
    """
    Goals are:

    * To have each of the individual fans spinning as slow as possible, three fans spinning slowly
    is better than two fans spinning quickly.

    * Whenever fewer than all fans are operating, we should expose a way to rotate which of the
    fans are on to prevent uneven wear between the fans over time

    * When asking fans to spin below the speed they can start and get to, make sure they first
    spin up to a speed where they can then spin down to the target speed.

    Assumptions:

    * All of the attached fans are the same model, and all cost the same to drive.

    """

    def __init__(self: "CoolerManager", pin_numbers: "Tuple[int, ...]"):
        """

        :param pin_numbers:
        """

        self._pwm_controllers: "List[PWM]" = [setup_pwm(pin_number) for pin_number in pin_numbers]

    def power(self: "CoolerManager", new_power: float) -> Tuple[int, ...]:
        """

        :param new_power: Float between 0 and 1. 0 maps to a single fan spinning as slowly as
        possible, 1 maps to all fans spinning as fast as possible.

        :return:
        """

        target_counts = linear_interpolate(
            x=new_power,
            in_min=POWER_MIN,
            in_max=POWER_MAX,
            out_min=SLOWEST_POSSIBLE_SPEED_DUTY,
            out_max=MAX_DUTY * len(self._pwm_controllers),
        )

        candidate_speeds: List[Tuple[int, ...]] = combinations_to_sum(
            potential_values=tuple(range(SLOWEST_POSSIBLE_SPEED_DUTY, MAX_DUTY)),
            target_length=len(self._pwm_controllers),
            target_value=target_counts,
        )

        scope_to_weight = {
            scope: (scope_index + 1) ** 3 for scope_index, scope in enumerate(WEIGHT_RANGES)
        }

        weights_and_speeds = [
            (total_weight(values=speeds, scope_to_weight=scope_to_weight), speeds)
            for speeds in candidate_speeds
        ]

        quietest_speeds = min(
            weights_and_speeds, key=lambda weight_and_speeds: weight_and_speeds[0]
        )[1]

        for pwm_pin, speed in zip(self._pwm_controllers, quietest_speeds):
            pwm_pin.duty_u16(speed)

        return quietest_speeds

    def rotate_active(self: "CoolerManager") -> "Tuple[int, ...]":
        """

        :return:
        """
