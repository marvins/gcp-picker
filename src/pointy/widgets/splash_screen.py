#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2026 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    splash_screen.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#

"""
Splash Screen - Basic splash screen for application startup
"""

# Standard library imports
import logging

# Third-party imports
from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QSplashScreen
from qtpy.QtCore import Qt, QTimer, QCoreApplication, QRect
from qtpy.QtGui import QFont, QPainter, QPixmap, QColor

# Project imports
from pointy.resources import resources
from pointy import __version__


class Splash_Screen(QSplashScreen):
    """Basic splash screen with progress bar and status updates."""

    def __init__(self):
        # Load logo using resource system
        self.logo_pixmap = resources.get_splash_logo()

        # Create a pixmap for the splash screen - reduced height, increased width
        self.pixmap = QPixmap(700, 250)  # Wider for larger logo
        self.pixmap.fill(QColor(45, 45, 48))  # Dark background

        super().__init__(self.pixmap)

        self.setup_ui()

    def setup_ui(self):
        """Setup the splash screen UI."""
        # Set splash screen properties
        self.setFixedSize(700, 250)  # Match new dimensions
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)

        # Progress tracking
        self.progress = 0
        self.max_progress = 100
        self.current_task = "Initializing..."

    def drawContents(self, painter):
        """Draw the splash screen contents."""
        painter.setPen(QColor(255, 255, 255))  # White text for dark background

        # Layout constants
        left_margin = 20
        logo_size = 200
        content_start_x = left_margin + logo_size + 30
        top_margin = 20

        # Draw logo on left side if available
        if self.logo_pixmap and not self.logo_pixmap.isNull():
            # Enable composition mode for proper transparency handling
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # Ensure the logo has an alpha channel for transparency
            if not self.logo_pixmap.hasAlpha():
                self.logo_pixmap = self.logo_pixmap.convertToFormat(QPixmap.Format_ARGB32)

            # Scale logo to desired size
            scaled_logo = self.logo_pixmap.scaled(
                logo_size, logo_size,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # Use SourceOver composition mode to preserve transparency
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Position logo on left side, vertically centered
            logo_x = left_margin
            logo_y = (self.height() - scaled_logo.height()) // 2

            # Draw the logo with transparency preserved
            painter.drawPixmap(logo_x, logo_y, scaled_logo)

        # Draw content on the right side
        content_x = content_start_x

        # Calculate total content height and center vertically
        title_height = 40
        title_spacing = 50
        version_height = 25
        version_spacing = 30
        task_height = 20
        task_spacing = 25
        progress_height = 10

        total_content_height = (title_height + title_spacing +
                              version_height + version_spacing +
                              task_height + task_spacing +
                              progress_height)

        # Center content in the available space (same vertical center as logo)
        current_y = (self.height() - total_content_height) // 2

        # App title
        title_font = QFont("Arial", 30, QFont.Bold)
        painter.setFont(title_font)
        title_rect = QRect(content_x, current_y, self.width() - content_x - 20, 40)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignTop, "Pointy-McPointface")
        current_y += 50

        # Version
        version_font = QFont("Arial", 16)
        painter.setFont(version_font)
        version_rect = QRect(content_x, current_y, self.width() - content_x - 20, 25)
        painter.drawText(version_rect, Qt.AlignLeft | Qt.AlignTop, f"Version {__version__}")
        current_y += 30

        # Current task
        task_font = QFont("Arial", 12)
        painter.setFont(task_font)
        task_rect = QRect(content_x, current_y, self.width() - content_x - 20, 20)
        painter.drawText(task_rect, Qt.AlignLeft | Qt.AlignTop, self.current_task)
        current_y += 25

        # Progress bar
        progress_width = 200
        progress_height = 10
        progress_x = content_x
        progress_y = current_y

        # Progress bar background
        painter.fillRect(progress_x, progress_y, progress_width, progress_height, QColor(70, 70, 70))

        # Progress bar fill
        fill_width = int((self.progress / self.max_progress) * progress_width)
        painter.fillRect(progress_x, progress_y, fill_width, progress_height, QColor(100, 200, 100))

        # Progress percentage
        progress_font = QFont("Arial", 10)
        painter.setFont(progress_font)
        progress_text = f"{self.progress}%"
        progress_rect = QRect(progress_x + progress_width + 15, progress_y - 2, 50, progress_height + 4)
        painter.drawText(progress_rect, Qt.AlignLeft | Qt.AlignVCenter, progress_text)

    def update_progress(self, value, task=None):
        """Update the progress bar and task text."""
        self.progress = min(value, self.max_progress)
        if task:
            self.current_task = task

        # Repaint the splash screen
        self.update()

        # Process events to ensure the splash screen updates
        QCoreApplication.processEvents()

    def show_message(self, message):
        """Show a status message."""
        self.current_task = message
        self.update()
        QCoreApplication.processEvents()


class Splash_Manager:
    """Manager for splash screen operations."""

    def __init__(self):
        self.splash = None
        self.steps = []
        self.current_step = 0

    def create_splash(self):
        """Create and show the splash screen."""
        self.splash = Splash_Screen()
        self.splash.show()

        # Initialize with default steps
        self.steps = [
            "Initializing application...",
            "Loading configuration...",
            "Creating main window...",
            "Setting up UI components...",
            "Connecting signals...",
            "Loading reference data...",
            "Ready!"
        ]

        self.current_step = 0
        self.update_progress(0, self.steps[0] if self.steps else "Starting...")

        return self.splash

    def update_progress(self, progress=None, task=None):
        """Update splash screen progress."""
        if not self.splash:
            return

        if progress is not None:
            self.splash.update_progress(progress, task)
        elif task:
            self.splash.show_message(task)

    def next_step(self):
        """Move to the next step."""
        if not self.splash or self.current_step >= len(self.steps):
            return

        self.current_step += 1
        progress = int((self.current_step / len(self.steps)) * 100)
        task = self.steps[self.current_step] if self.current_step < len(self.steps) else "Complete!"

        self.update_progress(progress, task)

    def close_splash(self):
        """Close the splash screen."""
        if self.splash:
            self.update_progress(100, "Complete!")

            # Show for a moment then close
            from qtpy.QtCore import QTimer
            QTimer.singleShot(500, self.splash.close)
            self.splash = None
