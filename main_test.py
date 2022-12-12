"""
Entry point for development.
"""

from time import sleep

from tesla_cooler.temperature_module import temperature_sensor


def main() -> None:
    """
    Run what we're testing.
    :return: None
    """

    reader = temperature_sensor.current_values()

    while True:
        tmp1, tmp2 = map(lambda value: round(value, 2), reader())
        print(tmp1, tmp2, abs(tmp1 - tmp2))
        sleep(0.25)
