"""
Splash Screen - Basic splash screen for application startup
"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QSplashScreen
from qtpy.QtCore import Qt, QTimer, QCoreApplication
from qtpy.QtGui import QFont, QPainter, QPixmap, QColor
from pointy.resources import resources
from pointy import __version__


class Splash_Screen(QSplashScreen):
    """Basic splash screen with progress bar and status updates."""

    def __init__(self):
        # Load logo using resource system
        self.logo_pixmap = resources.get_splash_logo()

        # Create a pixmap for the splash screen
        self.pixmap = QPixmap(500, 350)  # Increased height for better spacing
        self.pixmap.fill(QColor(45, 45, 48))  # Dark background

        super().__init__(self.pixmap)

        self.setup_ui()

    def setup_ui(self):
        """Setup the splash screen UI."""
        # Set splash screen properties
        self.setFixedSize(500, 350)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)

        # Progress tracking
        self.progress = 0
        self.max_progress = 100
        self.current_task = "Initializing..."

    def drawContents(self, painter):
        """Draw the splash screen contents."""
        painter.setPen(QColor(255, 255, 255))  # White text for dark background

        # Draw logo if available
        if self.logo_pixmap and not self.logo_pixmap.isNull():
            # Enable composition mode for proper transparency handling
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Center logo at top with more padding
            logo_x = (self.width() - self.logo_pixmap.width()) // 2
            logo_y = 15  # Reduced top padding
            painter.drawPixmap(logo_x, logo_y, self.logo_pixmap)

            # Reset composition mode
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Adjust text positions to account for logo with less spacing
            text_start_y = logo_y + self.logo_pixmap.height() + 15  # Reduced spacing
        else:
            # Fallback to text only
            text_start_y = 30

        # App title (smaller if logo is present)
        title_font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(title_font)
        title_rect = self.rect().adjusted(0, text_start_y, 0, -200)  # More space at bottom
        painter.drawText(title_rect, Qt.AlignCenter, "Pointy-McPointface")

        # Version
        version_font = QFont("Arial", 12)
        painter.setFont(version_font)
        version_rect = self.rect().adjusted(0, text_start_y + 25, 0, -170)  # Tighter spacing
        painter.drawText(version_rect, Qt.AlignCenter, f"Version {__version__}")

        # Current task
        task_font = QFont("Arial", 9)
        painter.setFont(task_font)
        task_rect = self.rect().adjusted(0, text_start_y + 60, 0, -80)
        painter.drawText(task_rect, Qt.AlignCenter, self.current_task)

        # Progress bar background - moved down to give more space
        progress_y = 270  # Lower position for progress bar
        progress_height = 8  # Smaller height
        progress_width = 300
        progress_x = 100  # Center the progress bar

        # Draw progress bar background
        painter.fillRect(progress_x, progress_y, progress_width, progress_height, QColor(60, 60, 60))

        # Draw progress bar fill
        if self.progress > 0:
            fill_width = int((self.progress / self.max_progress) * progress_width)
            painter.fillRect(progress_x, progress_y, fill_width, progress_height, QColor(76, 175, 80))

        # Draw progress bar border
        painter.setPen(QColor(100, 100, 100))
        painter.drawRect(progress_x, progress_y, progress_width, progress_height)

        # Progress percentage
        painter.setPen(QColor(255, 255, 255))  # White text for dark background
        painter.setFont(QFont("Arial", 10))
        progress_text = f"{self.progress}%"
        progress_rect = self.rect().adjusted(0, progress_y + progress_height + 5, 0, -progress_y - progress_height - 25)
        painter.drawText(progress_rect, Qt.AlignCenter, progress_text)

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
