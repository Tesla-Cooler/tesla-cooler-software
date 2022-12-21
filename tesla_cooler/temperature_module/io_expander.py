"""
For interacting with the IO expander on the temperature module. This device controls the LEDs and
is responsible for enabling/disabling downstream daisy-chained temperature modules.
"""

import struct

from machine import I2C

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

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


class OutputFlags:  # pylint: disable=too-many-instance-attributes
    """
    Convert human-readable flags to packed binary values to be sent to the IO expander.
    I really wish I could implement this with enums/other immutable data structures but these
    aren't currently available in micropython.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-locals
        self: "OutputFlags",
        downstream_address_0: bool = False,
        downstream_address_1: bool = False,
        downstream_enable_gate: bool = False,
        rgb_led_anode: bool = False,
        rgb_led_r_cathode: bool = True,
        rgb_led_g_cathode: bool = True,
        rgb_led_b_cathode: bool = True,
        blue_led_1_cathode: bool = False,
        emerald_led_1_cathode: bool = False,
        yellow_led_1_cathode: bool = False,
        red_led_1_cathode: bool = False,
        blue_led_2_cathode: bool = False,
        emerald_led_2_cathode: bool = False,
        yellow_led_2_cathode: bool = False,
        red_led_2_cathode: bool = False,
    ) -> None:
        """
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
        """

        self.downstream_address_0 = downstream_address_0
        self.downstream_address_1 = downstream_address_1
        self.downstream_enable_gate = downstream_enable_gate
        self.rgb_led_anode = rgb_led_anode
        self.rgb_led_r_cathode = rgb_led_r_cathode
        self.rgb_led_g_cathode = rgb_led_g_cathode
        self.rgb_led_b_cathode = rgb_led_b_cathode
        self.blue_led_1_cathode = blue_led_1_cathode
        self.emerald_led_1_cathode = emerald_led_1_cathode
        self.yellow_led_1_cathode = yellow_led_1_cathode
        self.red_led_1_cathode = red_led_1_cathode
        self.blue_led_2_cathode = blue_led_2_cathode
        self.emerald_led_2_cathode = emerald_led_2_cathode
        self.yellow_led_2_cathode = yellow_led_2_cathode
        self.red_led_2_cathode = red_led_2_cathode

    def set_cluster(
        self: "OutputFlags",
        cluster_index: int,
        blue: bool = False,
        emerald: bool = False,
        yellow: bool = False,
        red: bool = False,
    ) -> None:
        """
        Set the red/emerald/blue LEDs by cluster. Modifies the internal state of the flags.
        :param cluster_index: 0 are the LEDs near TMP1, and 1 are the LEDs near TMP2
        :param blue: The value the Blue LED should be set to.
        :param emerald: The value the Emerald LED should be set to.
        :param yellow: The value the Yellow LED should be set to.
        :param red: The value the Red LED should be set to.
        :return: None
        """

        if cluster_index == 0:
            self.blue_led_1_cathode = blue
            self.emerald_led_1_cathode = emerald
            self.yellow_led_1_cathode = yellow
            self.red_led_1_cathode = red
        elif cluster_index == 1:
            self.blue_led_2_cathode = blue
            self.emerald_led_2_cathode = emerald
            self.yellow_led_2_cathode = yellow
            self.red_led_2_cathode = red
        else:
            raise ValueError(f"Invalid Cluster Index: {cluster_index}")

    def render_payload(self: "OutputFlags") -> bytes:
        """
        Render the current state of the flags into bytes to be written to the IO expander.
        :return: 3 Bytes. The command byte, then the two bytes that comprise the port values.
        """

        bin_packed = sum(
            value << offset
            for offset, value in enumerate(
                (
                    self.downstream_address_0,
                    self.downstream_address_1,
                    self.downstream_enable_gate,
                    self.rgb_led_anode,
                    self.rgb_led_r_cathode,
                    self.rgb_led_g_cathode,
                    self.rgb_led_b_cathode,
                    self.blue_led_1_cathode,
                    self.emerald_led_1_cathode,
                    self.yellow_led_1_cathode,
                    self.red_led_1_cathode,
                    self.blue_led_2_cathode,
                    self.emerald_led_2_cathode,
                    self.yellow_led_2_cathode,
                    self.red_led_2_cathode,
                ),
                start=1,  # the 0th port on the IO expander isn't used.
            )
        )

        unpacked = struct.pack("i", bin_packed)

        return bytearray([COMMAND_REG_OUTPUT_0, unpacked[0], unpacked[1]])


def create_io_writer(i2c: I2C, address: int) -> "t.Callable[[OutputFlags], int]":
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

    def create_output_values(flags: OutputFlags) -> int:  # pylint: disable=too-many-arguments
        """
        Output function. Converts the human-readable input args to a payload that is written to the
        IO expander.
        :return: The number of bytes written to the I2C port.
        """

        return int(i2c.writeto(address, flags.render_payload()))

    return create_output_values
