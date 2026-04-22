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
#    File:    edge_aligner.py
#    Author:  Marvin Smith
#    Date:    04/17/2026
#
"""
Main orchestrator for edge-based genetic algorithm alignment.

Aligns test image to reference using Sobel edges and differential evolution,
then extracts synthetic GCPs from the converged transform.
"""

# Python Standard Libraries
import logging
import os
import time
from typing import Any, Callable, Tuple

# Third-Party Libraries
import cv2
import numpy as np

# Project Libraries
from pointy.core.auto_match import Edge_Alignment_Settings
from pointy.core.gcp import GCP
from pointy.core.match.types import Match_Result
from pointy.core.match.edge_alignment.ga_optimizer import GA_Optimizer, GA_Result, GA_Settings
from pointy.core.match.edge_alignment.sobel_edges import Sobel_Edges, Sobel_Edge_Settings

from tmns.geo.coord import Geographic, Pixel
from tmns.geo.proj.affine import Affine
from tmns.geo.proj.base import Projector


def bootstrap_affine_from_projector(prior: Projector, w_test: int, h_test: int) -> Affine:
    """Fit an Affine projector from a 5x5 grid of samples through any prior projector.

    Use this when the GA requires an Affine but the available model is TPS or RPC.
    The least-squares fit over 25 points gives a much better approximation than
    fitting to 4 corners alone.
    """
    N = 5
    gcps = [
        (Pixel(x_px=int(c / (N - 1) * (w_test - 1)),
               y_px=int(r / (N - 1) * (h_test - 1))),
         prior.pixel_to_world(Pixel(x_px=int(c / (N - 1) * (w_test - 1)),
                                    y_px=int(r / (N - 1) * (h_test - 1)))))
        for r in range(N) for c in range(N)
    ]
    affine = Affine()
    affine.solve_from_gcps(gcps)
    affine.update_model(
        transform_matrix=affine._transform_matrix,
        image_size=(w_test, h_test),
        image_bounds=(0, 0, w_test - 1, h_test - 1),
    )
    return affine


def cold_start_affine_projector(w_test: int, h_test: int, w_ref: int, h_ref: int,
                                ref_geo_transform: Callable[[float, float], Tuple[float, float]]) -> Affine:
    """Initialize an Affine projector when no prior model is available.

    Maps the test image pixel grid proportionally across the full ref chip geo
    extent.  Gives the GA a neutral starting point that covers the full search
    region.  For RPC cold-starts, the resulting Affine params can seed the
    rational polynomial bias/scale offsets.
    """
    N = 5
    gcps = []
    for r in range(N):
        for c in range(N):
            tx = int(c / (N - 1) * (w_test - 1))
            ty = int(r / (N - 1) * (h_test - 1))
            lon, lat = ref_geo_transform(c / (N - 1) * (w_ref - 1),
                                         r / (N - 1) * (h_ref - 1))
            gcps.append((Pixel(x_px=tx, y_px=ty),
                         Geographic(latitude_deg=lat, longitude_deg=lon)))
    affine = Affine()
    affine.solve_from_gcps(gcps)
    affine.update_model(
        transform_matrix=affine._transform_matrix,
        image_size=(w_test, h_test),
        image_bounds=(0, 0, w_test - 1, h_test - 1),
    )
    return affine


class Edge_Aligner:
    """Edge-based alignment using Sobel edges + genetic algorithm.

    Pipeline:
        1. Detect Sobel edges in both test and reference images
        2. Optimize affine transform via differential evolution
        3. Extract synthetic GCPs from transform (grid pattern)
        4. Solve RPC model if enough GCPs available (≥9)
    """

    def __init__(self, settings: Edge_Alignment_Settings, projector: Projector | None = None):
        self._settings = settings
        self._projector: Projector | None = projector
        self._test_edge_detector = Sobel_Edges(Sobel_Edge_Settings(
            kernel_size=settings.sobel_kernel_size,
            dilation=settings.test_dilation,
            threshold=settings.sobel_threshold,
            pre_blur_kernel=settings.test_pre_blur,
        ))
        self._ref_edge_detector = Sobel_Edges(Sobel_Edge_Settings(
            kernel_size=settings.sobel_kernel_size,
            dilation=settings.ref_dilation,
            threshold=settings.sobel_threshold,
            pre_blur_kernel=settings.ref_pre_blur,
        ))
        self._optimizer = GA_Optimizer(GA_Settings(
            popsize=settings.ga_popsize,
            maxiter=settings.ga_maxiter,
            mutation=settings.ga_mutation,
            recombination=settings.ga_recombination,
            max_edge_dim=settings.ga_max_edge_dim,
            workers=1,
            polish=True,
        ))


    def _save_debug_image(self, image: np.ndarray, filename: str, description: str) -> None:
        """Save debug image to disk if debug settings are enabled.

        Args:
            image: Image array to save (grayscale or color).
            filename: Base filename (without extension).
            description: Description for logging.
        """
        if not self._settings.debug.save_test_sobel and not self._settings.debug.save_ref_sobel:
            return

        try:
            # Create output directory if it doesn't exist
            os.makedirs(self._settings.debug.output_directory, exist_ok=True)

            # Construct full path
            output_path = os.path.join(self._settings.debug.output_directory, f"{filename}.png")

            # Convert to uint8 for PNG output
            if image.dtype != np.uint8:
                image = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)

            # Save image
            cv2.imwrite(output_path, image)
            logging.info(f'Edge_Aligner: Saved debug image - {description}: {output_path}')

        except Exception as e:
            logging.warning(f'Edge_Aligner: Failed to save debug image {filename}: {e}')

    def align(self,
              test_image: np.ndarray,
              ref_chip: np.ndarray,
              ref_geo_transform: Callable[[float, float], Tuple[float, float]],
              manual_gcps: list[GCP] | None = None,
              initial_model: Projector | None = None,
              progress_callback: Callable | None = None,
              return_refined_model: bool = False) -> Match_Result:
        """Execute edge-based alignment pipeline.

        Args:
            test_image:        Test image array (H, W) or (H, W, C) uint8.
            ref_chip:          Reference basemap chip, same shape convention.
            ref_geo_transform: Callable ``(px_x, px_y) -> (lon, lat)``.
            manual_gcps:       Optional list of GCP objects.
            initial_model:     Optional initial projector model to refine.
            progress_callback: Optional callback(iteration, score) for progress.
            return_refined_model: If True, return enhanced result with model refinement info.

        Returns:
            ``Match_Result`` with synthetic GCPs extracted from the transform.
            If return_refined_model=True, includes refined model and solver metrics.
        """
        original_projector = self._projector
        if initial_model is not None:
            self._projector = initial_model
            logging.info(f'Edge_Aligner: Using provided projector: {type(initial_model).__name__}')

        t0 = time.perf_counter()
        result = Match_Result()

        h_test, w_test = test_image.shape[:2]
        h_ref, w_ref = ref_chip.shape[:2]

        logging.info(f'Edge_Aligner: test={w_test}x{h_test}, ref={w_ref}x{h_ref}')

        # Stage 1: Edge detection
        logging.info('Edge_Aligner: detecting Sobel edges')
        test_edges = self._test_edge_detector.detect(test_image)
        ref_edges = self._ref_edge_detector.detect(ref_chip)

        # Save debug images if enabled
        if self._settings.debug.save_test_sobel:
            self._save_debug_image(test_edges, "test_edges", "Test image Sobel edges")
        if self._settings.debug.save_ref_sobel:
            self._save_debug_image(ref_edges, "ref_edges", "Reference image Sobel edges")


        # Stage 2: GA optimization with model parameters
        if self._projector is None:
            raise ValueError(
                'Edge_Aligner.align() requires a projector. '
                'Use bootstrap_affine_from_projector() or cold_start_affine_projector() '
                'to build one before calling align().'
            )
        logging.info(f'Edge_Aligner: optimizing with {type(self._projector).__name__} projector')

        # NOTE: Cropping ref_edges based on the initial model is unreliable since
        # that model is what we're trying to solve for. Each fitness call in the GA
        # is responsible for computing its own per-parameter-set crop window: project
        # the test corners through the trial model, determine the ref sub-view, warp
        # the test into that sub-view, and compare same-size edge images there.
        def cb(params, score):
            if progress_callback:
                progress_callback(score)

        init_params = self._projector.to_params()

        ga_result = self._optimizer.optimize_model(
            test_edges, ref_edges,
            model=self._projector,
            bounds_px=self._settings.search_bounds_px,
            callback=cb,
            init_params=init_params,
            manual_gcps=manual_gcps,
            gcp_weight=self._settings.gcp_weight,
            ref_geo_transform=ref_geo_transform,
        )

        if not ga_result.success:
            logging.warning(f'Edge_Aligner: GA did not converge: {ga_result.message}')
            result.error = f'GA optimization failed: {ga_result.message}'
            result.elapsed_sec = time.perf_counter() - t0
            return result

        edge_w = 1.0 - ga_result.gcp_weight
        logging.info(
            f'Edge_Aligner: GA converged\n'
            f'  combined score : {ga_result.score:.4f}\n'
            f'  edge  score    : {ga_result.edge_score:.4f}  (weight={edge_w:.2f})\n'
            f'  gcp   score    : {ga_result.gcp_score:.4f}  (weight={ga_result.gcp_weight:.2f})'
            + (f'  [{len(manual_gcps)} GCPs]' if manual_gcps else '  [no GCPs]')
        )

        # Update the projector with the optimized model
        if ga_result.optimized_model is not None:
            self._projector = ga_result.optimized_model
            logging.info(f'Edge_Aligner: updated projector with optimized model')
        else:
            logging.warning('Edge_Aligner: no optimized model returned from GA')

        # Stage 3: Extract synthetic GCPs from optimized model (grid pattern) for results
        gcp_pixels, gcp_geos = self._extract_gcps_from_model(
            self._projector,
            (w_test, h_test),
            (w_ref, h_ref),
            ref_geo_transform,
        )

        # Set result properties
        result.candidate_pixels = gcp_pixels
        result.candidate_geos = gcp_geos
        result.candidate_confidences = np.full(len(gcp_pixels), ga_result.score)
        result.n_inliers = len(gcp_pixels)
        result.elapsed_sec = time.perf_counter() - t0

        # Add model refinement information if requested
        if return_refined_model:
            if ga_result.success and self._projector is not None:
                # Store the refined model as a custom attribute
                result.refined_model = self._projector
                result.solver_iterations = getattr(self._optimizer, '_last_iterations', 0)
                result.solver_converged = True
                result.solver_fitness = result.candidate_confidences.mean() if result.candidate_confidences is not None else 0.0
                result.coverage_percent = (result.n_inliers / max(len(gcp_pixels), 1)) * 100
                result.rmse = ga_result.score if hasattr(ga_result, 'score') else 0.0
                result.error_message = ''
            else:
                result.refined_model = initial_model or original_projector
                result.solver_iterations = 0
                result.solver_converged = False
                result.solver_fitness = 0.0
                result.coverage_percent = 0.0
                result.rmse = 0.0
                result.error_message = result.error

        self._projector = original_projector

        logging.info(f'Edge_Aligner: extracted {len(gcp_pixels)} synthetic GCPs in {result.elapsed_sec:.2f}s')

        return result



    def _extract_gcps_from_model(self, model: Projector, test_size: tuple[int, int],
                                 ref_size: tuple[int, int], ref_geo_transform: Callable) -> tuple[np.ndarray, np.ndarray]:
        """Extract synthetic GCPs from the converged model.

        Args:
            model: Converged projector model.
            test_size: (w, h) of test image.
            ref_size: (w, h) of reference image.
            ref_geo_transform: Reference pixel -> geographic mapping.

        Returns:
            Tuple of (pixel_coords Nx2, geo_coords Nx2).
        """
        w_test, h_test = test_size
        w_ref, h_ref = ref_size

        # Generate 4x4 grid of points in test image
        grid_size = 4
        x_coords = np.linspace(0, w_test - 1, grid_size)
        y_coords = np.linspace(0, h_test - 1, grid_size)
        xx, yy = np.meshgrid(x_coords, y_coords)
        test_pts = np.column_stack([xx.ravel(), yy.ravel()]).astype(np.float64)

        # Convert test pixels to geographic coordinates using the model
        geo_pts = []
        for px, py in test_pts:
            pixel = Pixel(x_px=px, y_px=py)
            geo = model.pixel_to_world(pixel)
            geo_pts.append([geo.longitude_deg, geo.latitude_deg])

        geo_pts = np.array(geo_pts)

        return test_pts, geo_pts


    def get_projector(self) -> Projector | None:
        """Return the solved Projector (RPC/Affine), if available."""
        return self._projector

