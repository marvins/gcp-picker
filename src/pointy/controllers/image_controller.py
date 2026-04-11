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
#    File:    image_controller.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Image loading controller.

Owns all logic for loading test images, navigating collection image
sequences, histogram updates, and the seed-location workflow.
"""

# Python Standard Libraries
import logging
import tempfile
import time
from pathlib import Path

# Third-Party Libraries
import numpy as np
from qtpy.QtWidgets import QFileDialog, QMessageBox
from tomli_w import dump as toml_dump

# Project Libraries
from pointy.core.imagery_api import Imagery_Loader


class Image_Controller:
    """Manages test image loading, collection navigation, and histogram updates.

    Args:
        test_viewer:        Test_Image_Viewer instance.
        reference_viewer:   Leaflet_Reference_Viewer instance.
        sidebar:            Tabbed_Sidebar instance.
        collection_manager: Collection_Manager instance.
        gcp_controller:     GCP_Controller — used to bulk-load GCPs after collection load.
        status_bar:         QStatusBar for user feedback.
        ortho_controller:   Ortho_Controller instance for sidecar loading.
        parent_widget:      Parent QWidget for dialogs.
    """

    def __init__(self, test_viewer, reference_viewer, sidebar,
                 collection_manager, gcp_controller, status_bar,
                 ortho_controller=None, parent_widget=None):
        self._test      = test_viewer
        self._ref       = reference_viewer
        self._sidebar   = sidebar
        self._coll_mgr  = collection_manager
        self._gcp_ctrl  = gcp_controller
        self._status    = status_bar
        self._parent    = parent_widget
        self._imagery   = Imagery_Loader()
        self._pending_seed: tuple[float, float] | None = None
        self._ortho_ctrl = ortho_controller

    def connect(self):
        """Wire all signals managed by this controller."""
        self._test.image_loaded.connect(self.on_image_loaded)
        self._test.image_loaded.connect(self._on_image_loaded_update_histogram)
        self._test.image_adjusted.connect(self._on_image_adjusted_update_histogram)
        self._sidebar.get_view_control_panel().recompute_bounds_requested.connect(self._on_recompute_bounds)

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def on_image_loaded(self, image_path: str):
        """Handle test image load completion."""
        if self._pending_seed:
            lat, lon = self._pending_seed
            self._ref.set_center(lat, lon)
            self._status.showMessage(
                f'Loaded: {Path(image_path).name} (seed: {lat:.4f}, {lon:.4f})'
            )
            self._pending_seed = None
        else:
            self._status.showMessage(f'Loaded: {Path(image_path).name}')

        view_panel = self._sidebar.get_view_control_panel()
        if view_panel.is_auto_stretch():
            self._test.set_auto_stretch(True)

        # Check for ortho model sidecar
        if self._ortho_ctrl:
            self._ortho_ctrl.check_and_load_sidecar(image_path)

    def open_test_image(self):
        """Open a single test image by wrapping it in a temporary collection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self._parent, 'Open Test Image', '',
            'Image Files (*.tif *.tiff *.jpg *.jpeg *.png *.img);;All Files (*)'
        )
        if file_path:
            try:
                temp_path = self._create_single_image_collection(file_path)
                self.load_collection_from_path(temp_path)
            except Exception as e:
                QMessageBox.critical(self._parent, 'Error', f'Failed to load image:\n{e}')
                self._status.showMessage('Failed to load test image')

    # ------------------------------------------------------------------
    # Collection loading
    # ------------------------------------------------------------------

    def load_collection(self):
        """Load a collection configuration file via file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self._parent, 'Load Collection', '',
            'TOML Files (*.toml);;All Files (*)'
        )
        if file_path:
            self.load_collection_from_path(file_path)

    def load_collection_from_path(self, collection_path: str):
        """Load a collection from a specific path."""
        success = self._coll_mgr.load_collection(collection_path)
        if not success:
            QMessageBox.critical(self._parent, 'Error', f'Failed to load collection: {collection_path}')
            self._status.showMessage('Failed to load collection')
            return

        self._status.showMessage(f'Loaded collection: {self._coll_mgr.current_collection.name}')
        self._load_first_collection_image()

        gcp_file = self._coll_mgr.current_collection.gcp_file
        if Path(gcp_file).exists():
            try:
                count = self._gcp_ctrl.load_gcps_from_path(gcp_file)
                self._status.showMessage(f'Loaded collection with {count} GCPs')
            except Exception as e:
                logging.warning(f'Could not auto-load GCPs from {gcp_file}: {e}')

    # ------------------------------------------------------------------
    # Collection navigation
    # ------------------------------------------------------------------

    def load_next_collection_image(self):
        """Load the next image in the collection."""
        next_image = self._coll_mgr.get_next_image()
        if next_image:
            self._load_collection_image(next_image)
        else:
            self._status.showMessage('Already at last image in collection')

    def load_previous_collection_image(self):
        """Load the previous image in the collection."""
        prev_image = self._coll_mgr.get_previous_image()
        if prev_image:
            self._load_collection_image(prev_image)
        else:
            self._status.showMessage('Already at first image in collection')

    def load_last_collection_image(self):
        """Load the last image in the collection."""
        if not self._coll_mgr.has_collection():
            return
        total = len(self._coll_mgr.loaded_images)
        if total > 0:
            self._coll_mgr.current_image_index = total - 1
            last_image = self._coll_mgr.get_current_image()
            if last_image:
                self._load_collection_image(last_image)
        else:
            self._status.showMessage('No images in collection')

    # ------------------------------------------------------------------
    # Histogram
    # ------------------------------------------------------------------

    def _on_image_loaded_update_histogram(self, image_path: str):
        """Update histogram when image is loaded."""
        start = time.time()
        logging.debug(f'Updating histogram for image: {image_path}')

        image_data = self._test.get_image_data() if hasattr(self._test, 'get_image_data') else None
        if image_data is None:
            logging.warning('No image data available from test viewer')
            return

        view_panel = self._sidebar.get_view_control_panel()
        logging.debug(f'Got image data with shape: {image_data.shape}, dtype: {image_data.dtype}')

        if hasattr(self._test, 'bit_depth'):
            bit_depth  = self._test.bit_depth
            max_pixel  = (2 ** bit_depth) - 1
            view_panel.set_min_max_range(0, max_pixel)
            actual_min = int(np.min(image_data))
            actual_max = int(np.max(image_data))
            view_panel.min_pixel_spin.setValue(actual_min)
            view_panel.max_pixel_spin.setValue(actual_max)
            if not view_panel.auto_stretch_checkbox.isChecked():
                view_panel.min_pixel_spin.setEnabled(True)
                view_panel.max_pixel_spin.setEnabled(True)
            view_panel.update_histogram(image_data, num_bins=min(256, max_pixel + 1))
        else:
            view_panel.update_histogram(image_data)

        logging.debug(f'Total histogram update took: {time.time() - start:.3f}s')

    def _on_image_adjusted_update_histogram(self):
        """Update histogram when image adjustments are applied."""
        image_data = self._test.get_image_data() if hasattr(self._test, 'get_image_data') else None
        if image_data is None:
            return
        view_panel = self._sidebar.get_view_control_panel()
        if hasattr(self._test, 'bit_depth'):
            max_pixel = (2 ** self._test.bit_depth) - 1
            view_panel.update_histogram(image_data, num_bins=min(256, max_pixel + 1))
        else:
            view_panel.update_histogram(image_data)

    def _on_recompute_bounds(self):
        """Re-compute DRA bounds for the local view."""
        image_data = self._test.get_image_data() if hasattr(self._test, 'get_image_data') else None
        if image_data is None:
            return

        view_panel = self._sidebar.get_view_control_panel()
        actual_min = int(np.min(image_data))
        actual_max = int(np.max(image_data))
        view_panel.min_pixel_spin.setValue(actual_min)
        view_panel.max_pixel_spin.setValue(actual_max)
        self._status.showMessage(f'Updated DRA bounds: {actual_min}-{actual_max}')

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_first_collection_image(self):
        """Load the first image from the collection and seed the reference viewer."""
        if not self._coll_mgr.has_collection():
            return

        first_image = self._coll_mgr.get_first_image()
        if not first_image:
            QMessageBox.information(self._parent, 'Info', 'No images found in collection')
            return

        self._imagery.needs_seed_location(first_image)
        try:
            self._test.load_image(first_image)
            self._status.showMessage(f'Loaded: {Path(first_image).name}')

            seed = self._coll_mgr.get_collection_seed_location()
            if seed:
                lat, lon = seed
                self._ref.recreate_map_with_center(lat, lon)
                self._status.showMessage(
                    f'Centered on collection: ({lat:.4f}, {lon:.4f}) - {Path(first_image).name}'
                )

            self._update_nav_counter()

        except Exception as e:
            QMessageBox.critical(self._parent, 'Error', f'Failed to load image:\n{e}')
            self._status.showMessage('Failed to load collection image')
            raise

    def _load_collection_image(self, image_path: str):
        """Load a collection image with async loading and seed handling."""
        needs_seed = self._imagery.needs_seed_location(image_path)
        seed       = self._coll_mgr.get_collection_seed_location()

        self._test.load_image(image_path)

        if needs_seed and seed:
            self._pending_seed = seed
        else:
            self._pending_seed = None

        self._update_nav_counter()

    def _update_nav_counter(self):
        """Update the sidebar navigation counter."""
        if self._coll_mgr.has_collection():
            current = self._coll_mgr.current_image_index + 1
            total   = len(self._coll_mgr.loaded_images)
            self._sidebar.get_collection_nav_panel().update_counter(current, total)
        else:
            self._sidebar.get_collection_nav_panel().update_counter(0, 0)

    def _create_single_image_collection(self, image_path: str) -> str:
        """Create a temporary collection TOML for a single image."""
        image_name    = Path(image_path).stem
        collection_data = {
            'collection': {
                'name':        f'Single Image - {image_name}',
                'description': f'Temporary collection for single image: {image_name}',
                'version':     '1.0',
            },
            'imagery': [
                {
                    'name':        image_name,
                    'path':        str(Path(image_path).absolute()),
                    'source_type': 'test',
                    'description': f'Single test image: {image_name}',
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            toml_dump(collection_data, f)
            temp_path = f.name
        logging.info(f'Created temporary collection: {temp_path}')
        return temp_path
