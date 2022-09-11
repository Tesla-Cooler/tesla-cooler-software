"""
Pio/Python interface for generating 'slow' square waves. Can go slower than the rp2040's PWM
interface.
"""

from rp2 import PIO, asm_pio


@asm_pio(set_init=PIO.OUT_LOW)
def square_waver_pio() -> None:
    """
    Reads in a countdown value from the OSR, sets the pin high for that many clock cycles, then
    sets the pin low for the same number of clock cycles.
    You must send a countdown value for waves to start being created.
    :return: None
    """
    # pylint: disable=undefined-variable

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    wrap_target()  # type: ignore

    # If there is nothing in the OSR, the value currently stored in X will be fed in from the OSR.
    pull(noblock)  # type: ignore
    mov(x, osr)  # type: ignore

    mov(y, x)  # type: ignore
    set(pins, 1)  # type: ignore
    label("high_side_wait")  # type: ignore
    jmp(y_dec, "high_side_wait")  # type: ignore

    mov(y, x)  # type: ignore
    set(pins, 0)  # type: ignore
    label("low_side_wait")  # type: ignore
    jmp(y_dec, "low_side_wait")  # type: ignore

    wrap()  # type: ignore


def square_waver_pio_frequency_to_counts(
    state_machine_frequency_hz: int, frequency_hz: float
) -> int:
    """
    Prepares a desired output frequency for use with State Machine's running `square_waver_pio`.
    Converts a frequency in hz to clock cycles.
    :param state_machine_frequency_hz: The frequency the State Machine is running at in Hz.
    :param frequency_hz: The desired output frequency.
    :return: The number of clock cycles to count down.
    """
    return int((state_machine_frequency_hz / frequency_hz) / 2)
