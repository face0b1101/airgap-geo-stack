#!/usr/bin/env python
"""Shared pytest fixtures for the sample application."""

import pytest


@pytest.fixture
def str_input():
    """Return a string input for testing purposes.

    Returns:
        str: The string input "Hello World!".
    """
    return "Hello World!"


@pytest.fixture
def int_input():
    """Return an integer input value.

    Returns:
        int: The integer input value.
    """
    return 23
