"""
Leaflet Reference Viewer - Web-based map viewer with Leaflet and ArcGIS services
"""

# Standard library imports
import os
import logging
import tempfile

# Third-party imports
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QSizePolicy)
from qtpy.QtCore import Qt, Signal, QUrl, QObject, Slot
from qtpy.QtGui import QFont
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtWebChannel import QWebChannel
import folium
from qtpy.QtWebEngineCore import QWebEngineSettings

# Project imports
from app.core.config_manager import get_config_manager


class Leaflet_Bridge(QObject):
    """Bridge between JavaScript and Python for communication."""

    # Signals
    point_clicked = Signal(float, float, float, float)  # x, y, lon, lat
    map_ready = Signal()

    def __init__(self):
        super().__init__()

    @Slot(float, float, float, float)
    def point_clicked_from_js(self, x: float, y: float, lon: float, lat: float):
        self.point_clicked.emit(x, y, lon, lat)

    @Slot()
    def map_ready_from_js(self):
        self.map_ready.emit()


class Leaflet_Reference_Viewer(QWidget):
    """Web-based reference viewer using Leaflet with ArcGIS Imagery services."""

    # Signals
    point_selected = Signal(float, float, float, float)  # x, y, lon, lat
    reference_loaded = Signal(dict)  # reference info
    cursor_moved = Signal(float, float, float)  # lat, lon, alt (alt optional)

    def __init__(self):
        super().__init__()
        self.current_reference = None
        self.gcp_points = {}  # gcp_id -> (x, y)
        self.reference_transform = None

        # Setup logger
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Leaflet Reference Viewer")

        # Load configuration
        self.config_manager = get_config_manager()
        self.imagery_services = self.config_manager.get_imagery_services_dict()
        self.logger.debug(f"Loaded {len(self.imagery_services)} imagery services")

        # Initialize web components with error handling
        try:
            self.web_view = QWebEngineView()
            self._configure_web_view_settings()
            self.bridge = Leaflet_Bridge()
            self.web_channel = QWebChannel()
            self.logger.info("Web components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize web view: {e}")
            # Fallback to a simple label
            self.web_view = None
            self.bridge = None
            self.web_channel = None

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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Reference Map (Leaflet)")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Imagery service selector
        service_label = QLabel("Imagery:")
        header_layout.addWidget(service_label)

        self.service_combo = QComboBox()
        self.service_combo.addItems(list(self.imagery_services.keys()))

        # Set default service from config
        default_service = self.config_manager.get_default_service()
        if default_service in self.imagery_services:
            self.service_combo.setCurrentText(default_service)

        self.service_combo.currentTextChanged.connect(self.on_imagery_service_changed)
        header_layout.addWidget(self.service_combo)

        layout.addLayout(header_layout)

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
                self.logger.info("Web channel set up successfully")
            else:
                self.logger.error("Failed to get web page for channel setup")

            # Connect bridge signals
            self.bridge.point_clicked.connect(self.on_javascript_point_clicked)
            self.bridge.map_ready.connect(self.on_map_ready)

    def create_initial_map(self):
        """Create the initial Leaflet map."""
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
                var marker = L.marker([lat, lon]).addTo(map);
                marker.bindPopup('GCP ' + gcpId);
                return marker;
            }
        }

        function clearGCPPoints() {
            if (map) {
                map.eachLayer(function(layer) {
                    if (layer instanceof L.Marker) {
                        map.removeLayer(layer);
                    }
                });
            }
        }

        function highlightGCPPoint(gcpId) {
            console.log('Highlighting GCP ' + gcpId);
        }

        window.changeImageryService = changeImageryService;
        window.addGCPPoint = addGCPPoint;
        window.clearGCPPoints = clearGCPPoints;
        window.highlightGCPPoint = highlightGCPPoint;

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

    def on_imagery_service_changed(self, service_name: str):
        """Change the imagery service."""
        if service_name not in self.imagery_services:
            self.logger.warning(f"Service {service_name} not found in available services")
            return

        service = self.imagery_services[service_name]
        self.status_label.setText(f"Loading {service_name}...")
        self.logger.info(f"Changing imagery service to: {service_name}")

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
        self.logger.info(f"Successfully loaded imagery service: {service_name}")

    def on_javascript_point_clicked(self, x: float, y: float, lon: float, lat: float):
        """Handle point click from JavaScript."""
        self.point_selected.emit(x, y, lon, lat)
        self.status_label.setText(f"Selected: ({lat:.6f}, {lon:.6f})")

    def on_map_ready(self):
        """Handle map ready signal from JavaScript."""
        self.status_label.setText("Map ready - Click to select points")

    def add_gcp_point(self, gcp_id: int, x: float, y: float):
        """Add a GCP point to the map."""
        # This would need to be implemented with JavaScript bridge
        # For now, store the point
        self.gcp_points[gcp_id] = (x, y)

        # Call JavaScript to add the point
        js = f"addGCPPoint({gcp_id}, {x}, {y});"
        self.web_view.page().runJavaScript(js)

    def remove_gcp_point(self, gcp_id: int):
        """Remove a GCP point from the map."""
        if gcp_id in self.gcp_points:
            del self.gcp_points[gcp_id]

        # Clear and redraw all points
        js = "clearGCPPoints();"
        self.web_view.page().runJavaScript(js)

        for gcp_id, (x, y) in self.gcp_points.items():
            js = f"addGCPPoint({gcp_id}, {x}, {y});"
            self.web_view.page().runJavaScript(js)

    def highlight_gcp_point(self, x: float, y: float):
        """Highlight a specific GCP point."""
        # This would need to be implemented with JavaScript bridge
        js = f"highlightGCPPoint({x}, {y});"
        self.web_view.page().runJavaScript(js)

    def draw_gcp_points(self):
        """Draw all GCP points on the map."""
        # Clear existing points
        js = "clearGCPPoints();"
        self.web_view.page().runJavaScript(js)

        # Add all points
        for gcp_id, (x, y) in self.gcp_points.items():
            js = f"addGCPPoint({gcp_id}, {x}, {y});"
            self.web_view.page().runJavaScript(js)

    def clear_points(self):
        """Clear all GCP points."""
        self.gcp_points.clear()
        js = "clearGCPPoints();"
        self.web_view.page().runJavaScript(js)

    def is_initialized(self) -> bool:
        """Check if the reference viewer has a loaded reference source."""
        return self.current_reference is not None

    def get_reference_info(self) -> dict:
        """Get information about the current reference source."""
        if self.current_reference is None:
            return {}
        return self.current_reference.copy()

    def recreate_map_with_center(self, lat: float, lon: float, zoom: int = 12):
        """Recreate the map centered on a specific location."""
        if self.web_view is None:
            self.logger.warning("Web view not available, cannot recreate map")
            return

        self.logger.info(f"Recreating map centered on ({lat}, {lon}) zoom {zoom}")

        # Create a new folium map centered on the specified location
        m = folium.Map(
            location=[lat, lon],
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

        self.web_view.setUrl(QUrl.fromLocalFile(self._map_html_path))
        self.status_label.setText(f"Map centered on ({lat:.4f}, {lon:.4f})")
