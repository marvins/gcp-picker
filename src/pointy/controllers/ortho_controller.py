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
#    File:    ortho_controller.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Orthorectification controller.

Owns model fitting, image warping, projector lifecycle, and the
raw/ortho view mode toggle.
"""

# Python Standard Libraries
import logging

# Third-Party Libraries
import cv2
import numpy as np
from pyproj import Transformer as Proj_Transformer
from qtpy.QtWidgets import QMessageBox

# Project Libraries
from tmns.geo.coord import Geographic
from tmns.geo.coord.crs import CRS
from tmns.geo.proj import Transformation_Type
from tmns.geo.proj.factory import create_projector
from pointy.core.transformation import fit_transformation_model, warp_image
from pointy.core.ortho_model_persistence import save_ortho_model, sidecar_exists, load_ortho_model, apply_model_to_projector, get_sidecar_path
from pointy.sidebar.components.tools_panel import Output_Projection


class Ortho_Controller:
    """Manages model fitting, orthorectification warping, and view mode.

    Args:
        gcp_processor:    GCP_Processor instance.
        test_viewer:      Test_Image_Viewer instance.
        reference_viewer: Leaflet_Reference_Viewer instance.
        sidebar:          Tabbed_Sidebar instance (for tools/status panels).
        ortho_action:     QAction for the ortho toggle (toolbar checkbox).
        status_bar:       QStatusBar for user feedback.
        parent_widget:    Parent QWidget for dialogs.
    """

    def __init__(self, gcp_processor, test_viewer, reference_viewer,
                 sidebar, ortho_action, status_bar, parent_widget):
        self._gcp_proc  = gcp_processor
        self._test      = test_viewer
        self._ref       = reference_viewer
        self._sidebar   = sidebar
        self._ortho_act = ortho_action
        self._status    = status_bar
        self._parent    = parent_widget

    def connect(self):
        """Wire all signals managed by this controller."""
        tools_panel = self._sidebar.get_tools_panel()
        tools_panel.fit_requested.connect(self.on_fit_requested)
        tools_panel.sidecar_delete_requested.connect(self.on_delete_sidecar)
        self._test.view_mode_changed.connect(self.on_view_mode_changed)

    # ------------------------------------------------------------------
    # Model fitting
    # ------------------------------------------------------------------

    def on_fit_requested(self, model_name: str):
        """Fit the selected model to current GCPs and display residuals."""
        gcps = self._gcp_proc.get_gcps()
        min_gcps = 9 if model_name.lower() == 'rpc' else 3
        if len(gcps) < min_gcps:
            self._status.showMessage(
                f'Need at least {min_gcps} GCPs for {model_name} (have {len(gcps)})'
            )
            return

        tools_panel = self._sidebar.get_tools_panel()
        status_panel = self._sidebar.get_transformation_status_panel()

        try:
            self._status.showMessage(f'Fitting {model_name} model...')

            model_type = Transformation_Type(model_name.lower())
            projector, residuals_info = fit_transformation_model(gcps, model_type)
            self._set_projector(projector)

            tools_panel.update_fit_results(residuals_info['rmse'], residuals_info['gcps'])
            status_panel.update_transform_status(f'{model_name} model fitted', residuals_info['rmse'])
            self._status.showMessage(f'{model_name} fit complete — RMSE: {residuals_info["rmse"]:.3f} px')

            # Save model to sidecar file
            image_path = self._test.get_image_path()
            if image_path:
                try:
                    # Compute warp extent
                    extent = projector.warp_extent(self._test.get_image_data().shape[1], self._test.get_image_data().shape[0])

                    # Get output CRS from tools panel
                    panel_out_proj = tools_panel.get_output_projection()
                    if panel_out_proj == Output_Projection.WGS84:
                        output_crs = CRS.wgs84_geographic()
                    else:
                        # Compute UTM zone from extent centroid
                        cx = (extent.min_point.longitude_deg + extent.max_point.longitude_deg) / 2
                        zone = int((cx + 180) / 6) + 1
                        hemisphere = 'N' if extent.min_point.latitude_deg >= 0 else 'S'
                        output_crs = CRS.utm_zone(zone, hemisphere)

                    gcp_ids = [g.id for g in gcps]
                    img_shape = self._test.get_image_data().shape
                    save_ortho_model(image_path, model_type, projector, extent, output_crs, gcp_ids,
                                     image_size=(img_shape[1], img_shape[0]))
                    tools_panel.set_sidecar_status(True, model_type.value, replaced=True)
                    self._status.showMessage(f'{model_name} fit complete — RMSE: {residuals_info["rmse"]:.3f} px (saved)')
                except Exception as e:
                    logging.warning(f'Failed to save ortho model sidecar: {e}')
                    tools_panel.set_sidecar_status(False)
                    self._status.showMessage(f'{model_name} fit complete — RMSE: {residuals_info["rmse"]:.3f} px (sidecar save failed)')

            if self._test.ortho_btn.isChecked():
                self.perform_orthorectification()

        except Exception as e:
            logging.error(f'Fit failed: {e}')
            tools_panel.clear_fit_results()
            status_panel.update_transform_status('Fit failed')
            tools_panel.set_sidecar_status(False)
            self._status.showMessage(f'Fit failed: {e}')

    def on_delete_sidecar(self):
        """Delete the ortho model sidecar file and clear the projector."""
        image_path = self._test.get_image_path()
        if not image_path:
            return

        sidecar_path = get_sidecar_path(image_path)
        if not sidecar_path.exists():
            return

        try:
            sidecar_path.unlink()
            logging.info(f'Deleted ortho model sidecar: {sidecar_path}')

            # Clear projector
            self._set_projector(None)

            # Update UI
            tools_panel = self._sidebar.get_tools_panel()
            status_panel = self._sidebar.get_transformation_status_panel()
            tools_panel.clear_fit_results()
            status_panel.update_transform_status('No model fitted', None)
            tools_panel.set_sidecar_status(False)
            self._status.showMessage('Sidecar deleted - model cleared')

        except Exception as e:
            logging.error(f'Failed to delete sidecar: {e}', exc_info=True)
            self._status.showMessage(f'Failed to delete sidecar: {e}')

    # ------------------------------------------------------------------
    # View mode toggle
    # ------------------------------------------------------------------

    def on_view_mode_changed(self, ortho_mode: bool):
        """Switch the test viewer between raw and orthorectified rendering."""
        if ortho_mode:
            self.perform_orthorectification()
        else:
            self._test.reload_raw_image()
            self._ref.clear_image_boundary()

    # ------------------------------------------------------------------
    # Warp
    # ------------------------------------------------------------------

    def perform_orthorectification(self):
        """Warp the source image using the current projector and display the result."""
        if not self._test.has_image():
            return

        gcps = self._gcp_proc.get_gcps()
        if len(gcps) < 3:
            self._status.showMessage('Need at least 3 GCPs for orthorectification')
            return

        projector = self._gcp_proc.get_projector()
        if projector is None or projector.is_identity:
            self._status.showMessage('No model fitted — fit a model in the Ortho tab first')
            return

        try:
            model_name = projector.transformation_type.value.upper()
            self._status.showMessage(f'Warping image ({model_name} model)...')

            src = self._test.get_image_data()
            if src is None:
                self._status.showMessage('No image data available')
                return

            tools_panel = self._sidebar.get_tools_panel()
            panel_out_proj = tools_panel.get_output_projection()

            # Compute CRS based on panel selection
            if panel_out_proj == Output_Projection.WGS84:
                output_crs = CRS.wgs84_geographic()
            else:
                # Compute UTM zone from extent centroid
                extent = projector.warp_extent(src.shape[1], src.shape[0])
                cx = (extent.min_point.longitude_deg + extent.max_point.longitude_deg) / 2
                zone = int((cx + 180) / 6) + 1
                hemisphere = 'N' if extent.min_point.latitude_deg >= 0 else 'S'
                output_crs = CRS.utm_zone(zone, hemisphere)

            warped, extent = warp_image(src, projector, output_crs)

            self._test.display_warped_array(warped, warp_extent=extent)
            self._ref.set_image_boundary([(g.latitude_deg, g.longitude_deg) for g in extent.corners])
            self._status.showMessage(f'Orthorectification complete ({model_name}, {warped.shape[1]}x{warped.shape[0]}px)')

        except Exception as e:
            logging.error(f'Orthorectification warp failed: {e}', exc_info=True)
            self._status.showMessage(f'Warp failed: {e}')

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_projector(self, projector):
        """Push projector to all dependents."""
        self._gcp_proc.set_projector(projector)
        self._test.set_projector(projector)
        self._test.set_ortho_available(projector is not None)

    def check_and_load_sidecar(self, image_path: str):
        """Check for and load ortho model sidecar for the current image.

        Args:
            image_path: Path to the current image.
        """
        tools_panel = self._sidebar.get_tools_panel()
        status_panel = self._sidebar.get_transformation_status_panel()

        if not sidecar_exists(image_path):
            tools_panel.set_sidecar_status(False)
            return

        try:
            sidecar = load_ortho_model(Path(image_path))
            if sidecar is None:
                tools_panel.set_sidecar_status(False)
                return

            # Verify GCP IDs match (optional - could allow partial matches)
            current_gcp_ids = set(g.id for g in self._gcp_proc.get_gcps())
            sidecar_gcp_ids = set(sidecar.metadata.gcp_ids)

            if not current_gcp_ids.issuperset(sidecar_gcp_ids):
                logging.warning(f'Sidecar GCP IDs {sidecar_gcp_ids} not all present in current GCPs {current_gcp_ids}')
                tools_panel.set_sidecar_status(False)
                return

            # Create appropriate projector type using factory
            model_type = Transformation_Type(sidecar.metadata.model_type)
            projector = create_projector(model_type)

            # Apply model data to projector
            apply_model_to_projector(projector, sidecar.model_data, sidecar.metadata.model_type)

            # Set the projector
            self._set_projector(projector)

            # Update UI to show model is available
            tools_panel.update_fit_results(None, [])  # Clear residuals since we don't have them
            status_panel.update_transform_status(f'{model_type.value.capitalize()} model loaded (sidecar)', None)
            tools_panel.set_sidecar_status(True, model_type.value)

            logging.info(f'Loaded ortho model from sidecar for {image_path}')

        except Exception as e:
            logging.error(f'Failed to load ortho model sidecar: {e}', exc_info=True)
            tools_panel.set_sidecar_status(False)
