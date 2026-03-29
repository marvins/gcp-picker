#!/usr/bin/env python3
"""
GCP Picker - Ground Control Point Selection Application

A GUI application for selecting ground control points between test imagery
and reference sources with progressive orthorectification.
"""

# Standard library imports
import sys
import os
import logging
import argparse
from pathlib import Path

# Third-party imports
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer, Qt
from qtpy.QtWebEngineWidgets import QWebEngineView

# Project imports
from app.main_window import MainWindow

def gdal_data_path():
    return os.path.join(os.path.dirname(__file__), 'gdal_data')

def proj_lib_path():
    return os.path.join(os.path.dirname(__file__), 'proj_lib')

def setup_logging(verbose: bool = False, log_level: int = logging.INFO, log_file: str | None = None):
    """Setup logging configuration with filename and line numbers."""

    # Create formatter with filename and line number
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_path = Path(log_file)
    else:
        file_path = Path(__file__).parent.parent.parent / "gcp_picker.log"

    try:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not setup file logging: {e}")

def qt_message_handler(mode, context, message):
    """Qt message handler to redirect Qt messages to Python logging."""
    logger = logging.getLogger('Qt')

    # Use the properly imported Qt message constants
    if mode == QtDebugMsg:
        logger.debug(f"{context.file}:{context.function}:{context.line} - {message}")
    elif mode == QtInfoMsg:
        logger.info(f"{context.file}:{context.function}:{context.line} - {message}")
    elif mode == QtWarningMsg:
        logger.warning(f"{context.file}:{context.function}:{context.line} - {message}")
    elif mode == QtCriticalMsg:
        logger.critical(f"{context.file}:{context.function}:{context.line} - {message}")
    elif mode == QtFatalMsg:
        logger.error(f"{context.file}:{context.function}:{context.line} - {message}")

def parse_arguments():
    """Parse command line arguments using argparse."""
    parser = argparse.ArgumentParser(
        prog='gcp-picker',
        description='Ground Control Point Selection Application with progressive orthorectification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gcp-picker                    # Start with default settings
  gcp-picker --verbose          # Enable verbose logging
  gcp-picker --log-level DEBUG  # Set specific log level
  gcp-picker --config custom.json  # Use custom configuration
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (equivalent to --log-level DEBUG)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Log to specific file (default: gcp_picker.log in project root)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to custom configuration file'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='GCP Picker 1.0.0'
    )

    return parser.parse_args()

def main():
    """Main entry point for the GCP Picker application."""

    # Parse command line arguments
    args = parse_arguments()

    # Determine log level
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, args.log_level)

    # Setup logging
    setup_logging(verbose=args.verbose, log_level=args.log_level, log_file=args.log_file)
    logger = logging.getLogger(__name__)

    logger.info("Starting GCP Picker application")
    logger.debug(f"Command line arguments: {args}")

    # Set up GDAL environment
    os.environ['GDAL_DATA'] = gdal_data_path()
    os.environ['PROJ_LIB'] = proj_lib_path()
    logger.debug(f"GDAL_DATA: {gdal_data_path()}")
    logger.debug(f"PROJ_LIB: {proj_lib_path()}")

    # Initialize Qt application with proper attributes for QtWebEngine
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    app = QApplication(sys.argv)

    logger.info("Qt application initialized")

    # Configure QtWebEngine settings
    try:
        # Create a temporary web view to access settings
        temp_view = QWebEngineView()
        settings = temp_view.settings()

        # Skip QtWebEngine settings configuration - not essential
        logger.info("Skipping QtWebEngine settings configuration")
        temp_view.deleteLater()
    except Exception as e:
        logger.warning(f"Could not configure QtWebEngine settings: {e}")

    # Create and show main window
    logger.info("Creating main window")
    main_window = MainWindow()
    main_window.show()

    logger.info("Application ready - entering main event loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
