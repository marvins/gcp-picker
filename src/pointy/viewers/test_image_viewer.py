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
#    File:    test_image_viewer.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Test Image Viewer - Left panel for displaying and selecting points in test imagery
"""

#  Python Standard Libraries
import logging
import time
from pathlib import Path
import json
from typing import Dict

#  Third-Party Libraries
import cv2
import numpy as np
import rasterio
from PIL import Image
from qtpy.QtCore import Qt, Signal, QEvent
from qtpy.QtGui import QImage, QPixmap, QFont, QWheelEvent, QMovie
from qtpy.QtWidgets import (QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton)

#  Project Libraries
from pointy.core.coordinate import Pixel, Geographic
from pointy.core.qt_async_image_loader import Qt_Async_Image_Loader, Loading_Indicator_Widget
from pointy.widgets.graphics_image_view import Graphics_Image_View

class Test_Image_Viewer(QWidget):
    """Viewer for test image with point selection capabilities."""

    # Signals
    point_selected = Signal(float, float)  # x, y in image coordinates
    image_loaded = Signal(str)  # image path
    gcp_point_clicked = Signal(int)  # gcp_id
    cursor_moved = Signal(int, int, object, object, object, object)  # x, y, pixel_value, lat, lon, alt
    image_adjusted = Signal()  # emitted when image adjustments are applied

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

        # Async loading components
        self.async_loader = Qt_Async_Image_Loader(max_workers=2)
        self.loading_indicator = Loading_Indicator_Widget()
        self.loading_indicator.connect_to_loader(self.async_loader)
        self.current_load_id = None

        # Loading animation widget
        self.loading_movie = QMovie()
        self.loading_label_animation = QLabel()
        self.loading_label_animation.setAlignment(Qt.AlignCenter)
        self.loading_label_animation.setVisible(False)

        # Connect async loader signals
        logging.debug("Connecting async loader signals")
        self.async_loader.load_started.connect(self.on_load_started)
        self.async_loader.load_completed.connect(self.on_load_completed)
        self.async_loader.load_failed.connect(self.on_load_failed)
        logging.debug("Async loader signals connected")

        # Connect loading indicator signals
        self.loading_indicator.loading_started.connect(self.show_loading_indicator)
        self.loading_indicator.loading_finished.connect(self.hide_loading_indicator)

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

        # Loading indicator (initially hidden)
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
        self.loading_label.setVisible(False)
        header_layout.addWidget(self.loading_label)

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

        # Image view (replaces scroll area + image canvas)
        self.image_view = Graphics_Image_View()
        self.image_view.point_clicked.connect(self.on_point_clicked)
        self.image_view.gcp_point_clicked.connect(self.on_gcp_point_clicked)
        self.image_view.cursor_moved.connect(self._on_cursor_moved)

        layout.addWidget(self.image_view)

        # Loading overlay (positioned over image view)
        self.loading_overlay = QLabel("🔄 Loading...\nPlease wait")
        self.loading_overlay.setAlignment(Qt.AlignCenter)
        self.loading_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(128, 128, 128, 200);
                color: white;
                font-size: 16pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        self.loading_overlay.setVisible(False)

        # Position loading overlay over the image view
        self.loading_overlay.setParent(self.image_view)
        self.loading_overlay.raise_()

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
        """Load an image file asynchronously."""
        self.image_path = image_path
        logging.info(f"Starting async image load: {image_path}")

        # Start async load
        self.current_load_id = self.async_loader.load_image_async(image_path)

        # Update UI to show loading state
        self.info_label.setText(f"Loading: {Path(image_path).name}...")
        self.status_label.setText("Loading image...")
        self.load_btn.setEnabled(False)

        # Show loading overlay and set gray background
        logging.debug("Showing loading overlay")
        self.show_loading_overlay()
        self.image_view.setStyleSheet("""
            QGraphicsView {
                background-color: #808080;
                border: 1px solid #ccc;
            }
        """)

    def on_load_started(self, load_id: str, image_path: str):
        """Handle async load started signal."""
        self.current_load_id = load_id
        logging.info(f"Async load started: {load_id} - {image_path}")

    def on_load_completed(self, load_id: str, image_data: object, load_time: float):
        """Handle async load completed signal."""
        logging.debug(f"on_load_completed called with load_id: {load_id}, current_load_id: {self.current_load_id}")

        if load_id != self.current_load_id:
            logging.debug(f"Ignoring stale load: {load_id} != {self.current_load_id}")
            return  # Ignore stale loads

        try:
            logging.info(f"Async load completed: {load_id} ({load_time:.3f}s)")

            # Process the loaded image data
            self.process_loaded_image(image_data)

            # Update overlay position in case view resized
            self.update_overlay_position()

            # Update UI
            height, width = self.current_image.shape[:2]
            self.info_label.setText(f"{Path(self.image_path).name} - {width}x{height}px")
            self.status_label.setText("Image loaded successfully")
            self.load_btn.setEnabled(True)

            # Hide loading overlay and restore background
            logging.debug("Load completed, hiding overlay")
            self.hide_loading_overlay()
            self.image_view.setStyleSheet("""
                QGraphicsView {
                    background-color: white;
                    border: 1px solid #ccc;
                }
            """)

            # Emit signal
            self.image_loaded.emit(self.image_path)

            logging.info(f"Image displayed: {load_id} ({load_time:.3f}s)")

        except Exception as e:
            logging.error(f"Error processing loaded image: {e}")
            self.on_load_failed(load_id, str(self.image_path), str(e), load_time)

    def on_load_failed(self, load_id: str, image_path: str, error: str, load_time: float):
        """Handle async load failed signal."""
        if load_id != self.current_load_id:
            return  # Ignore stale loads

        logging.error(f"Async load failed: {load_id} - {image_path} - {error}")

        # Update UI
        self.info_label.setText(f"Failed to load: {Path(image_path).name}")
        self.status_label.setText(f"Error: {error}")
        self.load_btn.setEnabled(True)

        # Hide loading overlay and restore background
        self.hide_loading_overlay()
        self.image_view.setStyleSheet("""
            QGraphicsView {
                background-color: white;
                border: 1px solid #ccc;
            }
        """)
        self.current_load_id = None

    def show_loading_indicator(self, load_id: str, image_path: str):
        """Show loading indicator."""
        if load_id == self.current_load_id:
            self.loading_label.setVisible(True)
            self.loading_label.setText(f"Loading: {Path(image_path).name}...")

    def hide_loading_indicator(self, load_id: str):
        """Hide loading indicator."""
        if load_id == self.current_load_id:
            self.loading_label.setVisible(False)

    def process_loaded_image(self, image_data):
        """Process the loaded image data."""
        # Store original image
        self.original_image = image_data

        # Apply current adjustments
        self.current_image = self.original_image.copy()
        self.apply_image_adjustments()

        # Extract RPC data if available
        self.extract_rpc_data(self.image_path)

        # Set image data for histogram calculations
        self.image_view.set_image_data(self.original_image, self.bit_depth, self.dtype)

        # Update display
        self.update_display()

    def load_geotiff(self, image_path):
        """Load GeoTIFF using rasterio to preserve georeferencing and bit depth."""
        try:
            logging.info(f"Loading GeoTIFF: {image_path}")
            with rasterio.open(image_path) as src:
                # Preserve original data type and bit depth
                self.dtype = src.dtypes[0]
                self.bit_depth = src.dtypes[0].itemsize * 8
                logging.info(f"Detected dtype: {self.dtype}, bit depth: {self.bit_depth}")

                # Read all bands
                image_data = src.read()
                logging.info(f"Read image data with shape: {image_data.shape}")

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
                logging.info(f"Set max pixel to: {self.max_pixel}")

        except Exception as e:
            logging.error(f"Error loading GeoTIFF: {e}")
            # Fallback to regular image loading
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                raise ValueError(f"Could not load image: {image_path}")
            self.dtype = np.uint8
            self.bit_depth = 8
            self.max_pixel = 255
            logging.info(f"Fallback to 8-bit, max pixel: {self.max_pixel}")

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
                    self.status_label.setText("Image loaded with RPC data")

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
        self.image_view.set_pixmap(pixmap)

        # Draw GCP points
        self.draw_gcp_points()

    def draw_gcp_points(self):
        """Draw GCP points on the image."""
        self.image_view.clear_gcp_points()

        for gcp_id, (x, y) in self.gcp_points.items():
            self.image_view.add_gcp_point(gcp_id, x, y)

        self.image_view.update()

    def on_point_clicked(self, x, y):
        """Handle point click on image."""
        if self.current_image is None:
            return

        # Convert coordinates using projector if available
        img_x, img_y = self.convert_coordinates(x, y)

        # Emit signal
        self.point_selected.emit(img_x, img_y)

        self.status_label.setText(f"Point selected: ({img_x:.1f}, {img_y:.1f})")

    def set_projector(self, projector):
        """Set the projector for coordinate transformations."""
        self._projector = projector

    def convert_coordinates(self, x, y):
        """Convert coordinates using projector if available."""
        # Check if we have a projector available
        if hasattr(self, '_projector') and self._projector is not None:
            try:
                # Convert through projector pipeline

                # Convert scene coordinates to source pixel
                source_pixel = Pixel.create(x, y)

                # Transform to geographic coordinates
                geographic = self._projector.source_to_geographic(source_pixel)

                # Transform to destination pixel (orthorectified)
                dest_pixel = self._projector.geographic_to_destination(geographic)

                return dest_pixel.x_px, dest_pixel.y_px

            except Exception as e:
                # Fall back to passthrough on error
                return x, y
        else:
            # No projector - passthrough (Identity mode)
            return x, y

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
        self.image_view.highlight_point(x, y)

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

        # Reset zoom to fit entire image
        self.image_view.reset_zoom()

        # Apply adjustments
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

        # Emit signal that image was adjusted
        self.image_adjusted.emit()

    def get_image_data(self):
        """Get the current image data for histogram (after adjustments)."""
        return self.current_image

    def show_loading_overlay(self):
        """Show loading overlay over the image view."""
        # Position overlay in center of image view
        overlay_width = 200
        overlay_height = 80

        # Get the image view dimensions
        view_width = self.image_view.width()
        view_height = self.image_view.height()

        if view_width > 0 and view_height > 0:
            x = (view_width - overlay_width) // 2
            y = (view_height - overlay_height) // 2
            self.loading_overlay.setGeometry(x, y, overlay_width, overlay_height)
        else:
            # Fallback positioning if view has no size
            self.loading_overlay.setGeometry(50, 50, overlay_width, overlay_height)

        self.loading_overlay.setVisible(True)
        self.loading_overlay.raise_()

        # Force overlay to be on top
        self.loading_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(128, 128, 128, 200);
                color: white;
                font-size: 16pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 20px;
            }
        """)

    def update_overlay_position(self):
        """Update loading overlay position to center of image view."""
        if self.loading_overlay.isVisible():
            overlay_width = 200
            overlay_height = 80

            view_width = self.image_view.width()
            view_height = self.image_view.height()

            if view_width > 0 and view_height > 0:
                x = (view_width - overlay_width) // 2
                y = (view_height - overlay_height) // 2
                self.loading_overlay.setGeometry(x, y, overlay_width, overlay_height)
                logging.debug(f"Updated overlay position to ({x}, {y})")

    def hide_loading_overlay(self):
        """Hide loading overlay."""
        logging.debug("Hiding loading overlay")
        self.loading_overlay.setVisible(False)

    def cleanup(self):
        """Cleanup resources when viewer is destroyed."""
        if hasattr(self, 'async_loader'):
            self.async_loader.shutdown()
        if hasattr(self, 'loading_indicator'):
            self.loading_indicator.stop_animation()
