#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2025 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    main.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Pointy-McPointface - Main Entry Point
"""

#  Python Standard Libraries
import os
import sys
import logging
import argparse
import traceback
from pathlib import Path

#  Third-Party Libraries
from qtpy.QtWidgets import QApplication, QSplashScreen
from qtpy.QtCore import qInstallMessageHandler, QtMsgType, QMessageLogContext, Qt
from qtpy.QtGui import QPixmap, QIcon

#  Project Libraries
from pointy.core.config_manager import get_config_manager
from pointy.main_window import Main_Window
from pointy import __version__
from pointy import get_main_window
from pointy.resources import resources
from pointy.widgets.splash_screen import Splash_Manager
from tmns.geo.terrain import Manager as Terrain_Manager, Catalog, get_default_manager

def qt_message_handler(mode, context, message):
    """Qt message handler to force crashes in the Qt event loop."""
    if mode == QtMsgType.QtCriticalMsg or mode == QtMsgType.QtFatalMsg:
        raise RuntimeError(message)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pointy-McPointface - Where Coordinates Get Pointy!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pointy-mcpointface
  pointy-mcpointface -c collection.toml
  pointy-mcpointface --collection collection.toml --verbose
        """
    )

    parser.add_argument(
        "-c", "--collection",
        type=str,
        help="Load a collection configuration file on startup"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""

    level = logging.DEBUG if verbose else logging.INFO

    # Create formatters
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

    # Setup handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("pointy.log")
    file_handler.setLevel(logging.DEBUG)  # Always debug to file
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress verbose debug messages
    logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
    logging.getLogger("rasterio.env").setLevel(logging.WARNING)
    logging.getLogger("rasterio._base").setLevel(logging.WARNING)
    logging.getLogger("rasterio._io").setLevel(logging.WARNING)
    logging.getLogger("rasterio._filepath").setLevel(logging.WARNING)
    logging.getLogger("rasterio._env").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Starting Pointy-McPointface application")


def main():
    """Main entry point for Pointy-McPointface."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(verbose=args.verbose)

    logger = logging.getLogger(__name__)

    # Install Qt message handler to catch Qt errors
    qInstallMessageHandler(qt_message_handler)

    # Install exception hook to catch all unhandled exceptions during the Qt event loop.
    # Wrapped defensively: logger and Qt may be unavailable if the hook fires during teardown.
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        try:
            logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            pass
        os._exit(1)

    sys.excepthook = exception_hook

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Pointy-McPointface")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Terminus LLC")

    # Set application icon globally
    app_icon = resources.get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Initialize terrain manager
    terrain_manager = None
    try:
        # Get application settings from config
        config_manager = get_config_manager()
        app_settings = config_manager.get_application_settings()

        # Check if auto-fetch elevation is enabled
        if app_settings and app_settings.auto_fetch_elevation:
            terrain_manager = get_default_manager()
            if terrain_manager and terrain_manager.sources:
                total_sources = sum(len(catalog.sources) for catalog in terrain_manager.sources)
                logger.info(f"Terrain manager initialized with {total_sources} sources (auto-fetch enabled)")
            else:
                logger.warning("Terrain manager initialized but no terrain sources available")
        else:
            logger.info("Auto-fetch elevation disabled in configuration")
    except Exception as e:
        logger.error(f"Failed to initialize terrain manager: {e}")

    # Create and show splash screen
    splash_manager = Splash_Manager()
    splash = splash_manager.create_splash()

    logger.info("Creating main window")
    splash_manager.next_step()  # "Creating main window..."

    # Create main window
    main_window = Main_Window(terrain_manager=terrain_manager)

    splash_manager.next_step()  # "Setting up UI components..."
    main_window.setup_ui()

    splash_manager.next_step()  # "Connecting signals..."
    main_window.connect_signals()

    splash_manager.next_step()  # "Loading reference data..."
    main_window.show()

    if args.collection:
        splash_manager.update_progress(90, "Loading collection...")
        main_window.load_collection_from_path(args.collection)

    # Close splash screen
    splash_manager.close_splash()

    logger.info("Starting Qt event loop")

    # Start application
    return_code = app.exec()

    # Replace custom hook with a teardown-safe logger before Qt GC runs.
    # Uses sys.stderr directly (logger may already be torn down at this point).
    # This captures the actual root cause of any teardown exceptions.
    def teardown_exception_hook(exc_type, exc_value, exc_traceback):
        print("[teardown] Unhandled exception during Qt shutdown:", file=sys.stderr)
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)

    sys.excepthook = teardown_exception_hook

    logger.info(f"Application exited with code: {return_code}")
    return return_code


if __name__ == "__main__":
    main()
