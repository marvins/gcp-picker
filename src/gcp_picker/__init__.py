"""
GCP Picker - Ground Control Point Selection Application

A comprehensive PyQt6-based GUI application for selecting ground control points 
between test imagery and reference sources with progressive orthorectification.
"""

__version__ = "1.0.0"
__author__ = "GCP Picker Team"
__email__ = "contact@gcp-picker.dev"
__license__ = "MIT"

from .main import main

__all__ = ["main"]
