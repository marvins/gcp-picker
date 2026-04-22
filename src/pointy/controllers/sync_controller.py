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
#    File:    sync_controller.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Viewer synchronisation controller.

Owns all logic for keeping the test image viewer and the reference map
viewer in sync — update-button panning, GCP navigation, and zoom
translation between the two coordinate spaces.
"""

# Python Standard Libraries
import math

# Project Libraries
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.constants import EARTH_CIRCUMFERENCE_M


class Sync_Controller:
    """Synchronises the test image viewer and the Leaflet reference viewer.

    Args:
        test_viewer:       Test_Image_Viewer instance.
        reference_viewer:  Leaflet_Reference_Viewer instance.
        gcp_processor:     GCP_Processor instance (provides projector + GCP lookup).
        status_bar:        QStatusBar for user feedback.
    """

    def __init__(self, test_viewer, reference_viewer, gcp_processor, status_bar):
        self._test = test_viewer
        self._ref = reference_viewer
        self._gcp_proc = gcp_processor
        self._status = status_bar

    def connect(self):
        """Wire all signals managed by this controller."""
        self._test.update_requested.connect(self.on_test_update_requested)
        self._ref.update_requested.connect(self.on_reference_update_requested)

    # ------------------------------------------------------------------
    # Update-button handlers
    # ------------------------------------------------------------------

    def on_test_update_requested(self):
        """Pan the test viewer to match the reference map's geographic center."""
        self._ref.bridge.center_reported.connect(self._apply_ref_center_to_test)
        self._ref.request_center()

    def on_reference_update_requested(self):
        """Pan+zoom the reference map to match the test viewer's current geographic center."""
        center_tuple = self._test.image_view.get_view_center_pixel()
        if center_tuple is None:
            return

        cx, cy = center_tuple
        geo = self._test_pixel_to_geo(cx, cy)
        if geo is None:
            return

        zoom = self._leaflet_zoom_from_test_zoom(self._test.image_view.get_zoom())
        self._ref.recreate_map_with_center(geo, zoom=zoom)

    def _apply_ref_center_to_test(self, lat: float, lon: float, zoom: float):
        """Scroll+zoom the test viewer to match the reported map center and Leaflet zoom."""
        if self._test.is_orthorectified:
            result = self._test.geo_to_ortho_pixel(lat, lon)
            if result is None:
                return
            px, py = result
        else:
            projector = self._gcp_proc.get_projector()
            if projector is None or projector.is_identity:
                self._status.showMessage('No model fitted — fit a model in the Ortho tab first')
                return
            src_px = projector.world_to_pixel(Geographic.create(lat, lon))
            px, py = src_px.x_px, src_px.y_px

        self._test.image_view.centerOn(px, py)
        px_zoom = self._test_zoom_from_leaflet_zoom(zoom)
        if px_zoom is not None:
            self._test.image_view.set_zoom(px_zoom)
        self._status.showMessage(f'Test view centered on ({lat:.4f}, {lon:.4f})')

    # ------------------------------------------------------------------
    # GCP navigation (double-click in GCP manager)
    # ------------------------------------------------------------------

    def on_gcp_navigate(self, gcp_id: int):
        """Center both viewers on the GCP's location."""
        gcp = self._gcp_proc.get_gcp(gcp_id)
        if gcp is None:
            return

        self._test.image_view.set_zoom(1.0)
        self._test.image_view.centerOn(gcp.pixel.x_px, gcp.pixel.y_px)
        self._ref.recreate_map_with_center(gcp.geographic, zoom=17)
        self._status.showMessage(
            f'Navigated to GCP {gcp_id} — '
            f'pixel ({gcp.pixel.x_px:.0f}, {gcp.pixel.y_px:.0f}), '
            f'geo ({gcp.geographic.latitude_deg:.6f}, {gcp.geographic.longitude_deg:.6f})'
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _test_pixel_to_geo(self, cx: float, cy: float) -> Geographic | None:
        """Convert a test-viewer pixel to a Geographic coordinate.

        Handles both raw and orthorectified view modes.
        """
        if self._test.is_orthorectified:
            result = self._test.ortho_pixel_to_geo(cx, cy)
            if result is None:
                return None
            lat, lon = result
            return Geographic.create(lat, lon)

        projector = self._gcp_proc.get_projector()
        if projector is None or projector.is_identity:
            self._status.showMessage('No model fitted — fit a model in the Ortho tab first')
            return None
        return projector.pixel_to_world(Pixel.create(cx, cy))

    def _leaflet_zoom_from_test_zoom(self, pixel_zoom: float) -> int:
        """Estimate Leaflet zoom level from test viewer pixel zoom and projector GSD."""
        try:
            gsd = self._test.geo_scale_at_center()
            if gsd is None:
                return 12
            meters_per_screen_px = gsd / pixel_zoom
            leaflet_zoom = math.log2(EARTH_CIRCUMFERENCE_M / (meters_per_screen_px * 256))
            return max(1, min(20, round(leaflet_zoom)))
        except Exception:
            return 12

    def _test_zoom_from_leaflet_zoom(self, leaflet_zoom: float) -> float | None:
        """Estimate test viewer pixel zoom factor from Leaflet zoom level and projector GSD."""
        try:
            gsd = self._test.geo_scale_at_center()
            if gsd is None:
                return None
            meters_per_screen_px = EARTH_CIRCUMFERENCE_M / (256 * (2 ** leaflet_zoom))
            return gsd / meters_per_screen_px
        except Exception:
            return None
