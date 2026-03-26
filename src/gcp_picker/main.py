#!/usr/bin/env python3
"""
GCP Picker - Ground Control Point Selection Application

A GUI application for selecting ground control points between test imagery
and reference sources with progressive orthorectification.
"""

import sys
import os
from pathlib import Path
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer

from app.main_window import MainWindow

def main():
    """Main entry point for the GCP Picker application."""

    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("GCP Picker - Ground Control Point Selection Application")
        print("Usage: gcp-picker [options]")
        print("Options:")
        print("  --help, -h    Show this help message")
        print("\nA GUI application for selecting ground control points between")
        print("test imagery and reference sources with progressive orthorectification.")
        return

    # Set up GDAL environment variables for better performance
    os.environ['GDAL_CACHEMAX'] = '512'
    os.environ['GDAL_DATA'] = os.path.join(os.path.dirname(__file__), 'gdal_data')

    app = QApplication(sys.argv)
    app.setApplicationName("GCP Picker")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    main_window = MainWindow()
    main_window.show()

    # Process pending events to ensure proper initialization
    QTimer.singleShot(0, main_window.post_init)

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
