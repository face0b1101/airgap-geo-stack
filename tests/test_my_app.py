#!/usr/bin/env python
"""Unit tests covering the sample boilerplate behaviour."""

from python_uv_boilerplate.libs.my_lib import MyLib
from python_uv_boilerplate.main import hello, something
from rename_project import get_formatted_name


def test_something_with_string(str_input):
    """Return True when a string is provided."""
    assert something(str_input) is True


def test_something_with_input(int_input):
    """Return False for non-string input."""
    assert something(int_input) is False


def test_MyLib():
    """Ensure the sample library performs its placeholder action."""
    my_lib = MyLib()
    assert my_lib.do_something() == "My Lib is doing something!"


def test_hello(caplog):
    """Capture hello() logs via caplog."""
    with caplog.at_level("INFO"):
        hello(input="Hello Stranger!")

    assert "LOG_LEVEL: INFO" in caplog.text
    assert "DEFAULT_TZ: UTC" in caplog.text


def test_get_formatted_name():
    """Exercise the rename helper formatting options."""
    assert get_formatted_name("My App", "_") == "My_App"
    assert get_formatted_name("My App", "-") == "My-App"
