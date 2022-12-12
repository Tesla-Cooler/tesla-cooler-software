"""
Entry point for development.
"""

from time import sleep

from tesla_cooler.temperature_module import io_expander


def main() -> None:
    """
    Run what we're testing.
    :return: None
    """

    sleep_time = 1
    writer = io_expander.configured_writer()

    writer(rgb_led_anode=True, rgb_led_r_cathode=False)
    sleep(sleep_time)
    writer(rgb_led_anode=True, rgb_led_g_cathode=False)
    sleep(sleep_time)
    writer(rgb_led_anode=True, rgb_led_b_cathode=False)
    sleep(sleep_time)
    writer(blue_led_1_cathode=True)
    sleep(sleep_time)
    writer(emerald_led_1_cathode=True)
    sleep(sleep_time)
    writer(yellow_led_1_cathode=True)
    sleep(sleep_time)
    writer(red_led_1_cathode=True)
    sleep(sleep_time)
    writer(blue_led_2_cathode=True)
    sleep(sleep_time)
    writer(emerald_led_2_cathode=True)
    sleep(sleep_time)
    writer(yellow_led_2_cathode=True)
    sleep(sleep_time)
    writer(red_led_2_cathode=True)
    sleep(sleep_time)
