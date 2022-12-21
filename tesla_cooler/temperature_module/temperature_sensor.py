"""
For interacting with the temperature sensor over i2c.
"""

from collections import namedtuple

from machine import I2C

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

POINTER_VALUE_TEMP = 0b000


TemperatureModuleReadings = namedtuple(
    "TemperatureModuleReadings",
    ["tmp1", "tmp2"],
)


def _unpack_temperature_reading(packed_bytes: bytes) -> float:
    """
    Unpacks the raw bytes from the I2C bus into temperature in degrees C.
    :return: Temperature stored in the given bytes.
    """

    unpacked = int.from_bytes(packed_bytes, "big")
    rotated = unpacked >> 5  # Per the datasheet, these 5 bytes are unused.
    output = rotated * 0.125

    return output


def create_reader(
    i2c: I2C, tmp1_address: int, tmp2_address: int
) -> "t.Callable[[], TemperatureModuleReadings]":
    """
    Creates a callable that returns the current values from the temperature sensor via the I2C bus.
    :param i2c: Configured I2C bus instance. Addresses depend on how the `ADDRESS_0` and
    `ADDRESS_1` pins are set.
    :param tmp1_address: Address on the I2C bus where `TMP1` is located.
    :param tmp2_address: Address on the I2C bus where `TMP2` is located.
    :return: Callable that produces an NT containing the current reading for both temperature
    sensors.
    """

    return lambda: TemperatureModuleReadings(
        tmp1=_unpack_temperature_reading(i2c.readfrom_mem(tmp1_address, POINTER_VALUE_TEMP, 2)),
        tmp2=_unpack_temperature_reading(i2c.readfrom_mem(tmp2_address, POINTER_VALUE_TEMP, 2)),
    )
