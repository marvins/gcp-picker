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
#    Date:    04/19/2026
#
"""
Auto Model Solver CLI for Sobel edge-based alignment using genetic algorithms.
"""
# This tool allows testing the auto-match feature extraction and matching pipeline
# without the GUI, useful for debugging and parameter tuning.

# Python Standard Libraries
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Third-Party Libraries
import cv2
import numpy as np
import rasterio
from rasterio.transform import from_bounds

# Project Libraries
from pointy.apps.auto_model_solver.config import Configuration
from pointy.apps.auto_model_solver.init_utilities import load_test_image, load_reference_imagery
from pointy.apps.auto_model_solver.model_solver_result import Model_Solver_Result
from pointy.apps.auto_model_solver.plot import visualize_results
from pointy.apps.auto_model_solver.tile_capture import clear_tile_cache, estimate_gsd
from pointy.core.match.edge_alignment.edge_aligner import (
    Edge_Aligner,
    bootstrap_affine_from_projector,
    cold_start_affine_projector,
)
from pointy.core.ortho_model_persistence import apply_model_to_projector, load_ortho_model
from pointy.core.transformation import warp_image
from tmns.geo.coord.crs import CRS
from tmns.geo.proj import Transformation_Type
from tmns.geo.proj.factory import create_projector


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


def save_reference_chip_geotiff(ref_chip: np.ndarray, bounds: dict[str, float],
                                output_path: str, logger: logging.Logger) -> None:
    """Save the stitched reference chip as a georeferenced GeoTiff.

    Args:
        ref_chip: Reference chip image array (H, W, C) uint8.
        bounds: Geographic bounds {sw_lat, sw_lon, ne_lat, ne_lon}.
        output_path: Destination path for the GeoTiff.
        logger: Logger instance.
    """
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        h, w = ref_chip.shape[:2]
        img_rgb = ref_chip  # Tiles from PIL are already RGB; no conversion needed
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=h,
            width=w,
            count=img_rgb.shape[2] if img_rgb.ndim == 3 else 1,
            dtype=img_rgb.dtype,
            crs='EPSG:4326',
            transform=from_bounds(
                bounds['sw_lon'], bounds['sw_lat'],
                bounds['ne_lon'], bounds['ne_lat'],
                w, h,
            ),
        ) as dst:
            if img_rgb.ndim == 3:
                dst.write(img_rgb.transpose(2, 0, 1))
            else:
                dst.write(img_rgb, 1)
        logger.info(f"Reference chip GeoTiff saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save reference chip GeoTiff: {e}")


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

    # Suppress verbose third-party debug messages
    logging.getLogger('rasterio.env').setLevel(logging.WARNING)
    logging.getLogger('rasterio._base').setLevel(logging.WARNING)
    logging.getLogger('rasterio._env').setLevel(logging.WARNING)
    logging.getLogger('rasterio._io').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

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

    # Parse the configuration and setup the logger
    config = Configuration.parse()
    logger = setup_logging(config.cmd_args.verbose)

    # Let the user clear the tile cache if they want to
    if getattr(config.cmd_args, 'clear_cache', False):
        clear_tile_cache()
        logger.info('Tile cache cleared.')

    if not config.validate():
        return 1

    logger.info(
        f"Configuration loaded:\n"
        f"  config_file : {config.cmd_args.config_file}\n"
        f"  test_image  : {config.test_image.path}\n"
        f"  reference   : {config.reference.type}"
    )

    try:
        # Load test image
        test_image = load_test_image(config, logger)

        # Check test image for ortho sidecar
        test_bounds = config.check_ortho_sidecar(config.test_image.path)
        if test_bounds:
            logger.info(f"Test image has ortho sidecar with bounds: {test_bounds}")

            # Estimate GSD from test image
            gsd_info = estimate_gsd(test_image.shape, test_bounds)
            logger.info(f"Estimated test image GSD: {gsd_info['gsd_avg']:.3f} m/pixel (lat: {gsd_info['gsd_lat']:.3f}, lon: {gsd_info['gsd_lon']:.3f})")

        # Load full Ortho model from sidecar
        ortho_model = None
        ortho_model_bounds = None

        ortho_sidecar = load_ortho_model(Path(config.test_image.path))
        if ortho_sidecar:
            # Convert sidecar to Projector
            model_type = Transformation_Type(ortho_sidecar.metadata.model_type)
            ortho_model = create_projector(model_type)
            apply_model_to_projector(ortho_model, ortho_sidecar.model_data, ortho_sidecar.metadata.model_type)
            logger.info(f"Loaded Ortho model: {type(ortho_model).__name__}")

            # Extract bounds from the model
            ortho_model_bounds = config.get_ortho_model_bounds(config.test_image.path, test_image.shape[:2])
            if ortho_model_bounds:
                logger.info(f"Ortho model bounds: {ortho_model_bounds}")

        # Load reference imagery
        ref_chip, bounds, geo_transform = load_reference_imagery(config, logger, ortho_model_bounds)

        if config.output.ref_chip_output_path:
            save_reference_chip_geotiff(ref_chip, bounds, config.output.ref_chip_output_path, logger)

        # Load manual GCPs
        gcp_proc = config.load_manual_gcps()

        # Extract manual GCPs
        manual_gcps = list(gcp_proc.gcps.values()) if gcp_proc else []

        # Run auto-model solver
        logger.info("Running auto-model solver...")
        logger.info(f"Settings: {config.auto_match.to_log_string()}")

        # Build the initial projector for the GA before creating the aligner.
        # If a prior model exists (TPS, RPC), bootstrap an Affine from it.
        # Otherwise cold-start from the ref chip geo extent.
        h_test, w_test = test_image.shape[:2]
        h_ref, w_ref = ref_chip.shape[:2]
        if ortho_model is not None:
            logger.info(f'Bootstrapping Affine from {type(ortho_model).__name__} prior model')
            initial_projector = bootstrap_affine_from_projector(ortho_model, w_test, h_test)
        else:
            logger.info('No prior model — cold-starting Affine from ref geo extent')
            initial_projector = cold_start_affine_projector(w_test, h_test, w_ref, h_ref, geo_transform)

        # Create edge aligner with the pre-built projector
        aligner = Edge_Aligner(config.auto_match.edge_settings, projector=initial_projector)

        # Pass manual GCPs directly
        if manual_gcps:
            logger.info(f"Prepared {len(manual_gcps)} manual GCPs for edge alignment")

        # Run the edge alignment with model refinement
        start_time = time.time()
        result = aligner.align(
            test_image, ref_chip, geo_transform,
            manual_gcps=manual_gcps,
            return_refined_model=True
        )
        elapsed_time = time.time() - start_time

        if not result.success:
            logger.error(f"Auto-model solver failed: {result.error_message}")
            return 1

        # Create model solver result
        solver_result = Model_Solver_Result(
            refined_model=result.refined_model,
            original_model=ortho_model,
            success=result.success,
            n_candidates=len(result.candidate_pixels) if result.candidate_pixels is not None else 0,
            n_inliers=result.n_inliers,
            coverage_percent=result.coverage_percent,
            rmse=result.rmse,
            solver_iterations=result.solver_iterations,
            solver_converged=result.solver_converged,
            solver_fitness=result.solver_fitness,
            elapsed_seconds=elapsed_time,
            error_message=result.error_message
        )

        # Log results
        logger.info(f"Auto-model solver completed successfully")
        logger.info(solver_result.to_log_string())

        # Save refined model if configured
        if config.output.model_output_path:
            save_model_to_file(solver_result.refined_model, config.output.model_output_path, logger)
            logger.info(f"Saved refined model to {config.output.model_output_path}")

        # Print summary table
        summary = (
            "\n" + "="*60 + "\n" +
            "SUMMARY TABLE\n" +
            "="*60 + "\n" +
            f"{'Metric':<30} {'Value':>20}\n" +
            "-"*60 + "\n" +
            f"{'Final GCPs':<30} {solver_result.n_inliers:>20}\n" +
            f"{'Manual GCPs Loaded':<30} {len(manual_gcps):>20}\n" +
            f"{'Elapsed Time':<30} {solver_result.elapsed_seconds:>20.2f}s\n" +
            "="*60
        )
        logger.info(summary)

        # Log refined model parameters
        if result.refined_model is not None:
            refined = result.refined_model
            params = refined.to_params()
            logger.info(
                f'Refined model parameters: '
                f'm00={params[0]:.10f}, m01={params[1]:.10f}, m02={params[2]:.10f}, '
                f'm10={params[3]:.10f}, m11={params[4]:.10f}, m12={params[5]:.10f}'
            )

        # Write best-fit GeoTiff
        geotiff_path = Path('temp') / 'refined_model_output.tif'
        try:
            generate_geotiff_from_model(test_image, result.refined_model, geotiff_path)
            logger.info(f'Saved GeoTiff to {geotiff_path.absolute()}')
        except Exception as e:
            logger.warning(f'Failed to write GeoTiff: {e}')

        if result.n_inliers > 0:
            # Combine candidate_pixels and candidate_geos into rows
            candidate_rows = list(zip(result.candidate_pixels[:, 0], result.candidate_pixels[:, 1],
                                    result.candidate_geos[:, 0], result.candidate_geos[:, 1]))
            logger.info(f"Visualizing {len(candidate_rows)} candidate GCPs...")
            visualize_results(
                test_image,
                ref_chip,
                candidate_rows,
                Path('temp') / 'model_solver_results.html'
            )
            logger.info(f"Visualization results saved to {Path('temp').absolute()}")

    except Exception as e:
        logger.error(f"Auto-model solver failed: {e}")
        traceback.print_exc()
        return 1

    return 0


def save_model_to_file(model: Any, output_path: str, logger: logging.Logger) -> None:
    """Save the refined model to a file.

    Args:
        model: The refined projector model.
        output_path: Path to save the model.
        logger: Logger instance.
    """
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model_type': model.transformation_type.value,
            'model_data': model.serialize_model_data(),
        }
        with open(output_path, 'w') as f:
            json.dump(model_data, f, indent=2)
        logger.info(f"Model saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save model: {e}")


if __name__ == '__main__':
    sys.exit(main())
