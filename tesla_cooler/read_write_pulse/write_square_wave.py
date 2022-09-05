"""
Pio/Python interface for generating 'slow' square waves. Can go slower than the rp2040's PWM
interface.

TODO: Finish these implementations.
"""

import rp2
from machine import Pin
from rp2 import PIO, asm_pio

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    # we're probably on the pico if this occurs.
    pass


@asm_pio(set_init=(PIO.OUT_LOW,), fifo_join=PIO.JOIN_TX)
def slow_square_pio() -> None:
    """

    :return: None
    """
    # pylint: disable=undefined-variable

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    wrap_target()  # type: ignore

    pull(noblock)  # type: ignore
    mov(x, osr)  # type: ignore

    mov(y, osr)  # type: ignore
    label("high_side_wait")  # type: ignore
    set(pins, 1)  # type: ignore
    jmp(y_dec, "high_side_wait")  # type: ignore

    mov(y, osr)  # type: ignore
    label("low_side_wait")  # type: ignore
    set(pins, 0)  # type: ignore
    jmp(y_dec, "low_side_wait")  # type: ignore

    wrap()  # type: ignore


def square_waver(
    output_pin: Pin,
    state_machine_index: int,
) -> "t.Callable[[int], None]":
    """

    :param output_pin:
    :param state_machine_index:
    :return:
    """

    state_machine = rp2.StateMachine(
        state_machine_index, prog=slow_square_pio, set_base=output_pin, freq=50_000
    )

    state_machine.active(1)

    def change_frequency(frequency: int) -> None:
        """

        :param frequency:
        :return:
        """
        state_machine.put(frequency - 2)

    return change_frequency
