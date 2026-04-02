"""
Test Image Viewer - Left panel for displaying and selecting points in test imagery
"""

#  Python Standard Libraries
import json
from pathlib import Path

#  Third-Party Libraries
import numpy as np
import rasterio
import cv2
from PIL import Image
from qtpy.QtWidgets import (QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QScrollArea, QFrame)
from qtpy.QtCore import Qt, Signal, QPoint
from qtpy.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont, QMouseEvent

#  Project Libraries
from app.widgets.image_canvas import Image_Canvas

class Test_Image_Viewer(QWidget):
    """Viewer for test image with point selection capabilities."""

    # Signals
    point_selected = Signal(float, float)  # x, y in image coordinates
    image_loaded = Signal(str)  # image path
    gcp_point_clicked = Signal(int)  # gcp_id
    cursor_moved = Signal(int, int, object, object, object, object)  # x, y, pixel_value, lat, lon, alt

    def __init__(self):
        super().__init__()
        self.image_path = None
        self.original_image = None
        self.current_image = None
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.rpc_data = None
        self.is_orthorectified = False

        # Image adjustment parameters
        self.auto_stretch = False
        self.min_pixel = 0
        self.max_pixel = 255
        self.brightness = 0.0  # -1.0 to 1.0
        self.contrast = 1.0    # 0.0 to 2.0

        # Image metadata
        self.bit_depth = 8
        self.dtype = np.uint8

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
        self.image_canvas.cursor_moved.connect(self._on_cursor_moved)
        self.scroll_area.setWidget(self.image_canvas)

        layout.addWidget(self.scroll_area)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 9pt; }")
        layout.addWidget(self.status_label)

    def load_image_dialog(self):
        """Open file dialog to load test image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Test Image', '',
            'Image Files (*.tif *.tiff *.jpg *.jpeg *.png *.img);;All Files (*)'
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, image_path):
        """Load an image file."""
        try:
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
            self.apply_image_adjustments()  # Apply current settings to new image

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
        """Load GeoTIFF using rasterio to preserve georeferencing and bit depth."""
        try:
            with rasterio.open(image_path) as src:
                # Preserve original data type and bit depth
                self.dtype = src.dtypes[0]
                self.bit_depth = src.dtypes[0].itemsize * 8

                # Read all bands
                image_data = src.read()

                # Convert from (bands, height, width) to (height, width, bands)
                if image_data.ndim == 3:
                    image_data = np.transpose(image_data, (1, 2, 0))

                # Handle different band configurations
                if len(image_data.shape) == 3:
                    # RGB or multi-band - assume first 3 bands are RGB
                    if image_data.shape[2] >= 3:
                        self.original_image = image_data[:, :, :3]
                    else:
                        # Less than 3 bands, duplicate the bands
                        self.original_image = np.zeros((*image_data.shape[:2], 3), dtype=image_data.dtype)
                        for i in range(min(image_data.shape[2], 3)):
                            self.original_image[:, :, i] = image_data[:, :, i]
                else:
                    # Single band - convert to 3-channel
                    self.original_image = cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)

                # Update pixel range based on bit depth
                self.max_pixel = (2 ** self.bit_depth) - 1

        except Exception:
            # Fallback to regular image loading
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                raise ValueError(f"Could not load image: {image_path}")
            self.dtype = np.uint8
            self.bit_depth = 8
            self.max_pixel = 255

    def extract_rpc_data(self, image_path):
        """Extract RPC data from GeoTIFF if available."""
        try:
            with rasterio.open(image_path) as src:
                # Try to get RPC data from tags
                rpc_metadata = src.tags().get('RPC_METADATA')

                if rpc_metadata:
                    try:
                        self.rpc_data = json.loads(rpc_metadata)
                    except json.JSONDecodeError:
                        self.rpc_data = {'raw': rpc_metadata}
                    self.status_label.setText(f"Image loaded with RPC data")

        except Exception:
            pass  # No RPC data found

    def update_display(self):
        """Update the image display."""
        if self.current_image is None:
            return

        # Convert to display format (8-bit for Qt)
        display_image = self.current_image

        # Normalize to 8-bit for display if needed
        if self.bit_depth > 8:
            # Convert to 8-bit for display while preserving visual information
            display_image = ((display_image.astype(np.float32) / self.max_pixel) * 255).astype(np.uint8)
        else:
            display_image = display_image.astype(np.uint8)

        # Convert to QPixmap
        height, width = display_image.shape[:2]
        bytes_per_line = 3 * width

        if len(display_image.shape) == 3:
            q_image = display_image
        else:
            q_image = cv2.cvtColor(display_image, cv2.COLOR_GRAY2RGB)

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

    def _on_cursor_moved(self, x, y, pixel_value):
        """Handle cursor movement and forward signal with optional ortho coordinates."""
        # Get orthorectified coordinates if available
        lat, lon, alt = None, None, None
        if self.is_orthorectified and self.ortho_transform:
            # Calculate ortho coordinates from pixel coordinates
            lat, lon, alt = self.ortho_transform(x, y)

        self.cursor_moved.emit(x, y, pixel_value, lat, lon, alt)
        self.status_label.setText(f"Cursor: ({x}, {y}) Pixel: {pixel_value}")

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

    def set_auto_stretch(self, enabled: bool):
        """Set auto-stretch mode."""
        self.auto_stretch = enabled
        self.apply_image_adjustments()

    def set_min_pixel(self, value: int):
        """Set minimum pixel value."""
        self.min_pixel = value
        self.apply_image_adjustments()

    def set_max_pixel(self, value: int):
        """Set maximum pixel value."""
        self.max_pixel = value
        self.apply_image_adjustments()

    def set_brightness(self, value: float):
        """Set brightness value (-1.0 to 1.0)."""
        self.brightness = value
        self.apply_image_adjustments()

    def set_contrast(self, value: float):
        """Set contrast value (0.0 to 2.0)."""
        self.contrast = value
        self.apply_image_adjustments()

    def reset_view_settings(self):
        """Reset all view settings to defaults."""
        self.auto_stretch = False
        self.min_pixel = 0
        self.max_pixel = 255
        self.brightness = 0.0
        self.contrast = 1.0
        self.apply_image_adjustments()

    def apply_image_adjustments(self):
        """Apply current image adjustments to the original image."""
        if self.original_image is None:
            return

        # Start with original image
        adjusted = self.original_image.astype(np.float32)

        # Apply auto-stretch if enabled
        if self.auto_stretch:
            # Calculate actual min/max from image
            actual_min = np.percentile(adjusted, 2)
            actual_max = np.percentile(adjusted, 98)

            # Stretch to full range
            if actual_max > actual_min:
                adjusted = (adjusted - actual_min) / (actual_max - actual_min)
                adjusted = np.clip(adjusted * self.max_pixel, 0, self.max_pixel)
        else:
            # Apply manual min/max range
            if self.max_pixel > self.min_pixel:
                adjusted = np.clip(adjusted, self.min_pixel, self.max_pixel)
                adjusted = ((adjusted - self.min_pixel) / (self.max_pixel - self.min_pixel)) * self.max_pixel

        # Apply contrast
        if self.contrast != 1.0:
            center = self.max_pixel / 2.0
            adjusted = (adjusted - center) * self.contrast + center

        # Apply brightness
        if self.brightness != 0.0:
            adjusted = adjusted + (self.brightness * self.max_pixel)

        # Clip to valid range and convert back to original dtype
        adjusted = np.clip(adjusted, 0, self.max_pixel).astype(self.dtype)

        # Update current image
        self.current_image = adjusted
        self.update_display()

    def get_image_data(self):
        """Get the current image data for histogram."""
        return self.current_image
