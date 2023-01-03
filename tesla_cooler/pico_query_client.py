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

from machine import I2C, UART, Pin

from tesla_cooler import thermistor
from tesla_cooler.temperature_module import temperature_sensor

BAUD = 115200

COMMAND_EXIT = b"0"
COMMAND_INFO = b"1"
COMMAND_READ_TEMPERATURE = b"2"

CLIENT_INFO = {
    "firmware_version": "1.0.0",
    "zone_count": 2,
    "zone_sensors_type": "Washer Thermistor",
}

# Pin mappings
I2C_SCL_PIN = 21
I2C_SDA_PIN = 20
ADDRESS_1_PIN = 19
ADDRESS_0_PIN = 18

Z1_PIN = 26
Z2_PIN = 27
INTAKE_PIN = 28

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

    if temperature_module_mode:

        address_0 = Pin(ADDRESS_0_PIN, Pin.OUT)
        address_1 = Pin(ADDRESS_1_PIN, Pin.OUT)

        address_0.off()
        address_1.off()

        i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100_000)

        tm_reader = temperature_sensor.create_reader(
            i2c=i2c, tmp1_address=0b1001100, tmp2_address=0b1001110
        )

        def reader() -> TemperatureReading:
            """
            Temperature module reader. When called, reads from the attached temperature module
            and ADCs.
            :return: The `TemperatureReading`.
            """

            temperature_module_readings = tm_reader()

            return TemperatureReading(
                zone_1=temperature_module_readings.tmp1,
                zone_2=temperature_module_readings.tmp2,
                intake=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=INTAKE_PIN,
                    resistance_to_temperature=resistance_to_temp_environment,
                ),
                exhaust=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=INTAKE_PIN,  # TODO: Wrong!
                    resistance_to_temperature=resistance_to_temp_environment,
                ),
            )

    else:

        def reader() -> TemperatureReading:
            """
            ADC Temperature Reader. Looks up temperatures in the provided LUT for the sensor.
            This is likely going to have to change.
            :return: The `TemperatureReading`.
            """

            resistance_to_temp_washer = thermistor.read_resistance_to_temperature(
                lookup_json_path=thermistor.B2585_3984K_10K_JSON_PATH
            )

            return TemperatureReading(
                zone_1=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=Z1_PIN,
                    resistance_to_temperature=resistance_to_temp_washer,
                ),
                zone_2=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=Z2_PIN,
                    resistance_to_temperature=resistance_to_temp_washer,
                ),
                intake=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=INTAKE_PIN,
                    resistance_to_temperature=resistance_to_temp_environment,
                ),
                exhaust=thermistor.rp2040_adc_thermistor_temperature(
                    pin_number=INTAKE_PIN,  # TODO: Wrong!
                    resistance_to_temperature=resistance_to_temp_environment,
                ),
            )

    return reader


def query_loop(temperature_module_mode: bool = False) -> None:
    """
    Entrypoint for the Pico Query client. Waits for messages to arrive on the external UART
    interface and replies in kind. Currently doesn't handle errors well.
    :param temperature_module_mode: If the reported values should be from the temperature module
    via I2C or not (meaning it'll return converted ADC values). This needs to match the physical
    circuit so tread with caution.
    :return: None
    """

    uart_port = UART(0, baudrate=BAUD, tx=Pin(16), rx=Pin(17), bits=8, parity=None, stop=1)
    read_sensors = configure_temperature_reader(temperature_module_mode=temperature_module_mode)

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
