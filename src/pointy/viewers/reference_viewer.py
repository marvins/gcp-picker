"""
Reference Viewer - Right panel for displaying map-projected reference sources
"""

import os
import numpy as np
from pathlib import Path
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QComboBox, QLineEdit, QScrollArea,
                           QTabWidget, QFormLayout, QSpinBox, QDoubleSpinBox)
from qtpy.QtCore import Qt, Signal, QTimer
from qtpy.QtGui import QPixmap, QFont

from app.widgets.image_canvas import Image_Canvas
from app.widgets.zoom_controls import Zoom_Controls
from app.core.wms_client import WMSClient
from app.core.gdal_reader import GDALReader

class Reference_Viewer(QWidget):
    """Viewer for reference sources (WMS/WMTS/GDAL virtual rasters)."""

    # Signals
    point_selected = Signal(float, float, float, float)  # x, y, lon, lat
    reference_loaded = Signal(dict)  # reference info

    def __init__(self):
        super().__init__()
        self.current_reference = None
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.reference_transform = None

        # Initialize clients
        self.wms_client = WMSClient()
        self.gdal_reader = GDALReader()

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Reference Source")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Tab widget for different reference sources
        self.tab_widget = QTabWidget()

        # WMS/WMTS tab
        self.wms_tab = self.setup_wms_tab()
        self.tab_widget.addTab(self.wms_tab, "WMS/WMTS")

        # GDAL Virtual Raster tab
        self.gdal_tab = self.setup_gdal_tab()
        self.tab_widget.addTab(self.gdal_tab, "GDAL Virtual Raster")

        layout.addWidget(self.tab_widget)

        # Image display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.image_canvas = Image_Canvas()
        self.image_canvas.point_clicked.connect(self.on_point_clicked)
        self.image_canvas.gcp_point_clicked.connect(self.on_gcp_point_clicked)
        self.scroll_area.setWidget(self.image_canvas)

        layout.addWidget(self.scroll_area)

        # Zoom controls
        self.zoom_controls = Zoom_Controls()
        self.zoom_controls.zoom_changed.connect(self.on_zoom_changed)
        layout.addWidget(self.zoom_controls)

        # Status
        self.status_label = QLabel("Select reference source")
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 9pt; }")
        layout.addWidget(self.status_label)

    def setup_wms_tab(self):
        """Setup WMS/WMTS configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Service configuration
        form_layout = QFormLayout()

        # Service URL
        self.wms_url_edit = QLineEdit()
        self.wms_url_edit.setPlaceholderText("http://example.com/wms")
        self.wms_url_edit.setText("https://maps.wien.gv.at/wms")  # Example service
        form_layout.addRow("Service URL:", self.wms_url_edit)

        # Layer selection
        self.layer_combo = QComboBox()
        self.layer_combo.addItem("Select layer...")
        form_layout.addRow("Layer:", self.layer_combo)

        # Coordinate system
        self.crs_combo = QComboBox()
        self.crs_combo.addItems(["EPSG:3857", "EPSG:4326", "EPSG:31258", "EPSG:31259"])
        self.crs_combo.setCurrentText("EPSG:3857")
        form_layout.addRow("CRS:", self.crs_combo)

        # Image size
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4096)
        self.width_spin.setValue(800)
        size_layout.addWidget(QLabel("Width:"))
        size_layout.addWidget(self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 4096)
        self.height_spin.setValue(600)
        size_layout.addWidget(QLabel("Height:"))
        size_layout.addWidget(self.height_spin)

        form_layout.addRow("Image Size:", size_layout)

        layout.addLayout(form_layout)

        # Bounding box
        bbox_group = QFormLayout()

        self.bbox_min_x = QDoubleSpinBox()
        self.bbox_min_x.setRange(-180, 180)
        self.bbox_min_x.setValue(16.0)
        bbox_group.addRow("Min X:", self.bbox_min_x)

        self.bbox_min_y = QDoubleSpinBox()
        self.bbox_min_y.setRange(-90, 90)
        self.bbox_min_y.setValue(48.0)
        bbox_group.addRow("Min Y:", self.bbox_min_y)

        self.bbox_max_x = QDoubleSpinBox()
        self.bbox_max_x.setRange(-180, 180)
        self.bbox_max_x.setValue(16.5)
        bbox_group.addRow("Max X:", self.bbox_max_x)

        self.bbox_max_y = QDoubleSpinBox()
        self.bbox_max_y.setRange(-90, 90)
        self.bbox_max_y.setValue(48.3)
        bbox_group.addRow("Max Y:", self.bbox_max_y)

        layout.addLayout(bbox_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.get_layers_btn = QPushButton("Get Layers")
        self.get_layers_btn.clicked.connect(self.get_wms_layers)
        button_layout.addWidget(self.get_layers_btn)

        self.load_wms_btn = QPushButton("Load WMS")
        self.load_wms_btn.clicked.connect(self.load_wms)
        button_layout.addWidget(self.load_wms_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        return tab

    def setup_gdal_tab(self):
        """Setup GDAL Virtual Raster tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # File selection
        file_layout = QHBoxLayout()

        self.gdal_path_edit = QLineEdit()
        self.gdal_path_edit.setPlaceholderText("Path to GDAL virtual raster (.vrt) or any raster file")
        file_layout.addWidget(self.gdal_path_edit)

        self.browse_gdal_btn = QPushButton("Browse")
        self.browse_gdal_btn.clicked.connect(self.browse_gdal_file)
        file_layout.addWidget(self.browse_gdal_btn)

        layout.addLayout(file_layout)

        # Load button
        self.load_gdal_btn = QPushButton("Load GDAL Source")
        self.load_gdal_btn.clicked.connect(self.load_gdal_source)
        layout.addWidget(self.load_gdal_btn)

        layout.addStretch()

        return tab

    def get_wms_layers(self):
        """Get available layers from WMS service."""
        url = self.wms_url_edit.text().strip()
        if not url:
            self.status_label.setText("Please enter WMS service URL")
            return

        try:
            self.status_label.setText("Getting layers...")
            layers = self.wms_client.get_layers(url)

            self.layer_combo.clear()
            self.layer_combo.addItems(layers)

            if layers:
                self.status_label.setText(f"Found {len(layers)} layers")
            else:
                self.status_label.setText("No layers found")

        except Exception as e:
            self.status_label.setText(f"Error getting layers: {str(e)}")

    def load_wms(self):
        """Load WMS layer."""
        url = self.wms_url_edit.text().strip()
        layer = self.layer_combo.currentText()
        crs = self.crs_combo.currentText()

        if not url or layer == "Select layer...":
            self.status_label.setText("Please select service and layer")
            return

        try:
            self.status_label.setText("Loading WMS layer...")

            # Get bounding box
            bbox = [
                self.bbox_min_x.value(),
                self.bbox_min_y.value(),
                self.bbox_max_x.value(),
                self.bbox_max_y.value()
            ]

            # Load image from WMS
            image_data, transform = self.wms_client.get_map(
                url, layer, crs, bbox,
                self.width_spin.value(),
                self.height_spin.value()
            )

            if image_data is not None:
                self.display_reference_image(image_data, transform, {
                    'type': 'wms',
                    'url': url,
                    'layer': layer,
                    'crs': crs,
                    'bbox': bbox
                })

                self.status_label.setText(f"Loaded WMS layer: {layer}")
            else:
                self.status_label.setText("Failed to load WMS layer")

        except Exception as e:
            self.status_label.setText(f"Error loading WMS: {str(e)}")

    def browse_gdal_file(self):
        """Browse for GDAL virtual raster file."""
        from qtpy.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Select GDAL Virtual Raster', '',
            'GDAL Files (*.vrt *.tif *.tiff *.img);;All Files (*)'
        )

        if file_path:
            self.gdal_path_edit.setText(file_path)

    def load_gdal_source(self):
        """Load GDAL virtual raster or raster file."""
        file_path = self.gdal_path_edit.text().strip()
        if not file_path or not os.path.exists(file_path):
            self.status_label.setText("Please select a valid file")
            return

        try:
            self.status_label.setText("Loading GDAL source...")

            # Load using GDAL reader
            image_data, transform, metadata = self.gdal_reader.load_file(file_path)

            if image_data is not None:
                self.display_reference_image(image_data, transform, {
                    'type': 'gdal',
                    'file_path': file_path,
                    'metadata': metadata
                })

                self.status_label.setText(f"Loaded GDAL source: {Path(file_path).name}")
            else:
                self.status_label.setText("Failed to load GDAL source")

        except Exception as e:
            self.status_label.setText(f"Error loading GDAL source: {str(e)}")

    def display_reference_image(self, image_data, transform, reference_info):
        """Display reference image with georeferencing."""
        try:
            import cv2

            self.current_reference = reference_info
            self.reference_transform = transform

            # Convert image data to display format
            if len(image_data.shape) == 3:
                if image_data.shape[2] == 4:  # RGBA
                    image_data = cv2.cvtColor(image_data, cv2.COLOR_RGBA2RGB)
                elif image_data.shape[2] == 1:  # Single band
                    image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2RGB)
            else:
                image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2RGB)

            # Convert to QPixmap
            height, width = image_data.shape[:2]
            bytes_per_line = 3 * width

            from qtpy.QtGui import QImage

            qt_image = QImage(
                image_data.data, width, height, bytes_per_line, QImage.Format_RGB888
            )

            pixmap = QPixmap.fromImage(qt_image)
            self.image_canvas.set_pixmap(pixmap)

            # Set georeferencing info for coordinate conversion
            self.image_canvas.set_georeferencing(transform, width, height)

            # Draw existing GCP points
            self.draw_gcp_points()

            # Emit signal
            self.reference_loaded.emit(reference_info)

        except Exception as e:
            self.status_label.setText(f"Error displaying image: {str(e)}")

    def draw_gcp_points(self):
        """Draw GCP points on reference image."""
        if self.current_reference is None:
            return  # Don't draw GCPs if no reference is loaded

        self.image_canvas.clear_gcp_points()

        for gcp_id, (x, y) in self.gcp_points.items():
            self.image_canvas.add_gcp_point(x, y, gcp_id)

        self.image_canvas.update()

    def on_point_clicked(self, x, y):
        """Handle point click on reference image."""
        if self.current_reference is None:
            self.status_label.setText("No reference source loaded - please load a reference first")
            return

        # Convert pixel coordinates to image coordinates
        img_x, img_y = self.image_canvas.pixel_to_image_coords(x, y)

        # Convert to geographic coordinates if transform is available
        lon, lat = self.image_coords_to_geographic(img_x, img_y)

        # Emit signal
        self.point_selected.emit(img_x, img_y, lon, lat)

        self.status_label.setText(f"Point selected: ({lon:.6f}, {lat:.6f})")

    def on_gcp_point_clicked(self, gcp_id):
        """Handle GCP point click."""
        self.status_label.setText(f"GCP {gcp_id} selected")

    def on_zoom_changed(self, zoom_factor):
        """Handle zoom change."""
        self.image_canvas.set_zoom(zoom_factor)

    def image_coords_to_geographic(self, x, y):
        """Convert image coordinates to geographic coordinates."""
        # TODO: Implement coordinate transformation
        pass

    def on_point_clicked(self, x, y):
        """Handle point click on reference image."""
        if self.current_reference is None:
            self.status_label.setText("No reference source loaded - please load a reference first")
            return

        # Convert pixel coordinates to image coordinates
        img_x, img_y = self.image_canvas.pixel_to_image_coords(x, y)

        # Convert to geographic coordinates if transform is available
        lon, lat = self.image_coords_to_geographic(img_x, img_y)

        # Emit signal
        self.point_selected.emit(img_x, img_y, lon, lat)

    def geographic_to_image_coords(self, lon, lat):
        """Convert geographic coordinates to image coordinates."""
        if self.reference_transform is None:
            return lon, lat

        try:
            # If using Web Mercator, convert from lat/lon
            if self.current_reference.get('crs') == 'EPSG:3857':
                map_x = lon * 20037508.34 / 180
                map_y = np.log(np.tan((90 + lat) * np.pi / 360)) * 20037508.34 / np.pi
            else:
                map_x, map_y = lon, lat

            # Convert map to pixel coordinates
            transform = self.reference_transform
            x = (map_x - transform[0] - transform[2] * transform[3]) / transform[1]
            y = (map_y - transform[3] - transform[4] * transform[0]) / transform[5]

            return x, y

        except Exception:
            return lon, lat

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
        if self.current_reference is None:
            return  # Don't highlight if no reference is loaded

        self.image_canvas.highlight_point(x, y)

    def clear_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()
        self.draw_gcp_points()

    def is_initialized(self) -> bool:
        """Check if the reference viewer has a loaded reference source."""
        return self.current_reference is not None

    def get_reference_info(self) -> dict:
        """Get information about the current reference source."""
        if self.current_reference is None:
            return {}
        return self.current_reference.copy()
