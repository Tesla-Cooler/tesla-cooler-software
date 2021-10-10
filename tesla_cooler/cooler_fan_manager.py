"""
Functions for controlling the speed of fans.
TODO: add more docs here
"""

import utime
from machine import PWM, Pin

from tesla_cooler.fan_constants import FanConstants
from tesla_cooler.fan_speed_control import fan_drive_values
from tesla_cooler.pure_python_itertools import left_rotate_list

try:
    from typing import Callable, Dict, List, Sequence, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def set_fan_to_duty(pwm_pin: PWM, duty: int, min_cold_start_duty: int) -> None:
    """
    Write the pwm pin to the given duty cycle.
    :param pwm_pin: Pin to modify.
    :param duty: Target duty cycle.
    :param min_cold_start_duty: Slowest speed the fan can reliably spin to after starting.
    :return: None
    """

    current_fan_duty = pwm_pin.duty_u16()

    if current_fan_duty == 0 and duty < min_cold_start_duty:
        pwm_pin.duty_u16(min_cold_start_duty)
        utime.sleep(1)
        # Fan should now be spinning and can reach lower RPMs without stalling.

    pwm_pin.duty_u16(duty)


class CoolerFanManager:
    """
    Manages a single cooler's group of fans.

    Goals are:
    * To have each of the individual fans spinning as slow as possible, three fans spinning slowly
    is better than two fans spinning quickly.
    * Whenever fewer than all fans are operating, expose a way to rotate which of the
    fans are on to prevent uneven wear between the fans over time.
    * When asking stopped fans to spin below the speed they can start and get to, make sure they
    first spin up to a speed where they can then spin down to the target speed.

    Assumptions:
    * All of the attached fans are the same model, and all cost the same to drive.
    """

    def __init__(
        self: "CoolerFanManager",
        pin_numbers: "Tuple[int, ...]",
        fan_constants: FanConstants,
        speeds_per_power: int,
    ):
        """
        :param pin_numbers: Locations of the mosfets that control the fans.
        :param fan_constants: Contains info about the fans that are attached.
        :param speeds_per_power: For a given power setting, decides the number of potential
        speed values that can be used.
        """

        def setup_pwm(pin_number: int) -> PWM:
            """
            Set the pwm frequency of the pins that will drive the fan and return the pwm object.
            :param pin_number: Pin number on the Pico
            :return: PWM object ready to go.
            """
            pwm = PWM(Pin(pin_number))
            pwm.freq(fan_constants.pwm_freq)
            return pwm

        self._pwm_controllers: "List[PWM]" = [setup_pwm(pin_number) for pin_number in pin_numbers]
        self._fan_constants = fan_constants
        self._speeds_per_power = speeds_per_power

    def power(self: "CoolerFanManager", new_power: float) -> "Tuple[int, ...]":
        """
        Set the attached fans to the given power. Logic under the hood decides how that actually
        translates to rotational speed of each of the fans, see `fan_drive_values` for more
        details.
        :param new_power: Float between 0 and 1. 0 maps to a single fan spinning as slowly as
        possible, 1 maps to all fans spinning as fast as possible.
        :return: The speeds that were written to the pins.
        """

        # This resulting tuple is going to be sorted fastest speed to slowest speed.
        speeds = fan_drive_values(
            power=new_power,
            num_fans=len(self._pwm_controllers),
            output_ranges=self._fan_constants.duty_ranges,
            num_speeds=self._speeds_per_power,
        )

        for pwm_pin, speed in zip(self._pwm_controllers, speeds):
            set_fan_to_duty(
                pwm_pin=pwm_pin,
                duty=speed,
                min_cold_start_duty=self._fan_constants.min_cold_start_duty,
            )

        return speeds

    def rotate_active(self: "CoolerFanManager") -> None:
        """
        Rotating the order of the objects in memory does the trick as speeds are always written
        in order of fastest speed first.
        :return: None
        """
        self._pwm_controllers = list(left_rotate_list(self._pwm_controllers))
