import machine
from machine import SPI, Pin
from tesla_cooler import thermistor

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def mcp3008_reader(spi: SPI, chip_select: Pin, channels: "t.Tuple[int, ...]") -> "t.Callable[[], t.List[int]]":
    """

    :param spi:
    :param chip_select:
    :return:
    """

    # Must be same length to use `write_readinto`.
    output_buffer = bytearray(3)
    input_buf = bytearray(3)

    output_buffer[0] = 1

    chip_select.on()  # Initially disable

    def read_channel(channel: int) -> int:
        """

        :param channel:
        :return:
        """

        chip_select.off()
        output_buffer[1] = (1 << 7) | (channel << 4)
        spi.write_readinto(output_buffer, input_buf)
        chip_select.on()

        return ((input_buf[1] & 0x03) << 8) | input_buf[2]

    def read_channels() -> "t.List[int]":
        """

        :return:
        """
        return list(map(read_channel, channels))

    return read_channels


def loop_read() -> None:
    """

    :return:
    """

    cs = machine.Pin(5, machine.Pin.OUT)
    cs.off()

    spi = machine.SPI(
        0,
        sck=machine.Pin(2),
        mosi=machine.Pin(3),
        miso=machine.Pin(4),
    )

    reader = mcp3008_reader(spi=spi, chip_select=cs, channels=(0, 1, 2))

    lookup = thermistor.read_resistance_to_temperature(thermistor.B2550_3950K_10K_JSON_PATH)

    while True:



        print(f"Temperatures: {        [thermistor.thermistor_temperature_resistance(
            resistance=thermistor.thermistor_resistance(
            adc_count=adc_count,
            v_in_count=thermistor.U_10_MAX,
        ),
            resistance_to_temperature=lookup
        ) for adc_count in reader() ]}")
