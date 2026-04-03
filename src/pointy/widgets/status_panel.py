"""
Status Panel Widget - Display application status
"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from qtpy.QtGui import QFont

class Status_Panel(QWidget):
    """Status panel for displaying application status."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_label = QLabel("Status")
        header_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(header_label)

        # Status message placeholder
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("QLabel { color: #666; }")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def update_status(self, message: str):
        """Update the status message.
        """
        self.status_label.setText(message)

    def clear_status(self):
        """Clear the status message."""
        self.status_label.setText("Ready")
