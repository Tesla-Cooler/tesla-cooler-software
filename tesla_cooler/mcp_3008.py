"""
Interface for the MCP3008 SPI ADC.
"""

from machine import SPI, Pin

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def mcp3008_reader(
    spi: SPI,
    chip_select: Pin,
) -> "t.Callable[[int], int]":
    """
    Configure the attached MCP3008 and return an interface for reading data.
    :param spi: Usable SPI interface to talk to the MCP with.
    :param chip_select: Chip select `Pin` to enable/disable on writes.
    :return: Callable that takes the MCP channel number and returns the ADC counts.
    """

    # Must be same length to use `write_readinto`.
    output_buffer = bytearray(3)
    input_buf = bytearray(3)

    output_buffer[0] = 1

    chip_select.on()  # Initially disable

    def read_channel(channel: int) -> int:
        """
        Read the ADC counts for the given channel.
        :param channel: Channel index, 0-7.
        :return: The current ADC counts for the given channel.
        """

        chip_select.off()
        output_buffer[1] = (1 << 7) | (channel << 4)
        spi.write_readinto(output_buffer, input_buf)
        chip_select.on()

        return ((input_buf[1] & 0x03) << 8) | input_buf[2]

    return read_channel
