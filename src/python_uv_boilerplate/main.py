#!/usr/bin/env python
"""Sample entry points for python_uv_boilerplate."""

import logging

from rich import print
from rich.logging import RichHandler

from python_uv_boilerplate import DEFAULT_TZ, LOG_LEVEL


def something(input: str) -> bool:
    """Return True when the placeholder receives a string.

    Swap this function out when wiring real domain behaviour so tests stay meaningful.

    Args:
        input (str): Any input string

    Returns:
        bool: Boolean indicating whether the function was successful or not
    """
    return isinstance(input, str)


def hello(input: str = "Hello World!") -> None:
    """Main entry point for the application."""
    # setup basic logging
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(module)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        level=LOG_LEVEL.upper(),
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    logging.info(f"LOG_LEVEL: {logging.getLevelName(logging.root.level)}")
    logging.info(f"DEFAULT_TZ: {DEFAULT_TZ}")

    if something(input):
        print(input)
    else:
        print("Nope!")


if __name__ == "__main__":
    hello(input="Hello Stranger!")
