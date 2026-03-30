"""
GCP Picker - Ground Control Point Selection Application

A comprehensive PyQt6-based GUI application for selecting ground control points
between test imagery and reference sources with progressive orthorectification.
"""

from pathlib import Path
import tomllib

# Import version info from generated file
from ._version import (
    __version__,
    __build_date__,
    __git_hash__,
    get_version_info,
)

# Read author info from pyproject.toml (source of truth)
_pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
with open(_pyproject_path, "rb") as f:
    _pyproject_data = tomllib.load(f)

_project = _pyproject_data["project"]
_authors = _project["authors"]
__author__ = _authors[0]["name"]
__email__ = _authors[0]["email"]
__license__ = _project["license"]["file"]

from .main import main

__all__ = ["main", "get_version_info", "__version__", "__build_date__", "__git_hash__", "__author__", "__email__", "__license__"]
