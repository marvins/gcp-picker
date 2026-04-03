"""
Status Panel - Application status and information display
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                           QTextEdit, QFrame)
from qtpy.QtGui import QFont, QTextCursor

from pointy.widgets.status_panel import Status_Panel as Original_Status_Panel


class Status_Panel(QWidget):
    """Status and information panel."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the status panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_label = QLabel("Status & Information")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Original status panel (reuse existing widget)
        self.original_status_panel = Original_Status_Panel()
        layout.addWidget(self.original_status_panel)

        # Panel styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 2px;
                padding: 3px;
                font-family: monospace;
                font-size: 8pt;
            }
        """)

    def update_status(self, message: str):
        """Update the status message."""
        self.original_status_panel.update_status(message)

    def clear_status(self):
        """Clear the status message."""
        self.original_status_panel.clear_status()
