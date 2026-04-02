"""
Main Window for GCP Picker Application
"""

#  Python Standard Libraries
import os
from pathlib import Path

#  Third-Party Libraries
import numpy as np
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QKeySequence, QGuiApplication
from qtpy.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                        QSplitter, QMenuBar, QStatusBar, QFileDialog,
                        QMessageBox, QToolBar, QAction)

#  Project Libraries
from app.viewers.test_image_viewer import Test_Image_Viewer
from app.viewers.leaflet_reference_viewer import Leaflet_Reference_Viewer
from app.widgets.gcp_manager import GCP_Manager
from app.widgets.about_dialog import show_about_dialog
from .sidebar.tabbed_sidebar import Tabbed_Sidebar
from app.core.gcp_processor import GCP_Processor
from app.core.orthorectifier import Orthorectifier
from app.core.collection_manager import Collection_Manager, Collection_Info
from app.core.imagery_api import Imagery_Loader

class MainWindow(QMainWindow):
    """Main application window for GCP Picker."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pointy-McPointface - Where Coordinates Get Pointy!")

        # Get screen dimensions and set window size to fit
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Set window size to 80% of screen size, with minimum dimensions
        window_width = min(int(screen_geometry.width() * 0.8), 1200)
        window_height = min(int(screen_geometry.height() * 0.8), 800)

        # Center the window on screen
        x = (screen_geometry.width() - window_width) // 2
        y = (screen_geometry.height() - window_height) // 2

        self.setGeometry(x, y, window_width, window_height)

        # Initialize core components
        self.gcp_processor = GCP_Processor()
        self.orthorectifier = Orthorectifier()
        self.collection_manager = Collection_Manager()
        self.imagery_loader = Imagery_Loader()

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

        # Set initial splitter sizes (reference viewer 35%, test viewer 65%)
        self.image_splitter.setSizes([350, 650])

        # Create vertical splitter for main content and sidebar
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Add the image splitter to the left
        self.main_splitter.addWidget(self.image_splitter)

        # Create sidebar widget using Tabbed_Sidebar
        self.sidebar = Tabbed_Sidebar()
        self.gcp_panel = self.sidebar.get_gcp_panel()
        self.gcp_manager = self.gcp_panel.gcp_manager
        self.status_panel = self.sidebar.get_status_panel()

        # Connect GCP panel lock signal
        self.gcp_panel.lock_state_changed.connect(self.on_gcp_lock_changed)

        # Connect collection nav panel signals
        nav_panel = self.sidebar.get_collection_nav_panel()
        nav_panel.first_image_requested.connect(self.load_first_collection_image)
        nav_panel.previous_image_requested.connect(self.load_previous_collection_image)
        nav_panel.next_image_requested.connect(self.load_next_collection_image)
        nav_panel.last_image_requested.connect(self.load_last_collection_image)

        # Set sidebar width and add to main splitter
        self.sidebar.setMaximumWidth(400)
        self.sidebar.setMinimumWidth(300)
        self.main_splitter.addWidget(self.sidebar)

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

        # Collection menu
        collection_menu = menubar.addMenu('&Collection')

        load_collection_action = QAction('Load Collection...', self)
        load_collection_action.setShortcut(QKeySequence.Open)
        load_collection_action.setStatusTip('Load a collection configuration file')
        load_collection_action.triggered.connect(self.load_collection)
        collection_menu.addAction(load_collection_action)

        collection_menu.addSeparator()

        next_image_action = QAction('Next Image', self)
        next_image_action.setShortcut('Ctrl+N')
        next_image_action.setStatusTip('Load next image in collection')
        next_image_action.triggered.connect(self.load_next_collection_image)
        collection_menu.addAction(next_image_action)

        prev_image_action = QAction('Previous Image', self)
        prev_image_action.setShortcut('Ctrl+P')
        prev_image_action.setStatusTip('Load previous image in collection')
        prev_image_action.triggered.connect(self.load_previous_collection_image)
        collection_menu.addAction(prev_image_action)

        collection_menu.addSeparator()
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
        self.test_viewer.image_loaded.connect(self._on_image_loaded_update_histogram)

        # Reference viewer signals
        self.reference_viewer.point_selected.connect(self.on_reference_point_selected)
        self.reference_viewer.reference_loaded.connect(self.on_reference_loaded)

        # GCP manager signals
        self.gcp_manager.gcp_added.connect(self.on_gcp_added)
        self.gcp_manager.gcp_removed.connect(self.on_gcp_removed)
        self.gcp_manager.gcp_selected.connect(self.on_gcp_selected)

        # View control panel signals
        view_panel = self.sidebar.get_view_control_panel()
        view_panel.min_pixel_changed.connect(self.on_min_pixel_changed)
        view_panel.max_pixel_changed.connect(self.on_max_pixel_changed)
        view_panel.brightness_changed.connect(self.on_brightness_changed)
        view_panel.contrast_changed.connect(self.on_contrast_changed)
        view_panel.auto_stretch_toggled.connect(self.on_auto_stretch_toggled)
        view_panel.reset_requested.connect(self.on_view_reset_requested)

        # Metadata panel connections - cursor tracking
        # Note: These signals need to be emitted by the viewers on mouse move
        self.reference_viewer.cursor_moved.connect(self.on_reference_cursor_moved)
        self.test_viewer.cursor_moved.connect(self.on_test_cursor_moved)

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

    def _on_image_loaded_update_histogram(self, image_path):
        """Update histogram when image is loaded."""
        # Get image data from test viewer
        if hasattr(self.test_viewer, 'get_image_data'):
            image_data = self.test_viewer.get_image_data()
            if image_data is not None:
                view_panel = self.sidebar.get_view_control_panel()

                # Set pixel range based on image bit depth
                if hasattr(self.test_viewer, 'bit_depth'):
                    bit_depth = self.test_viewer.bit_depth
                    max_pixel = (2 ** bit_depth) - 1

                    # Set the range and get actual data min/max
                    view_panel.set_min_max_range(0, max_pixel)

                    # Calculate actual pixel range from the image data
                    actual_min = int(np.min(image_data))
                    actual_max = int(np.max(image_data))

                    # Set the spin boxes to actual data range
                    view_panel.min_pixel_spin.setValue(actual_min)
                    view_panel.max_pixel_spin.setValue(actual_max)

                    # Enable the controls for manual adjustment
                    if not view_panel.auto_stretch_checkbox.isChecked():
                        view_panel.min_pixel_spin.setEnabled(True)
                        view_panel.max_pixel_spin.setEnabled(True)

                view_panel.update_histogram(image_data)

    def on_reference_loaded(self, reference_info):
        """Handle reference source loading."""
        self.gcp_processor.set_reference_info(reference_info)

    def on_gcp_lock_changed(self, is_locked: bool):
        """Handle GCP panel lock state changes."""
        if is_locked:
            self.status_bar.showMessage('GCP selection is locked - points disabled')
        else:
            self.status_bar.showMessage('GCP selection is unlocked - points enabled')

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

    def on_min_pixel_changed(self, value: int):
        """Handle minimum pixel value change."""
        self.test_viewer.set_min_pixel(value)

    def on_max_pixel_changed(self, value: int):
        """Handle maximum pixel value change."""
        self.test_viewer.set_max_pixel(value)

    def on_brightness_changed(self, value: float):
        """Handle brightness adjustment."""
        self.test_viewer.set_brightness(value)

    def on_contrast_changed(self, value: float):
        """Handle contrast adjustment."""
        self.test_viewer.set_contrast(value)

    def on_auto_stretch_toggled(self, enabled: bool):
        """Handle auto-stretch toggle."""
        self.test_viewer.set_auto_stretch(enabled)

    def on_view_reset_requested(self):
        """Handle reset to default view settings."""
        self.test_viewer.reset_view_settings()

    def on_reference_cursor_moved(self, lat: float, lon: float, alt: float | None = None):
        """Handle cursor movement over reference viewer."""
        self.sidebar.get_metadata_panel().update_reference_metadata(lat, lon, alt)

    def on_test_cursor_moved(self, x: int, y: int, pixel_value: str | None = None,
                              lat: float | None = None, lon: float | None = None, alt: float | None = None):
        """Handle cursor movement over test viewer."""
        self.sidebar.get_metadata_panel().update_test_metadata(x, y, pixel_value, lat, lon, alt)

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
        show_about_dialog(self)

    def load_collection_from_path(self, collection_path: str):
        """Load a collection from a specific path (used by CLI)."""
        success = self.collection_manager.load_collection(collection_path)
        if success:
            self.status_bar.showMessage(f'Loaded collection: {self.collection_manager.current_collection.name}')
            # Auto-load first image
            self.load_first_collection_image()
        else:
            QMessageBox.critical(self, 'Error', f'Failed to load collection: {collection_path}')
            self.status_bar.showMessage('Failed to load collection')

    def load_collection(self):
        """Load a collection configuration file via file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Load Collection', '',
            'TOML Files (*.toml);;All Files (*)'
        )

        if file_path:
            self.load_collection_from_path(file_path)

    def load_first_collection_image(self):
        """Load the first image from the collection and set seed location."""
        if not self.collection_manager.has_collection():
            return

        first_image = self.collection_manager.get_first_image()
        if not first_image:
            QMessageBox.information(self, 'Info', 'No images found in collection')
            return

        # Check if image needs seed location
        needs_seed = self.imagery_loader.needs_seed_location(first_image)

        # Get collection seed location
        seed_location = self.collection_manager.get_collection_seed_location()

        # Load the image
        try:
            self.test_viewer.load_image(first_image)
            self.status_bar.showMessage(f'Loaded: {Path(first_image).name}')

            # Always center reference viewer on collection location
            seed_location = self.collection_manager.get_collection_seed_location()
            if seed_location:
                lat, lon = seed_location
                self.reference_viewer.recreate_map_with_center(lat, lon)
                self.status_bar.showMessage(f'Centered on collection: ({lat:.4f}, {lon:.4f}) - {Path(first_image).name}')

            # Update navigation counter
            self._update_nav_counter()

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load image:\n{str(e)}')
            self.status_bar.showMessage('Failed to load collection image')

    def load_next_collection_image(self):
        """Load next image in collection."""
        next_image = self.collection_manager.get_next_image()
        if next_image:
            self._load_collection_image(next_image)
        else:
            self.status_bar.showMessage('Already at last image in collection')

    def load_previous_collection_image(self):
        """Load previous image in collection."""
        prev_image = self.collection_manager.get_previous_image()
        if prev_image:
            self._load_collection_image(prev_image)
        else:
            self.status_bar.showMessage('Already at first image in collection')

    def load_last_collection_image(self):
        """Load last image in collection."""
        if not self.collection_manager.has_collection():
            return

        # Jump to last index
        total = len(self.collection_manager.loaded_images)
        if total > 0:
            self.collection_manager.current_image_index = total - 1
            last_image = self.collection_manager.get_current_image()
            if last_image:
                self._load_collection_image(last_image)
        else:
            self.status_bar.showMessage('No images in collection')

    def _update_nav_counter(self):
        """Update sidebar navigation counter."""
        if self.collection_manager.has_collection():
            current = self.collection_manager.current_image_index + 1
            total = len(self.collection_manager.loaded_images)
            self.sidebar.get_collection_nav_panel().update_counter(current, total)
        else:
            self.sidebar.get_collection_nav_panel().update_counter(0, 0)

    def _load_collection_image(self, image_path: str):
        """Helper to load a collection image with seed handling."""
        needs_seed = self.imagery_loader.needs_seed_location(image_path)
        seed_location = self.collection_manager.get_collection_seed_location()

        try:
            self.test_viewer.load_image(image_path)

            if needs_seed and seed_location:
                lat, lon = seed_location
                self.reference_viewer.set_center(lat, lon)
                self.status_bar.showMessage(f'Loaded: {Path(image_path).name} (seed: {lat:.4f}, {lon:.4f})')
            else:
                self.status_bar.showMessage(f'Loaded: {Path(image_path).name}')

            # Update navigation counter
            self._update_nav_counter()

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load image:\n{str(e)}')

    def post_init(self):
        """Post-initialization tasks."""
        self.status_bar.showMessage('Ready - Open a test image or load a collection to begin')
