"""Main module."""

import utime
from machine import ADC, Pin

COOLER_FAN_PINS = [1, 3, 5, 7, 9, 11, 25]

RESISTANCE_OF_PULLDOWN = 10_000


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    pins = [Pin(pin_number, Pin.OUT) for pin_number in COOLER_FAN_PINS]

    while True:

        for pin in pins:
            pin.toggle()

        utime.sleep(1)


def print_resistor(pin: ADC) -> None:
    """

    :return:
    """

    return (RESISTANCE_OF_PULLDOWN * (65535 / pin.read_u16())) - RESISTANCE_OF_PULLDOWN


if __name__ == "__main__":
    main()
