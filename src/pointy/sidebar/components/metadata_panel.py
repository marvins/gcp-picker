"""
Metadata Panel - Sidebar widget showing cursor position metadata
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                           QGroupBox, QGridLayout, QFrame)
from qtpy.QtGui import QFont


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
        title_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(title_label)

        # Reference Viewer Group
        ref_group = QGroupBox("Reference Viewer")
        ref_layout = QGridLayout(ref_group)
        ref_layout.setSpacing(4)
        ref_layout.setColumnStretch(0, 0)  # Labels don't stretch
        ref_layout.setColumnStretch(1, 1)  # Values stretch

        # Combine lat/lon on same row
        latlon_label = QLabel("Lat, Lon:")
        latlon_label.setStyleSheet("font-size: 10px; color: #666;")
        ref_layout.addWidget(latlon_label, 0, 0)
        self.ref_latlon_label = QLabel("--, --")
        self.ref_latlon_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        ref_layout.addWidget(self.ref_latlon_label, 0, 1)

        alt_label = QLabel("Alt:")
        alt_label.setStyleSheet("font-size: 10px; color: #666;")
        ref_layout.addWidget(alt_label, 1, 0)
        self.ref_alt_label = QLabel("--")
        self.ref_alt_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        ref_layout.addWidget(self.ref_alt_label, 1, 1)

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
        test_layout.setColumnStretch(0, 0)  # Labels don't stretch
        test_layout.setColumnStretch(1, 1)  # Values stretch

        # Combine pixel X,Y and value on same rows
        pixel_xy_label = QLabel("Pixel X,Y:")
        pixel_xy_label.setStyleSheet("font-size: 10px; color: #666;")
        test_layout.addWidget(pixel_xy_label, 0, 0)
        self.test_xy_label = QLabel("--, --")
        self.test_xy_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        test_layout.addWidget(self.test_xy_label, 0, 1)

        pixel_value_label = QLabel("Pixel Value:")
        pixel_value_label.setStyleSheet("font-size: 10px; color: #666;")
        test_layout.addWidget(pixel_value_label, 1, 0)
        self.test_pixel_label = QLabel("--")
        self.test_pixel_label.setStyleSheet("font-family: monospace; font-size: 10px;")
        test_layout.addWidget(self.test_pixel_label, 1, 1)

        # Combine rectified lat/lon on same row
        rectified_latlon_label = QLabel("Rectified Lat, Lon:")
        rectified_latlon_label.setStyleSheet("font-size: 10px; color: #666;")
        test_layout.addWidget(rectified_latlon_label, 2, 0)
        self.test_latlon_label = QLabel("--, --")
        self.test_latlon_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #666;")
        test_layout.addWidget(self.test_latlon_label, 2, 1)

        rectified_alt_label = QLabel("Rectified Alt:")
        rectified_alt_label.setStyleSheet("font-size: 10px; color: #666;")
        test_layout.addWidget(rectified_alt_label, 3, 0)
        self.test_alt_label = QLabel("--")
        self.test_alt_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #666;")
        test_layout.addWidget(self.test_alt_label, 3, 1)

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
        # Update combined lat/lon label
        if lat is not None and lon is not None:
            self.ref_latlon_label.setText(f"{lat:.6f}, {lon:.6f}")
        elif lat is not None and lon is None:
            self.ref_latlon_label.setText(f"{lat:.6f}, --")
        elif lat is None and lon is not None:
            self.ref_latlon_label.setText(f"--, {lon:.6f}")
        else:
            self.ref_latlon_label.setText("--, --")

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
            lat: Rectified latitude (optional)
            lon: Rectified longitude (optional)
            alt: Rectified altitude (optional)
        """
        # Update combined X,Y label
        if x is not None and y is not None:
            self.test_xy_label.setText(f"{x}, {y}")
        elif x is not None and y is None:
            self.test_xy_label.setText(f"{x}, --")
        elif x is None and y is not None:
            self.test_xy_label.setText(f"--, {y}")
        else:
            self.test_xy_label.setText("--, --")

        if pixel_value is not None:
            self.test_pixel_label.setText(str(pixel_value))
        else:
            self.test_pixel_label.setText("--")

        # Update combined rectified lat/lon label
        if lat is not None and lon is not None:
            self.test_latlon_label.setText(f"{lat:.6f}, {lon:.6f}")
            self.test_latlon_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #000;")
        elif lat is not None or lon is not None:
            # Handle case where only one coordinate is available
            lat_str = f"{lat:.6f}" if lat is not None else "--"
            lon_str = f"{lon:.6f}" if lon is not None else "--"
            self.test_latlon_label.setText(f"{lat_str}, {lon_str}")
            self.test_latlon_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #000;")
        else:
            self.test_latlon_label.setText("--, --")
            self.test_latlon_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #666;")

        if alt is not None:
            self.test_alt_label.setText(f"{alt:.1f} m")
            self.test_alt_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #000;")
        else:
            self.test_alt_label.setText("--")
            self.test_alt_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #666;")

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
