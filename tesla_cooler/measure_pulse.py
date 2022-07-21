"""
Use PIO to measure properties of square waves.

Adapted from a post by `danjperrorn` on the micropython forum:
    https://forum.micropython.org/viewtopic.php?f=21&t=9895#p55342

"""


import rp2
import uasyncio
from machine import Pin, mem32
from rp2 import PIO, asm_pio

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


@asm_pio()
def pulse_length_pio() -> None:  # pylint: disable=all
    """
    PIO program to read pulse length.

    Given:
        - Clock set at 500Khz, Cycle is 2us
        - Drive output low for at least 20ms

    :return: None
    """

    # Set the pin as an input
    set(pindirs, 0)  # type: ignore

    wrap_target()  # type: ignore

    # Wait for the CPU to send us a byte. This is how we're signaled to start looking for
    # Pulses.
    pull(block)  # type: ignore

    # Set the x scratch register to 0
    set(x, 0)  # type: ignore

    # Wait for the input pin to go low, then to go high.
    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    label("wait_for_low")  # type: ignore

    # Decrease the value of x by a single count.
    # If this value is non-zero, go to the loop 2 label.
    # If this value is zero, do nothing.
    jmp(x_dec, "x_decremented")  # type: ignore
    label("x_decremented")  # type: ignore

    # If the pin is still high, loop back around to loop1
    # This means we'll keep counting down x until the pin goes low.
    # Once the pin goes low, we'll move onto the next instruction.
    jmp(pin, "wait_for_low")  # type: ignore

    # The pin has gone low, and x represents how many clock cycles it took to complete.
    # Push the current value of x onto the input shift register.
    # The input shift register is connected to the RX FIFO, so this value will be transferred
    # out from the state machine to the CPU.
    mov(isr, x)  # type: ignore

    # Push the contents of the contents of the ISR into the RX FIFO
    push()  # type: ignore

    # Signal the CPU that we've read a pulse.
    irq(block)  # type: ignore

    wrap()  # type: ignore


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

    lock = uasyncio.Lock()
    lock.acquire()

    state_machine = rp2.StateMachine(state_machine_index)
    state_machine.init(pulse_length_pio, freq=10000000, in_base=data_pin)
    state_machine.irq(handler=lambda pio: lock.release())

    state_machine.active(1)

    def measure(timeout_us: int = 10000) -> "t.Optional[int]":  # pylint: disable=unused-argument
        """
        Output Callable.
        TODO: Implement timeout
        :param timeout_us: If a pulse doesn't occur within this amount of time, `None` will be
        returned.
        :return: The pulse duration if a pulse occurs, `None` if otherwise.
        """

        # Push a single byte into the StateMachine's fifo, to signal it to read a waveform.
        state_machine.put(0x0)

        # Only the interrupt at the end of the pio program can unlock this lock, so we'll
        # wait around until it's ready.
        lock.acquire()

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


if __name__ == "__main__":
    main()
