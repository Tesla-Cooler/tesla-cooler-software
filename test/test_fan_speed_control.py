"""
Test suite.
"""

import tesla_cooler.fan_speed_control


def test__subset_sum() -> None:

    inputs = tuple(range(0, 1010, 10))

    tesla_cooler.fan_speed_control.combinations_to_sum(inputs, 3, 2000, tolerance=100)
    print("stop")
