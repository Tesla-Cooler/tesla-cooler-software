"""
Pure-python implementations of a few itertools functions.
Designed to be run on a micropython board, or on a PC.
These are pretty much copied directly from the itertools docs:
https://docs.python.org/3/library/itertools.html
"""

try:
    from typing import Any, Iterable, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass  # we're probably on the pico if this occurs.


def combinations_with_replacement(  # type: ignore
    iterable: "Iterable[Any]", r: int
) -> "Iterable[Tuple[Any]]":
    """
    Return r length subsequences of elements from the input iterable allowing individual elements
    to be repeated more than once.
    The combination tuples are emitted in lexicographic ordering according to the order of the
    input iterable. So, if the input iterable is sorted, the combination tuples will be produced
    in sorted order.
    Elements are treated as unique based on their position, not on their value. So if the input
    elements are unique, the generated combinations will also be unique.
    See: https://docs.python.org/3/library/itertools.html#itertools.combinations_with_replacement
    :param iterable: Iterable to get combinations of.
    :param r: Length of outputs.
    :return: `r` length subsequences of elements from the input iterable allowing individual
    elements to be repeated more than once.
    """

    pool = tuple(iterable)
    n = len(pool)
    if not n and r:
        return
    indices = [0] * r
    yield tuple(pool[i] for i in indices)  # type: ignore
    while True:
        for i in reversed(range(r)):
            if indices[i] != n - 1:
                break
        else:
            return
        indices[i:] = [indices[i] + 1] * (r - i)  # pylint: disable=undefined-loop-variable
        yield tuple(pool[i] for i in indices)  # type: ignore


def chain_from_iterable(iterables: "Iterable[Iterable[Any]]"):  # type: ignore
    """
    Gets chained inputs from a single iterable argument that is evaluated lazily.
    :param iterables: Iterable of Iterables to combine.
    :return: Each element in each input iterable as a single iterable.
    """

    for it in iterables:
        for element in it:
            yield element


def left_rotate_list(tup: "List[Any, ...]") -> "List[Any, ...]":  # type: ignore
    """
    Rotate the items in a tuple to the left one index.
    This isn't in itertools but hey who's keeping track.
    :param tup: Tuple to rotate.
    :return: Rotated tuple.
    """
    return tup[1:] + tup[:1]
