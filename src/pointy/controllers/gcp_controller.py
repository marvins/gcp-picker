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
#    File:    gcp_controller.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
GCP lifecycle controller.

Owns all logic for GCP creation, selection, removal, persistence, and
the pending-point workflow that auto-creates a GCP when both a test
pixel and a reference coordinate have been picked.
"""

# Python Standard Libraries
import logging
from pathlib import Path

# Third-Party Libraries
from qtpy.QtCore import QObject, QRunnable, QThreadPool, Signal
from qtpy.QtWidgets import QFileDialog, QMessageBox

# Project Libraries
from tmns.geo.coord import Geographic


class GCP_Load_Task(QRunnable):
    """Runnable task for loading GCPs in background thread."""

    def __init__(self, image_path: str, gcp_processor, controller):
        """Initialize GCP load task.

        Args:
            image_path: Path to image file
            gcp_processor: GCP_Processor instance
            controller: GCP_Controller reference for emitting signals
        """
        super().__init__()
        self.image_path = image_path
        self.gcp_processor = gcp_processor
        self.controller = controller
        self.setAutoDelete(True)

    def run(self):
        """Execute GCP loading task in background.

        Raises:
            Exception: Propagates any error loading GCPs (malformed files,
                missing keys, etc.) without catching - caller must handle.
        """
        # Look for GCP sidecar file
        sidecar = Path(self.image_path + '.gcps.json')
        gcps = []
        count = 0

        if sidecar.exists():
            count = self.gcp_processor.load_gcps(str(sidecar))
            gcps = self.gcp_processor.get_gcps()

        # Emit completion signal with results
        self.controller.gcp_load_completed.emit(self.image_path, gcps, count)


class GCP_Controller(QObject):
    """Manages the GCP lifecycle.

    Args:
        gcp_processor:    GCP_Processor instance.
        gcp_manager:      GCP_Manager widget.
        gcp_panel:        GCP panel (sidebar) widget.
        test_viewer:      Test_Image_Viewer instance.
        reference_viewer: Leaflet_Reference_Viewer instance.
        collection_manager: Collection_Manager instance.
        status_bar:       QStatusBar for user feedback.
        parent_widget:    Parent QWidget for dialogs (usually Main_Window).
    """

    # Signals for async GCP loading
    gcp_load_completed = Signal(str, list, int)  # image_path, gcps, count

    def __init__(self, gcp_processor, gcp_manager, gcp_panel,
                 test_viewer, reference_viewer, collection_manager,
                 status_bar, parent_widget):
        super().__init__()
        self._gcp_proc       = gcp_processor
        self._mgr            = gcp_manager
        self._panel          = gcp_panel
        self._test           = test_viewer
        self._ref            = reference_viewer
        self._coll_mgr       = collection_manager
        self._status         = status_bar
        self._parent         = parent_widget

        # Thread pool for async operations
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)


    def connect(self):
        """Wire all signals managed by this controller."""
        self._mgr.gcp_added.connect(self.on_gcp_added)
        self._mgr.gcp_removed.connect(self.on_gcp_removed)
        self._mgr.gcp_selected.connect(self.on_gcp_selected)

        self._panel.save_gcps_requested.connect(self.save_gcps)
        self._panel.load_gcps_requested.connect(self.load_gcps)
        self._panel.clear_gcps_requested.connect(self.clear_all_gcps)
        self._panel.create_gcp_requested.connect(self.create_gcp_from_pending_points)
        self._panel.export_gcps_requested.connect(self.export_gcps)

        self._test.point_selected.connect(self.on_test_point_selected)
        self._test.gcp_point_clicked.connect(self.on_test_gcp_clicked)
        self._ref.point_selected.connect(self.on_reference_point_selected)

        # Connect async GCP loading signals
        self.gcp_load_completed.connect(self._on_gcp_load_completed)

    # ------------------------------------------------------------------
    # Point selection
    # ------------------------------------------------------------------

    def on_test_point_selected(self, x: float, y: float):
        """Handle test image point selection.

        Note: The test viewer handles ortho-to-source conversion internally
        in on_point_clicked before emitting the signal, so x,y are always
        source image pixel coordinates regardless of view mode.
        """
        if self._panel.is_locked():
            self._status.showMessage('GCP selection is locked - unlock to select points')
            return

        self._gcp_proc.set_pending_test_point(x, y)
        self._status.showMessage(f'Test point selected: ({x:.1f}, {y:.1f})')
        self._test.image_view.set_pending_test_point(int(x), int(y))
        self._mgr.show_pending_test_point(x, y)

        if self._gcp_proc.has_pending_reference_point():
            self.create_gcp_from_pending_points()

    def on_reference_point_selected(self, x: float, y: float, lon: float, lat: float):
        """Handle reference map point selection."""
        if self._panel.is_locked():
            self._status.showMessage('GCP selection is locked - unlock to select points')
            return

        logging.debug(f'Reference point selected at ({lon:.6f}, {lat:.6f})')
        self._gcp_proc.set_pending_reference_point(x, y, lon, lat)
        self._status.showMessage(f'Reference point selected: ({lon:.6f}, {lat:.6f})')
        self._mgr.show_pending_reference_point(x, y, lon, lat)

        if self._gcp_proc.has_pending_test_point():
            logging.debug('Auto-creating GCP (reference point second)')
            self.create_gcp_from_pending_points()

    def on_test_gcp_clicked(self, gcp_id: int):
        """Handle GCP marker click in test viewer."""
        self._mgr.select_gcp_by_id(gcp_id)

    # ------------------------------------------------------------------
    # GCP lifecycle
    # ------------------------------------------------------------------

    def on_gcp_added(self, gcp):
        """Handle GCP addition."""
        self._gcp_proc.add_gcp(gcp)
        self._test.add_gcp_point(int(gcp.pixel.x_px), int(gcp.pixel.y_px), gcp.id)
        self._ref.add_gcp_point(gcp.id, gcp.geographic.longitude_deg, gcp.geographic.latitude_deg)
        self._status.showMessage(f'Added GCP {gcp.id}')

    def on_gcp_removed(self, gcp_id: int):
        """Handle GCP removal."""
        self._gcp_proc.remove_gcp(gcp_id)
        self._test.remove_gcp_point(gcp_id)
        self._ref.remove_gcp_point(gcp_id)
        self._status.showMessage(f'Removed GCP {gcp_id}')

    def on_gcp_selected(self, gcp_id: int):
        """Handle GCP selection — highlight in both viewers and update info panel."""
        gcp = self._gcp_proc.get_gcp(gcp_id)
        if gcp:
            self._test.highlight_gcp_point(int(gcp.pixel.x_px), int(gcp.pixel.y_px))
            self._ref.highlight_gcp_point(gcp.geographic.longitude_deg, gcp.geographic.latitude_deg)
            self._panel.update_gcp_info(gcp)

    def create_gcp_from_pending_points(self):
        """Create a GCP from the current pending test and reference points."""
        test_point = self._gcp_proc.get_pending_test_point()
        ref_point  = self._gcp_proc.get_pending_reference_point()

        if test_point and ref_point:
            try:
                gcp = self._gcp_proc.create_gcp_from_pending()
                self._mgr.add_gcp(gcp)

                test_x, test_y = test_point
                tx, ty = self._gcp_proc.transform_test_coordinates(test_x, test_y)
                self._test.add_gcp_point(int(tx), int(ty), gcp.id)
                self._test.image_view.clear_pending_test_point()
                self._mgr.clear_pending_point()
                self._status.showMessage(f'GCP {gcp.id} created automatically')
                self._gcp_proc.clear_pending_points()
            except RuntimeError as e:
                QMessageBox.critical(self._parent, 'Elevation Error', str(e))
                self._status.showMessage('Failed to create GCP: elevation lookup failed')
                self._gcp_proc.clear_pending_points()
                self._test.image_view.clear_pending_test_point()
                self._mgr.clear_pending_point()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_gcps(self):
        """Save GCPs to file."""
        if not self._gcp_proc.has_gcps():
            QMessageBox.information(self._parent, 'Info', 'No GCPs to save')
            return

        if self._coll_mgr.has_collection():
            image_path = self._gcp_proc.test_image_path or ''
            if not image_path:
                self._status.showMessage('No image loaded — cannot save GCPs')
                return
            file_path = image_path + '.gcps.json'
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self._parent, 'Save GCPs', '',
                'GCP Files (*.json *.gcp *.txt);;All Files (*)'
            )
            if not file_path:
                return

        try:
            self._gcp_proc.save_gcps(file_path)
            self._status.showMessage(
                f'Saved {self._gcp_proc.gcp_count()} GCPs to {Path(file_path).name}'
            )
        except Exception as e:
            QMessageBox.critical(self._parent, 'Error', f'Failed to save GCPs:\n{e}')
            self._status.showMessage('Failed to save GCPs')

    def load_gcps(self):
        """Load GCPs from file."""
        if self._coll_mgr.has_collection():
            image_path = self._gcp_proc.test_image_path or ''
            file_path  = image_path + '.gcps.json' if image_path else ''
            if not file_path or not Path(file_path).exists():
                self._status.showMessage('No GCP sidecar found for current image')
                return
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self._parent, 'Load GCPs', '',
                'GCP Files (*.json *.gcp *.txt);;All Files (*)'
            )
            if not file_path:
                return

        try:
            count = self._gcp_proc.load_gcps(file_path)
            self._mgr.update_gcp_list(self._gcp_proc.get_gcps())
            self._status.showMessage(
                f'Loaded {count} GCPs from {Path(file_path).name}'
            )
        except Exception as e:
            QMessageBox.critical(self._parent, 'Error', f'Failed to load GCPs:\n{e}')
            self._status.showMessage('Failed to load GCPs')

    def export_gcps(self):
        """Export GCPs to file."""
        if not self._gcp_proc.has_gcps():
            QMessageBox.information(self._parent, 'Info', 'No GCPs to export')
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self._parent, 'Export GCPs', '',
            'GCP Files (*.gcp *.txt);;CSV Files (*.csv);;All Files (*)'
        )
        if file_path:
            try:
                self._gcp_proc.save_gcps(file_path)
                self._status.showMessage(f'Exported {self._gcp_proc.gcp_count()} GCPs to file')
            except Exception as e:
                QMessageBox.critical(self._parent, 'Error', f'Failed to export GCPs:\n{e}')
                self._status.showMessage('Failed to export GCPs')

    def _clear_all_gcps_silent(self):
        """Clear all GCPs without user prompt (for internal/programmatic use)."""
        logging.info('_clear_all_gcps_silent called')
        self._gcp_proc.clear_gcps()
        self._mgr.clear_all_gcps()
        self._test.clear_points()
        self._ref.clear_points()
        logging.info('_clear_all_gcps_silent complete')

    def clear_all_gcps(self):
        """Prompt and clear all GCPs."""
        reply = QMessageBox.question(
            self._parent, 'Confirm', 'Clear all ground control points?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._clear_all_gcps_silent()
        self._status.showMessage('Cleared all GCPs')

    def load_gcps_for_image(self, image_path: str):
        """Load GCPs for a specific image (collection-level GCPs) asynchronously.

        Clears existing GCPs and loads the collection's GCP file if available.
        If no collection is loaded or no GCP file exists, the viewers are left empty.

        Args:
            image_path: Path to the image file.
        """
        # Always clear viewers and processor first
        self._mgr.clear_all_gcps()
        self._test.clear_points()
        self._ref.clear_points()
        self._gcp_proc.clear_gcps()
        self._gcp_proc.set_test_image_path(image_path)

        # Start async GCP loading in background
        task = GCP_Load_Task(image_path, self._gcp_proc, self)
        self.thread_pool.start(task)

    def _on_gcp_load_completed(self, image_path: str, gcps: list, count: int):
        """Handle async GCP load completion."""
        if gcps:
            self._mgr.update_gcp_list(gcps)
            logging.info(f'Loaded {count} GCPs for image: {Path(image_path).name}')


    def check_unsaved_before_exit(self) -> bool:
        """Check for unsaved GCP changes before exiting.

        Returns True if it's OK to exit, False if the user cancelled.
        """
        if self._gcp_proc.is_dirty:
            reply = QMessageBox.question(
                self._parent,
                'Unsaved GCPs',
                'You have unsaved GCP changes. Do you want to save them before exiting?',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_gcps()
                return True
            elif reply == QMessageBox.StandardButton.Discard:
                return True
            else:
                return False
        return True
