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
#    File:    auto_gcp_solver_controller.py
#    Author:  Marvin Smith
#    Date:    04/19/2026
#
"""
Auto GCP Solver Controller — orchestrates the feature-based GCP matching pipeline.

This controller handles the computer vision-based GCP creation using AKAZE/ORB
feature matching.
"""

# Python Standard Libraries
import logging
import time
from typing import Callable

# Third-Party Libraries
from qtpy.QtCore import QThread, Signal
import numpy as np

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings
from pointy.core.match.gcp_solver_pipeline import GCP_Solver_Pipeline
from pointy.core.match.types import Match_Result


class Auto_GCP_Solver_Worker(QThread):
    """Worker thread for running the auto GCP solver pipeline."""

    finished = Signal(object)  # Match_Result

    def __init__(self, settings: Auto_Match_Settings, test_image: np.ndarray,
                 ref_chip: np.ndarray, geo_transform: Callable):
        super().__init__()
        self.settings = settings
        self.test_image = test_image
        self.ref_chip = ref_chip
        self.geo_transform = geo_transform

    def run(self):
        """Execute the auto GCP solver pipeline."""
        try:
            pipeline = GCP_Solver_Pipeline(self.settings)
            result = pipeline.run(self.test_image, self.ref_chip, self.geo_transform)
            self.finished.emit(result)
        except Exception as e:
            logging.error(f"Auto GCP Solver worker error: {e}")
            error_result = Match_Result()
            error_result.success = False
            error_result.error = str(e)
            self.finished.emit(error_result)


class Auto_GCP_Solver_Controller:
    """Orchestrates automatic GCP feature matching using computer vision.

    Args:
        gcp_processor:    ``GCP_Processor`` — source of manual GCPs and
                          destination for auto-matched GCPs.
        test_viewer:      ``Test_Image_Viewer`` — provides raw image data.
        reference_viewer: ``Leaflet_Reference_Viewer`` — provides the
                          reference basemap for chip fetching.
        sidebar:          ``Tabbed_Sidebar`` — access to the auto GCP solver panel.
        status_bar:       ``QStatusBar`` — user-facing status messages.
    """

    def __init__(self, gcp_processor, test_viewer, reference_viewer,
                 sidebar, status_bar):
        self.gcp_processor = gcp_processor
        self.test_viewer = test_viewer
        self.reference_viewer = reference_viewer
        self.status_bar = status_bar

        # Get the auto GCP solver panel from sidebar
        self.panel = sidebar.get_auto_gcp_solver_panel()
        self.panel.run_requested.connect(self._on_run_requested)

        self.worker = None

    def _on_run_requested(self, settings: Auto_Match_Settings):
        """Handle run request from the auto GCP solver panel."""
        logging.info("Auto GCP Solver run requested")

        # Validate preconditions
        if not self._validate_preconditions():
            return

        # Get image data
        test_image = self.test_viewer.get_current_image_data()
        if test_image is None:
            self.status_bar.showMessage("Error: No test image loaded", 5000)
            return

        ref_chip, geo_transform = self.reference_viewer.get_current_chip()
        if ref_chip is None:
            self.status_bar.showMessage("Error: No reference chip available", 5000)
            return

        # Update UI
        self.panel.clear_results()
        self.status_bar.showMessage("Running Auto GCP Solver...")
        self.panel.setEnabled(False)

        # Start worker thread
        self.worker = Auto_GCP_Solver_Worker(settings, test_image, ref_chip, geo_transform)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _validate_preconditions(self) -> bool:
        """Validate that all required data is available."""
        if self.test_viewer.get_current_image_data() is None:
            self.status_bar.showMessage("Error: No test image loaded", 5000)
            return False

        if self.reference_viewer.get_current_chip()[0] is None:
            self.status_bar.showMessage("Error: No reference chip available", 5000)
            return False

        return True

    def _on_worker_finished(self, result: Match_Result):
        """Handle completion of the auto GCP solver worker."""
        self.panel.setEnabled(True)

        if result.success:
            # Update results panel
            candidates = len(result.candidate_pixels) if result.candidate_pixels is not None else 0
            coverage = self._calculate_coverage(result)
            rmse = self._calculate_rmse(result)

            # Convert results to table format
            rows = []
            if result.candidate_pixels is not None and result.candidate_geos is not None:
                for i, (px, geo) in enumerate(zip(result.candidate_pixels, result.candidate_geos)):
                    rows.append([i + 1, f"{px[0]:.1f}", f"{px[1]:.1f}", f"{geo[0]:.6f}", f"{geo[1]:.6f}"])

            self.panel.update_results(candidates, result.n_inliers, coverage, rmse, rows)

            # Add GCPs to processor if we have good results
            if result.n_inliers >= 4:
                self._add_gcps_to_processor(result)
                self.status_bar.showMessage(f"Auto GCP Solver completed: {result.n_inliers} GCPs added", 3000)
            else:
                self.status_bar.showMessage(f"Auto GCP Solver completed: Too few inliers ({result.n_inliers})", 3000)
        else:
            self.status_bar.showMessage(f"Auto GCP Solver failed: {result.error}", 5000)

        self.worker = None

    def _calculate_coverage(self, result: Match_Result) -> float:
        """Calculate the percentage coverage of matched points."""
        if result.candidate_pixels is None or len(result.candidate_pixels) == 0:
            return 0.0

        # Simple coverage based on bounding box
        px_coords = result.candidate_pixels
        x_range = px_coords[:, 0].max() - px_coords[:, 0].min()
        y_range = px_coords[:, 1].max() - px_coords[:, 1].min()

        # Get image dimensions (assuming test image)
        if hasattr(self, '_test_image_shape'):
            img_area = self._test_image_shape[0] * self._test_image_shape[1]
            match_area = x_range * y_range
            return (match_area / img_area) * 100 if img_area > 0 else 0.0

        return 0.0

    def _calculate_rmse(self, result: Match_Result) -> float:
        """Calculate RMSE for the matched points."""
        # This is a placeholder - actual RMSE calculation would depend on
        # the specific requirements and available data
        return 0.0

    def _add_gcps_to_processor(self, result: Match_Result):
        """Add the matched GCPs to the GCP processor."""
        if result.candidate_pixels is None or result.candidate_geos is None:
            return

        from pointy.core.gcp import GCP

        for px, geo in zip(result.candidate_pixels, result.candidate_geos):
            gcp = GCP(
                pixel_x=px[0],
                pixel_y=px[1],
                lon=geo[0],
                lat=geo[1],
                source="auto_gcp_solver"
            )
            self.gcp_processor.add_gcp(gcp)
