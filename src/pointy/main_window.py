#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2025 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    main_window.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Main Window for Pointy-McPointface Application
"""

#  Third-Party Libraries
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence, QGuiApplication, QIcon
from qtpy.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                        QSplitter, QStatusBar, QToolBar, QAction, QMessageBox)

#  Project Libraries
from pointy import resources
from pointy.viewers.test_image_viewer import Test_Image_Viewer
from pointy.viewers.leaflet_reference_viewer import Leaflet_Reference_Viewer
from pointy.widgets.gcp_manager import GCP_Manager
from pointy.widgets.about_dialog import show_about_dialog
from pointy.sidebar.tabbed_sidebar import Tabbed_Sidebar
from pointy.core.gcp_processor import GCP_Processor
from pointy.core.collection_manager import Collection_Manager
from pointy.controllers.auto_match_controller import Auto_Match_Controller
from pointy.controllers.gcp_controller import GCP_Controller
from pointy.controllers.image_controller import Image_Controller
from pointy.controllers.ortho_controller import Ortho_Controller
from pointy.controllers.sync_controller import Sync_Controller
from pointy.resources import resources

class Main_Window(QMainWindow):
    """Main application window for Pointy-McPointface."""

    def __init__(self, terrain_manager=None):
        super().__init__()
        self.setWindowTitle("Pointy-McPointface")

        # Set application icon
        app_icon = resources.get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        # Store terrain manager for ortho module access
        self.terrain_manager = terrain_manager

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
        self.collection_manager = Collection_Manager()

        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()

        # Create controllers
        self.sync_ctrl = Sync_Controller( test_viewer      = self.test_viewer,
                                          reference_viewer = self.reference_viewer,
                                          gcp_processor    = self.gcp_processor,
                                          status_bar       = self.status_bar )

        self.gcp_ctrl = GCP_Controller( gcp_processor      = self.gcp_processor,
                                        gcp_manager        = self.gcp_manager,
                                        gcp_panel          = self.gcp_panel,
                                        test_viewer        = self.test_viewer,
                                        reference_viewer   = self.reference_viewer,
                                        collection_manager = self.collection_manager,
                                        status_bar         = self.status_bar,
                                        parent_widget      = self )

        self.ortho_ctrl = Ortho_Controller( gcp_processor    = self.gcp_processor,
                                            test_viewer      = self.test_viewer,
                                            reference_viewer = self.reference_viewer,
                                            sidebar          = self.sidebar,
                                            ortho_action     = self.ortho_toggle_action,
                                            status_bar       = self.status_bar,
                                            parent_widget    = self )

        self.image_ctrl = Image_Controller( test_viewer        = self.test_viewer,
                                            reference_viewer   = self.reference_viewer,
                                            sidebar            = self.sidebar,
                                            collection_manager = self.collection_manager,
                                            gcp_controller     = self.gcp_ctrl,
                                            status_bar         = self.status_bar,
                                            ortho_controller   = self.ortho_ctrl,
                                            parent_widget      = self )

        self.auto_match_ctrl = Auto_Match_Controller( gcp_processor    = self.gcp_processor,
                                                      test_viewer      = self.test_viewer,
                                                      reference_viewer = self.reference_viewer,
                                                      sidebar          = self.sidebar,
                                                      status_bar       = self.status_bar )

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
        self.reference_viewer = Leaflet_Reference_Viewer(terrain_manager=self.terrain_manager)
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
        # Connect GCP panel lock signal
        self.gcp_panel.lock_state_changed.connect(self.on_gcp_lock_changed)

        # Connect collection nav panel signals
        nav_panel = self.sidebar.get_collection_nav_panel()
        nav_panel.first_image_requested.connect(self.load_first_collection_image)
        nav_panel.previous_image_requested.connect(self.load_previous_collection_image)
        nav_panel.next_image_requested.connect(self.load_next_collection_image)
        nav_panel.last_image_requested.connect(self.load_last_collection_image)

        # Set sidebar width and add to main splitter
        self.sidebar.setMaximumWidth(450)
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
        about_action.setStatusTip('About Pointy-McPointface')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready')

    def connect_signals(self):
        """Connect signals between components."""
        # Delegated to controllers
        self.sync_ctrl.connect()
        self.gcp_ctrl.connect()
        self.ortho_ctrl.connect()
        self.image_ctrl.connect()
        self.auto_match_ctrl.connect()

        # GCP navigation — Sync_Controller
        self.gcp_manager.gcp_navigate.connect(self.sync_ctrl.on_gcp_navigate)

        # Reference loaded
        self.reference_viewer.reference_loaded.connect(self.on_reference_loaded)

        # View control panel — thin pass-throughs that belong to no controller
        view_panel = self.sidebar.get_view_control_panel()
        view_panel.min_pixel_changed.connect(self.on_min_pixel_changed)
        view_panel.max_pixel_changed.connect(self.on_max_pixel_changed)
        view_panel.brightness_changed.connect(self.on_brightness_changed)
        view_panel.contrast_changed.connect(self.on_contrast_changed)
        view_panel.auto_stretch_toggled.connect(self.on_auto_stretch_toggled)
        view_panel.reset_requested.connect(self.on_view_reset_requested)

        # Cursor tracking — metadata panel
        self.reference_viewer.cursor_moved.connect(self.on_reference_cursor_moved)
        self.test_viewer.cursor_moved.connect(self.on_test_cursor_moved)

    def on_gcp_lock_changed(self, is_locked: bool):
        """Handle GCP panel lock state changes."""
        msg = 'GCP selection is locked - points disabled' if is_locked else 'GCP selection is unlocked - points enabled'
        self.status_bar.showMessage(msg)

    def on_fit_requested(self, model_name: str):
        """Delegate model fitting to Ortho_Controller."""
        self.ortho_ctrl.on_fit_requested(model_name)

    def load_first_collection_image(self):
        """Delegate to Image_Controller."""
        self.image_ctrl._load_first_collection_image()

    def save_gcps(self):
        """Delegate to GCP_Controller."""
        self.gcp_ctrl.save_gcps()

    def load_gcps(self):
        """Delegate to GCP_Controller."""
        self.gcp_ctrl.load_gcps()

    def clear_all_gcps(self):
        """Delegate to GCP_Controller."""
        self.gcp_ctrl.clear_all_gcps()

    def toggle_orthorectification(self, enabled: bool):
        """Delegate ortho toggle to Ortho_Controller."""
        if enabled:
            self.ortho_ctrl.perform_orthorectification()
        else:
            self.ortho_ctrl.on_view_mode_changed(False)

    def on_reference_loaded(self, reference_info):
        """Handle reference source loading."""
        self.gcp_processor.set_reference_info(reference_info)
        self.status_bar.showMessage(f'Reference loaded: {reference_info.get("name", "Unknown")}')

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

    def show_about(self):
        """Show about dialog."""
        show_about_dialog(self)

    def load_collection_from_path(self, collection_path: str):
        """Load a collection from a specific path (used by CLI)."""
        self.image_ctrl.load_collection_from_path(collection_path)

    def load_collection(self):
        """Load a collection configuration file via file dialog."""
        self.image_ctrl.load_collection()

    def load_next_collection_image(self):
        """Load next image in collection."""
        self.image_ctrl.load_next_collection_image()

    def load_previous_collection_image(self):
        """Load previous image in collection."""
        self.image_ctrl.load_previous_collection_image()

    def load_last_collection_image(self):
        """Load last image in collection."""
        self.image_ctrl.load_last_collection_image()

    def open_test_image(self):
        """Open a single test image by creating a temporary collection."""
        self.image_ctrl.open_test_image()

    def post_init(self):
        """Post-initialization tasks."""
        self.status_bar.showMessage('Ready - Open a test image or load a collection to begin')

    def closeEvent(self, event):
        """Handle window close event - check for unsaved GCPs."""
        if not self.gcp_ctrl.check_unsaved_before_exit():
            event.ignore()
        else:
            event.accept()
