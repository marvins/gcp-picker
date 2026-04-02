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
import sys
import argparse

from pointy import MainWindow
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QSettings


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
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("pointy.log")
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Pointy-McPointface application")


def main():
    """Main entry point for Pointy-McPointface."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Pointy-McPointface")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Terminus-Geo")

    # Setup Qt settings
    QSettings.setDefaultFormat(QSettings.IniFormat)

    # Create main window
    main_window = MainWindow()
    main_window.show()

    # Load collection if specified
    if args.collection:
        main_window.load_collection_from_path(args.collection)

    # Start event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
