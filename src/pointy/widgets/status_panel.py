"""
Status Panel Widget - Display status and GCP information
"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont

class Status_Panel(QWidget):
    """Status panel for displaying GCP information and application status."""

    def __init__(self):
        super().__init__()
        self.current_gcp = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_label = QLabel("Status")
        header_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(header_label)

        # Create frame for GCP info
        gcp_frame = QFrame()
        gcp_frame.setFrameStyle(QFrame.Box)
        gcp_frame.setStyleSheet("QFrame { background-color: #f0f0f0; }")

        gcp_layout = QVBoxLayout(gcp_frame)

        # GCP information
        self.gcp_info_label = QLabel("No GCP selected")
        self.gcp_info_label.setFont(QFont("Arial", 9))
        self.gcp_info_label.setWordWrap(True)
        gcp_layout.addWidget(self.gcp_info_label)

        # Coordinate details
        self.coord_details_label = QLabel("")
        self.coord_details_label.setFont(QFont("Courier", 8))
        self.coord_details_label.setStyleSheet("QLabel { color: #666; }")
        gcp_layout.addWidget(self.coord_details_label)

        layout.addWidget(gcp_frame)

        # Transformation status
        transform_frame = QFrame()
        transform_frame.setFrameStyle(QFrame.Box)
        transform_frame.setStyleSheet("QFrame { background-color: #f0f0f0; }")

        transform_layout = QVBoxLayout(transform_frame)

        transform_header = QLabel("Transformation Status")
        transform_header.setFont(QFont("Arial", 9, QFont.Bold))
        transform_layout.addWidget(transform_header)

        self.transform_status_label = QLabel("Not calculated")
        self.transform_status_label.setFont(QFont("Arial", 8))
        self.transform_status_label.setStyleSheet("QLabel { color: #666; }")
        transform_layout.addWidget(self.transform_status_label)

        self.accuracy_label = QLabel("RMSE: N/A")
        self.accuracy_label.setFont(QFont("Arial", 8))
        self.accuracy_label.setStyleSheet("QLabel { color: blue; }")
        transform_layout.addWidget(self.accuracy_label)

        layout.addWidget(transform_frame)

        layout.addStretch()

    def update_gcp_info(self, gcp):
        """Update the displayed GCP information."""
        self.current_gcp = gcp

        if gcp:
            info_text = f"GCP {gcp.id}"
            self.gcp_info_label.setText(info_text)

            coord_text = (
                f"Test: ({gcp.test_x:.2f}, {gcp.test_y:.2f})\n"
                f"Ref:  ({gcp.ref_x:.2f}, {gcp.ref_y:.2f})\n"
                f"Geo:  ({gcp.longitude:.6f}, {gcp.latitude:.6f})"
            )
            self.coord_details_label.setText(coord_text)
        else:
            self.gcp_info_label.setText("No GCP selected")
            self.coord_details_label.setText("")

    def update_transform_status(self, status, rmse=None):
        """Update transformation status."""
        self.transform_status_label.setText(status)

        if rmse is not None:
            self.accuracy_label.setText(f"RMSE: {rmse:.3f} pixels")
        else:
            self.accuracy_label.setText("RMSE: N/A")

    def clear_info(self):
        """Clear all information."""
        self.current_gcp = None
        self.gcp_info_label.setText("No GCP selected")
        self.coord_details_label.setText("")
        self.transform_status_label.setText("Not calculated")
        self.accuracy_label.setText("RMSE: N/A")
