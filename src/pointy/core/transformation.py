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
#    File:    transformation.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Pure functions for transformation model fitting and image warping.

This module provides Qt-independent functions for fitting transformation models
(Affine, TPS, RPC) to Ground Control Points (GCPs) and warping images using
these models. The functions are designed for use by both GUI applications and
CLI tools.

Key functionality:

- **fit_transformation_model**: Fit a transformation model to GCPs and compute
  residual errors. Supports Affine (3+ GCPs), TPS (3+ GCPs), and RPC (9+ GCPs).

- **warp_image**: Warp an image using a fitted projector to a specified output
  coordinate reference system (CRS). Supports WGS84 geographic and UTM projections.

Typical workflow:

1. Collect GCPs with test_pixel and geographic coordinates
2. Fit a transformation model using fit_transformation_model()
3. Warp the image using warp_image() with the fitted projector
4. Evaluate residuals to assess model quality

Example::

    from pointy.core.transformation import fit_transformation_model, warp_image
    from tmns.geo.proj import Transformation_Type
    from tmns.geo.coord.crs import CRS
    import numpy as np

    # Fit a TPS model to GCPs
    projector, residuals = fit_transformation_model(
        gcps=my_gcps,
        model_type=Transformation_Type.TPS
    )

    print(f'Overall RMSE: {residuals["rmse"]:.2f} pixels')

    # Warp the image to UTM zone 11N
    src_image = np.array(...)  # H x W x C
    warped, extent = warp_image(
        src_image=src_image,
        projector=projector,
        output_crs=CRS.utm_zone(11, 'N'),
        gsd=1.0  # 1 meter ground sample distance
    )

    print(f'Warped image size: {warped.shape}')
    print(f'Geographic bounds: {extent.min_point} to {extent.max_point}')

Performance considerations:

- Affine: Fast, suitable for linear distortions (rotation, scale, shear)
- TPS: Slower, suitable for non-linear sensor distortions (uses sparse grid interpolation)
- RPC: Moderate speed, suitable for satellite imagery with RPC coefficients

For large images (>10K pixels), TPS and RPC warping may take several seconds due to
per-pixel coordinate transformations.
"""

import logging
import time
from typing import List, NamedTuple, Tuple

import cv2
import numpy as np
import pyproj
from scipy.interpolate import LinearNDInterpolator

from tmns.geo.coord import Geographic, Pixel, UTM
from tmns.geo.coord.crs import CRS
from tmns.geo.coord.transformer import Transformer
from tmns.geo.proj import Affine, Projector_Union, TPS, RPC, Transformation_Type, Warp_Extent


class GCP_Residual(NamedTuple):
    """Residual information for a single Ground Control Point.

    This NamedTuple stores the residual error between the predicted pixel
    coordinates (from the fitted transformation model) and the actual test
    pixel coordinates for a GCP, along with full coordinate context for
    reuse in analysis, visualization, and quality control workflows.

    Attributes:
        gcp_id: Unique identifier for the GCP.
        actual_pixel: Actual test pixel coordinates from the GCP.
        predicted_pixel: Predicted pixel coordinates from the transformation.
        geographic: Geographic coordinates (for reference and reprojection).
        dx_px: X-direction pixel error (predicted_x - actual_x) in pixels.
            Positive values indicate the predicted point is to the right of
            the actual point.
        dy_px: Y-direction pixel error (predicted_y - actual_y) in pixels.
            Positive values indicate the predicted point is below the actual
            point (image coordinate system).
        rms_px: Root-mean-square error in pixels, computed as sqrt(dx^2 + dy^2).
            This is the total distance between predicted and actual points.

    Example::

        from tmns.geo.coord import Pixel, Geographic
        from pointy.core.transformation import GCP_Residual

        residual = GCP_Residual(
            gcp_id=1,
            actual_pixel=Pixel(100.0, 200.0),
            predicted_pixel=Pixel(102.5, 198.7),
            geographic=Geographic(35.5, -117.5, 100.0),
            dx_px=2.5,
            dy_px=-1.3,
            rms_px=2.82
        )
        print(f'GCP {residual.gcp_id} error: {residual.rms_px:.2f} pixels')

        # Can access full coordinate objects for analysis
        print(f'Actual pixel: {residual.actual_pixel}')
        print(f'Geographic: {residual.geographic}')
    """
    gcp_id: int
    actual_pixel: Pixel
    predicted_pixel: Pixel
    geographic: Geographic
    dx_px: float
    dy_px: float
    rms_px: float


def fit_transformation_model(
    gcps: List,
    model_type: Transformation_Type
) -> Tuple[Projector_Union, dict]:
    """Fit a transformation model to Ground Control Points.

    This function fits a transformation model (Affine, TPS, or RPC) to a set
    of GCPs and computes residual errors for each GCP to assess model quality.

    Args:
        gcps: List of GCP objects with test_pixel and geographic attributes.
            Each GCP must have:
            - test_pixel: Pixel coordinates in the source image (Pixel object)
            - geographic: Geographic coordinates (Geographic object)
            Minimum required GCPs:
            - Affine: 3 GCPs (for 6 DOF transformation)
            - TPS: 3 GCPs (minimum for TPS interpolation)
            - RPC: 9 GCPs (for polynomial coefficient fitting)
        model_type: Type of transformation to fit. Must be one of:
            - Transformation_Type.AFFINE: Linear transformation (rotation, scale, shear, translation)
            - Transformation_Type.TPS: Thin-Plate Spline for non-linear distortions
            - Transformation_Type.RPC: Rational Polynomial Coefficients for satellite imagery

    Returns:
        Tuple of (projector, residuals_info):
        - projector: Fitted projector object (Affine, TPS, or RPC instance).
            Can be used with warp_image() for image warping.
        - residuals_info: Dictionary with residual information:
            {
                'gcps': [GCP_Residual(...), ...],  # List of GCP_Residual objects
                'rmse': float  # Overall RMSE in pixels across all GCPs
            }

    Raises:
        ValueError: If insufficient GCPs for the requested model type.
        ValueError: If unknown model type is specified.

    Example::

        from tmns.geo.proj import Transformation_Type
        from pointy.core.transformation import fit_transformation_model

        # Fit a TPS model
        projector, residuals = fit_transformation_model(
            gcps=my_gcps,
            model_type=Transformation_Type.TPS
        )

        # Check overall RMSE
        print(f'Overall RMSE: {residuals["rmse"]:.2f} pixels')

        # Check individual GCP residuals
        for residual in residuals['gcps']:
            if residual.rms_px > 10.0:
                print(f'GCP {residual.gcp_id} has high error: {residual.rms_px:.2f}px')
                print(f'  Actual: {residual.actual_pixel}')
                print(f'  Predicted: {residual.predicted_pixel}')
                print(f'  Geographic: {residual.geographic}')
    """
    min_gcps = 9 if model_type == Transformation_Type.RPC else 3
    if len(gcps) < min_gcps:
        raise ValueError(f'Need at least {min_gcps} GCPs for {model_type.value} (have {len(gcps)})')

    model_map = {
        Transformation_Type.AFFINE: Affine,
        Transformation_Type.TPS:    TPS,
        Transformation_Type.RPC:    RPC,
    }

    projector_cls = model_map.get(model_type)
    if projector_cls is None:
        raise ValueError(f'Unknown model: {model_type}')

    projector = projector_cls()
    control_points = [(gcp.test_pixel, gcp.geographic) for gcp in gcps]
    projector.solve_from_gcps(control_points)

    # Calculate residuals
    residuals = []
    sq_errors = []
    for gcp in gcps:
        pred = projector.geographic_to_source(gcp.geographic)
        rms = ((pred.x_px - gcp.test_pixel.x_px) ** 2 + (pred.y_px - gcp.test_pixel.y_px) ** 2) ** 0.5
        residuals.append(GCP_Residual(
            gcp_id=gcp.id,
            actual_pixel=gcp.test_pixel,
            predicted_pixel=pred,
            geographic=gcp.geographic,
            dx_px=pred.x_px - gcp.test_pixel.x_px,
            dy_px=pred.y_px - gcp.test_pixel.y_px,
            rms_px=rms
        ))
        sq_errors.append(rms ** 2)

    overall_rmse = (sum(sq_errors) / len(sq_errors)) ** 0.5 if sq_errors else 0.0

    return projector, {
        'gcps': residuals,
        'rmse': overall_rmse
    }


def warp_image(
    src_image: np.ndarray,
    projector: Projector_Union,
    output_crs: CRS,
    output_size: Tuple[int, int] | None = None,
    gsd: float | None = None
) -> Tuple[np.ndarray, Warp_Extent]:
    """Warp an image using a fitted transformation projector.

    This function warps a source image to a specified output coordinate reference
    system (CRS) using a fitted projector (Affine, TPS, or RPC). The warping
    uses OpenCV's remap function with linear interpolation.

    The function computes remap coordinates by:
    1. Creating an output grid in the target CRS (UTM or geographic)
    2. Converting grid coordinates to geographic (lat/lon)
    3. Using the projector's compute_remap_coordinates() to map geographic
       coordinates back to source image pixel coordinates
    4. Applying cv2.remap with the computed remap maps

    Args:
        src_image: Source image as numpy array (H x W x C). Can be grayscale (H x W)
            or color (H x W x 3 for RGB/BGR). Data type should be uint8 or float32.
        projector: Fitted projector object (Affine, TPS, or RPC). Must not be identity.
            Use fit_transformation_model() to create a fitted projector.
        output_crs: Output coordinate reference system. Supported types:
            - CRS.wgs84_geographic(): WGS84 latitude/longitude (degrees)
            - CRS.utm_zone(zone, hemisphere): UTM projection (meters)
            Example: CRS.utm_zone(11, 'N') for UTM zone 11 North.
        output_size: Optional output size as (width, height) in pixels.
            If None and gsd is provided, computes size from warp extent and GSD.
            If None and gsd is None, uses source image size.
        gsd: Ground sample distance in output CRS units.
            - For UTM: meters per pixel (e.g., 1.0 for 1m GSD)
            - For WGS84: degrees per pixel (e.g., 0.0001 for high resolution)
            If provided with output_size=None, computes output size from warp extent.

    Returns:
        Tuple of (warped_image, warp_extent):
        - warped_image: Warped image as numpy array with same data type as src_image.
            Shape is (out_h, out_w, C) or (out_h, out_w) for grayscale.
        - warp_extent: Warp_Extent NamedTuple with geographic bounds:
            - min_point: Geographic coordinate of output image top-left
            - max_point: Geographic coordinate of output image bottom-right
            - lon_min, lon_max: Longitude bounds in degrees
            - lat_min, lat_max: Latitude bounds in degrees

    Raises:
        ValueError: If projector.is_identity is True (no model fitted).

    Performance notes:
    - Affine: Fast (<1s for 10K x 10K image)
    - TPS: Moderate (~6s for 10K x 10K image with sparse grid optimization)
    - RPC: Moderate (~10-15s for 10K x 10K image with batch inverse transformation)

    Example::

        from tmns.geo.coord.crs import CRS
        from pointy.core.transformation import warp_image
        import numpy as np

        # Warp to UTM with 1m GSD
        warped, extent = warp_image(
            src_image=src_image,
            projector=projector,
            output_crs=CRS.utm_zone(11, 'N'),
            gsd=1.0
        )

        print(f'Output size: {warped.shape[1]}x{warped.shape[0]}')
        print(f'Bounds: {extent.min_point} to {extent.max_point}')

        # Warp to WGS84 with fixed output size
        warped, extent = warp_image(
            src_image=src_image,
            projector=projector,
            output_crs=CRS.wgs84_geographic(),
            output_size=(5000, 5000)
        )
    """
    if projector.is_identity:
        raise ValueError('Projector is identity, no model fitted')

    src_h, src_w = src_image.shape[:2]

    # Get warp extent first
    extent = projector.warp_extent(src_w, src_h)
    logging.debug(f'Warp extent: lon=[{extent.min_point.longitude_deg:.6f}, {extent.max_point.longitude_deg:.6f}], '
                  f'lat=[{extent.min_point.latitude_deg:.6f}, {extent.max_point.latitude_deg:.6f}]')

    # Compute output size from GSD if provided
    if output_size is None and gsd is not None:
        out_w, out_h = extent.compute_output_size(output_crs, gsd)
    elif output_size is None:
        # Default to source size
        out_w, out_h = src_w, src_h
    else:
        out_w, out_h = output_size

    model_name = projector.transformation_type.value.upper()
    logging.info(f'Warping image {src_w}x{src_h} -> {out_w}x{out_h} ({model_name} model, {output_crs})')

    # Create output grid based on CRS type
    _t0 = time.perf_counter()
    if output_crs.is_utm_zone():
        # UTM: create grid in UTM coordinates
        zone, hemisphere = output_crs.get_utm_zone_info()
        transformer = Transformer()
        utm_min = transformer.geo_to_utm(extent.min_point, zone=zone)
        utm_max = transformer.geo_to_utm(extent.max_point, zone=zone)
        x0, y0 = utm_min.easting_m, utm_min.northing_m
        x1, y1 = utm_max.easting_m, utm_max.northing_m
        x_grid = np.linspace(x0, x1, out_w)
        y_grid = np.linspace(y1, y0, out_h)
        x_mesh, y_mesh = np.meshgrid(x_grid, y_grid)

        # Convert UTM mesh back to geographic using vectorized pyproj
        _proj = pyproj.Transformer.from_crs(
            pyproj.CRS(output_crs.epsg_code), pyproj.CRS(4326), always_xy=True
        )
        lons_flat, lats_flat = _proj.transform(x_mesh.ravel(), y_mesh.ravel())
        lon_mesh = lons_flat.reshape(x_mesh.shape)
        lat_mesh = lats_flat.reshape(y_mesh.shape)
        logging.debug(f'UTM (EPSG:{output_crs.epsg_code}), x=[{x0:.1f}, {x1:.1f}] y=[{y0:.1f}, {y1:.1f}]')
        logging.debug(f'Grid + UTM->geo conversion: {time.perf_counter() - _t0:.2f}s')
    else:
        # Geographic (WGS84): create grid in lat/lon
        params = Geographic.compute_extent_params(extent.min_point, extent.max_point, (out_w, out_h))
        lon_grid = extent.min_point.longitude_deg + np.arange(out_w, dtype=np.float64) * params.step_x
        lat_grid = extent.max_point.latitude_deg - np.arange(out_h, dtype=np.float64) * params.step_y
        lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
        logging.debug(f'Geographic grid {out_w}x{out_h}, lon_step={params.step_x:.8f}, lat_step={params.step_y:.8f}')
        logging.debug(f'Grid creation: {time.perf_counter() - _t0:.2f}s')

    # Compute remap coordinates using projector-specific implementation
    _t1 = time.perf_counter()
    map_x, map_y = projector.compute_remap_coordinates(lon_mesh, lat_mesh, src_w, src_h)
    logging.debug(f'Remap coordinates: map_x=[{map_x.min():.1f}, {map_x.max():.1f}], '
                  f'map_y=[{map_y.min():.1f}, {map_y.max():.1f}]')
    logging.debug(f'Total remap coordinate computation: {time.perf_counter() - _t1:.2f}s')

    # Warp image
    _t2 = time.perf_counter()
    warped = cv2.remap(src_image, map_x, map_y,
                      interpolation=cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    logging.debug(f'cv2.remap: {time.perf_counter() - _t2:.2f}s')
    logging.info(f'Warp complete: output {warped.shape[1]}x{warped.shape[0]}')

    return warped, extent
