"""
Graphics Image View - Interactive image display using QGraphicsView framework
"""

from qtpy.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from qtpy.QtCore import Qt, Signal, QPoint
from qtpy.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QMouseEvent, QWheelEvent
import numpy as np


class Graphics_Image_View(QGraphicsView):
    """Interactive image view using QGraphicsView with built-in pan and zoom."""

    # Signals
    point_clicked = Signal(int, int)  # x, y in image coordinates
    gcp_point_clicked = Signal(int)  # gcp_id
    cursor_moved = Signal(int, int, object)  # x, y, pixel_value

    def __init__(self):
        super().__init__()

        # Scene and item setup
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.pixmap_item = None
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.highlighted_point = None
        self.georeferencing = None  # (transform, width, height)

        # Image metadata for histogram
        self.original_image = None
        self.bit_depth = 8
        self.dtype = np.uint8

        # Zoom and pan state
        self.zoom_factor = 1.0
        self._drag_start_pos = None
        self._last_pan_pos = None

        # View configuration
        self.setMouseTracking(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Enable smooth transformations
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)

    def set_pixmap(self, pixmap):
        """Set the pixmap to display."""
        if self.pixmap_item:
            self.scene.removeItem(self.pixmap_item)

        if pixmap:
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.pixmap_item)
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        else:
            self.pixmap_item = None

        self.update()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming with mouse position as origin."""
        if not self.pixmap_item:
            return

        # Get wheel delta
        delta = event.angleDelta().y()

        # Calculate zoom factor change
        zoom_step = 0.1
        if delta > 0:
            new_zoom = min(self.zoom_factor + zoom_step, 5.0)  # Max 5x zoom
        else:
            new_zoom = max(self.zoom_factor - zoom_step, 0.1)  # Min 0.1 zoom

        # Get mouse position in view coordinates
        mouse_pos = event.position()

        # Get the point under the mouse in scene coordinates before zoom
        old_scene_pos = self.mapToScene(mouse_pos.toPoint())

        # Apply zoom
        self.zoom_factor = new_zoom
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

        # Get the same point in scene coordinates after zoom
        new_scene_pos = self.mapToScene(mouse_pos.toPoint())

        # Calculate the offset to keep the mouse over the same scene point
        offset = new_scene_pos - old_scene_pos
        self.translate(offset.x(), offset.y())

        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning and point selection."""
        if event.button() == Qt.MiddleButton:
            # Start panning
            self._drag_start_pos = event.pos()
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            # Convert to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if clicking on a GCP point
            for gcp_id, (x, y) in self.gcp_points.items():
                distance = ((scene_pos.x() - x) ** 2 + (scene_pos.y() - y) ** 2) ** 0.5
                if distance <= 10 / self.zoom_factor:  # Adjust tolerance for zoom
                    self.gcp_point_clicked.emit(gcp_id)
                    return

            # Emit point clicked signal in image coordinates
            self.point_clicked.emit(int(scene_pos.x()), int(scene_pos.y()))

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning and cursor tracking."""
        if self._drag_start_pos and event.buttons() & Qt.MiddleButton:
            # Handle panning
            delta = event.pos() - self._last_pan_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._last_pan_pos = event.pos()
            event.accept()
            return

        # Emit cursor_moved signal for metadata panel
        scene_pos = self.mapToScene(event.pos())
        self.cursor_moved.emit(int(scene_pos.x()), int(scene_pos.y()), None)

        # Check if hovering over a GCP point
        hovering_gcp = False
        for gcp_id, (x, y) in self.gcp_points.items():
            distance = ((scene_pos.x() - x) ** 2 + (scene_pos.y() - y) ** 2) ** 0.5
            if distance <= 10 / self.zoom_factor:
                hovering_gcp = True
                if self.highlighted_point != gcp_id:
                    self.highlighted_point = gcp_id
                    self.update()
                break

        if not hovering_gcp and self.highlighted_point is not None:
            self.highlighted_point = None
            self.update()

        # Set cursor based on hover state
        if hovering_gcp:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MiddleButton:
            # Stop panning
            self._drag_start_pos = None
            self._last_pan_pos = None
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def add_gcp_point(self, gcp_id, x, y):
        """Add a GCP point at the specified image coordinates."""
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

    def set_georeferencing(self, transform, width, height):
        """Set georeferencing transform for coordinate conversion."""
        self.georeferencing = (transform, width, height)

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

    def set_zoom(self, zoom_factor):
        """Set zoom factor."""
        self.zoom_factor = max(0.1, min(zoom_factor, 5.0))
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

    def get_zoom(self):
        """Get current zoom factor."""
        return self.zoom_factor

    def paintEvent(self, event):
        """Override paint to draw GCP points."""
        super().paintEvent(event)

        if not self.pixmap_item or not self.gcp_points:
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw GCP points
        for gcp_id, (x, y) in self.gcp_points.items():
            # Convert scene coordinates to view coordinates
            view_pos = self.mapFromScene(QPoint(x, y))

            # Draw point
            is_highlighted = (self.highlighted_point == gcp_id)
            color = QColor(255, 0, 0) if is_highlighted else QColor(255, 255, 0)
            painter.setPen(QPen(color, 2))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
            painter.drawEllipse(view_pos, 12, 12)

            # Draw label
            painter.setPen(QPen(color, 1))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(view_pos + QPoint(15, -5), f"GCP{gcp_id}")

    def set_image_data(self, image_data, bit_depth=8, dtype=np.uint8):
        """Set image data for histogram calculations."""
        self.original_image = image_data
        self.bit_depth = bit_depth
        self.dtype = dtype

    def get_image_data(self):
        """Get current image data for histogram."""
        return self.original_image
