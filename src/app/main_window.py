"""
Main Window for GCP Picker Application
"""

import os
from pathlib import Path
from qtpy.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMenuBar, QStatusBar, QFileDialog,
    QMessageBox, QToolBar, QAction
)
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QKeySequence

from app.viewers.test_image_viewer import Test_Image_Viewer
from app.viewers.leaflet_reference_viewer import Leaflet_Reference_Viewer
from app.widgets.gcp_manager import GCP_Manager
from app.widgets.status_panel import Status_Panel
from app.core.gcp_processor import GCP_Processor
from app.core.orthorectifier import Orthorectifier

class MainWindow(QMainWindow):
    """Main application window for GCP Picker."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCP Picker - Ground Control Point Selection")
        self.setGeometry(100, 100, 1400, 800)

        # Initialize core components
        self.gcp_processor = GCP_Processor()
        self.orthorectifier = Orthorectifier()

        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()

        # Connect signals
        self.connect_signals()

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create main horizontal splitter for left/right panels
        self.image_splitter = QSplitter(Qt.Horizontal)

        # Left panel - Reference viewer (Leaflet)
        self.reference_viewer = Leaflet_Reference_Viewer()
        ref_container = QWidget()
        ref_layout = QVBoxLayout(ref_container)
        ref_layout.setContentsMargins(0, 0, 0, 0)
        ref_layout.addWidget(self.reference_viewer)

        self.image_splitter.addWidget(ref_container)

        # Right panel - Test image viewer
        self.test_viewer = Test_Image_Viewer()
        test_container = QWidget()
        test_layout = QVBoxLayout(test_container)
        test_layout.setContentsMargins(0, 0, 0, 0)
        test_layout.addWidget(self.test_viewer)

        self.image_splitter.addWidget(test_container)

        # Set initial splitter sizes (make panels smaller and equal)
        self.image_splitter.setSizes([500, 500])

        # Create vertical splitter for main content and sidebar
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Add the image splitter to the left
        self.main_splitter.addWidget(self.image_splitter)

        # Create sidebar widget
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)

        # GCP Manager in sidebar (for now, until we integrate the new sidebar)
        self.gcp_manager = GCP_Manager()
        sidebar_layout.addWidget(self.gcp_manager)

        # Status Panel in sidebar (for now, until we integrate the new sidebar)
        self.status_panel = Status_Panel()
        sidebar_layout.addWidget(self.status_panel)

        # Set sidebar width and add to main splitter
        sidebar.setMaximumWidth(400)
        sidebar.setMinimumWidth(300)
        self.main_splitter.addWidget(sidebar)

        # Set main splitter sizes (images 70%, sidebar 30%)
        self.main_splitter.setSizes([1000, 300])

        main_layout.addWidget(self.main_splitter)

    def setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('&File')

        # Open test image
        open_test_action = QAction('Open Test Image...', self)
        open_test_action.setShortcut(QKeySequence.Open)
        open_test_action.setStatusTip('Open the test image for GCP selection')
        open_test_action.triggered.connect(self.open_test_image)
        file_menu.addAction(open_test_action)

        file_menu.addSeparator()

        # Save GCPs
        save_gcps_action = QAction('Save GCPs...', self)
        save_gcps_action.setShortcut(QKeySequence.Save)
        save_gcps_action.setStatusTip('Save ground control points to file')
        save_gcps_action.triggered.connect(self.save_gcps)
        file_menu.addAction(save_gcps_action)

        # Load GCPs
        load_gcps_action = QAction('Load GCPs...', self)
        load_gcps_action.setStatusTip('Load ground control points from file')
        load_gcps_action.triggered.connect(self.load_gcps)
        file_menu.addAction(load_gcps_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu('&Edit')

        # Clear all GCPs
        clear_gcps_action = QAction('Clear All GCPs', self)
        clear_gcps_action.setStatusTip('Remove all ground control points')
        clear_gcps_action.triggered.connect(self.clear_all_gcps)
        edit_menu.addAction(clear_gcps_action)

        # View menu
        view_menu = menubar.addMenu('&View')

        # Toggle orthorectification
        self.ortho_toggle_action = QAction('Enable Orthorectification', self)
        self.ortho_toggle_action.setCheckable(True)
        self.ortho_toggle_action.setStatusTip('Toggle progressive orthorectification')
        self.ortho_toggle_action.triggered.connect(self.toggle_orthorectification)
        view_menu.addAction(self.ortho_toggle_action)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('About', self)
        about_action.setStatusTip('About GCP Picker')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Open test image
        open_test_action = QAction('Open Test Image', self)
        open_test_action.triggered.connect(self.open_test_image)
        toolbar.addAction(open_test_action)

        toolbar.addSeparator()

        # Save/Load GCPs
        save_gcps_action = QAction('Save GCPs', self)
        save_gcps_action.triggered.connect(self.save_gcps)
        toolbar.addAction(save_gcps_action)

        load_gcps_action = QAction('Load GCPs', self)
        load_gcps_action.triggered.connect(self.load_gcps)
        toolbar.addAction(load_gcps_action)

        toolbar.addSeparator()

        # Clear GCPs
        clear_gcps_action = QAction('Clear All', self)
        clear_gcps_action.triggered.connect(self.clear_all_gcps)
        toolbar.addAction(clear_gcps_action)

    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready')

    def connect_signals(self):
        """Connect signals between components."""
        # Test viewer signals
        self.test_viewer.point_selected.connect(self.on_test_point_selected)
        self.test_viewer.image_loaded.connect(self.on_test_image_loaded)
        self.test_viewer.gcp_point_clicked.connect(self.on_test_gcp_clicked)

        # Reference viewer signals
        self.reference_viewer.point_selected.connect(self.on_reference_point_selected)
        self.reference_viewer.reference_loaded.connect(self.on_reference_loaded)

        # GCP manager signals
        self.gcp_manager.gcp_added.connect(self.on_gcp_added)
        self.gcp_manager.gcp_removed.connect(self.on_gcp_removed)
        self.gcp_manager.gcp_selected.connect(self.on_gcp_selected)

    def on_reference_point_selected(self, x, y, lon, lat):
        """Handle reference point selection."""
        self.gcp_processor.set_pending_reference_point((x, y, lon, lat))
        self.status_bar.showMessage(f'Reference point selected: ({lon:.6f}, {lat:.6f})')
        self.update_reference_status(lat=lat, lon=lon)

    def on_test_point_selected(self, x, y):
        """Handle test image point selection."""
        self.gcp_processor.set_pending_test_point(x, y)
        self.status_bar.showMessage(f'Test point selected: ({x:.1f}, {y:.1f})')
        self.update_test_status(x=x, y=y)

    def on_test_image_loaded(self, image_path):
        """Handle test image loading."""
        self.gcp_processor.set_test_image_path(image_path)
        self.status_bar.showMessage(f'Test image loaded: {Path(image_path).name}')

    def on_test_gcp_clicked(self, gcp_id):
        """Handle GCP point click in test viewer."""
        self.gcp_manager.select_gcp(gcp_id)

    def on_reference_loaded(self, reference_info):
        """Handle reference source loading."""
        self.gcp_processor.set_reference_info(reference_info)
        self.status_bar.showMessage(f'Reference loaded: {reference_info.get("name", "Unknown")}')

    def update_reference_status(self, zoom_level=None, lat=None, lon=None):
        """Update reference viewer status bar."""
        zoom_text = f"Zoom: {zoom_level}%" if zoom_level else "Zoom: 100%"
        lat_text = f"Lat: {lat:.6f}" if lat else "Lat: N/A"
        lon_text = f"Lon: {lon:.6f}" if lon else "Lon: N/A"
        self.status_bar.showMessage(f"Reference {zoom_text} | {lat_text} | {lon_text}")

    def update_test_status(self, zoom_level=None, x=None, y=None):
        """Update test viewer status bar."""
        zoom_text = f"Zoom: {zoom_level}%" if zoom_level else "Zoom: 100%"
        x_text = f"X: {x:.1f}" if x is not None else "X: N/A"
        y_text = f"Y: {y:.1f}" if y is not None else "Y: N/A"
        self.status_bar.showMessage(f"Test {zoom_text} | {x_text} | {y_text}")

    def open_test_image(self):
        """Open a test image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Test Image', '',
            'Image Files (*.tif *.tiff *.jpg *.jpeg *.png *.img);;All Files (*)'
        )

        if file_path:
            try:
                self.test_viewer.load_image(file_path)
                self.status_bar.showMessage(f'Loaded test image: {Path(file_path).name}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load test image:\n{str(e)}')
                self.status_bar.showMessage('Failed to load test image')

    def save_gcps(self):
        """Save GCPs to file."""
        if not self.gcp_processor.has_gcps():
            QMessageBox.information(self, 'Info', 'No GCPs to save')
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save GCPs', '',
            'GCP Files (*.gcp *.txt);;All Files (*)'
        )

        if file_path:
            try:
                self.gcp_processor.save_gcps(file_path)
                self.status_bar.showMessage(f'Saved {self.gcp_processor.gcp_count()} GCPs to file')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to save GCPs:\n{str(e)}')
                self.status_bar.showMessage('Failed to save GCPs')

    def load_gcps(self):
        """Load GCPs from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Load GCPs', '',
            'GCP Files (*.gcp *.txt);;All Files (*)'
        )

        if file_path:
            try:
                self.gcp_processor.load_gcps(file_path)
                self.gcp_manager.update_gcp_list(self.gcp_processor.get_gcps())
                self.status_bar.showMessage(f'Loaded {self.gcp_processor.gcp_count()} GCPs from file')

                # Trigger orthorectification if enabled
                if self.ortho_toggle_action.isChecked():
                    self.perform_orthorectification()

            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load GCPs:\n{str(e)}')
                self.status_bar.showMessage('Failed to load GCPs')

    def clear_all_gcps(self):
        """Clear all GCPs."""
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all ground control points?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.gcp_processor.clear_gcps()
            self.gcp_manager.clear_gcps()
            self.test_viewer.clear_points()
            self.reference_viewer.clear_points()
            self.status_bar.showMessage('Cleared all GCPs')

    def toggle_orthorectification(self, enabled):
        """Toggle orthorectification on/off."""
        if enabled and self.gcp_processor.gcp_count() >= 3:
            self.perform_orthorectification()
        elif enabled:
            self.ortho_toggle_action.setChecked(False)
            QMessageBox.information(self, 'Info', 'Need at least 3 GCPs for orthorectification')

    def perform_orthorectification(self):
        """Perform orthorectification using current GCPs."""
        if not self.test_viewer.has_image():
            return

        try:
            self.status_bar.showMessage('Performing orthorectification...')
            gcps = self.gcp_processor.get_gcps()
            self.orthorectifier.orthorectify(
                self.test_viewer.get_image_path(),
                gcps,
                self.test_viewer.get_rpc_data()
            )
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Orthorectification failed:\n{str(e)}')
            self.status_bar.showMessage('Orthorectification failed')

    def on_test_point_selected(self, x, y):
        """Handle point selection in test image."""
        self.gcp_processor.set_pending_test_point(x, y)
        self.status_bar.showMessage(f'Test point selected: ({x:.2f}, {y:.2f})')

        # Check if we have a matching reference point
        if self.gcp_processor.has_pending_reference_point():
            self.create_gcp_from_pending_points()

    def on_reference_point_selected(self, x, y, lon, lat):
        """Handle point selection in reference image."""
        self.gcp_processor.set_pending_reference_point(x, y, lon, lat)
        self.status_bar.showMessage(f'Reference point selected: ({lon:.6f}, {lat:.6f})')

        # Check if we have a matching test point
        if self.gcp_processor.has_pending_test_point():
            self.create_gcp_from_pending_points()

    def on_test_image_loaded(self, image_path):
        """Handle test image loading."""
        self.gcp_processor.set_test_image_path(image_path)

    def on_reference_loaded(self, reference_info):
        """Handle reference source loading."""
        self.gcp_processor.set_reference_info(reference_info)

    def on_gcp_added(self, gcp):
        """Handle GCP addition."""
        self.gcp_processor.add_gcp(gcp)

        # Add visual markers
        self.test_viewer.add_gcp_point(gcp.test_x, gcp.test_y, gcp.id)
        self.reference_viewer.add_gcp_point(gcp.ref_x, gcp.ref_y, gcp.id)

        self.status_bar.showMessage(f'Added GCP {gcp.id}')

        # Trigger orthorectification if enabled and we have enough points
        if (self.ortho_toggle_action.isChecked() and
            self.gcp_processor.gcp_count() >= 3):
            self.perform_orthorectification()

    def on_gcp_removed(self, gcp_id):
        """Handle GCP removal."""
        self.gcp_processor.remove_gcp(gcp_id)

        # Remove visual markers
        self.test_viewer.remove_gcp_point(gcp_id)
        self.reference_viewer.remove_gcp_point(gcp_id)

        self.status_bar.showMessage(f'Removed GCP {gcp_id}')

    def on_gcp_selected(self, gcp_id):
        """Handle GCP selection."""
        gcp = self.gcp_processor.get_gcp(gcp_id)
        if gcp:
            self.test_viewer.highlight_gcp_point(gcp.test_x, gcp.test_y)
            self.reference_viewer.highlight_gcp_point(gcp.ref_x, gcp.ref_y)
            self.status_panel.update_gcp_info(gcp)

    def on_orthorectification_complete(self, ortho_image_path):
        """Handle orthorectification completion."""
        self.test_viewer.update_orthorectified_image(ortho_image_path)
        self.status_bar.showMessage(f'Orthorectification complete: {Path(ortho_image_path).name}')

    def create_gcp_from_pending_points(self):
        """Create a GCP from pending test and reference points."""
        test_point = self.gcp_processor.get_pending_test_point()
        ref_point = self.gcp_processor.get_pending_reference_point()

        if test_point and ref_point:
            gcp = self.gcp_processor.create_gcp_from_pending()
            self.gcp_manager.add_gcp(gcp)

            # Clear pending points
            self.gcp_processor.clear_pending_points()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, 'About GCP Picker',
            'GCP Picker v1.0.0\n\n'
            'A GUI application for selecting ground control points between '
            'test imagery and reference sources with progressive orthorectification.\n\n'
            'Features:\n'
            '• Dual viewer interface\n'
            '• WMS/WMTS/GDAL virtual raster support\n'
            '• Progressive RPC orthorectification\n'
            '• GCP management and persistence'
        )

    def post_init(self):
        """Post-initialization tasks."""
        self.status_bar.showMessage('Ready - Open a test image to begin')
