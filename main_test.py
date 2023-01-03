"""
Entry point for development.
"""

from tesla_cooler.pico_query_client import query_loop


def main() -> None:
    """
    Run what we're testing.
    :return: None
    """

    query_loop()
