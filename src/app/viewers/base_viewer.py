"""
Base Viewer - Abstract base class for image viewers

Provides common functionality for both test and reference image viewers including:
- Image loading and display
- Zoom and pan controls
- GCP point management
- Coordinate transformations
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QImage, QPixmap

from app.core.coordinate import PixelCoordinate, GeographicCoordinate


class BaseViewer(ABC, QWidget):
    """Abstract base class for image viewers (test and reference)."""

    # Signals
    point_selected = Signal(float, float)  # x, y in image coordinates
    cursor_moved = Signal(float, float)  # x, y in image coordinates
    image_loaded = Signal(str)  # image path
    gcp_point_clicked = Signal(int)  # gcp_id

    def __init__(self, parent=None):
        super().__init__(parent)

        # Image data
        self.image_path: str | None = None
        self.original_image: np.ndarray | None = None
        self.current_image: np.ndarray | None = None
        self.display_pixmap: QPixmap | None = None

        # Zoom state
        self.zoom_factor: float = 1.0
        self.min_zoom: float = 0.1
        self.max_zoom: float = 10.0

        # GCP points: gcp_id -> (x, y) in image coordinates
        self.gcp_points: dict[int, tuple[float, float]] = {}

        # Coordinate transformation
        self.transform: Any | None = None  # Geotransform for geo-referenced images

        # UI setup (implemented by subclasses)
        self.setup_ui()

    @abstractmethod
    def setup_ui(self):
        """Setup the viewer UI. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_status_label(self) -> QLabel:
        """Get the status label for this viewer."""
        pass

    def load_image(self, image_path: str) -> bool:
        """Load an image file. Returns True if successful."""
        raise NotImplementedError("Subclasses must implement image loading")

    def has_image(self) -> bool:
        """Check if an image is currently loaded."""
        return self.original_image is not None

    def get_image_path(self) -> str | None:
        """Get the path of the currently loaded image."""
        return self.image_path

    def get_image_data(self) -> np.ndarray | None:
        """Get the current image data as numpy array."""
        return self.current_image

    def get_image_dimensions(self) -> tuple[int, int] | None:
        """Get (width, height) of current image."""
        if self.current_image is None:
            return None
        height, width = self.current_image.shape[:2]
        return (width, height)

    def clear_image(self):
        """Clear the current image."""
        self.image_path = None
        self.original_image = None
        self.current_image = None
        self.display_pixmap = None
        self.clear_points()
        self.update_display()

    def set_zoom(self, zoom: float):
        """Set zoom factor (clamped to min/max)."""
        self.zoom_factor = max(self.min_zoom, min(self.max_zoom, zoom))
        self.update_display()

    def zoom_in(self, factor: float = 1.25):
        """Zoom in by factor."""
        self.set_zoom(self.zoom_factor * factor)

    def zoom_out(self, factor: float = 0.8):
        """Zoom out by factor."""
        self.set_zoom(self.zoom_factor * factor)

    def reset_zoom(self):
        """Reset zoom to 1.0."""
        self.set_zoom(1.0)

    def get_zoom(self) -> float:
        """Get current zoom factor."""
        return self.zoom_factor

    def add_gcp_point(self, gcp_id: int, x: float, y: float):
        """Add a GCP point at image coordinates."""
        self.gcp_points[gcp_id] = (x, y)

    def remove_gcp_point(self, gcp_id: int):
        """Remove a GCP point."""
        self.gcp_points.pop(gcp_id, None)

    def clear_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()

    def get_gcp_points(self) -> dict[int, tuple[float, float]]:
        """Get all GCP points."""
        return self.gcp_points.copy()

    def set_geotransform(self, transform: Any):
        """Set geotransform for coordinate conversion."""
        self.transform = transform

    def image_to_geo_coords(self, x: float, y: float) -> tuple[float, float] | None:
        """Convert image pixel coordinates to geographic coordinates."""
        if self.transform is None:
            return None

        # GDAL geotransform: [origin_x, pixel_width, rotation_x, origin_y, rotation_y, pixel_height]
        geo_x = self.transform[0] + x * self.transform[1] + y * self.transform[2]
        geo_y = self.transform[3] + x * self.transform[4] + y * self.transform[5]
        return (geo_x, geo_y)

    def geo_to_image_coords(self, geo_x: float, geo_y: float) -> tuple[float, float] | None:
        """Convert geographic coordinates to image pixel coordinates."""
        if self.transform is None:
            return None

        # Inverse transform (simplified, assumes no rotation)
        x = (geo_x - self.transform[0]) / self.transform[1]
        y = (geo_y - self.transform[3]) / self.transform[5]
        return (x, y)

    def update_display(self):
        """Update the display with current image and zoom."""
        raise NotImplementedError("Subclasses must implement display update")

    def _numpy_to_pixmap(self, image_array: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap."""
        if len(image_array.shape) == 2:
            # Grayscale
            height, width = image_array.shape
            bytes_per_line = width
            image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        elif len(image_array.shape) == 3:
            # Color (RGB or RGBA)
            height, width, channels = image_array.shape
            bytes_per_line = channels * width

            if channels == 3:
                # RGB
                image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            elif channels == 4:
                # RGBA
                image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
            else:
                raise ValueError(f"Unsupported number of channels: {channels}")
        else:
            raise ValueError(f"Unsupported image shape: {image_array.shape}")

        return QPixmap.fromImage(image)

    def pixel_to_image_coords(self, widget_x: int, widget_y: int) -> tuple[float, float]:
        """Convert widget pixel coordinates to image coordinates (accounting for zoom)."""
        img_x = widget_x / self.zoom_factor
        img_y = widget_y / self.zoom_factor
        return (img_x, img_y)

    def image_to_pixel_coords(self, img_x: float, img_y: float) -> tuple[int, int]:
        """Convert image coordinates to widget pixel coordinates (accounting for zoom)."""
        widget_x = int(img_x * self.zoom_factor)
        widget_y = int(img_y * self.zoom_factor)
        return (widget_x, widget_y)
