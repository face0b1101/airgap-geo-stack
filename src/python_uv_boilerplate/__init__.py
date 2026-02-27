"""python_uv_boilerplate: A template project for Python applications using uv.

This package provides a starting point for Python projects with uv,
including basic structure and common utilities.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

try:
    __version__ = pkg_version("python-uv-boilerplate")
except PackageNotFoundError:  # pragma: no cover - only during editable installs
    __version__ = "0.0.0"

# Convenience imports
from .config.env import DEFAULT_TZ, LOG_LEVEL
from .main import something

# If you want to control what's imported with "from package import *"
__all__ = ["DEFAULT_TZ", "LOG_LEVEL", "something"]
