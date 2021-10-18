"""
Sanity check of these functions
"""

from tesla_cooler import linear_interpolate


def test_linterp_int() -> None:
    """
    Makes sure the obvious ones work and that the clamp works.
    :return: None
    """

    assert linear_interpolate.linterp_int(0.5, 0, 1, 0, 100) == 50
    assert linear_interpolate.linterp_int(0.33, 0, 1, 0, 100) == 33
    assert linear_interpolate.linterp_int(1, 0, 1, 0, 100) == 100
    assert linear_interpolate.linterp_int(0, 0, 1, 0, 100) == 0
    assert linear_interpolate.linterp_int(2, 0, 1, 0, 100) == 100
    assert linear_interpolate.linterp_int(-1, 0, 1, 0, 100) == 0


def test_linterp_float() -> None:
    """
    Makes sure the obvious ones work and that the clamp works.
    :return: None
    """

    assert linear_interpolate.linterp_float(0.5, 0, 1, 0, 3) == 1.5
    assert linear_interpolate.linterp_float(0.1, 0, 1, 0, 10) == 1
    assert linear_interpolate.linterp_float(1, 0, 1, 0, 3) == 3
    assert linear_interpolate.linterp_float(0, 0, 1, 0, 3) == 0
    assert linear_interpolate.linterp_float(2, 0, 1, 0, 3) == 3
    assert linear_interpolate.linterp_float(-1, 0, 1, 0, 3) == 0
