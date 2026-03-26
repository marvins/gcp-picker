"""
Image Canvas Widget - Interactive image display with point selection
"""

from qtpy.QtWidgets import QWidget, QLabel
from qtpy.QtCore import Qt, Signal, QPoint, QRect
from qtpy.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QMouseEvent

class Image_Canvas(QWidget):
    """Interactive image canvas with point selection capabilities."""

    # Signals
    point_clicked = Signal(int, int)  # x, y in widget coordinates
    gcp_point_clicked = Signal(int)  # gcp_id

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.zoom_factor = 1.0
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.highlighted_point = None
        self.georeferencing = None  # (transform, width, height)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

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

    def highlight_point(self, x, y):
        """Highlight a specific point."""
        self.highlighted_point = (x, y)
        self.update()

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
        """Handle mouse move for hover effects."""
        x, y = event.x(), event.y()

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
