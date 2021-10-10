"""
Makes sure the helper functions work in a range of cases.
"""

from typing import Dict, List, Tuple

import pytest

from tesla_cooler import fan_speed_control

SIMPLE_WEIGHTS = {
    (1, 5): 1,
    (6, 10): 2,
}


@pytest.mark.parametrize(
    "values,range_to_weight,expected_result",
    [
        (
            (5,),
            SIMPLE_WEIGHTS,
            1,
        ),
        (
            (10,),
            SIMPLE_WEIGHTS,
            2,
        ),
        (
            (10, 10),
            SIMPLE_WEIGHTS,
            4,
        ),
        (
            (1, 8),
            SIMPLE_WEIGHTS,
            3,
        ),
        (
            (5, 10),
            SIMPLE_WEIGHTS,
            3,
        ),
        (
            (5, 10, 0),
            SIMPLE_WEIGHTS,
            3,
        ),
        (
            (0,),  # zero weight is hardcoded in function.
            SIMPLE_WEIGHTS,
            0,
        ),
    ],
)
def test__weigh_values(
    values: Tuple[int, ...], range_to_weight: Dict[Tuple[int, int], int], expected_result: int
) -> None:
    """
    Makes sure the weighing process works as expected.
    :param values: Input.
    :param range_to_weight: Input.
    :param expected_result: Expected output of function under test.
    :return: None
    """
    assert (
        fan_speed_control._weigh_values(  # pylint: disable=protected-access
            values=values, range_to_weight=range_to_weight
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "potential_values,target_length,target_value,tolerance,expected_result",
    [
        (
            (1, 2, 3),
            3,
            3,
            0,
            [
                (3, 0, 0),
                (1, 1, 1),
                (1, 0, 2),
            ],
        ),
        (
            (1, 2, 3),
            3,
            3,
            1,
            [
                (3, 0, 0),  # These three sum to three
                (1, 1, 1),
                (1, 0, 2),
                (0, 0, 2),  # These sum to two
                (0, 1, 1),
                (0, 2, 2),  # These sum to four
                (3, 0, 1),
                (1, 1, 2),
            ],
        ),
        (
            (2, 3),
            3,
            3,
            0,
            [
                (3, 0, 0),
            ],
        ),
        (
            (2, 3, 10),
            3,
            3,
            0,
            [
                (3, 0, 0),
            ],
        ),
    ],
)
def test__combinations_to_sum(
    potential_values: Tuple[int, ...],
    target_length: int,
    target_value: int,
    tolerance: int,
    expected_result: List[Tuple[int, ...]],
) -> None:
    """
    Simple checks to make sure that this is working in principal, will break if underlying ideas
    are violated.
    :param potential_values: Input.
    :param target_length: Input.
    :param target_value: Input.
    :param tolerance: Input.
    :param expected_result:Expected output of function under test.
    :return: None
    """
    combinations = fan_speed_control._combinations_to_sum(  # pylint: disable=protected-access
        potential_values=potential_values,
        target_length=target_length,
        target_value=target_value,
        tolerance=tolerance,
    )

    assert len(combinations) == len(expected_result)
    assert set(combinations) == {tuple(sorted(combo)) for combo in expected_result}
