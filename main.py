"""Main module."""

import utime
from machine import ADC

from tesla_cooler import thermistor

COOLER_FAN_PINS = [1, 3, 5, 7, 9, 11, 25]

RESISTANCE_OF_PULLDOWN = 10_000


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    thermistor_pin = ADC(26)
    current_temp = thermistor.thermistor_temperature(pin=thermistor_pin)

    while True:
        print(f"Current temp: {(current_temp() * 1.8) + 32} deg F")
        utime.sleep(1)


if __name__ == "__main__":
    main()
