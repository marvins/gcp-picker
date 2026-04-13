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

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings


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

    def connect(self):
        """Wire signals from the Auto Match panel."""
        panel = self._sidebar.get_auto_match_panel()
        panel.run_requested.connect(self.on_run_requested)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def on_run_requested(self, settings: Auto_Match_Settings):
        """Handle "Run Auto-Match" button press.

        Phase 0: validates pre-conditions and logs the requested settings.
        Matching logic will be implemented in Phase 1.

        Args:
            settings: Current ``Auto_Match_Settings`` from the panel.
        """
        panel = self._sidebar.get_auto_match_panel()
        panel.clear_results()

        if not self._test.has_image():
            self._status.showMessage('Auto-Match: no image loaded')
            return

        image_path = self._test.get_image_path()
        if not image_path:
            self._status.showMessage('Auto-Match: image path unavailable')
            return

        manual_gcps = self._gcp_proc.get_gcps() if settings.use_manual_prior else []
        logging.info(
            f'Auto-Match requested: algo={settings.algo.value}, '
            f'max_features={settings.max_features}, '
            f'pyramid={settings.pyramid_level}, '
            f'clahe={settings.clahe}, '
            f'ratio={settings.ratio_test}, '
            f'matcher={settings.matcher.value}, '
            f'rejection={settings.rejection_method.value}, '
            f'threshold={settings.inlier_threshold} px, '
            f'manual_prior={settings.use_manual_prior} ({len(manual_gcps)} GCPs)'
        )

        self._status.showMessage(
            f'Auto-Match: pipeline not yet implemented '
            f'(algo={settings.algo.value.upper()}, '
            f'{len(manual_gcps)} manual GCPs as prior)'
        )
