"""
For interacting with the IO expander on the temperature module. This device controls the LEDs and
is responsible for enabling/disabling downstream daisy-chained temperature modules.
"""

import struct

from machine import I2C, Pin

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

PIN_OFFSETS: "t.Dict[str, int]" = {
    field: offset
    for offset, field in enumerate(
        (
            "downstream_address_0",
            "downstream_address_1",
            "downstream_enable_gate",
            "rgb_led_anode",
            "rgb_led_r_cathode",
            "rgb_led_g_cathode",
            "rgb_led_b_cathode",
            "blue_led_1_cathode",
            "emerald_led_1_cathode",
            "yellow_led_1_cathode",
            "red_led_1_cathode",
            "blue_led_2_cathode",
            "emerald_led_2_cathode",
            "yellow_led_2_cathode",
            "red_led_2_cathode",
        ),
        start=1,
    )
}

# Pin mappings
I2C_SCL = 21
I2C_SDA = 20
ADDRESS_1 = 19
ADDRESS_0 = 18

# Values for the command register. See datasheet for details.
COMMAND_REG_INPUT_0 = 0
COMMAND_REG_INPUT_1 = 1
COMMAND_REG_OUTPUT_0 = 2
COMMAND_REG_OUTPUT_1 = 3
COMMAND_REG_POLARITY_INVERSION_0 = 4
COMMAND_REG_POLARITY_INVERSION_1 = 5
COMMAND_REG_CONFIG_0 = 6
COMMAND_REG_CONFIG_1 = 7


def _flags_to_payload(flags: "t.Dict[str, bool]") -> bytes:
    """
    Convert human-readable flags to packed binary values to be sent to the IO expander.
    :param flags: A dict, mapping the name of the output port to which value it should be set to.
    :return: The payload that should be sent to the IO expander via I2C. Includes the command byte.
    """

    bin_packed = sum(value << PIN_OFFSETS[key] for key, value in flags.items())
    unpacked = struct.pack("i", bin_packed)
    return bytearray([COMMAND_REG_OUTPUT_0, unpacked[0], unpacked[1]])


def create_io_writer(i2c: I2C, address: int) -> "t.Callable[[bool], int]":
    """
    Creates a convince wrapper that creates a simple interface for interacting with the IO expander.
    Configured the IO expander for outputting and then provides an interface for doing the writes.
    :param i2c: Configured I2C interface that the IO expander is connected to.
    :param address: The target address of the IO expander.
    :return: Resulting callable takes keyword arguments for each possible port value. If set to
    True, the IO pin on the IO expander will be set high. Not all pins need to be provided.
    """

    # Set all 16 ports to outputs.
    i2c.writeto(address, bytearray([COMMAND_REG_CONFIG_0, 0b00000000, 0b00000000]))

    def create_output_values(  # pylint: disable=too-many-arguments
        downstream_address_0: "t.Optional[bool]" = False,
        downstream_address_1: "t.Optional[bool]" = False,
        downstream_enable_gate: "t.Optional[bool]" = False,
        rgb_led_anode: "t.Optional[bool]" = False,
        rgb_led_r_cathode: "t.Optional[bool]" = True,
        rgb_led_g_cathode: "t.Optional[bool]" = True,
        rgb_led_b_cathode: "t.Optional[bool]" = True,
        blue_led_1_cathode: "t.Optional[bool]" = False,
        emerald_led_1_cathode: "t.Optional[bool]" = False,
        yellow_led_1_cathode: "t.Optional[bool]" = False,
        red_led_1_cathode: "t.Optional[bool]" = False,
        blue_led_2_cathode: "t.Optional[bool]" = False,
        emerald_led_2_cathode: "t.Optional[bool]" = False,
        yellow_led_2_cathode: "t.Optional[bool]" = False,
        red_led_2_cathode: "t.Optional[bool]" = False,
    ) -> int:
        """
        Output function. Converts the human-readable input args to a payload that is written to the
        IO expander.
        :param downstream_address_0: See schematic.
        :param downstream_address_1: See schematic.
        :param downstream_enable_gate: See schematic.
        :param rgb_led_anode: See schematic.
        :param rgb_led_r_cathode: See schematic.
        :param rgb_led_g_cathode: See schematic.
        :param rgb_led_b_cathode: See schematic.
        :param blue_led_1_cathode: See schematic.
        :param emerald_led_1_cathode: See schematic.
        :param yellow_led_1_cathode: See schematic.
        :param red_led_1_cathode: See schematic.
        :param blue_led_2_cathode: See schematic.
        :param emerald_led_2_cathode: See schematic.
        :param yellow_led_2_cathode: See schematic.
        :param red_led_2_cathode: See schematic.
        :return: The number of bytes written to the I2C port.
        """

        return int(
            i2c.writeto(
                address,
                _flags_to_payload(
                    flags={
                        "downstream_address_0": downstream_address_0,
                        "downstream_address_1": downstream_address_1,
                        "downstream_enable_gate": downstream_enable_gate,
                        "rgb_led_anode": rgb_led_anode,
                        "rgb_led_r_cathode": rgb_led_r_cathode,
                        "rgb_led_g_cathode": rgb_led_g_cathode,
                        "rgb_led_b_cathode": rgb_led_b_cathode,
                        "blue_led_1_cathode": blue_led_1_cathode,
                        "emerald_led_1_cathode": emerald_led_1_cathode,
                        "yellow_led_1_cathode": yellow_led_1_cathode,
                        "red_led_1_cathode": red_led_1_cathode,
                        "blue_led_2_cathode": blue_led_2_cathode,
                        "emerald_led_2_cathode": emerald_led_2_cathode,
                        "yellow_led_2_cathode": yellow_led_2_cathode,
                        "red_led_2_cathode": red_led_2_cathode,
                    }
                ),
            )
        )

    return create_output_values


def configured_writer() -> "t.Callable[[bool], int]":
    """
    Given the development pin mappings, configures the IO expander and returns the function to
    control it.
    :return: Control callable.
    """

    address_0 = Pin(ADDRESS_0, Pin.OUT)
    address_1 = Pin(ADDRESS_1, Pin.OUT)

    address_0.off()
    address_1.off()

    return create_io_writer(
        i2c=I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400_000), address=0b0100100
    )
