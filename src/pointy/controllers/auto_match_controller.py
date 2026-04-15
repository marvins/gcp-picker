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
#    File:    auto_match_controller.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Auto-Match Controller — orchestrates the automatic GCP matching pipeline.

Phase 0: UI shell only.  The controller wires the panel signal and validates
pre-conditions, but the matching logic itself is not yet implemented.
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
from pointy.core.match.pipeline import Auto_Matcher
from pointy.core.match.types import Match_Result


class Auto_Match_Controller:
    """Orchestrates automatic GCP feature matching.

    Args:
        gcp_processor:    ``GCP_Processor`` — source of manual GCPs and
                          destination for auto-matched GCPs.
        test_viewer:      ``Test_Image_Viewer`` — provides raw image data.
        reference_viewer: ``Leaflet_Reference_Viewer`` — provides the
                          reference basemap for chip fetching.
        sidebar:          ``Tabbed_Sidebar`` — access to the auto-match panel.
        status_bar:       ``QStatusBar`` — user-facing status messages.
    """

    def __init__(self, gcp_processor, test_viewer, reference_viewer,
                 sidebar, status_bar):
        self._gcp_proc  = gcp_processor
        self._test      = test_viewer
        self._ref       = reference_viewer
        self._sidebar   = sidebar
        self._status    = status_bar
        self._worker: Auto_Match_Worker | None = None

    def connect(self):
        """Wire signals from the Auto Match panel."""
        panel = self._sidebar.get_auto_match_panel()
        panel.run_requested.connect(self.on_run_requested)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def on_run_requested(self, settings: Auto_Match_Settings):
        """Handle "Run Auto-Match" button press.

        Validates pre-conditions and launches the matching pipeline on a
        background worker thread.  The button is disabled during execution
        and progress updates are shown.

        Args:
            settings: Current ``Auto_Match_Settings`` from the panel.
        """
        try:
            t_start = time.perf_counter()
            logging.debug('[AUTO-MATCH] on_run_requested: entered')

            panel = self._sidebar.get_auto_match_panel()
            panel.clear_results()
            logging.debug(f'[AUTO-MATCH] panel.clear_results: {time.perf_counter()-t_start:.3f}s')

            if self._test.is_loading:
                self._status.showMessage('Auto-Match: image is still loading, please wait')
                panel.set_run_button_enabled(True)
                return

            if not self._test.has_image():
                self._status.showMessage('Auto-Match: no image loaded')
                return

            t1 = time.perf_counter()
            image_path = self._test.get_image_path()
            logging.debug(f'[AUTO-MATCH] get_image_path: {time.perf_counter()-t1:.3f}s')
            if not image_path:
                self._status.showMessage('Auto-Match: image path unavailable')
                return

            t2 = time.perf_counter()
            manual_gcps = self._gcp_proc.get_gcps() if settings.use_manual_prior else []
            logging.debug(f'[AUTO-MATCH] get_gcps ({len(manual_gcps)} gcps): {time.perf_counter()-t2:.3f}s')

            logging.info(f'Auto-Match requested: {settings.to_log_string()} | gcps={len(manual_gcps)}')

            test_image = self._test.get_image_array()
            if test_image is None:
                self._status.showMessage('Auto-Match: image data unavailable')
                return

            # Disable button while we wait for the chip grab and run
            panel.set_run_button_enabled(False)
            panel.set_progress_visible(True)
            panel.set_progress(5, 'Grabbing reference chip...')
            logging.debug(f'[AUTO-MATCH] total pre-launch: {time.perf_counter()-t_start:.3f}s')

            def _launch_worker(ref_chip, ref_xform):
                if ref_chip is None or ref_xform is None:
                    self._status.showMessage('Auto-Match: failed to capture reference chip')
                    panel.set_run_button_enabled(True)
                    panel.set_progress_visible(False)
                    return

                logging.info(f'[AUTO-MATCH] ref chip: {ref_chip.shape}, launching worker')
                panel.set_progress(10, 'Extracting features...')

                self._worker = Auto_Match_Worker(settings, test_image, ref_chip, ref_xform)
                self._worker.stage_started.connect(lambda s: panel.set_progress(20, s))
                self._worker.progress.connect(panel.set_progress)
                self._worker.finished.connect(self._on_match_finished)
                self._worker.error.connect(self._on_match_error)
                self._worker.start()

            self._ref.grab_ref_chip(_launch_worker)
            logging.debug(f'[AUTO-MATCH] grab_ref_chip dispatched in {time.perf_counter()-t_start:.3f}s')

        except Exception as exc:
            logging.exception("Auto-Match failed with unhandled exception")
            self._status.showMessage(f'Auto-Match error: {exc}')
            # Re-enable button on error
            try:
                panel = self._sidebar.get_auto_match_panel()
                panel.set_run_button_enabled(True)
                panel.set_progress_visible(False)
            except Exception:
                pass

    def _on_match_finished(self, result: Match_Result):
        """Handle worker completion.

        Args:
            result: The ``Match_Result`` from the pipeline.
        """
        panel = self._sidebar.get_auto_match_panel()
        panel.set_run_button_enabled(True)
        panel.set_progress_visible(False)

        if result.error:
            self._status.showMessage(f'Auto-Match failed: {result.error}')
            return

        n_cands = len(result.candidate_pixels)

        # Populate results panel
        candidate_rows = [
            (float(result.candidate_pixels[i, 0]),
             float(result.candidate_pixels[i, 1]),
             float(result.candidate_geos[i, 0]),
             float(result.candidate_geos[i, 1]))
            for i in range(n_cands)
        ]
        panel.update_results(
            candidates  = result.n_raw_matches,
            inliers     = result.n_inliers,
            coverage    = None,
            rmse        = None,
            candidate_rows = candidate_rows,
        )

        # Draw candidate markers on the test image viewer
        marker_pts = [(float(result.candidate_pixels[i, 0]),
                       float(result.candidate_pixels[i, 1]))
                      for i in range(n_cands)]
        self._test.set_candidate_markers(marker_pts)

        self._status.showMessage(
            f'Auto-Match complete: {n_cands} candidates '
            f'({result.n_inliers} inliers) in {result.elapsed_sec:.1f}s'
        )

    def _on_match_error(self, error_msg: str):
        """Handle worker error.

        Args:
            error_msg: The error message from the worker thread.
        """
        panel = self._sidebar.get_auto_match_panel()
        panel.set_run_button_enabled(True)
        panel.set_progress_visible(False)
        self._status.showMessage(f'Auto-Match error: {error_msg}')
        logging.error(f'Auto-Match worker error: {error_msg}')


class Auto_Match_Worker(QThread):
    """Background worker thread for auto-match pipeline execution.

    Signals:
        stage_started(str):   Emitted when a stage starts (e.g., "Extracting features")
        stage_finished(str):  Emitted when a stage finishes
        progress(int):        Progress percentage 0-100
        finished(Match_Result): Emitted with the result when complete
        error(str):           Emitted if an exception occurs
    """

    stage_started  = Signal(str)
    stage_finished = Signal(str)
    progress       = Signal(int)
    finished       = Signal(object)
    error          = Signal(str)

    def __init__(self, settings: Auto_Match_Settings,
                 test_image: np.ndarray,
                 ref_chip: np.ndarray,
                 ref_geo_transform: Callable[[float, float], tuple[float, float]]):
        super().__init__()
        self._settings  = settings
        self._test_img  = test_image
        self._ref_chip  = ref_chip
        self._ref_xform = ref_geo_transform

    def run(self):
        """Execute the auto-match pipeline in the background."""
        try:
            self.stage_started.emit("Initializing matcher")
            matcher = Auto_Matcher(self._settings)
            self.progress.emit(10)
            self.stage_finished.emit("Initializing matcher")

            self.stage_started.emit("Extracting features")
            self.progress.emit(20)
            result = matcher.run(self._test_img, self._ref_chip, self._ref_xform)
            self.progress.emit(100)
            self.stage_finished.emit("Extracting features")

            self.finished.emit(result)
        except Exception as exc:
            logging.exception("Auto_Match_Worker failed")
            self.error.emit(str(exc))
