"""
Function used in a few places.

Works like Arduino's `map`, thanks to this post for the port:
https://forum.micropython.org/viewtopic.php?f=2&t=7615
"""

try:
    from typing import Union  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def _clamp(
    x: Union[int, float], out_min: Union[int, float], out_max: Union[int, float]
) -> Union[int, float]:
    """
    Truncates x to the given bounds.
    :param x: Value to truncate.
    :param out_min: Lower bound.
    :param out_max: Upper bound.
    :return: Truncated value... or not.
    """

    return max(min(x, out_max), out_min)


def linterp_int(x: float, in_min: float, in_max: float, out_min: int, out_max: int) -> int:
    """
    Output will be an int! Note output is truncated if outside of output bounds.
    :param x: Value to scale.
    :param in_min: Minimum bound of input.
    :param in_max: Max bound of input.
    :param out_min: Minimum output.
    :param out_max: Maximum output.
    :return: Scaled value in the space between `out_min` and `out_max`.
    """
    raw = (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min
    return int(_clamp(raw, out_min, out_max))


def linterp_float(x: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """
    Output will be a float! Note output is truncated if outside of output bounds.
    :param x: Value to scale.
    :param in_min: Minimum bound of input.
    :param in_max: Max bound of input.
    :param out_min: Minimum output.
    :param out_max: Maximum output.
    :return: Scaled value in the space between `out_min` and `out_max`.
    """
    raw = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return float(_clamp(raw, out_min, out_max))
