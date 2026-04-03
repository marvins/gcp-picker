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
#    File:    image_canvas.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Image Canvas Widget - Interactive image display with point selection, zoom, and pan
"""

#  Python Standard Libraries
import logging

#  Third-Party Libraries
from qtpy.QtCore import QPoint, Qt, Signal
from qtpy.QtGui import QColor, QFont, QMouseEvent, QPen, QPainter, QWheelEvent
from qtpy.QtWidgets import QScrollArea, QWidget

class Image_Canvas(QWidget):
    """Interactive image canvas with point selection capabilities."""

    # Signals
    point_clicked = Signal(int, int)  # x, y in widget coordinates
    gcp_point_clicked = Signal(int)  # gcp_id
    cursor_moved = Signal(int, int, object)  # x, y, pixel_value

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.zoom_factor = 1.0
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.highlighted_point = None
        self.georeferencing = None  # (transform, width, height)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        # Panning state
        self._panning = False
        self._last_pan_pos = None

    def set_pixmap(self, pixmap):
        """Set the pixmap to display."""
        self.pixmap = pixmap
        if self.pixmap:
            self.setFixedSize(self.pixmap.size() * self.zoom_factor)
        else:
            self.setFixedSize(400, 300)
        self.update()

    def set_zoom(self, zoom_factor):
        """Set zoom factor."""
        self.zoom_factor = zoom_factor
        if self.pixmap:
            self.setFixedSize(self.pixmap.size() * self.zoom_factor)
        self.update()

    def _get_scroll_area(self) -> QScrollArea | None:
        """Get the parent QScrollArea if available."""
        parent = self.parent()
        if isinstance(parent, QScrollArea):
            return parent
        return None

    def set_georeferencing(self, transform, width, height):
        """Set georeferencing information."""
        self.georeferencing = (transform, width, height)

    def add_gcp_point(self, x, y, gcp_id):
        """Add a GCP point."""
        self.gcp_points[gcp_id] = (x, y)
        self.update()

    def remove_gcp_point(self, gcp_id):
        """Remove a GCP point."""
        if gcp_id in self.gcp_points:
            del self.gcp_points[gcp_id]
            self.update()

    def clear_gcp_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if not self.pixmap:
            return

        # Accept the event to prevent it from being handled by the scroll area
        event.accept()

        # Get wheel delta
        delta = event.angleDelta().y()

        # Calculate zoom factor change
        zoom_step = 0.1
        if delta > 0:
            new_zoom = min(self.zoom_factor + zoom_step, 5.0)  # Max 5x zoom
        else:
            new_zoom = max(self.zoom_factor - zoom_step, 0.1)  # Min 0.1x zoom

        # Get scroll area and current scroll position
        scroll_area = self._get_scroll_area()
        if not scroll_area:
            self.set_zoom(new_zoom)
            return

        # Get current scroll values
        h_scroll = scroll_area.horizontalScrollBar().value()
        v_scroll = scroll_area.verticalScrollBar().value()

        # Get mouse position in widget coordinates
        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Debug logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Before zoom - h_scroll={h_scroll}, v_scroll={v_scroll}, mouse=({mouse_x},{mouse_y}), zoom={self.zoom_factor}")

        # Calculate the point in the image that is under the mouse before zoom
        # This is: (scroll_position + mouse_position) / current_zoom
        image_under_mouse_x = (h_scroll + mouse_x) / self.zoom_factor
        image_under_mouse_y = (v_scroll + mouse_y) / self.zoom_factor

        # Apply zoom
        self.set_zoom(new_zoom)

        # Calculate new scroll position to keep the same image point under the mouse
        # New scroll = (image_point * new_zoom) - mouse_position
        new_h_scroll = int(image_under_mouse_x * new_zoom - mouse_x)
        new_v_scroll = int(image_under_mouse_y * new_zoom - mouse_y)

        logger.debug(f"After zoom - new_h_scroll={new_h_scroll}, new_v_scroll={new_v_scroll}, new_zoom={new_zoom}")
        logger.debug(f"Image point under mouse: ({image_under_mouse_x},{image_under_mouse_y})")

        # Apply new scroll position
        scroll_area.horizontalScrollBar().setValue(new_h_scroll)
        scroll_area.verticalScrollBar().setValue(new_v_scroll)

    def pixel_to_image_coords(self, pixel_x, pixel_y):
        """Convert pixel coordinates to image coordinates."""
        if self.zoom_factor == 0:
            return pixel_x, pixel_y

        img_x = pixel_x / self.zoom_factor
        img_y = pixel_y / self.zoom_factor
        return img_x, img_y

    def image_to_pixel_coords(self, img_x, img_y):
        """Convert image coordinates to pixel coordinates."""
        pixel_x = img_x * self.zoom_factor
        pixel_y = img_y * self.zoom_factor
        return pixel_x, pixel_y

    def paintEvent(self, event):
        """Paint the canvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        # Draw image
        if self.pixmap:
            scaled_pixmap = self.pixmap.scaled(
                self.pixmap.size() * self.zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled_pixmap)

        # Draw GCP points
        for gcp_id, (x, y) in self.gcp_points.items():
            pixel_x, pixel_y = self.image_to_pixel_coords(x, y)
            self.draw_gcp_marker(painter, pixel_x, pixel_y, gcp_id)

        # Draw highlighted point
        if self.highlighted_point:
            x, y = self.highlighted_point
            pixel_x, pixel_y = self.image_to_pixel_coords(x, y)
            self.draw_highlight_marker(painter, pixel_x, pixel_y)

    def draw_gcp_marker(self, painter, x, y, gcp_id):
        """Draw a GCP marker."""
        # Outer circle (red)
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QColor(255, 0, 0, 100))
        painter.drawEllipse(QPoint(x, y), 8, 8)

        # Inner circle (white)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPoint(x, y), 3, 3)

        # GCP ID label
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.drawText(QPoint(x + 12, y - 8), str(gcp_id))

    def draw_highlight_marker(self, painter, x, y):
        """Draw a highlighted marker."""
        # Yellow crosshair
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        painter.drawLine(x - 15, y, x + 15, y)
        painter.drawLine(x, y - 15, x, y + 15)

        # Yellow circle
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        painter.setBrush(QColor(255, 255, 0, 50))
        painter.drawEllipse(QPoint(x, y), 12, 12)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MiddleButton:
            # Start panning
            self._panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()

            # Check if clicking on a GCP point
            for gcp_id, (px, py) in self.gcp_points.items():
                pixel_x, pixel_y = self.image_to_pixel_coords(px, py)
                distance = ((x - pixel_x) ** 2 + (y - pixel_y) ** 2) ** 0.5
                if distance <= 10:  # Click tolerance
                    self.gcp_point_clicked.emit(gcp_id)
                    return

            # Otherwise, emit point clicked signal
            self.point_clicked.emit(x, y)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for hover effects and panning."""
        x, y = event.x(), event.y()

        # Handle panning
        if self._panning and self._last_pan_pos:
            scroll_area = self._get_scroll_area()
            if scroll_area:
                delta_x = self._last_pan_pos.x() - x
                delta_y = self._last_pan_pos.y() - y

                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()

                # Update scroll position immediately for smooth panning
                h_bar.setValue(h_bar.value() + delta_x)
                v_bar.setValue(v_bar.value() + delta_y)

            self._last_pan_pos = event.pos()
            event.accept()
            return

        # Emit cursor_moved signal for metadata panel
        img_x, img_y = self.pixel_to_image_coords(x, y)
        self.cursor_moved.emit(int(img_x), int(img_y), None)  # pixel_value will be added later

        # Check if hovering over a GCP point
        hovering_gcp = False
        for gcp_id, (px, py) in self.gcp_points.items():
            pixel_x, pixel_y = self.image_to_pixel_coords(px, py)
            distance = ((x - pixel_x) ** 2 + (y - pixel_y) ** 2) ** 0.5
            if distance <= 10:
                hovering_gcp = True
                break

        if hovering_gcp:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MiddleButton:
            # Stop panning
            self._panning = False
            self._last_pan_pos = None
            self.setCursor(Qt.CrossCursor)
            event.accept()
