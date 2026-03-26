"""
Test Image Viewer - Left panel for displaying and selecting points in test imagery
"""

import os
import numpy as np
from pathlib import Path
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QScrollArea, QFrame)
from qtpy.QtCore import Qt, Signal, QPoint
from qtpy.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QMouseEvent

from app.widgets.image_canvas import Image_Canvas
from app.widgets.zoom_controls import Zoom_Controls

class Test_Image_Viewer(QWidget):
    """Viewer for test image with point selection capabilities."""

    # Signals
    point_selected = Signal(float, float)  # x, y in image coordinates
    image_loaded = Signal(str)  # image path
    gcp_point_clicked = Signal(int)  # gcp_id

    def __init__(self):
        super().__init__()
        self.image_path = None
        self.original_image = None
        self.current_image = None
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.rpc_data = None
        self.is_orthorectified = False

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Test Image")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Load image button
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self.load_image_dialog)
        header_layout.addWidget(self.load_btn)

        layout.addLayout(header_layout)

        # Image info label
        self.info_label = QLabel("No image loaded")
        self.info_label.setStyleSheet("QLabel { color: gray; font-size: 9pt; }")
        layout.addWidget(self.info_label)

        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        # Image canvas
        self.image_canvas = Image_Canvas()
        self.image_canvas.point_clicked.connect(self.on_point_clicked)
        self.image_canvas.gcp_point_clicked.connect(self.on_gcp_point_clicked)
        self.scroll_area.setWidget(self.image_canvas)

        layout.addWidget(self.scroll_area)

        # Zoom controls
        self.zoom_controls = Zoom_Controls()
        self.zoom_controls.zoom_changed.connect(self.on_zoom_changed)
        layout.addWidget(self.zoom_controls)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 9pt; }")
        layout.addWidget(self.status_label)

    def load_image_dialog(self):
        """Open file dialog to load test image."""
        from qtpy.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Test Image', '',
            'Image Files (*.tif *.tiff *.jpg *.jpeg *.png *.img);;All Files (*)'
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, image_path):
        """Load an image file."""
        try:
            import cv2
            from PIL import Image

            self.image_path = image_path

            # Load image using OpenCV for better format support
            if image_path.lower().endswith(('.tif', '.tiff')):
                # Use GDAL for GeoTIFF files to get RPC data
                self.load_geotiff(image_path)
            else:
                # Use PIL/OpenCV for regular images
                self.original_image = cv2.imread(image_path)
                if self.original_image is None:
                    # Try PIL as fallback
                    pil_image = Image.open(image_path)
                    self.original_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            self.current_image = self.original_image.copy()
            self.update_display()

            # Extract RPC data if available
            self.extract_rpc_data(image_path)

            # Update info
            height, width = self.current_image.shape[:2]
            self.info_label.setText(f"{Path(image_path).name} - {width}x{height}px")

            # Emit signal
            self.image_loaded.emit(image_path)
            self.status_label.setText("Image loaded successfully")

        except Exception as e:
            self.status_label.setText(f"Error loading image: {str(e)}")
            raise

    def load_geotiff(self, image_path):
        """Load GeoTIFF using GDAL to preserve georeferencing."""
        try:
            from osgeo import gdal

            dataset = gdal.Open(image_path)
            if dataset is None:
                raise ValueError(f"Could not open GeoTIFF: {image_path}")

            # Read image data
            self.original_image = dataset.ReadAsArray()

            # Handle different band configurations
            if len(self.original_image.shape) == 3:
                # RGB or multi-band - assume first 3 bands are RGB
                if self.original_image.shape[0] >= 3:
                    self.original_image = np.transpose(
                        self.original_image[:3], (1, 2, 0)
                    )
                else:
                    self.original_image = np.transpose(
                        self.original_image, (1, 2, 0)
                    )
            else:
                # Single band - convert to 3-channel
                self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_GRAY2BGR)

            dataset = None

        except ImportError:
            # Fallback to regular image loading
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                raise ValueError(f"Could not load image: {image_path}")

    def extract_rpc_data(self, image_path):
        """Extract RPC data from GeoTIFF if available."""
        try:
            from osgeo import gdal

            dataset = gdal.Open(image_path)
            if dataset is None:
                return

            # Try to get RPC data
            rpc_data = {}
            rpc_domain = dataset.GetDomain('RPC')

            if rpc_domain:
                for i in range(dataset.GetMetadataDomainCount()):
                    domain = dataset.GetMetadataDomain(i)
                    if domain == 'RPC':
                        metadata = dataset.GetMetadata(domain)
                        for key, value in metadata.items():
                            rpc_data[key] = float(value) if '.' in value else int(value)
                        break

            if rpc_data:
                self.rpc_data = rpc_data
                self.status_label.setText(f"Image loaded with RPC data")

            dataset = None

        except ImportError:
            pass  # GDAL not available
        except Exception:
            pass  # No RPC data found

    def update_display(self):
        """Update the image display."""
        if self.current_image is None:
            return

        # Convert to QPixmap
        height, width = self.current_image.shape[:2]
        bytes_per_line = 3 * width

        if len(self.current_image.shape) == 3:
            q_image = self.current_image
        else:
            q_image = cv2.cvtColor(self.current_image, cv2.COLOR_GRAY2RGB)

        from qtpy.QtGui import QImage

        qt_image = QImage(
            q_image.data, width, height, bytes_per_line, QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qt_image)
        self.image_canvas.set_pixmap(pixmap)

        # Draw GCP points
        self.draw_gcp_points()

    def draw_gcp_points(self):
        """Draw GCP points on the image."""
        self.image_canvas.clear_gcp_points()

        for gcp_id, (x, y) in self.gcp_points.items():
            self.image_canvas.add_gcp_point(x, y, gcp_id)

        self.image_canvas.update()

    def on_point_clicked(self, x, y):
        """Handle point click on image."""
        if self.current_image is None:
            return

        # Convert pixel coordinates to image coordinates
        img_x, img_y = self.image_canvas.pixel_to_image_coords(x, y)

        # Emit signal
        self.point_selected.emit(img_x, img_y)

        self.status_label.setText(f"Point selected: ({img_x:.1f}, {img_y:.1f})")

    def on_gcp_point_clicked(self, gcp_id):
        """Handle GCP point click."""
        self.gcp_point_clicked.emit(gcp_id)
        self.status_label.setText(f"GCP {gcp_id} selected")

    def on_zoom_changed(self, zoom_factor):
        """Handle zoom change."""
        self.image_canvas.set_zoom(zoom_factor)

    def add_gcp_point(self, x, y, gcp_id):
        """Add a GCP point."""
        self.gcp_points[gcp_id] = (x, y)
        self.draw_gcp_points()

    def remove_gcp_point(self, gcp_id):
        """Remove a GCP point."""
        if gcp_id in self.gcp_points:
            del self.gcp_points[gcp_id]
            self.draw_gcp_points()

    def highlight_gcp_point(self, x, y):
        """Highlight a specific GCP point."""
        self.image_canvas.highlight_point(x, y)

    def clear_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()
        self.draw_gcp_points()

    def update_orthorectified_image(self, ortho_image_path):
        """Update display with orthorectified image."""
        try:
            # Load orthorectified image
            ortho_image = cv2.imread(ortho_image_path)
            if ortho_image is not None:
                self.current_image = ortho_image
                self.is_orthorectified = True
                self.update_display()

                # Update info
                height, width = self.current_image.shape[:2]
                self.info_label.setText(
                    f"{Path(ortho_image_path).name} (Orthorectified) - {width}x{height}px"
                )

        except Exception as e:
            self.status_label.setText(f"Error loading orthorectified image: {str(e)}")

    def has_image(self):
        """Check if an image is loaded."""
        return self.current_image is not None

    def get_image_path(self):
        """Get the current image path."""
        return self.image_path

    def get_rpc_data(self):
        """Get RPC data if available."""
        return self.rpc_data
