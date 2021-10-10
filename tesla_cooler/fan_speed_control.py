"""
Code for controlling fan speed!
TODO - more docs
"""

import itertools
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt

POWER_MIN, POWER_MAX = (0.0, 1.0)


WEIGHT_RANGES = (
    (1000, 20_000),  # Makes no noise.
    (20_001, 30_000),
    (30_001, 40_000),  # Makes some noise.
    (40_001, 50_000),  # Makes a lot of noise.
    (50_001, 60_000),  # Makes a lot of noise.
    (60_001, 65_025),
)


def weigh_values(values: Sequence[int], scope_to_weight: Dict[Tuple[int, int], int]) -> int:
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
    potential_values: Tuple[int, ...], target_length: int, target_value: int, tolerance
) -> List[Tuple[int, ...]]:
    """
    Combinations that are +/- `tolerance` away from `target_value` are also considered.

    :param potential_values: Complete list of candidate values to add together to make
    `target_value`.
    :param target_length: Number of values that can be added together to make `target_value`.
    :param target_value: Value to create.
    :return: A list of tuples that add up to `target_value`.
    """

    target_min = target_value - tolerance
    target_max = target_value + tolerance

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
                    if target_min <= sum(combo) <= target_max
                ]
                for sub_length in range(target_length)
            ]
        )
    )

    sorted_valid = [tuple(sorted(combo)) for combo in all_valid]

    return list(set(sorted_valid))


def quietest_drive_values(
    power: float,
    num_fans: int,
    output_ranges: Tuple[Tuple[int, int], ...],
    num_speeds: int,
    power_min: float = POWER_MIN,
    power_max: float = POWER_MAX,
) -> Tuple[int, ...]:

    all_values = list(itertools.chain.from_iterable(output_ranges))
    min_output = min(all_values)
    max_output = max(all_values)

    all_fans_max_output = max_output * num_fans

    target_counts = linear_interpolate(
        x=power,
        in_min=power_min,
        in_max=power_max,
        out_min=min_output,
        out_max=all_fans_max_output,
    )

    step = (max_output - min_output) // num_speeds

    speeds = tuple(range(min_output, max_output, step))

    candidate_speeds: List[Tuple[int, ...]] = combinations_to_sum(
        potential_values=speeds, target_length=num_fans, target_value=target_counts, tolerance=step
    )

    scope_to_weight = {
        scope: (scope_index + 1) ** 3 for scope_index, scope in enumerate(output_ranges)
    }

    weights_and_speeds = [
        (weigh_values(values=speeds, scope_to_weight=scope_to_weight), speeds)
        for speeds in candidate_speeds
    ]

    output = min(weights_and_speeds, key=lambda ws: ws[0])[1]
    return output


if __name__ == "__main__":

    powers = [power / 10000 for power in list(range(0, 10001, 1))]

    x_values = range(len(powers))

    def log(power):
        return quietest_drive_values(
            power=power, num_fans=3, output_ranges=WEIGHT_RANGES, num_speeds=50
        )

    fan_speeds = [log(power) for power in powers]

    speeds_per_fan = list(zip(*fan_speeds))

    fig, ax = plt.subplots()

    for fan_index, fs in enumerate(speeds_per_fan):

        if fan_index > 0:
            previous_speeds = speeds_per_fan[0:fan_index]
            bottom = [sum(values) for values in zip(*previous_speeds)]
        else:
            bottom = None

        ax.bar(x_values, fs, bottom=bottom, label=f"Fan #{fan_index}", width=1.0)

    ax.legend()

    fig.savefig("test.png")
    plt.show()
