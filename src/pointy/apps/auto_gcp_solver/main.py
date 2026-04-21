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
import cv2
import numpy as np
import rasterio
from rasterio.transform import from_bounds

# Project Libraries
from pointy.apps.auto_gcp_solver.config import Configuration
from pointy.apps.auto_gcp_solver.init_utilities import load_test_image, load_reference_imagery
from pointy.apps.auto_gcp_solver.plot import visualize_results
from pointy.apps.auto_gcp_solver.tile_capture import estimate_gsd
from pointy.core.gcp import GCP
from pointy.core.match.gcp_solver_pipeline import GCP_Solver_Pipeline
from pointy.core.transformation import warp_image
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.coord.crs import CRS


def generate_geotiff_from_model(image: np.ndarray, model: Any, output_path: Path) -> None:
    """Generate a georectified GeoTiff using a Projector model (RPC, Affine, etc.).

    Args:
        image: Input image array (H, W) or (H, W, C) uint8.
        model: Solved Projector model from terminus_core_python.
        output_path: Path where to save the GeoTiff.
    """
    # Warp image using the shared warp_image function
    warped, extent = warp_image(image, model, CRS.wgs84_geographic())

    # Convert BGR to RGB if needed (OpenCV uses BGR)
    if len(warped.shape) == 3 and warped.shape[2] == 3:
        warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)

    # Save as GeoTiff
    h, w = warped.shape[:2]
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=h,
        width=w,
        count=warped.shape[2] if len(warped.shape) == 3 else 1,
        dtype=warped.dtype,
        crs='EPSG:4326',
        transform=from_bounds(
            extent.min_point.longitude_deg,
            extent.min_point.latitude_deg,
            extent.max_point.longitude_deg,
            extent.max_point.latitude_deg,
            w,
            h
        )
    ) as dst:
        if len(warped.shape) == 3:
            dst.write(warped.transpose(2, 0, 1))
        else:
            dst.write(warped, 1)


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
    test_image = load_test_image(config, logger)

    # Check for Ortho model sidecar to get full test image bounds
    ortho_model_bounds = config.get_ortho_model_bounds(config.test_image.path, test_image.shape[:2])
    if ortho_model_bounds:
        logger.info(f"Ortho model bounds: {ortho_model_bounds}")

    # Load reference imagery
    ref_chip, bounds, geo_transform = load_reference_imagery(config, logger, ortho_model_bounds)

    # Load manual GCPs
    gcp_proc = config.load_manual_gcps()

    # Extract manual GCPs
    manual_gcps = list(gcp_proc.gcps.values()) if gcp_proc else []

    # Run auto-gcp solver
    logger.info("Running auto-gcp solver...")
    logger.info(f"Settings: {config.auto_match.to_log_string()}")

    try:
        matcher = GCP_Solver_Pipeline(config.auto_match)

        # Pass manual GCPs directly (conversion to numpy happens internally)
        if manual_gcps:
            logger.info(f"Prepared {len(manual_gcps)} manual GCPs for feature matching")

        # Run the pipeline
        result = matcher.run(test_image, ref_chip, geo_transform, manual_gcps=manual_gcps)

        if not result.success:
            logger.error(f"Auto-GCP solver failed: {result.error}")
            return 1

        logger.info(f"Auto-GCP solver completed successfully in {result.elapsed_sec:.2f}s")
        logger.info(f"Generated {result.n_inliers} GCP candidates from {result.n_raw_matches} raw matches")

        # Print summary table
        summary = (
            "\n" + "="*60 + "\n" +
            "SUMMARY TABLE\n" +
            "="*60 + "\n" +
            f"{'Metric':<30} {'Value':>20}\n" +
            "-"*60 + "\n" +
            f"{'Test Image Features':<30} {result.n_raw_matches:>20}\n" +
            f"{'Reference Image Features':<30} {result.n_ref_keypoints:>20}\n" +
            f"{'Initial Matches':<30} {result.n_candidates:>20}\n" +
            f"{'Final GCPs':<30} {result.n_inliers:>20}\n" +
            f"{'Manual GCPs Loaded':<30} {len(manual_gcps):>20}\n" +
            f"{'Elapsed Time':<30} {result.elapsed_sec:>20.2f}s\n" +
            "="*60
        )
        logger.info(summary)

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
                manual_gcps=manual_gcps,
                bounds=bounds,
                inlier_mask=result.inlier_mask,
                raw_match_pixels=result.raw_match_pixels,
                raw_match_ref_pixels=result.raw_match_ref_pixels
            )
            logger.info(f"Visualization results saved to {Path('temp').absolute()}")
    except Exception as e:
        logger.error(f"Auto-GCP solver failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
