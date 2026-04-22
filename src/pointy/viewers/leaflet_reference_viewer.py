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
#    File:    leaflet_reference_viewer.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Leaflet Reference Viewer - Web-based map viewer with Leaflet and ArcGIS services
"""

#  Python Standard Libraries
import logging
import os
import tempfile
import time
from pathlib import Path

#  Third-Party Libraries
import folium
import numpy as np

# Set Qt attributes BEFORE any Qt imports
from qtpy.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

from qtpy.QtCore import QObject, QUrl, Signal, Slot, QTimer
from qtpy.QtGui import QFont
from qtpy.QtWebChannel import QWebChannel
from qtpy.QtWebEngineCore import QWebEngineSettings
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtWidgets import (QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
                           QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy,
                           QSpinBox, QTabWidget, QVBoxLayout, QWidget)

# Project imports
from pointy.core.config_manager import get_config_manager
from tmns.geo.terrain import Manager as Terrain_Manager
from tmns.geo.coord import Geographic

class Leaflet_Bridge(QObject):
    """Bridge between JavaScript and Python for communication."""

    # Signals
    point_clicked = Signal(float, float, float, float)  # x, y, lon, lat
    map_ready = Signal()
    cursor_moved = Signal(float, float, float)  # lat, lon, alt (alt optional)
    center_reported = Signal(float, float, float)  # lat, lon, zoom

    def __init__(self):
        super().__init__()

    @Slot(float, float, float, float)
    def point_clicked_from_js(self, x: float, y: float, lon: float, lat: float):
        self.point_clicked.emit(x, y, lon, lat)

    @Slot()
    def map_ready_from_js(self):
        self.map_ready.emit()

    @Slot(float, float, float)
    def cursor_moved_from_js(self, lat: float, lon: float, alt: float = 0.0):
        self.cursor_moved.emit(lat, lon, alt)

    @Slot(float, float, float)
    def report_center_from_js(self, lat: float, lon: float, zoom: float):
        self.center_reported.emit(lat, lon, zoom)


class Leaflet_Reference_Viewer(QWidget):
    """Web-based reference viewer using Leaflet with ArcGIS Imagery services."""

    # Signals
    point_selected = Signal(float, float, float, float)  # x, y, lon, lat
    reference_loaded = Signal(dict)  # reference info
    cursor_moved = Signal(float, float, float)  # lat, lon, alt (alt optional)
    update_requested = Signal()  # emitted when Update button is clicked

    def __init__(self, terrain_manager=None):
        super().__init__()
        self.current_reference = None
        self.gcp_points = {}  # gcp_id -> (lon, lat)
        self.reference_transform = None
        self.map_is_ready = False
        self.pending_gcps = []  # Queue of (gcp_id, lon, lat) to add when map is ready
        self._image_boundary_corners: list[tuple[float, float]] | None = None  # [(lat, lon), ...]
        self._last_center: tuple[float, float, float] | None = None
        self._map_was_ready = False  # Track if map was ever ready (to distinguish initial load from recreation)

        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing Leaflet Reference Viewer")

        # Load configuration
        self.config_manager = get_config_manager()
        self.imagery_services = self.config_manager.get_imagery_services_dict()
        self.logger.debug(f"Loaded {len(self.imagery_services)} imagery services")

        # Store terrain manager with throttling
        self.terrain_manager = terrain_manager
        self.cursor_throttle_timer = QTimer()
        self.cursor_throttle_timer.setSingleShot(True)
        self.cursor_throttle_timer.timeout.connect(self._query_elevation_throttled)
        self.pending_cursor_coords = None

        # Initialize web components
        self.web_view = QWebEngineView()
        self._configure_web_view_settings()
        self.bridge = Leaflet_Bridge()
        self.web_channel = QWebChannel()
        self.logger.debug("Web components initialized successfully")

        self.setup_ui()
        if self.web_view is not None:
            self.setup_web_channel()
            self.create_initial_map()

    def _configure_web_view_settings(self):
        """Configure web view to allow local HTML to load remote JS/CSS/tile resources."""
        if self.web_view is None:
            return

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

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
            QComboBox {
                color: #cccccc;
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 1px 6px;
                font-size: 9pt;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #cccccc;
                selection-background-color: #0d6efd;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 0, 4, 0)
        toolbar_layout.setSpacing(2)

        title_label = QLabel("Reference Map")
        toolbar_layout.addWidget(title_label)

        toolbar_layout.addStretch()

        # Imagery service selector
        service_label = QLabel("Imagery:")
        service_label.setStyleSheet("QLabel { font-weight: normal; }")
        toolbar_layout.addWidget(service_label)

        self.service_combo = QComboBox()
        self.service_combo.addItems(list(self.imagery_services.keys()))

        # Set default service from config
        default_service = self.config_manager.get_default_service()
        if default_service in self.imagery_services:
            self.service_combo.setCurrentText(default_service)

        self.service_combo.currentTextChanged.connect(self.on_imagery_service_changed)
        toolbar_layout.addWidget(self.service_combo)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("QFrame { color: #555555; }")
        toolbar_layout.addWidget(sep)

        # Update button
        self.update_btn = QPushButton("↺  Update")
        self.update_btn.setToolTip("Pan test image to match this map's geographic center")
        self.update_btn.clicked.connect(self.update_requested)
        toolbar_layout.addWidget(self.update_btn)

        layout.addWidget(toolbar)

        # Web view for map or fallback
        if self.web_view is not None:
            self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self.web_view, 1)
        else:
            # Fallback message
            fallback_label = QLabel("Web view not available. QtWebEngine failed to initialize.")
            fallback_label.setStyleSheet("QLabel { color: red; padding: 20px; }")
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(fallback_label, 1)

        # Status bar
        self.status_label = QLabel("Loading map...")
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 8pt; padding: 1px 2px; }")
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status_label.setMaximumHeight(20)
        layout.addWidget(self.status_label)

        layout.setStretch(1, 1)

    def setup_web_channel(self):
        """Setup the web channel for JavaScript-Python communication."""
        if self.web_view is not None and self.bridge is not None:
            # Create and register the web channel BEFORE loading content
            self.web_channel = QWebChannel()
            self.web_channel.registerObject("bridge", self.bridge)

            # Set the web channel on the page
            page = self.web_view.page()
            if page is not None:
                page.setWebChannel(self.web_channel)
                self.logger.debug("Web channel set up successfully")
            else:
                self.logger.error("Failed to get web page for channel setup")

            # Connect bridge signals
            self.bridge.point_clicked.connect(self.on_javascript_point_clicked)
            self.bridge.map_ready.connect(self.on_map_ready)
            self.bridge.cursor_moved.connect(self.on_cursor_moved_throttled)
            self.bridge.center_reported.connect(self._on_center_reported)

    def create_initial_map(self):
        """Create the initial Leaflet map."""
        # Ensure was-ready flag is reset for initial load
        self._map_was_ready = False

        # Get map settings from config
        map_settings = self.config_manager.get_map_settings()
        default_center = map_settings.default_center
        default_zoom = map_settings.default_zoom

        # Create a folium map centered on configured location
        m = folium.Map(
            location=[default_center["latitude_deg"], default_center["longitude_deg"]],
            zoom_start=default_zoom,
            tiles=None  # We'll add our own tiles
        )

        # Add default imagery service from config
        default_service = self.config_manager.get_default_service()
        service = self.imagery_services.get(default_service, {})
        if service.get("type") == "xyz":
            folium.TileLayer(
                tiles=service["url"],
                attr=service["attribution"],
                name=service.get("name", "Base Map")
            ).add_to(m)

        # Add JavaScript for point clicking and communication
        map_html = self._add_custom_javascript(m.get_root().render())

        # Load map via local file URL (avoids data: URL storage/security limits)
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as map_file:
            map_file.write(map_html)
            self._map_html_path = map_file.name

        self.web_view.setUrl(QUrl.fromLocalFile(self._map_html_path))
        self.status_label.setText("Map loaded - Click to select points")

    def _add_custom_javascript(self, html: str) -> str:
        """Add custom JavaScript for point clicking and communication."""
        # Add QWebChannel library
        qwebchannel_js = """
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        """

        js_code = """
        <script>
        var map = null;
        var bridge = null;
        var isMapReady = false;

        function getLeafletMap() {
            if (typeof L === 'undefined') {
                return null;
            }
            for (var key in window) {
                var value = window[key];
                if (value && typeof value === 'object' && value instanceof L.Map) {
                    return value;
                }
            }
            return null;
        }

        function setupMapHandlers() {
            if (!map || typeof map.on !== 'function') {
                return;
            }
            map.on('click', function(e) {
                if (!bridge || typeof bridge.point_clicked_from_js !== 'function') {
                    return;
                }
                bridge.point_clicked_from_js(
                    e.containerPoint.x,
                    e.containerPoint.y,
                    e.latlng.lng,
                    e.latlng.lat
                );
            });

            // Add cursor tracking
            map.on('mousemove', function(e) {
                console.log('Mouse move detected:', e.latlng.lat, e.latlng.lng);
                if (!bridge || typeof bridge.cursor_moved_from_js !== 'function') {
                    console.log('Bridge or cursor_moved_from_js not available');
                    return;
                }
                try {
                    bridge.cursor_moved_from_js(
                        e.latlng.lat,
                        e.latlng.lng,
                        0.0  // Default altitude to 0 since we don't have terrain data yet
                    );
                    console.log('Cursor moved signal sent');
                } catch (error) {
                    console.error('Error sending cursor moved signal:', error);
                }
            });
        }

        function notifyMapReady() {
            if (bridge && typeof bridge.map_ready_from_js === 'function') {
                bridge.map_ready_from_js();
            }
        }

        function initializeBridgeAndMap() {
            map = getLeafletMap();
            if (!map) {
                return false;
            }

            var onBridgeReady = function() {
                isMapReady = true;
                setupMapHandlers();
                notifyMapReady();
            };

            if (typeof qt !== 'undefined' && qt.webChannelTransport) {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    bridge = channel.objects.bridge;
                    onBridgeReady();
                });
            } else {
                onBridgeReady();
            }
            return true;
        }

        function waitForLeafletAndInitialize(attempts) {
            attempts = attempts || 0;
            if (typeof L === 'undefined') {
                if (attempts < 30) {
                    setTimeout(function() {
                        waitForLeafletAndInitialize(attempts + 1);
                    }, 200);
                }
                return;
            }

            if (!initializeBridgeAndMap()) {
                if (attempts < 30) {
                    setTimeout(function() {
                        waitForLeafletAndInitialize(attempts + 1);
                    }, 200);
                }
            }
        }

        function changeImageryService(serviceType, serviceUrl, attribution, layers, format, attempts) {
            attempts = attempts || 0;
            if (!map) {
                map = getLeafletMap();
            }
            if (!map) {
                if (attempts < 20) {
                    setTimeout(function() {
                        changeImageryService(serviceType, serviceUrl, attribution, layers, format, attempts + 1);
                    }, 200);
                }
                return;
            }

            map.eachLayer(function(layer) {
                if (layer instanceof L.TileLayer) {
                    map.removeLayer(layer);
                }
            });

            var tileLayer = null;

            if (serviceType === 'xyz') {
                tileLayer = L.tileLayer(serviceUrl, {
                    attribution: attribution,
                    maxZoom: 20
                });
            } else if (serviceType === 'arcgis') {
                var tileUrl = serviceUrl.indexOf('{z}') !== -1 ? serviceUrl : (serviceUrl + '/tile/{z}/{y}/{x}');
                tileLayer = L.tileLayer(tileUrl, {
                    attribution: attribution,
                    maxZoom: 20
                });
            } else if (serviceType === 'wms') {
                tileLayer = L.tileLayer.wms(serviceUrl, {
                    attribution: attribution,
                    layers: layers,
                    format: format,
                    transparent: true,
                    version: '1.1.1'
                });
            }

            if (tileLayer) {
                tileLayer.addTo(map);
            }
        }

        function addGCPPoint(gcpId, lon, lat) {
            if (map) {
                var marker = L.circleMarker([lat, lon], {
                    radius: 8,
                    color: '#ffffff',
                    weight: 2,
                    fillColor: '#0d6efd',
                    fillOpacity: 0.85
                }).addTo(map);
                marker.bindPopup('GCP ' + gcpId);
                return marker;
            }
        }

        function addGCPPointsBatch(gcpPoints) {
            // gcpPoints is array of [gcpId, lon, lat]
            if (map && Array.isArray(gcpPoints)) {
                for (var i = 0; i < gcpPoints.length; i++) {
                    var point = gcpPoints[i];
                    var marker = L.circleMarker([point[2], point[1]], {
                        radius: 8,
                        color: '#ffffff',
                        weight: 2,
                        fillColor: '#0d6efd',
                        fillOpacity: 0.85
                    }).addTo(map);
                    marker.bindPopup('GCP ' + point[0]);
                }
            }
        }

        function clearGCPPoints() {
            if (map) {
                map.eachLayer(function(layer) {
                    if (layer instanceof L.Marker || layer instanceof L.CircleMarker) {
                        map.removeLayer(layer);
                    }
                });
            }
        }

        function highlightGCPPoint(gcpId) {
            console.log('Highlighting GCP ' + gcpId);
        }

        function reportCenter() {
            if (map && bridge && typeof bridge.report_center_from_js === 'function') {
                var center = map.getCenter();
                var zoom = map.getZoom();
                bridge.report_center_from_js(center.lat, center.lng, zoom);
            }
        }

        var imageBoundaryLayer = null;

        function setImageBoundary(latlngs) {
            if (map) {
                if (imageBoundaryLayer) {
                    map.removeLayer(imageBoundaryLayer);
                }
                imageBoundaryLayer = L.polygon(latlngs, {
                    color: '#ff6600',
                    weight: 2,
                    fillOpacity: 0.08,
                    dashArray: '6 4'
                }).addTo(map);
            }
        }

        function clearImageBoundary() {
            if (map && imageBoundaryLayer) {
                map.removeLayer(imageBoundaryLayer);
                imageBoundaryLayer = null;
            }
        }

        window.changeImageryService = changeImageryService;
        window.addGCPPoint = addGCPPoint;
        window.addGCPPointsBatch = addGCPPointsBatch;
        window.clearGCPPoints = clearGCPPoints;
        window.highlightGCPPoint = highlightGCPPoint;
        window.reportCenter = reportCenter;
        window.setImageBoundary = setImageBoundary;
        window.clearImageBoundary = clearImageBoundary;

        document.addEventListener('DOMContentLoaded', function() {
            waitForLeafletAndInitialize(0);
        });

        </script>
        """

        # Insert the JavaScript before the closing body tag
        if "</body>" in html:
            html = html.replace("</body>", qwebchannel_js + js_code + "</body>")
        else:
            html += qwebchannel_js + js_code

        return html

    def request_center(self):
        """Ask the map to report its current center via the bridge signal."""
        if self.map_is_ready and self.web_view is not None:
            self.web_view.page().runJavaScript("reportCenter();")

    def _on_center_reported(self, lat: float, lon: float, zoom: float):
        """Store the latest reported map center."""
        self._last_center = (lat, lon, zoom)

    def on_imagery_service_changed(self, service_name: str):
        """Change the imagery service."""
        if service_name not in self.imagery_services:
            self.logger.warning(f"Service {service_name} not found in available services")
            return

        service = self.imagery_services[service_name]
        self.status_label.setText(f"Loading {service_name}...")
        self.logger.debug(f"Changing imagery service to: {service_name}")

        # Update current reference info
        self.current_reference = {
            "name": service_name,
            "url": service["url"],
            "type": service["type"],
            "attribution": service["attribution"]
        }

        # Call JavaScript to change the imagery service
        layers = service.get("layers", "")
        format = service.get("format", "image/png")

        js = f"""
        changeImageryService(
            '{service["type"]}',
            '{service["url"]}',
            '{service["attribution"]}',
            '{layers}',
            '{format}'
        );
        """

        if self.web_view is not None:
            self.logger.debug("Executing JavaScript to change imagery service")
            self.web_view.page().runJavaScript(js)
        else:
            self.logger.error("Web view not available, cannot change imagery service")

        self.reference_loaded.emit(self.current_reference)
        self.status_label.setText(f"Loaded {service_name}")
        self.logger.info(f"Imagery service changed to: {service_name}")

    def on_javascript_point_clicked(self, x: float, y: float, lon: float, lat: float):
        """Handle point click from JavaScript."""
        self.point_selected.emit(x, y, lon, lat)
        self.status_label.setText(f"Selected: ({lat:.6f}, {lon:.6f})")

    def on_map_ready(self):
        """Handle map ready signal from JavaScript."""
        was_ready_before = self._map_was_ready
        self.map_is_ready = True
        self._map_was_ready = True
        self.status_label.setText("Map ready - Click to select points")

        self.logger.info(f"on_map_ready called: was_ready_before={was_ready_before}, "
                        f"pending_gcps={len(self.pending_gcps)}, "
                        f"gcp_points={len(self.gcp_points)}, "
                        f"map_is_ready={self.map_is_ready}")

        # Draw any pending GCPs that were added before map was ready
        if self.pending_gcps:
            self.logger.debug(f"Drawing {len(self.pending_gcps)} pending GCPs")
            t0 = time.perf_counter()
            # Use batch addition for performance
            gcp_array = str([[gcp_id, lon, lat] for gcp_id, lon, lat in self.pending_gcps])
            js = f"addGCPPointsBatch({gcp_array});"
            self.web_view.page().runJavaScript(js)
            self.pending_gcps.clear()
            self.logger.debug(f"Finished drawing pending GCPs in {time.perf_counter() - t0:.3f}s")

        # Redraw all existing GCPs only if map was recreated (was ready before, now ready again)
        if was_ready_before and self.gcp_points:
            self.logger.info(f"Map was recreated - redrawing {len(self.gcp_points)} existing GCPs")
            t0 = time.perf_counter()
            gcp_array = str([[gcp_id, lon, lat] for gcp_id, (lon, lat) in self.gcp_points.items()])
            js = f"addGCPPointsBatch({gcp_array});"
            self.web_view.page().runJavaScript(js)
            self.logger.debug(f"Finished redrawing existing GCPs in {time.perf_counter() - t0:.3f}s")
        else:
            self.logger.info(f"Initial map load (was_ready_before={was_ready_before}) - skipping GCP redraw")

        # Restore image boundary polygon if one was set
        if self._image_boundary_corners is not None:
            self._draw_image_boundary()

    def add_gcp_point(self, gcp_id: int, lon: float, lat: float):
        """Add a GCP point to the map."""
        # Store the point with geographic coordinates
        self.gcp_points[gcp_id] = (lon, lat)

        if self.map_is_ready:
            # Map is ready, call JavaScript directly
            t0 = time.perf_counter()
            js = f"addGCPPoint({gcp_id}, {lon}, {lat});"
            self.web_view.page().runJavaScript(js)
            self.logger.debug(f"add_gcp_point({gcp_id}): {time.perf_counter() - t0:.3f}s")
        else:
            # Map isn't ready yet, queue the GCP for later
            self.pending_gcps.append((gcp_id, lon, lat))
            self.logger.debug(f"Queued GCP {gcp_id} for later drawing (map not ready, "
                           f"was_ready={self._map_was_ready}, pending_count={len(self.pending_gcps)})")

    def remove_gcp_point(self, gcp_id: int):
        """Remove a GCP point from the map."""
        if gcp_id in self.gcp_points:
            del self.gcp_points[gcp_id]

        if self.map_is_ready:
            t0 = time.perf_counter()
            # Clear and redraw all points using batch function
            js_clear = "clearGCPPoints();"
            self.web_view.page().runJavaScript(js_clear)

            gcp_array = str([[gcp_id, lon, lat] for gcp_id, (lon, lat) in self.gcp_points.items()])
            js_add = f"addGCPPointsBatch({gcp_array});"
            self.web_view.page().runJavaScript(js_add)
            self.logger.debug(f"remove_gcp_point: redraw {len(self.gcp_points)} GCPs in {time.perf_counter() - t0:.3f}s")

    def highlight_gcp_point(self, x: float, y: float):
        """Highlight a specific GCP point."""
        if self.map_is_ready:
            js = f"highlightGCPPoint({x}, {y});"
            self.web_view.page().runJavaScript(js)

    def draw_gcp_points(self):
        """Draw all GCP points on the map."""
        if self.map_is_ready:
            t0 = time.perf_counter()
            # Clear existing points
            js_clear = "clearGCPPoints();"
            self.web_view.page().runJavaScript(js_clear)

            # Add all points using batch function
            gcp_array = str([[gcp_id, lon, lat] for gcp_id, (lon, lat) in self.gcp_points.items()])
            js_add = f"addGCPPointsBatch({gcp_array});"
            self.web_view.page().runJavaScript(js_add)
            self.logger.debug(f"draw_gcp_points: drew {len(self.gcp_points)} GCPs in {time.perf_counter() - t0:.3f}s")

    def _draw_image_boundary(self):
        """Internal: push the stored boundary corners to JavaScript."""
        if self._image_boundary_corners is None or not self.map_is_ready:
            return
        latlngs = str([[float(lat), float(lon)] for lat, lon in self._image_boundary_corners])
        self.web_view.page().runJavaScript(f"setImageBoundary({latlngs});")

    def set_image_boundary(self, corners: list[tuple[float, float]]):
        """Draw a polygon on the map showing the orthorectified image boundary.

        Args:
            corners: List of (lat, lon) tuples in order TL, TR, BR, BL.
        """
        self._image_boundary_corners = corners
        self._draw_image_boundary()

    def clear_image_boundary(self):
        """Remove the image boundary polygon from the map."""
        self._image_boundary_corners = None
        if self.map_is_ready and self.web_view is not None:
            self.web_view.page().runJavaScript("clearImageBoundary();")

    def clear_points(self):
        """Clear all GCP points."""
        self.logger.info(f"clear_points called: map_is_ready={self.map_is_ready}, gcp_points={len(self.gcp_points)}")
        self.gcp_points.clear()
        self.pending_gcps.clear()
        if self.map_is_ready:
            js = "clearGCPPoints();"
            self.web_view.page().runJavaScript(js)
            self.logger.info("clearGCPPoints() JS called")

    def is_initialized(self) -> bool:
        """Check if the reference viewer has a loaded reference source."""
        return self.current_reference is not None

    def get_reference_info(self) -> dict:
        """Get information about the current reference source."""
        if self.current_reference is None:
            return {}
        return self.current_reference.copy()

    def recreate_map_with_center(self, center: Geographic, zoom: int = 12):
        """Recreate the map centered on a geographic coordinate."""
        if self.web_view is None:
            self.logger.warning("Web view not available, cannot recreate map")
            return

        self.logger.info(f"Recreating map centered on {center} zoom {zoom}, "
                        f"was_ready={self._map_was_ready}, "
                        f"pending_gcps={len(self.pending_gcps)}, "
                        f"gcp_points={len(self.gcp_points)}")

        # Set map_is_ready to False since we're recreating
        self.map_is_ready = False

        # Create a new folium map centered on the specified location
        m = folium.Map(
            location=center.to_leaflet(),
            zoom_start=zoom,
            tiles=None
        )

        # Add default imagery service from config
        default_service = self.config_manager.get_default_service()
        service = self.imagery_services.get(default_service, {})
        if service.get("type") == "xyz":
            folium.TileLayer(
                tiles=service["url"],
                attr=service["attribution"],
                name=service.get("name", "Base Map")
            ).add_to(m)

        # Add JavaScript for point clicking and communication
        map_html = self._add_custom_javascript(m.get_root().render())

        # Clean up old map file
        if hasattr(self, '_map_html_path') and self._map_html_path:
            try:
                os.unlink(self._map_html_path)
            except OSError:
                pass

        # Load map via local file URL
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as map_file:
            map_file.write(map_html)
            self._map_html_path = map_file.name

        self.map_is_ready = False
        # Don't queue existing GCPs - they're already in gcp_points and will be redrawn by on_map_ready
        self.web_view.setUrl(QUrl.fromLocalFile(self._map_html_path))
        self.status_label.setText(f"Map centered on ({center.latitude_deg:.4f}, {center.longitude_deg:.4f})")

    def grab_ref_chip(self, callback) -> None:
        """Capture the current map viewport as a numpy array and call back with it.

        Grabs a screenshot of the web view and queries JS for the current map
        geographic bounds.  Once both are available, calls:

            callback(chip: np.ndarray, geo_transform: Callable[[float, float], tuple[float, float]])

        where ``geo_transform(px_x, px_y) -> (lon, lat)`` maps chip pixel
        coordinates to geographic coordinates using a linear interpolation
        over the viewport bounds.

        Args:
            callback: Called with (chip_array, geo_transform) once ready.
        """
        if self.web_view is None or not self.map_is_ready:
            self.logger.warning("grab_ref_chip: map not ready")
            callback(None, None)
            return

        pixmap = self.web_view.grab()
        chip_w = pixmap.width()
        chip_h = pixmap.height()

        def _on_bounds(result):
            try:
                if not result:
                    self.logger.error("grab_ref_chip: getBounds() returned empty result")
                    callback(None, None)
                    return

                sw_lat = float(result['sw_lat'])
                sw_lon = float(result['sw_lon'])
                ne_lat = float(result['ne_lat'])
                ne_lon = float(result['ne_lon'])

                image = pixmap.toImage()
                image = image.convertToFormat(image.Format.Format_RGB888)
                img_w = image.width()
                img_h = image.height()
                stride = image.bytesPerLine()
                ptr = image.bits()
                ptr.setsize(img_h * stride)
                arr = np.frombuffer(ptr, dtype=np.uint8).reshape((img_h, stride))
                chip = arr[:, :img_w * 3].reshape((img_h, img_w, 3)).copy()
                chip_w = img_w
                chip_h = img_h

                def geo_transform(px_x: float, px_y: float) -> tuple[float, float]:
                    lon = sw_lon + (px_x / chip_w) * (ne_lon - sw_lon)
                    lat = ne_lat - (px_y / chip_h) * (ne_lat - sw_lat)
                    return lon, lat

                callback(chip, geo_transform)

            except Exception as exc:
                self.logger.error(f"grab_ref_chip: failed to process result: {exc}")
                callback(None, None)

        js = """
(function() {
    var b = map.getBounds();
    return {
        sw_lat: b.getSouthWest().lat,
        sw_lon: b.getSouthWest().lng,
        ne_lat: b.getNorthEast().lat,
        ne_lon: b.getNorthEast().lng
    };
})()
"""
        self.web_view.page().runJavaScript(js, _on_bounds)

    def _query_elevation_throttled(self):
        """Query elevation for pending cursor coordinates (throttled)."""
        if self.pending_cursor_coords and self.terrain_manager:
            lat, lon = self.pending_cursor_coords
            try:
                # Query elevation
                geo_coord = Geographic(lat, lon)
                elevation = self.terrain_manager.elevation(geo_coord)

                if elevation is not None:
                    # Update cursor signal with real altitude
                    self.cursor_moved.emit(lat, lon, elevation)
                else:
                    # No elevation data available, emit with 0
                    self.cursor_moved.emit(lat, lon, 0.0)
                    self.logger.debug(f"No elevation data at ({lat:.4f}, {lon:.4f})")

            except Exception as e:
                self.logger.error(f"Elevation query failed: {e}")
                # Fallback to 0 altitude
                self.cursor_moved.emit(lat, lon, 0.0)

        self.pending_cursor_coords = None

    def on_cursor_moved_throttled(self, lat: float, lon: float):
        """Handle cursor movement with throttling to avoid performance issues."""
        # Store pending coordinates
        self.pending_cursor_coords = (lat, lon)

        # Start/restart throttle timer (12ms delay - 4x faster than 50ms)
        self.cursor_throttle_timer.start(12)

    def is_terrain_available(self) -> bool:
        """Check if terrain elevation data is available."""
        return self.terrain_manager is not None

    def get_terrain_status(self) -> str:
        """Get terrain status message."""
        if self.terrain_manager is None:
            return "Terrain data unavailable"
        total_sources = sum(len(catalog.sources) for catalog in self.terrain_manager.sources) if self.terrain_manager.sources else 0
        return f"Terrain data available ({total_sources} sources)"
