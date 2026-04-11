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
#    File:    status_panel.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Status Panel Widget - Display application status
"""

# Third-Party Libraries
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

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

    def update_gcp_info(self, gcp):
        """Update status panel with GCP information.

        Args:
            gcp: Ground Control Point object
        """
        if gcp:
            status_msg = f"GCP Selected: ID={gcp.id}, "
            if hasattr(gcp, 'test_point') and gcp.test_point:
                status_msg += f"Test: ({gcp.test_point.x:.1f}, {gcp.test_point.y:.1f})"
            if hasattr(gcp, 'reference_point') and gcp.reference_point:
                status_msg += f", Ref: ({gcp.reference_point.lon:.6f}, {gcp.reference_point.lat:.6f})"
            self.update_status(status_msg)
        else:
            self.clear_status()
