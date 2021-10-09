"""
Common code used across multiple library modules.
"""

try:
    from typing import Sequence, TypeVar, Union  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


U_16_MAX = 65535


def closest_to_value(
    value: float, list_of_values: "Union[Sequence[int], Sequence[float]]"
) -> "Union[int, float]":
    """
    Given a value, and a list of values, find the closest value in the list to the input.
    :param value: Value to find in list.
    :param list_of_values: Candidate output values.
    :return: The value closest to `value` in `list_of_values`.
    """
    return list_of_values[
        min(range(len(list_of_values)), key=lambda i: abs(list_of_values[i] - value))
    ]
