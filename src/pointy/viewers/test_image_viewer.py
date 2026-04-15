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
import math
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
from qtpy.QtGui import QImage, QPixmap, QFont, QWheelEvent
from qtpy.QtWidgets import (QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QFrame)

#  Project Libraries
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.constants import METERS_PER_DEG_LAT
from tmns.geo.proj import Warp_Extent
from pointy.core.qt_async_image_loader import Qt_Async_Image_Loader
from pointy.widgets.graphics_image_view import Graphics_Image_View

class Test_Image_Viewer(QWidget):
    """Viewer for test image with point selection capabilities."""

    # Signals
    point_selected = Signal(float, float)  # x, y in image coordinates
    image_loaded = Signal(str)  # image path
    gcp_point_clicked = Signal(int)  # gcp_id
    cursor_moved = Signal(int, int, object, object, object, object)  # x, y, pixel_value, lat, lon, alt
    image_adjusted = Signal()  # emitted when image adjustments are applied
    update_requested = Signal()  # emitted when Update button is clicked
    view_mode_changed = Signal(bool)  # True = ortho, False = raw

    def __init__(self):
        super().__init__()
        self.image_path = None
        self.original_image = None
        self.current_image = None
        self._warped_image = None  # Store warped ortho image separately
        self.is_loading = False
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.is_orthorectified = False
        self._projector = None
        self._warp_extent: Warp_Extent | None = None

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
        self.current_load_id = None

        # Connect async loader signals
        logging.debug("Connecting async loader signals")
        self.async_loader.load_started.connect(self.on_load_started)
        self.async_loader.load_completed.connect(self.on_load_completed)
        self.async_loader.load_failed.connect(self.on_load_failed)
        logging.debug("Async loader signals connected")

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Integrated toolbar bar
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: none;
            }
            QLabel {
                color: #cccccc;
                font-size: 9pt;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 0 6px;
            }
            QPushButton {
                color: #cccccc;
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 2px 10px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #444444;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
            QPushButton:checked {
                background-color: #0d6efd;
                color: #ffffff;
            }
            QPushButton:disabled {
                color: #666666;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 0, 4, 0)
        toolbar_layout.setSpacing(2)

        title_label = QLabel("Test Image")
        toolbar_layout.addWidget(title_label)

        # Loading indicator (initially hidden)
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("QLabel { color: #f0a500; font-weight: bold; background: transparent; border: none; }")
        self.loading_label.setVisible(False)
        toolbar_layout.addWidget(self.loading_label)

        toolbar_layout.addStretch()

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("QFrame { color: #555555; }")
        toolbar_layout.addWidget(sep)

        # Update button
        self.update_btn = QPushButton("↺  Update")
        self.update_btn.setToolTip("Pan the reference map to match this view's geographic center")
        self.update_btn.clicked.connect(self.update_requested)
        toolbar_layout.addWidget(self.update_btn)

        # Raw / Ortho toggle
        self.ortho_btn = QPushButton("Raw")
        self.ortho_btn.setCheckable(True)
        self.ortho_btn.setEnabled(False)
        self.ortho_btn.setToolTip("Switch between raw and orthorectified view (requires ortho model)")
        self.ortho_btn.clicked.connect(self._on_ortho_toggle)
        toolbar_layout.addWidget(self.ortho_btn)

        layout.addWidget(toolbar)

        # Image info label
        self.info_label = QLabel("No image loaded")
        self.info_label.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
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
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 8pt; font-family: monospace; }")
        layout.addWidget(self.status_label)

    def _on_ortho_toggle(self, checked: bool):
        """Handle Raw/Ortho button toggle."""
        self.ortho_btn.setText("Ortho" if checked else "Raw")
        self.view_mode_changed.emit(checked)

    def set_ortho_available(self, available: bool):
        """Enable or disable the ortho toggle based on whether a model is ready."""
        self.ortho_btn.setEnabled(available)
        if not available:
            self.ortho_btn.setChecked(False)
            self.ortho_btn.setText("Raw")

    def reload_raw_image(self):
        """Reload and display the original raw image, discarding any ortho rendering."""
        self._warp_extent = None
        self._warped_image = None
        self.is_orthorectified = False
        if self.image_path:
            self.load_image(self.image_path)

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
        self.is_loading = True
        logging.debug(f"Starting async image load: {image_path}")

        # Start async load
        self.current_load_id = self.async_loader.load_image_async(image_path)

        # Update UI to show loading state
        self.info_label.setText(f"Loading: {Path(image_path).name}...")
        self.status_label.setText("Loading image...")

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
        logging.debug(f"Async load started: {load_id} - {image_path}")

    def on_load_completed(self, load_id: str, image_data: object, load_time: float):
        """Handle async load completed signal."""
        logging.debug(f"on_load_completed called with load_id: {load_id}, current_load_id: {self.current_load_id}")

        if load_id != self.current_load_id:
            logging.debug(f"Ignoring stale load: {load_id} != {self.current_load_id}")
            return  # Ignore stale loads

        try:
            logging.debug(f"Async load completed: {load_id} ({load_time:.3f}s)")

            # Process the loaded image data
            self.process_loaded_image(image_data)

            # Update overlay position in case view resized
            self.update_overlay_position()

            # Update UI
            height, width = self.current_image.shape[:2]
            self.info_label.setText(f"{Path(self.image_path).name} - {width}x{height}px")
            self.status_label.setText("Image loaded successfully")

            # Hide loading overlay and restore background
            logging.debug("Load completed, hiding overlay")
            self.is_loading = False
            self.hide_loading_overlay()
            self.image_view.setStyleSheet("""
                QGraphicsView {
                    background-color: white;
                    border: 1px solid #ccc;
                }
            """)

            # Emit signal
            self.image_loaded.emit(self.image_path)

            logging.info(f"Image loaded and displayed: {Path(self.image_path).name} ({load_time:.3f}s)")

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
        self.is_loading = False

        # Hide loading overlay and restore background
        self.hide_loading_overlay()
        self.image_view.setStyleSheet("""
            QGraphicsView {
                background-color: white;
                border: 1px solid #ccc;
            }
        """)
        self.current_load_id = None

    def process_loaded_image(self, image_data):
        """Process the loaded image data."""
        # Store original image
        self.original_image = image_data

        # Apply current adjustments
        self.current_image = self.original_image.copy()
        self.apply_image_adjustments()

        # Set image data for histogram calculations
        self.image_view.set_image_data(self.original_image, self.bit_depth, self.dtype)

        # Update display
        self.update_display()

    def load_geotiff(self, image_path):
        """Load GeoTIFF using rasterio to preserve georeferencing and bit depth."""
        try:
            logging.debug(f"Loading GeoTIFF: {image_path}")
            with rasterio.open(image_path) as src:
                # Preserve original data type and bit depth
                self.dtype = src.dtypes[0]
                self.bit_depth = src.dtypes[0].itemsize * 8
                logging.debug(f"Detected dtype: {self.dtype}, bit depth: {self.bit_depth}")

                # Read all bands
                image_data = src.read()
                logging.debug(f"Read image data with shape: {image_data.shape}")

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
                logging.debug(f"Set max pixel to: {self.max_pixel}")

        except Exception as e:
            logging.error(f"Error loading GeoTIFF: {e}")
            # Fallback to regular image loading
            self.original_image = cv2.imread(image_path)
            if self.original_image is None:
                raise ValueError(f"Could not load image: {image_path}")
            self.dtype = np.uint8
            self.bit_depth = 8
            self.max_pixel = 255
            logging.debug(f"Fallback to 8-bit, max pixel: {self.max_pixel}")

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
        """Draw GCP points on the image.

        In raw mode draws at stored source pixel coordinates.
        In ortho mode projects each GCP through the projector to the
        warped output grid before drawing.
        """
        self.image_view.clear_gcp_points()

        for gcp_id, (x, y) in self.gcp_points.items():
            draw_x, draw_y = x, y

            if (self.is_orthorectified
                    and self._warp_extent is not None
                    and self._projector is not None
                    and self.current_image is not None):
                try:
                    geo = self._projector.source_to_geographic(Pixel(x_px=x, y_px=y))
                    result = self.geo_to_ortho_pixel(geo.latitude_deg, geo.longitude_deg)
                    if result is not None:
                        draw_x, draw_y = result
                except Exception:
                    pass

            self.image_view.add_gcp_point(gcp_id, draw_x, draw_y)

        self.image_view.update()

    def geo_to_ortho_pixel(self, lat: float, lon: float) -> tuple[float, float] | None:
        """Convert a geographic coordinate to ortho output pixel (col, row).

        Returns None if the viewer is not in ortho mode or extents are unavailable.
        """
        if self._warp_extent is None or self.current_image is None:
            return None
        h, w = self.current_image.shape[:2]
        ext = self._warp_extent
        params = Geographic.compute_extent_params(ext.min_point, ext.max_point, (w, h))
        px = (lon - ext.min_point.longitude_deg) / params.width * w
        py = (ext.max_point.latitude_deg - lat) / params.height * h
        return px, py

    def ortho_pixel_to_geo(self, x: float, y: float) -> tuple[float, float] | None:
        """Convert an ortho output pixel (col, row) to (lat, lon).

        Returns None if the viewer is not in ortho mode or extents are unavailable.
        """
        if self._warp_extent is None or self.current_image is None:
            return None
        h, w = self.current_image.shape[:2]
        ext = self._warp_extent
        params = Geographic.compute_extent_params(ext.min_point, ext.max_point, (w, h))
        lon = ext.min_point.longitude_deg + (x / w) * params.width
        lat = ext.max_point.latitude_deg - (y / h) * params.height
        return lat, lon

    def on_point_clicked(self, x, y):
        """Handle point click on image.

        In raw mode, (x, y) are already source image pixel coordinates.
        In ortho mode, (x, y) are in the warped output grid; they are
        inverted back to source pixel space via the warp extent + projector
        before emitting.
        """
        if self.current_image is None:
            return

        if self.is_orthorectified and self._warp_extent is not None and self._projector is not None:
            geo = self.ortho_pixel_to_geo(x, y)
            if geo is None:
                return
            lat, lon = geo
            try:
                src_px = self._projector.geographic_to_source(Geographic(latitude_deg=lat, longitude_deg=lon))
                x, y = src_px.x_px, src_px.y_px
            except Exception as e:
                logging.debug(f'Ortho click inversion failed: {e}')
                return

        self.point_selected.emit(x, y)
        self.status_label.setText(f"Point selected: ({x:.1f}, {y:.1f})")

    def set_projector(self, projector):
        """Set the projector used to convert source image pixels to geographic coordinates."""
        self._projector = projector

    def source_pixel_to_geographic(self, x: float, y: float) -> Geographic | None:
        """Convert a source image pixel to geographic coordinates via the projector.

        Returns None if no projector is set or the transformation fails.

        Args:
            x: Source image pixel x coordinate.
            y: Source image pixel y coordinate.

        Returns:
            Geographic (lat, lon) or None.
        """
        if self._projector is None:
            return None
        try:
            return self._projector.source_to_geographic(Pixel(x_px=x, y_px=y))
        except Exception as e:
            logging.debug(f"source_pixel_to_geographic failed at ({x}, {y}): {e}")
            return None

    def geo_scale_at_center(self) -> float | None:
        """Return the ground sample distance (metres/pixel) at the image centre.

        Uses the current projector to project two nearby pixels and measures
        the resulting geographic distance.  Returns None if no projector is set
        or the image has not been loaded yet.
        """
        if self._projector is None or self._projector.is_identity:
            return None
        if self.original_image is None:
            return None
        try:
            src_h, src_w = self.original_image.shape[:2]
            delta = max(src_w, src_h) * 0.01
            cx, cy = src_w / 2.0, src_h / 2.0
            geo_a = self._projector.source_to_geographic(Pixel(x_px=cx,         y_px=cy))
            geo_b = self._projector.source_to_geographic(Pixel(x_px=cx + delta, y_px=cy))
            d_deg = abs(geo_b.longitude_deg - geo_a.longitude_deg)
            meters_per_deg_lon = METERS_PER_DEG_LAT * math.cos(math.radians(geo_a.latitude_deg))
            return d_deg * meters_per_deg_lon / delta
        except Exception as e:
            logging.debug(f'geo_scale_at_center failed: {e}')
            return None

    def on_gcp_point_clicked(self, gcp_id):
        """Handle GCP point click."""
        self.gcp_point_clicked.emit(gcp_id)

    def _on_cursor_moved(self, x, y, pixel_value):
        """Handle cursor movement - convert source pixel to geographic if projector is set.

        Coordinates (x, y) are in source image pixel space (reported by
        Graphics_Image_View after accounting for zoom/pan).  The projector
        converts them to geographic (lat, lon) when available.
        """
        geo = self.source_pixel_to_geographic(x, y)

        lat = geo.latitude_deg if geo is not None else None
        lon = geo.longitude_deg if geo is not None else None
        alt = None  # altitude not available from 2-D projectors

        self.cursor_moved.emit(x, y, pixel_value, lat, lon, alt)

        if geo is not None:
            self.status_label.setText(
                f"Cursor: ({x}, {y}) | {geo.latitude_deg:.6f}\u00b0N  {geo.longitude_deg:.6f}\u00b0E"
            )
        else:
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
        """Highlight a specific GCP point.

        In ortho mode, converts source pixel coordinates to ortho pixel coordinates.
        """
        if self.is_orthorectified and self._warp_extent is not None:
            # Convert source pixel to geographic, then to ortho pixel
            geo = self.source_pixel_to_geographic(x, y)
            if geo is not None:
                ortho_result = self.geo_to_ortho_pixel(geo.latitude_deg, geo.longitude_deg)
                if ortho_result is not None:
                    x, y = ortho_result
        self.image_view.highlight_point(x, y)

    def clear_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()
        self.draw_gcp_points()

    def get_image_array(self) -> np.ndarray | None:
        """Return the original loaded image as a numpy array (H, W, C) uint8, or None."""
        return self.original_image

    def set_candidate_markers(self, pts: list[tuple[float, float]]):
        """Display auto-match candidate positions as cyan crosses on the image.

        Args:
            pts: List of (x, y) pixel coordinates in full-res image space.
        """
        self.image_view.set_candidate_markers(pts)

    def clear_candidate_markers(self):
        """Remove all auto-match candidate markers from the image view."""
        self.image_view.clear_candidate_markers()

    def display_warped_array(self, warped: np.ndarray, warp_extent: Warp_Extent | None = None):
        """Display a pre-warped numpy image array (H x W x 3, uint8) as the ortho view."""
        self._warped_image = warped.copy()
        self.current_image = self._warped_image.copy()
        self.is_orthorectified = True
        self._warp_extent = warp_extent
        self.update_display()
        h, w = warped.shape[:2]
        self.info_label.setText(f"Orthorectified - {w}x{h}px")
        self.draw_gcp_points()

    def update_orthorectified_image(self, ortho_image_path):
        """Update display with orthorectified image."""
        try:
            # Load orthorectified image
            ortho_image = cv2.imread(ortho_image_path)
            if ortho_image is not None:
                self._warped_image = ortho_image.copy()
                self.current_image = self._warped_image.copy()
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
        """Check if an image is fully loaded and ready (not still loading)."""
        return self.current_image is not None and not self.is_loading

    def get_image_path(self):
        """Get the current image path."""
        return self.image_path


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
        """Apply current image adjustments to the appropriate base image."""
        if self.original_image is None:
            return

        # Use warped image as base if in ortho mode, otherwise use original
        if self.is_orthorectified and self._warped_image is not None:
            base_image = self._warped_image
        else:
            base_image = self.original_image

        # Start with base image
        adjusted = base_image.astype(np.float32)

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
