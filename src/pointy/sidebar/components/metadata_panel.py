"""
Metadata Panel - Sidebar widget showing cursor position metadata
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QGroupBox, QGridLayout, QFrame)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QPalette, QColor


class Metadata_Panel(QWidget):
    """Panel displaying cursor position metadata from reference and test viewers."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the metadata panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Title
        title_label = QLabel("Cursor Metadata")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Reference Viewer Group
        ref_group = QGroupBox("Reference Viewer")
        ref_layout = QGridLayout(ref_group)
        ref_layout.setSpacing(4)

        ref_layout.addWidget(QLabel("Lat:"), 0, 0)
        self.ref_lat_label = QLabel("--")
        self.ref_lat_label.setStyleSheet("font-family: monospace;")
        ref_layout.addWidget(self.ref_lat_label, 0, 1)

        ref_layout.addWidget(QLabel("Lon:"), 1, 0)
        self.ref_lon_label = QLabel("--")
        self.ref_lon_label.setStyleSheet("font-family: monospace;")
        ref_layout.addWidget(self.ref_lon_label, 1, 1)

        ref_layout.addWidget(QLabel("Alt:"), 2, 0)
        self.ref_alt_label = QLabel("--")
        self.ref_alt_label.setStyleSheet("font-family: monospace;")
        ref_layout.addWidget(self.ref_alt_label, 2, 1)

        layout.addWidget(ref_group)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Test Viewer Group
        test_group = QGroupBox("Test Viewer")
        test_layout = QGridLayout(test_group)
        test_layout.setSpacing(4)

        test_layout.addWidget(QLabel("Pixel X:"), 0, 0)
        self.test_x_label = QLabel("--")
        self.test_x_label.setStyleSheet("font-family: monospace;")
        test_layout.addWidget(self.test_x_label, 0, 1)

        test_layout.addWidget(QLabel("Pixel Y:"), 1, 0)
        self.test_y_label = QLabel("--")
        self.test_y_label.setStyleSheet("font-family: monospace;")
        test_layout.addWidget(self.test_y_label, 1, 1)

        test_layout.addWidget(QLabel("Pixel Value:"), 2, 0)
        self.test_pixel_label = QLabel("--")
        self.test_pixel_label.setStyleSheet("font-family: monospace;")
        test_layout.addWidget(self.test_pixel_label, 2, 1)

        # Ortho coordinates (only shown when orthorectified)
        test_layout.addWidget(QLabel("Ortho Lat:"), 3, 0)
        self.test_lat_label = QLabel("--")
        self.test_lat_label.setStyleSheet("font-family: monospace; color: #666;")
        test_layout.addWidget(self.test_lat_label, 3, 1)

        test_layout.addWidget(QLabel("Ortho Lon:"), 4, 0)
        self.test_lon_label = QLabel("--")
        self.test_lon_label.setStyleSheet("font-family: monospace; color: #666;")
        test_layout.addWidget(self.test_lon_label, 4, 1)

        test_layout.addWidget(QLabel("Ortho Alt:"), 5, 0)
        self.test_alt_label = QLabel("--")
        self.test_alt_label.setStyleSheet("font-family: monospace; color: #666;")
        test_layout.addWidget(self.test_alt_label, 5, 1)

        layout.addWidget(test_group)

        # Add stretch at bottom
        layout.addStretch()

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
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px;
            }
        """)

    def update_reference_metadata(self, lat: float | None, lon: float | None, alt: float | None = None):
        """Update reference viewer metadata.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters (optional)
        """
        if lat is not None:
            self.ref_lat_label.setText(f"{lat:.6f}")
        else:
            self.ref_lat_label.setText("--")

        if lon is not None:
            self.ref_lon_label.setText(f"{lon:.6f}")
        else:
            self.ref_lon_label.setText("--")

        if alt is not None:
            self.ref_alt_label.setText(f"{alt:.1f} m")
        else:
            self.ref_alt_label.setText("--")

    def update_test_metadata(self, x: int | None, y: int | None, pixel_value: str | None = None,
                            lat: float | None = None, lon: float | None = None, alt: float | None = None):
        """Update test viewer metadata.

        Args:
            x: Pixel X coordinate
            y: Pixel Y coordinate
            pixel_value: String representation of pixel value(s)
            lat: Orthorectified latitude (optional)
            lon: Orthorectified longitude (optional)
            alt: Orthorectified altitude (optional)
        """
        if x is not None:
            self.test_x_label.setText(f"{x}")
        else:
            self.test_x_label.setText("--")

        if y is not None:
            self.test_y_label.setText(f"{y}")
        else:
            self.test_y_label.setText("--")

        if pixel_value is not None:
            self.test_pixel_label.setText(str(pixel_value))
        else:
            self.test_pixel_label.setText("--")

        # Update ortho coordinates (grayed out if not available)
        if lat is not None:
            self.test_lat_label.setText(f"{lat:.6f}")
            self.test_lat_label.setStyleSheet("font-family: monospace; color: #000;")
        else:
            self.test_lat_label.setText("--")
            self.test_lat_label.setStyleSheet("font-family: monospace; color: #666;")

        if lon is not None:
            self.test_lon_label.setText(f"{lon:.6f}")
            self.test_lon_label.setStyleSheet("font-family: monospace; color: #000;")
        else:
            self.test_lon_label.setText("--")
            self.test_lon_label.setStyleSheet("font-family: monospace; color: #666;")

        if alt is not None:
            self.test_alt_label.setText(f"{alt:.1f} m")
            self.test_alt_label.setStyleSheet("font-family: monospace; color: #000;")
        else:
            self.test_alt_label.setText("--")
            self.test_alt_label.setStyleSheet("font-family: monospace; color: #666;")

    def clear_reference_metadata(self):
        """Clear reference viewer metadata."""
        self.ref_lat_label.setText("--")
        self.ref_lon_label.setText("--")
        self.ref_alt_label.setText("--")

    def clear_test_metadata(self):
        """Clear test viewer metadata."""
        self.test_x_label.setText("--")
        self.test_y_label.setText("--")
        self.test_pixel_label.setText("--")
        self.test_lat_label.setText("--")
        self.test_lon_label.setText("--")
        self.test_alt_label.setText("--")
        self.test_lat_label.setStyleSheet("font-family: monospace; color: #666;")
        self.test_lon_label.setStyleSheet("font-family: monospace; color: #666;")
        self.test_alt_label.setStyleSheet("font-family: monospace; color: #666;")
