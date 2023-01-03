"""
Entry point for development.
"""

from tesla_cooler.mcp_3008 import loop_read


def main() -> None:
    """
    Run what we're testing.
    :return: None
    """

    loop_read()
