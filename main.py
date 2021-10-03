"""Main module."""

import machine
import utime


def main() -> None:
    """
    Main entry point for tesla_cooler
    :return: None
    """

    led_onboard = machine.Pin(25, machine.Pin.OUT)
    while True:
        led_onboard.toggle()
        utime.sleep(1)


if __name__ == "__main__":
    main()
