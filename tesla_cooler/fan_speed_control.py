"""
Code for controlling fan speed!
TODO - more docs
"""

try:
    from typing import Dict, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


from tesla_cooler import pure_python_itertools

DEFAULT_POWER_MIN, DEFAULT_POWER_MAX = (0.0, 1.0)


def _weigh_values(values: "Tuple[int, ...]", range_to_weight: "Dict[Tuple[int, int], int]") -> int:
    """
    For each of the values in `values`, look up it's weight in `range_to_weight`, the return
    the cumulative sum of all of weights in `values`.

    Note: If a value in `values` is zero, it's resulting weight will be zero.
    :param values: Values to weigh.
    :param range_to_weight: A dictionary that maps possible ranges of `value` to their corresponding
    weights. Both sides of each bound is inclusive! For example, If the value 15 is weighed in the
    following dictionary, it's weight will be 1:
    {
        (10, 20): 1,
        (21, 30): 2,
    }
    :return: The total weight of `values`.
    """
    return sum(
        filter(
            lambda weight: weight is not None,
            [
                0 if value == 0 else (weight if scope_min <= value <= scope_max else None)
                for (scope_min, scope_max), weight in range_to_weight.items()
                for value in values
            ],
        )
    )


def _linear_interpolate(x: float, in_min: float, in_max: float, out_min: int, out_max: int) -> int:
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


def _combinations_to_sum(  # pylint: disable=unused-argument
    potential_values: "Tuple[int, ...]", target_length: int, target_value: int, tolerance: int
) -> "List[Tuple[int, ...]]":
    """
    Finds unique combinations of `potential_values` that are of length `target_length` and sum to
    `target_value`. Combinations that are +/- `tolerance` away from `target_value` are also
    returned. Combinations can include 0.

    This is also called `Partitioning`, or the `Subset Sum` problem. See:
    * https://en.wikipedia.org/wiki/Partition_(number_theory)
    * https://en.wikipedia.org/wiki/Subset_sum_problem

    This approach is EXTREMELY NAIVE! No attempts to optimize performance have been made.
    Instead of speeding this up, `potential_values` is is typically short in length and `tolerance`
    is used to make sure the resulting set is representative.

    :param potential_values: Complete list of candidate values to add together to make
    `target_value`.
    :param target_length: Number of values that can be added together to make `target_value`.
    :param target_value: Value to create.
    :param tolerance: Combinations can be within this tolerance from the actual target and
    be returned.
    :return: A list of tuples that add up to `target_value`.
    """
    target_min = target_value - tolerance
    target_max = target_value + tolerance

    pad = tuple((0 for _ in range(target_length)))

    def pad_to_target_length(tup: "Tuple[int, ...]") -> "Tuple[int, ...]":
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
        pure_python_itertools.chain_from_iterable(
            [
                [
                    pad_to_target_length(combo)
                    for combo in pure_python_itertools.combinations_with_replacement(
                        potential_values, sub_length + 1
                    )
                    if target_min <= sum(combo) <= target_max
                ]
                for sub_length in range(target_length)
            ]
        )
    )

    sorted_valid = [tuple(sorted(combo)) for combo in all_valid]

    return list(set(sorted_valid))


def _ranges_to_stats(output_ranges: "Tuple[Tuple[int, int], ...]") -> "Tuple[int, int]":
    """
    Compute some statistics about the output ranges.
    :param output_ranges: Ranges to find stats for.
    :return: (all values in the ranges, min value of ranges, max value of ranges)
    """
    all_values = list(pure_python_itertools.chain_from_iterable(output_ranges))
    return min(all_values), max(all_values)


def fan_drive_values(
    power: float,
    num_fans: int,
    output_ranges: "Tuple[Tuple[int, int], ...]",
    num_speeds: int,
    power_min: float = DEFAULT_POWER_MIN,
    power_max: float = DEFAULT_POWER_MAX,
) -> "Tuple[int, ...]":
    """
    For a given power (which is by default a float between 0..1), come up with duty cycles for the
    fans that blow at the required power but do it as quietly as possible. The power is converted
    to a sum of duty cycles. This sum is then achieved across the number of fans.
    TODO: This is a complicated function, probably needs better docs.
    :param power: How strong the fans should be blowing.
    :param num_fans: The number of fans to compute duty cycles for.
    :param output_ranges: The different duty cycle ranges that an individual fan can spin at.
    :param num_speeds: Number of possible choices that each fan can spin at to achieve the given
    input power.
    :param power_min: Min value of `power`. If `power` is this value, a single fan will be spinning
    as slowly as possible.
    :param power_max: Max value of `power`. If `power` is this value, all three fans will be
    spinning as quickly as possible.
    :return: A tuple of duty cycles to write to fans.
    """
    min_output, max_output = _ranges_to_stats(output_ranges)

    # The values written to the three fans are trying to spin this quickly.
    # Assumes airflow adds linearly, which we're okay with for our application.
    all_fans_max_output = max_output * num_fans

    target_counts = _linear_interpolate(
        x=power,
        in_min=power_min,
        in_max=power_max,
        out_min=min_output,
        out_max=all_fans_max_output,
    )

    step = (max_output - min_output) // num_speeds

    # This makes the following call to `_combinations_to_sum` easier to compute by limiting
    # the number of inputs to make the combinations.
    speeds = tuple(range(min_output, max_output, step))

    # Combinations of fan speeds that add up to `target_counts`.
    candidate_speeds: "List[Tuple[int, ...]]" = _combinations_to_sum(
        potential_values=speeds, target_length=num_fans, target_value=target_counts, tolerance=step
    )

    # Each subsequent range is ^3 as expensive to use as the previous one.
    # This encodes the behavior that two fans spinning slowly are better than a single
    # fan spinning quickly.
    scope_to_weight = {
        scope: (scope_index + 1) ** 3 for scope_index, scope in enumerate(output_ranges)
    }

    weights_and_speeds = [
        (_weigh_values(values=speeds, range_to_weight=scope_to_weight), speeds)
        for speeds in candidate_speeds
    ]

    # Lowest weight here will be the slowest speed ie. the quietest.
    return min(weights_and_speeds, key=lambda ws: ws[0])[1]
