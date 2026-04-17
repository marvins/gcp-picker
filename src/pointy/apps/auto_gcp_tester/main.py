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
#    File:    main.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Auto-GCP Tester CLI - Standalone tool for testing auto-match pipeline.

This tool allows testing the auto-match feature extraction and matching pipeline
without the GUI, useful for debugging and parameter tuning.
"""

# Python Standard Libraries
import logging
import sys
from pathlib import Path
from typing import Any

# Third-Party Libraries
import numpy as np
import rasterio
from rasterio.transform import from_bounds

# Project Libraries
from pointy.apps.auto_gcp_tester.config import Configuration
from pointy.apps.auto_gcp_tester.plot import visualize_results
from pointy.apps.auto_gcp_tester.tile_capture import calculate_zoom_for_resolution, capture_tiles, estimate_gsd
from pointy.core.match.pipeline import Auto_Matcher


def setup_logging(verbose: bool = False):
    """Configure logging for the application.

    Args:
        verbose: If True, set logging level to DEBUG; otherwise INFO.

    Returns:
        logging.Logger: Configured logger instance for the module.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        stream=sys.stdout
    )

    # Suppress verbose rasterio.env debug messages
    logging.getLogger('rasterio.env').setLevel(logging.WARNING)
    logging.getLogger('rasterio._base').setLevel(logging.WARNING)
    logging.getLogger('rasterio._env').setLevel(logging.WARNING)
    logging.getLogger('rasterio._io').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def main() -> int:
    """Main entry point for the auto-gcp-tester CLI.

    This function:
    1. Parses configuration from command line and TOML file
    2. Validates the configuration
    3. Loads the test image and reference imagery
    4. Loads manual GCPs if configured
    5. Runs the auto-match pipeline
    6. Outputs results including candidate GCPs and statistics

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    config = Configuration.parse()

    logger = setup_logging(config.cmd_args.verbose)

    if not config.validate():
        return 1

    logger.info(f"Configuration loaded from: {config.cmd_args.config_file}")
    logger.info(f"Test image: {config.test_image.path}")
    logger.info(f"Reference: {config.reference.type}")

    # Check test image for ortho sidecar
    test_bounds = config.check_ortho_sidecar(config.test_image.path)
    if test_bounds:
        logger.info(f"Test image has ortho sidecar with bounds: {test_bounds}")

        # Estimate GSD from test image
        gsd_info = estimate_gsd(test_image.shape, test_bounds)
        logger.info(f"Estimated test image GSD: {gsd_info['gsd_avg']:.3f} m/pixel (lat: {gsd_info['gsd_lat']:.3f}, lon: {gsd_info['gsd_lon']:.3f})")

    # Load test image
    logger.info("Loading test image...")
    try:
        with rasterio.open(config.test_image.path) as src:
            test_image = src.read()
            if test_image.ndim == 3:
                test_image = np.transpose(test_image, (1, 2, 0))
            logger.info(f"Test image shape: {test_image.shape}, dtype: {test_image.dtype}")
    except Exception as e:
        logger.error(f"Failed to load test image: {e}")
        return 1

    # Check for Ortho model sidecar to get full test image bounds
    ortho_model_bounds = config.get_ortho_model_bounds(config.test_image.path, test_image.shape[:2])
    if ortho_model_bounds:
        logger.info(f"Ortho model bounds: {ortho_model_bounds}")

    # Load reference imagery
    if config.reference.type == "file":
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
                    return 1

            def geo_transform(px_x: float, px_y: float) -> tuple[float, float]:
                lon = bounds["sw_lon"] + (px_x / ref_chip.shape[1]) * (bounds["ne_lon"] - bounds["sw_lon"])
                lat = bounds["ne_lat"] - (px_y / ref_chip.shape[0]) * (bounds["ne_lat"] - bounds["sw_lat"])
                return lon, lat
        except Exception as e:
            logger.error(f"Failed to load reference image: {e}")
            return 1
    # Load manual GCPs early to get geographic bounds for reference imagery
    gcp_proc = config.load_manual_gcps()

    # Extract manual GCPs and calculate geographic bounds
    manual_gcp_rows = []
    gcp_bounds = None
    if gcp_proc:
        lons = []
        lats = []
        for gcp in gcp_proc.gcps.values():
            manual_gcp_rows.append((gcp.test_pixel.x, gcp.test_pixel.y, gcp.geographic.longitude_deg, gcp.geographic.latitude_deg))
            lons.append(gcp.geographic.longitude_deg)
            lats.append(gcp.geographic.latitude_deg)
        # Calculate bounds with some padding
        gcp_bounds = {
            'sw_lat': min(lats) - 0.01,
            'sw_lon': min(lons) - 0.01,
            'ne_lat': max(lats) + 0.01,
            'ne_lon': max(lons) + 0.01,
        }
        logger.info(f"GCP geographic bounds: {gcp_bounds}")

    if config.reference.type == "leaflet":
        logger.info(f"Capturing reference imagery from {config.reference.service}")

        # Prioritize bounds: Ortho model > GCP bounds > GeoTIFF sidecar > fallback
        target_bounds = ortho_model_bounds or gcp_bounds or config.check_ortho_sidecar(config.test_image.path)

        # Calculate appropriate zoom if bounds available
        if target_bounds:
            recommended_zoom = calculate_zoom_for_resolution(test_image.shape, config.reference.center['lat'], target_bounds)
            logger.info(f"Bounds detected: {target_bounds}")
            logger.info(f"Recommended zoom level: {recommended_zoom} (config: {config.reference.zoom})")
            zoom = recommended_zoom
        else:
            zoom = config.reference.zoom

        try:
            # Use bounds to expand tile grid for full coverage
            ref_chip, bounds = capture_tiles(
                service_name=config.reference.service,
                center_lat=config.reference.center['lat'],
                center_lon=config.reference.center['lon'],
                zoom=zoom,
                target_bounds=target_bounds
            )
            logger.info(f"Reference chip shape: {ref_chip.shape}, dtype: {ref_chip.dtype}")

            # Calculate GSD of reference image
            from pointy.apps.auto_gcp_tester.tile_capture import estimate_gsd
            gsd_info = estimate_gsd(ref_chip.shape[:2], bounds)
            logger.info(f"Reference image GSD: {gsd_info}")

            # Write reference image as TIFF for inspection
            ref_tiff_path = Path('temp/reference_image.tif')
            ref_tiff_path.parent.mkdir(exist_ok=True)
            # Create geotransform from bounds
            transform = from_bounds(bounds['sw_lon'], bounds['sw_lat'], bounds['ne_lon'], bounds['ne_lat'], ref_chip.shape[1], ref_chip.shape[0])
            with rasterio.open(ref_tiff_path, 'w', driver='GTiff', height=ref_chip.shape[0], width=ref_chip.shape[1], count=3, dtype=ref_chip.dtype, crs='EPSG:4326', transform=transform) as dst:
                dst.write(ref_chip.transpose(2, 0, 1))  # rasterio expects (bands, height, width)
            logger.info(f"Saved reference image as TIFF: {ref_tiff_path}")

            def geo_transform(px_x: float, px_y: float) -> tuple[float, float]:
                lon = bounds["sw_lon"] + (px_x / ref_chip.shape[1]) * (bounds["ne_lon"] - bounds["sw_lon"])
                lat = bounds["ne_lat"] - (px_y / ref_chip.shape[0]) * (bounds["ne_lat"] - bounds["sw_lat"])
                return lon, lat
        except Exception as e:
            logger.error(f"Failed to capture reference imagery: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        logger.error(f"Unknown reference type: {config.reference.type}")
        return 1

    # Run auto-match pipeline
    logger.info("Running auto-match pipeline...")
    logger.info(f"Settings: {config.auto_match.to_log_string()}")

    try:
        matcher = Auto_Matcher(config.auto_match)
        result = matcher.run(test_image, ref_chip, geo_transform)

        logger.info(f"Raw matches: {result.n_raw_matches}")
        logger.info(f"Candidates: {result.n_candidates}")
        logger.info(f"Inliers: {result.n_inliers}")

        # Print summary table
        logger.info("\n" + "="*60)
        logger.info("SUMMARY TABLE")
        logger.info("="*60)
        logger.info(f"{'Metric':<30} {'Value':>20}")
        logger.info("-"*60)
        logger.info(f"{'Test Image Keypoints':<30} {result.n_raw_matches:>20}")
        logger.info(f"{'Reference Image Keypoints':<30} {result.n_ref_keypoints:>20}")
        logger.info(f"{'Matches after Ratio Test':<30} {result.n_candidates:>20}")
        logger.info(f"{'Inliers after RANSAC':<30} {result.n_inliers:>20}")
        logger.info(f"{'Manual GCPs Loaded':<30} {len(manual_gcp_rows):>20}")
        logger.info(f"{'Elapsed Time':<30} {result.elapsed_sec:>20.2f}s")
        logger.info("="*60)

        if result.n_inliers > 0:
            # Combine candidate_pixels and candidate_geos into rows
            candidate_rows = list(zip(result.candidate_pixels[:, 0], result.candidate_pixels[:, 1],
                                    result.candidate_geos[:, 0], result.candidate_geos[:, 1]))
            logger.info(f"Visualizing {len(candidate_rows)} candidate GCPs...")
            visualize_results(
                test_image,
                ref_chip,
                candidate_rows,
                Path('temp'),
                manual_gcps=manual_gcp_rows,
                bounds=bounds,
                inlier_mask=result.inlier_mask,
                raw_match_pixels=result.raw_match_pixels,
                raw_match_ref_pixels=result.raw_match_ref_pixels
            )
            logger.info(f"Visualization results saved to {Path('temp').absolute()}")
    except Exception as e:
        logger.error(f"Auto-match pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
