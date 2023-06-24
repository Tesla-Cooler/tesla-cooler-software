"""
Export high-level controls for the temperature module board.
"""


from time import sleep

from machine import I2C, Pin

from tesla_cooler.temperature_module import io_expander, temperature_sensor
from tesla_cooler.temperature_module.temperature_sensor import TemperatureModuleReadings

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.

# Pin mappings
I2C_SCL = 21
I2C_SDA = 20
ADDRESS_1 = 19
ADDRESS_0 = 18


def configured_temperature_reader() -> "t.Tuple[I2C, t.Callable[[], TemperatureModuleReadings]]":
    """
    Given the current global pin mapping, enable and return a temperature reader.
    :return: A tuple (configured i2c interface, temperature reader).
    """

    address_0 = Pin(ADDRESS_0, Pin.OUT)
    address_1 = Pin(ADDRESS_1, Pin.OUT)

    address_0.off()
    address_1.off()

    i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=100_000)

    return i2c, temperature_sensor.create_reader(
        i2c=i2c, tmp1_address=0b1001_100, tmp2_address=0b1001_110
    )


def proof_of_concept() -> None:
    """

    :return:
    """

    i2c, reader = configured_temperature_reader()

    io_writer = io_expander.create_io_writer(i2c=i2c, address=0b0100100)

    while True:

        flags = io_expander.OutputFlags(rgb_led_anode=True, rgb_led_r_cathode=False)

        current_temperatures = reader()

        print(f"Read Temps: {current_temperatures}")

        for cluster_index, temperature in enumerate(current_temperatures):
            if temperature < 30:
                flags.set_cluster(cluster_index=cluster_index, blue=True)
            elif 30 <= temperature < 40:
                flags.set_cluster(cluster_index=cluster_index, emerald=True)
            elif 40 <= temperature < 50:
                flags.set_cluster(cluster_index=cluster_index, yellow=True)
            elif temperature >= 50:
                flags.set_cluster(cluster_index=cluster_index, red=True)

        io_writer(flags)

        sleep(1)
