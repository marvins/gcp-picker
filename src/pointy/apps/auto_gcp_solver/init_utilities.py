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
#    File:    init_utilities.py
#    Author:  Marvin Smith
#    Date:    04/19/2026
#
"""
Initialization utilities for auto-gcp-tester.
"""

import logging
from typing import Callable

import numpy as np
import rasterio
from rasterio.transform import from_bounds

from pointy.apps.auto_gcp_tester.config import Configuration
from pointy.apps.auto_gcp_tester.tile_capture import calculate_zoom_for_resolution, capture_tiles


def load_test_image(config: Configuration, logger: logging.Logger) -> np.ndarray:
    """Load the test image from the configuration.

    Args:
        config: Configuration object.
        logger: Logger instance.

    Returns:
        Test image array (H, W) or (H, W, C).

    Raises:
        Exception: If image loading fails.
    """
    logger.info("Loading test image...")
    try:
        with rasterio.open(config.test_image.path) as src:
            test_image = src.read()
            if test_image.ndim == 3:
                test_image = np.transpose(test_image, (1, 2, 0))
            logger.info(f"Test image shape: {test_image.shape}, dtype: {test_image.dtype}")
            return test_image
    except Exception as e:
        logger.error(f"Failed to load test image: {e}")
        raise


def load_reference_imagery(config: Configuration, logger: logging.Logger, ortho_model_bounds: dict | None = None) -> tuple[np.ndarray, dict, Callable | None]:
    """Load reference imagery from file or leaflet service.

    Args:
        config: Configuration object.
        logger: Logger instance.
        ortho_model_bounds: Optional ortho model bounds for leaflet capture.

    Returns:
        Tuple of (ref_chip, bounds, geo_transform_func). geo_transform_func is None for leaflet.
    """
    if config.reference.type == "file":
        return load_file_reference(config, logger)

    elif config.reference.type == "leaflet":
        logger.info(f"Capturing reference imagery from {config.reference.service}")

        # Prioritize bounds: Ortho model > GeoTIFF sidecar
        target_bounds = ortho_model_bounds or config.check_ortho_sidecar(config.test_image.path)

        # Load test image to calculate zoom
        test_image = load_test_image(config, logger)

        # Calculate appropriate zoom if bounds available
        if target_bounds:
            recommended_zoom = calculate_zoom_for_resolution(test_image.shape, config.reference.center['lat'], target_bounds)
            logger.info(f"Bounds detected: {target_bounds}")
            logger.info(f"Recommended zoom level: {recommended_zoom} (config: {config.reference.zoom})")
            zoom = recommended_zoom
        else:
            zoom = config.reference.zoom

        # Use bounds to expand tile grid for full coverage
        ref_chip, bounds = capture_tiles(
            service_name=config.reference.service,
            center_lat=config.reference.center['lat'],
            center_lon=config.reference.center['lon'],
            zoom=zoom,
            target_bounds=target_bounds
        )
        logger.info(f"Reference chip shape: {ref_chip.shape}, dtype: {ref_chip.dtype}")

        # Create geo transform from bounds
        def geo_transform(px_x: float, px_y: float) -> tuple[float, float]:
            lon = bounds["sw_lon"] + (px_x / ref_chip.shape[1]) * (bounds["ne_lon"] - bounds["sw_lon"])
            lat = bounds["ne_lat"] - (px_y / ref_chip.shape[0]) * (bounds["ne_lat"] - bounds["sw_lat"])
            return lon, lat

        return ref_chip, bounds, geo_transform

    else:
        raise ValueError(f"Unknown reference type: {config.reference.type}")


def load_file_reference(config: Configuration, logger: logging.Logger) -> tuple[np.ndarray, dict, Callable]:
    """Load reference imagery from a file.

    Args:
        config: Configuration object.
        logger: Logger instance.

    Returns:
        Tuple of (ref_chip, bounds, geo_transform_func).
    """
    logger.info(f"Loading reference image: {config.reference.file_path}")
    try:
        with rasterio.open(config.reference.file_path) as src:
            ref_chip = src.read()
            if ref_chip.ndim == 3:
                ref_chip = np.transpose(ref_chip, (1, 2, 0))
            logger.info(f"Reference chip shape: {ref_chip.shape}, dtype: {ref_chip.dtype}")

        # Create geo transform from bounds
        bounds = config.reference.bounds
        if bounds is None:
            bounds = config.auto_detect_bounds()
            if bounds:
                logger.info(f"Auto-detected bounds from image metadata: {bounds}")
            else:
                logger.error("Reference bounds required and could not be auto-detected")
                raise ValueError("Reference bounds required")

        def geo_transform(px_x: float, px_y: float) -> tuple[float, float]:
            lon = bounds["sw_lon"] + (px_x / ref_chip.shape[1]) * (bounds["ne_lon"] - bounds["sw_lon"])
            lat = bounds["ne_lat"] - (px_y / ref_chip.shape[0]) * (bounds["ne_lat"] - bounds["sw_lat"])
            return lon, lat

        return ref_chip, bounds, geo_transform
    except Exception as e:
        logger.error(f"Failed to load reference image: {e}")
        raise
