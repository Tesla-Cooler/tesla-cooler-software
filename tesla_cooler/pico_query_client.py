"""
Simple serial protocol to transfer data between the pico and a host PC.
This is the client, designed to be run on the Raspberry Pi Pico.
"""

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

import json
import struct
from collections import namedtuple

from machine import SPI, UART, Pin

from tesla_cooler import thermistor
from tesla_cooler.mcp_3008 import mcp3008_reader
from tesla_cooler.temperature_module import configured_temperature_reader

BAUD = 115200

COMMAND_EXIT = b"0"
COMMAND_INFO = b"1"
COMMAND_READ_TEMPERATURE = b"2"

CLIENT_INFO = {
    "firmware_version": "1.0.0",
    "zone_count": 2,
    "zone_sensors_type": "Washer Thermistor",
}


TemperatureReading = namedtuple(
    "TemperatureReading",
    ["zone_1", "zone_2", "intake", "exhaust"],
)


def configure_temperature_reader(
    temperature_module_mode: bool,
) -> "t.Callable[[], TemperatureReading]":
    """
    Configures the desired temperature sensing mode producing a callable that produces temperature
    readings on demand.
    :param temperature_module_mode: If True, it is assumed that a temperature module is attached to
    the I2C bus, so both temperature sensors on that board can be queried. If False, temperature
    will be read off of only the ADCs.
    :return:
    """

    # This will be used in either case to read the environmental ADCs.
    resistance_to_temp_environment = thermistor.read_resistance_to_temperature(
        lookup_json_path=thermistor.B2550_3950K_10K_JSON_PATH
    )

    mcp_reader = mcp3008_reader(
        spi=SPI(
            0,
            sck=Pin(2),
            mosi=Pin(3),
            miso=Pin(4),
        ),
        chip_select=Pin(5, Pin.OUT),
    )

    def mcp_temperature(
        mcp_channel: int, lookup: "t.Dict[float, float]" = resistance_to_temp_environment
    ) -> float:
        """
        Wrapper to get current temperature of a thermistor attached to an MCP channel.
        :param mcp_channel: Channel to read.
        :param lookup: Mapping for the attached thermistor.
        :return: Temperature in degrees Celsius.
        """

        return thermistor.thermistor_temperature_resistance(
            resistance=thermistor.thermistor_resistance(
                adc_count=mcp_reader(mcp_channel),
                v_in_count=thermistor.U_10_MAX,
            ),
            resistance_to_temperature=lookup,
        )

    if temperature_module_mode:

        _, tm_reader = configured_temperature_reader()

        def output() -> TemperatureReading:
            """
            Temperature module reader. When called, reads from the attached temperature module
            and ADCs.
            :return: The `TemperatureReading`.
            """

            temperature_module_readings = tm_reader()

            return TemperatureReading(
                zone_1=temperature_module_readings.tmp1,
                zone_2=temperature_module_readings.tmp2,
                intake=mcp_temperature(mcp_channel=1),
                exhaust=mcp_temperature(mcp_channel=0),
            )

    else:

        def output() -> TemperatureReading:
            """
            ADC Temperature Reader. Looks up temperatures in the provided LUT for the sensor.
            This is likely going to have to change.
            :return: The `TemperatureReading`.
            """

            resistance_to_temp_washer = thermistor.read_resistance_to_temperature(
                lookup_json_path=thermistor.B2585_3984K_10K_JSON_PATH
            )

            return TemperatureReading(
                zone_1=mcp_temperature(mcp_channel=2, lookup=resistance_to_temp_washer),
                zone_2=mcp_temperature(mcp_channel=3, lookup=resistance_to_temp_washer),
                exhaust=mcp_temperature(mcp_channel=0),
                intake=mcp_temperature(mcp_channel=1),
            )

    return output


def query_loop() -> None:
    """
    Entrypoint for the Pico Query client. Waits for messages to arrive on the external UART
    interface and replies in kind. Currently doesn't handle errors well.
    :return: None
    """

    uart_port = UART(0, baudrate=BAUD, tx=Pin(16), rx=Pin(17), bits=8, parity=None, stop=1)
    read_sensors = configure_temperature_reader(temperature_module_mode=False)

    print(f"Client Info: {CLIENT_INFO}")
    print(f"Sample Reading: {read_sensors()}")

    while True:
        if uart_port.any():
            command_byte = uart_port.read(1)
            if command_byte in (COMMAND_INFO, COMMAND_READ_TEMPERATURE):
                if command_byte == COMMAND_INFO:
                    encoded_output = json.dumps(CLIENT_INFO).encode("utf-8")
                elif command_byte == COMMAND_READ_TEMPERATURE:
                    encoded_output = bytes().join(
                        (struct.pack("f", value) for value in read_sensors())
                    )
                else:
                    encoded_output = "Protocol error!".encode("utf-8")
                uart_port.write(
                    command_byte + len(encoded_output).to_bytes(2, "big") + encoded_output
                )
            else:
                print(f"Invalid command byte: {command_byte}")
