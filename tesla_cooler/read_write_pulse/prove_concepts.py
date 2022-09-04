"""
Proves out each of the individual concepts used to actually measure pulses. Completed as an
exercise to improve my understanding.
"""

import rp2
from machine import Pin
from rp2 import asm_pio

try:
    import typing as t  # pylint: disable=unused-import
except ImportError:
    # we're probably on the pico if this occurs.
    pass

PICO_CLOCK_FREQUENCY_HZ = int(1.25e8)


@asm_pio(sideset_init=rp2.PIO.OUT_LOW)
def create_square_wave() -> None:
    """
    Simple PIO to measure how accurately the PIO can create a square wave
    :return: None
    """
    # pylint: disable=undefined-variable

    wrap_target()  # type: ignore
    nop().side(1)  # type: ignore
    nop().side(0)  # type: ignore
    wrap()  # type: ignore


def invoke_create_square_wave() -> None:
    """
    Interacts with the `create_square_wave` PIO program.
    :return: None
    """

    state_machine = rp2.StateMachine(
        0,
        prog=create_square_wave,
        sideset_base=Pin(1),
        freq=PICO_CLOCK_FREQUENCY_HZ,
    )

    state_machine.active(1)

    while True:
        pass


@asm_pio()
def return_input() -> None:
    """
    Demonstrates that a state machine can send an unmodified input back to the user's program.
    :return: None
    """
    # pylint: disable=undefined-variable

    wrap_target()  # type: ignore

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore
    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def invoke_return_input() -> None:
    """
    Interacts with the `return_input` PIO program.
    :return: None
    """

    state_machine = rp2.StateMachine(
        0,
        prog=return_input,
        freq=PICO_CLOCK_FREQUENCY_HZ,
    )

    state_machine.active(1)
    input_value = 0xFFFFFFFF

    while True:
        state_machine.put(input_value)
        output_value = state_machine.get()
        print(
            f"Sent: {input_value}, Received: {output_value}, Equal? {input_value == output_value}"
        )


@asm_pio()
def modify_input() -> None:
    """
    Demonstrates that a state machine can modify an input from the user and return it to their
    program.
    :return: None
    """
    # pylint: disable=undefined-variable

    wrap_target()  # type: ignore

    set(y, 31)  # type: ignore

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore

    label("count return")  # type: ignore
    jmp(y_dec, "dec x")  # type: ignore
    jmp("write output")  # type: ignore
    label("dec x")  # type: ignore
    jmp(x_dec, "count return")  # type: ignore
    label("write output")  # type: ignore
    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def invoke_modify_input() -> None:
    """
    Interacts with the `modify_input` PIO program.
    :return: None
    """

    state_machine = rp2.StateMachine(
        0,
        prog=modify_input,
        freq=PICO_CLOCK_FREQUENCY_HZ,
    )

    state_machine.active(1)
    input_value = 0xFFFFFFFF

    while True:
        state_machine.put(input_value)
        output_value = state_machine.get()
        correct = output_value == input_value - 31
        print(f"Sent: {input_value}, Received: {output_value}, Correct? {correct}")


@asm_pio(set_init=rp2.PIO.OUT_LOW)
def high_for_count() -> None:
    """
    Reads in a value from the TX FIFO, and counts down from this number to zero.
    While the SM is counting down, the `set` pin will be high. Once it reaches zero `set` pin will
    go low. For 32 counts after the the countdown has been completed, the `set` pin will be low.
    :return: None
    """
    # pylint: disable=undefined-variable

    pull(block)  # type: ignore
    mov(y, osr)  # type: ignore
    mov(x, y)  # type: ignore

    wrap_target()  # type: ignore

    set(pins, 1)  # type: ignore
    label("high")  # type: ignore
    jmp(x_dec, "high")  # type: ignore
    set(pins, 0)  # type: ignore

    set(x, 31)  # type: ignore
    label("low")  # type: ignore
    jmp(x_dec, "low")  # type: ignore

    mov(x, y)  # type: ignore

    wrap()  # type: ignore


def invoke_countdown_timer() -> None:
    """
    Interacts with the `high_for_count` PIO program.
    :return: None
    """

    state_machine = rp2.StateMachine(
        0, prog=high_for_count, freq=PICO_CLOCK_FREQUENCY_HZ, set_base=(Pin(1))
    )

    state_machine.active(1)
    input_value = 62
    state_machine.put(input_value)

    while True:
        pass


@asm_pio()
def pulse_period() -> None:
    """
    Measures the amount of time in clock cycles an input pulse is high for by decrementing a value
    stored in the x scratch register.
    :return: None
    """
    # pylint: disable=undefined-variable

    pull(block)  # type: ignore
    mov(y, osr)  # type: ignore

    wrap_target()  # type: ignore

    mov(x, y)  # type: ignore

    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    # Wait for a falling edge.
    label("decrement")  # type: ignore
    jmp(x_dec, "decremented")  # type: ignore
    label("decremented")  # type: ignore
    jmp(pin, "decrement")  # type: ignore

    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def invoke_pulse_period() -> None:
    """
    Interacts with the `pulse_period` PIO program.
    :return: None
    """

    freq = int(1.25e8)

    state_machine = rp2.StateMachine(0, prog=pulse_period, freq=freq, jmp_pin=Pin(0))

    state_machine.active(1)

    input_value = 0xFFFFFFFF
    state_machine.put(input_value)

    while True:
        pio_output = state_machine.get()
        print(f"Input: {input_value}, Output: {pio_output}, Diff: {input_value - pio_output}")


@asm_pio()
def measure_pulse() -> None:
    """
    Measures the duration of the high pulse, stores this in `x`, measures the duration of the low
    side of the square wave, stores this in `y`. These values are then pushed out in two successive
    `push` operations.

    Note that it takes two clock cycles to detect the wave initially going low, and then 3 for it
    going high again. This is handled in the python side of the program, but getting the true
    system clock counts needs a multiple of 2,3 respectively.
    :return: None
    """
    # pylint: disable=undefined-variable

    wrap_target()  # type: ignore

    pull(block)  # type: ignore
    mov(x, osr)  # type: ignore
    mov(y, x)  # type: ignore

    wait(0, pin, 0)  # type: ignore
    wait(1, pin, 0)  # type: ignore

    # Wait for a falling edge.
    label("decrement")  # type: ignore
    jmp(x_dec, "decremented")  # type: ignore
    label("decremented")  # type: ignore
    jmp(pin, "decrement")  # type: ignore

    # Wait for another rising edge.
    label("still low")  # type: ignore
    jmp(y_dec, "pin check")  # type: ignore
    label("pin check")  # type: ignore
    jmp(pin, "high found")  # type: ignore
    jmp("still low")  # type: ignore
    label("high found")  # type: ignore

    in_(x, 32)  # type: ignore
    push(block)  # type: ignore

    in_(y, 32)  # type: ignore
    push(block)  # type: ignore

    wrap()  # type: ignore


def list_mean(values: "t.List[int]") -> float:
    """
    Get the mean of a list of numbers.
    :param values: Either ints or floats.
    :return: The mean of the input list.
    """
    return float(sum(values) / len(values))


def invoke_measure_pulse() -> None:
    """
    Interacts with the `measure_pulse` PIO program.
    :return: None
    """

    freq = int(1.25e8)

    state_machine = rp2.StateMachine(0, prog=measure_pulse, freq=freq, jmp_pin=Pin(0))

    state_machine.active(1)
    input_value = 0xFFFFFFFF

    while True:

        a_s = []
        b_s = []

        for _ in range(100):
            state_machine.put(input_value)
            a_s.append((input_value - state_machine.get()) * 2)
            b_s.append((input_value - state_machine.get()) * 3)

        a_average = list_mean(a_s)
        b_average = list_mean(b_s)
        total = a_average + b_average

        total_period = total * (1 / freq)

        frequency_khz = (1 / total_period) / 1e3

        o_raw_values = ("{:.5f}".format(a_average), "{:.5f}".format(b_average))
        o_freq = "{:.5f}".format(frequency_khz)
        o_duty = "{:.3f}".format(a_average / total)

        print(f"Values from PIO (a, b): {o_raw_values}, Frequency (KHz): {o_freq}, Duty: {o_duty}")
