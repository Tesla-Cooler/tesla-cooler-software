"""
For interacting with the temperature sensor over i2c
"""

from machine import I2C, Pin

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

# Pin mappings
I2C_SCL = 21
I2C_SDA = 20
ADDRESS_1 = 19
ADDRESS_0 = 18

POINTER_VALUE_TEMP = 0b000


def current_values() -> "t.Callable[[],t.Tuple[float, float]]":
    """

    :return:
    """

    address_0 = Pin(ADDRESS_0, Pin.OUT)
    address_1 = Pin(ADDRESS_1, Pin.OUT)

    address_0.off()
    address_1.off()

    i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400_000)

    def convert(packed_bytes: bytes) -> float:
        """

        :return:
        """

        return (int.from_bytes(packed_bytes, "big") >> 5) * 0.125

    def output() -> "t.Tuple[float, float]":
        """

        :return:
        """

        return convert(i2c.readfrom_mem(0b1001100, POINTER_VALUE_TEMP, 2)), convert(
            i2c.readfrom_mem(0b1001110, POINTER_VALUE_TEMP, 2)
        )

    return output
