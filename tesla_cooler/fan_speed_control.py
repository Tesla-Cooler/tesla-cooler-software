"""
Code for controlling fan speed!
TODO - more docs
"""

import itertools
from typing import Dict, List, Sequence, Tuple


def total_weight(values: Sequence[int], scope_to_weight: Dict[Tuple[int, int], int]) -> int:
    """

    :param values:
    :param scope_to_weight:
    :return:
    """

    return sum(
        filter(
            lambda weight: weight is not None,
            [
                0 if value == 0 else (weight if scope_min <= value <= scope_max else None)
                for (scope_min, scope_max), weight in scope_to_weight.items()
                for value in values
            ],
        )
    )


def linear_interpolate(x: float, in_min: float, in_max: float, out_min: int, out_max: int) -> int:
    """
    Works like Arduino's `map`, thanks to this post for the port:
    https://forum.micropython.org/viewtopic.php?f=2&t=7615
    :param x: Value to scale.
    :param in_min: Minimum bound of input.
    :param in_max: Max bound of input.
    :param out_min: Minimum output.
    :param out_max: Maximum output.
    :return: Scaled value in the space between `out_min` and `out_max`.
    """
    return int((x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)


def combinations_to_sum(  # pylint: disable=unused-argument
    potential_values: Tuple[int, ...], target_length: int, target_value: int
) -> List[Tuple[int, ...]]:
    """
    TODO!
    :param potential_values: Complete list of candidate values to add together to make
    `target_value`.
    :param target_length: Number of values that can be added together to make `target_value`.
    :param target_value: Value to create.
    :return: A list of tuples that add up to `target_value`.
    """

    pad = tuple((0 for _ in range(target_length)))

    def zero_pad(tup: Tuple[int, ...]) -> Tuple[int, ...]:
        """
        If the input tuple is less than the target length, add zeros to the tuple until it
        reaches the length.
        :param tup: Tuple to potentially modify.
        :return: Tuple padded to length.
        """

        if len(tup) < target_length:
            return (tup + pad)[:target_length]
        else:
            return tup

    all_valid = list(
        itertools.chain.from_iterable(
            [
                [
                    zero_pad(combo)
                    for combo in itertools.combinations_with_replacement(
                        potential_values, sub_length + 1
                    )
                    if sum(combo) == target_value
                ]
                for sub_length in range(target_length)
            ]
        )
    )

    sorted_valid = [tuple(sorted(combo)) for combo in all_valid]

    return list(set(sorted_valid))
