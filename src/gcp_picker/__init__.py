"""
GCP Picker - Ground Control Point Selection Application

A comprehensive PyQt6-based GUI application for selecting ground control points
between test imagery and reference sources with progressive orthorectification.
"""

from ._version import (
    __version__,
    __build_date__,
    __git_hash__,
    get_version_info,
)

__author__ = "GCP Picker Team"
__email__ = "contact@gcp-picker.dev"
__license__ = "MIT"

from .main import main


def get_version_info() -> dict:
    """
    Return version information as a dictionary.

    Returns:
        dict with keys: version, build_date, git_hash
    """
    return _get_version_info()


__all__ = ["main", "get_version_info", "__version__", "__build_date__", "__git_hash__"]
