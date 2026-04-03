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
#    File:    transformation_status_panel.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Transformation Status Panel - Widget for displaying transformation status and accuracy
"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from qtpy.QtGui import QFont


class Transformation_Status_Panel(QWidget):
    """Panel for displaying transformation status and accuracy information."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the transformation status panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_label = QLabel("Transformation Status")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Transformation status frame
        transform_frame = QFrame()
        transform_frame.setFrameStyle(QFrame.Box)
        transform_frame.setStyleSheet("QFrame { background-color: #f0f0f0; }")

        transform_layout = QVBoxLayout(transform_frame)

        # Status label
        self.transform_status_label = QLabel("Not calculated")
        self.transform_status_label.setFont(QFont("Arial", 9))
        self.transform_status_label.setStyleSheet("QLabel { color: #666; }")
        transform_layout.addWidget(self.transform_status_label)

        # Accuracy label
        self.accuracy_label = QLabel("RMSE: N/A")
        self.accuracy_label.setFont(QFont("Arial", 9))
        self.accuracy_label.setStyleSheet("QLabel { color: blue; font-weight: bold; }")
        transform_layout.addWidget(self.accuracy_label)

        layout.addWidget(transform_frame)

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
            QFrame {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 8px;
                background-color: #fafafa;
            }
        """)

    def update_transform_status(self, status: str, rmse: float | None = None):
        """Update transformation status display.

        Args:
            status: Status message to display
            rmse: Root Mean Square Error value (optional)
        """
        self.transform_status_label.setText(status)

        if rmse is not None:
            self.accuracy_label.setText(f"RMSE: {rmse:.3f} pixels")
            # Color code based on accuracy
            if rmse < 1.0:
                self.accuracy_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            elif rmse < 2.0:
                self.accuracy_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
            else:
                self.accuracy_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        else:
            self.accuracy_label.setText("RMSE: N/A")
            self.accuracy_label.setStyleSheet("QLabel { color: #666; font-weight: bold; }")

    def clear_status(self):
        """Clear the transformation status."""
        self.transform_status_label.setText("Not calculated")
        self.accuracy_label.setText("RMSE: N/A")
        self.accuracy_label.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
