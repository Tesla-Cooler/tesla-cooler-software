"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342

"""


import rp2
import utime
from machine import Pin, mem32
from rp2 import PIO, asm_pio

SIO_BASE_ADDRESS = 0xD0000000
PIO_BASE_ADDRESSES = (0x50200000, 0x50300000)
FSTAT_MASK = 0x4

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


@asm_pio()
def pulse_length_pio() -> None:  # pylint: disable=all  # type: ignore
    """
    PIO program to read pulse length.

    Given:
        - Clock set at 500Khz, Cycle is 2us
        - Drive output low for at least 20ms

    :return: None
    """

    set(pindirs, 0)  # type: ignore
    set(x, 0)  # type: ignore
    mov(osr, x)  # type: ignore
    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore
    label("loop1")  # type: ignore
    jmp(x_dec, "loop2")  # type: ignore
    label("loop2")  # type: ignore
    jmp(pin, "loop1")  # type: ignore
    mov(isr, x)  # type: ignore
    push()  # type: ignore
    label("done")  # type: ignore
    jmp("done")  # type: ignore


def measure_pulse_duration(
    data_pin: int, state_machine_index: int = 0
) -> "t.Callable[[], t.Optional[int]]":
    """
    Creates a callable to measure the length of a square-wave pulse on a GPIO pin.
    Calling the returned callable will measure the most recent pulse duration in microseconds.

    # TODO: Want to validate `data_pin` and `state_machine_index`, these are really enums.
    :param data_pin: Index of pin attached to the pulse source.
    :param state_machine_index: The PIO state machine index to be used to make the measurements.
    :return: Callable that returns the pulse duration in microseconds.
    """

    cpu_id = mem32[SIO_BASE_ADDRESS]
    fifo_stat_address = PIO_BASE_ADDRESSES[cpu_id] | FSTAT_MASK
    state_machine = rp2.StateMachine(state_machine_index)

    def is_fifo_rx_empty() -> bool:
        """
        Checks to see if the PIO program has finished.
        :return: True if the data is ready to be read, False if otherwise.
        """

        # Shouldn't we be able to do this check with an interrupt/callback rather than having to
        # poll the address directly?
        current_fifo_stat = mem32[fifo_stat_address]

        if state_machine_index == 0:
            output = (current_fifo_stat >> 8) & 1
        elif state_machine_index == 1:
            output = (current_fifo_stat >> 9) & 1
        elif state_machine_index == 2:
            output = (current_fifo_stat >> 10) & 1
        else:
            output = (current_fifo_stat >> 11) & 1

        return bool(output)

    def measure(timeout_us: int = 10000) -> "t.Optional[int]":
        """
        Output Callable.
        :param timeout_us: If a pulse doesn't occur within this amount of time, `None` will be
        returned.
        :return: The pulse duration if a pulse occurs, `None` if otherwise.
        """

        state_machine.init(pulse_length_pio, freq=10000000, in_base=data_pin, jmp_pin=data_pin)
        state_machine.put(0x100)
        state_machine.active(1)

        start = utime.ticks_us()

        while True:
            if (utime.ticks_us() - start) > timeout_us:
                return None
            level = is_fifo_rx_empty()
            if level == 0:
                return int((3 + (0xFFFFFFFF - state_machine.get())) // 5)

    return measure


def main() -> None:
    """
    Entrypoint. Prints pulse duration periodically.
    :return: None
    """

    read_pulse = measure_pulse_duration(data_pin=Pin(0, Pin.IN))

    while True:
        print(f"High side pulse of: {read_pulse()} microseconds detected.")
        utime.sleep_ms(250)


if __name__ == "__main__":
    main()
