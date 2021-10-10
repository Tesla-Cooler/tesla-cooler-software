"""
Sanity checks of the pure python re-implementations against the real things.
"""

import itertools
from typing import Iterable

import pytest

from tesla_cooler import pure_python_itertools


@pytest.mark.parametrize("iterable,r", [([1, 2, 3], 3), ([10, 20, 5], 2)])
def test_combinations_with_replacement(iterable: Iterable[int], r: int) -> None:
    """
    Checks to see that rewrite matches the original in a few cases.
    :param iterable: Input.
    :param r: Input.
    :return: None
    """
    assert list(pure_python_itertools.combinations_with_replacement(iterable, r)) == list(
        itertools.combinations_with_replacement(iterable, r)
    )


def test_chain_from_iterable() -> None:
    """
    Single check is good enough here.
    :return: None
    """
    tuples = [(1, 2, 3), (4, 5, 6)]
    assert list(pure_python_itertools.chain_from_iterable(tuples)) == list(
        itertools.chain.from_iterable(tuples)
    )


def test_left_rotate_list() -> None:
    """
    Did this rotation by hand (lol).
    :return: None
    """
    assert pure_python_itertools.left_rotate_list([1, 2, 3]) == [2, 3, 1]
