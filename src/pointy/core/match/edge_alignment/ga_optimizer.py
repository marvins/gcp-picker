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
#    File:    ga_optimizer.py
#    Author:  Marvin Smith
#    Date:    04/17/2026
#
"""
Genetic algorithm optimizer for edge-based image alignment.

Uses scipy's differential evolution to find the optimal affine/homography
transform that maximizes edge correlation between test and reference images.
"""

# Python Standard Libraries
from dataclasses import dataclass
import logging
import time
from typing import Any, Callable, Tuple

# Third-Party Libraries
import cv2
import numpy as np
from scipy.optimize import differential_evolution

# Project Libraries
from tmns.geo.coord import Pixel
from tmns.geo.proj.affine import Affine
from tmns.geo.proj.base import Projector, Transformation_Type
from tmns.geo.proj.factory import create_projector

@dataclass
class GA_Result:
    """Result container for genetic algorithm optimization.

    Attributes:
        success:          Whether optimization converged.
        transform:        3x3 homography or affine matrix (best fit) - deprecated.
        score:            Final combined score (higher is better).
        edge_score:       Final Sobel edge NCC component, normalized to [0, 1].
        gcp_score:        Final GCP reprojection component [0, 1] (0.0 if no GCPs).
        gcp_weight:       Weight applied to gcp_score in the combined score.
        n_iterations:     Number of iterations performed.
        n_function_evals: Number of fitness evaluations.
        message:          Optimizer exit message.
        optimized_model:  The optimized projector model (Affine or RPC).
    """
    success:          bool
    transform:        np.ndarray | None
    score:            float
    edge_score:       float
    gcp_score:        float
    gcp_weight:       float
    n_iterations:     int
    n_function_evals: int
    message:          str
    optimized_model:  Any = None


@dataclass
class GA_Settings:
    """Configuration for genetic algorithm optimization.

    Attributes:
        popsize:       Population size multiplier (actual pop = popsize * n_params).
        maxiter:       Maximum iterations.
        mutation:      Mutation factor (min, max) tuple.
        recombination: Recombination/crossover probability.
        tol:           Convergence tolerance (relative). Smaller = less likely to stop early.
        workers:       Number of parallel workers (-1 = all cores).
        polish:        L-BFGS-B refinement at end.
    """
    popsize:       int           = 100
    maxiter:       int           = 1000
    mutation:      Tuple[float, float] = (0.5, 1.0)
    recombination: float         = 0.7
    tol:           float         = 0.001
    workers:       int           = -1
    polish:        bool          = True
    max_edge_dim:  int           = 2048


class GA_Optimizer:
    """Differential evolution optimizer for edge image alignment.

    Optimizes transform parameters to maximize normalized cross-correlation
    between warped test edges and reference edges.
    """

    def __init__(self, settings: GA_Settings):
        self._settings = settings

    def optimize_model(self,
                       test_edges: np.ndarray,
                       ref_edges: np.ndarray,
                       model: Projector,
                       ref_geo_transform: Callable,
                       bounds_px: float = 50.0,
                       callback: Callable | None = None,
                       init_params: np.ndarray | None = None,
                       manual_gcps: list | None = None,
                       gcp_weight: float = 0.0) -> GA_Result:
        """Optimize model parameters using differential evolution.

        Args:
            test_edges:        Test edge image (H, W) float32.
            ref_edges:         Reference edge image (H, W) float32.
            model:             Projector model (Affine) to optimize.
            ref_geo_transform: Callable ``(px_x, px_y) -> (lon, lat)`` for the reference chip.
                               Required for correct pixel-space warping of the test image.
            bounds_px:         Search bounds for parameter variations.
            callback:          Optional callback(params, score) for progress.
            init_params:       Optional initial model parameters for warm-starting.
            manual_gcps:       Optional list of manual GCPs to include in fitness evaluation.
            gcp_weight:        Weight [0-1] of GCP score in combined fitness.

        Returns:
            GA_Result with best model parameters and optimization info.
        """
        # Downsample edge images for faster fitness evaluation
        MAX_EDGE_DIM = self._settings.max_edge_dim
        h_test_full, w_test_full = test_edges.shape[:2]
        h_ref_full,  w_ref_full  = ref_edges.shape[:2]
        ref_scale  = min(MAX_EDGE_DIM / h_ref_full,  MAX_EDGE_DIM / w_ref_full,  1.0)
        test_scale = min(MAX_EDGE_DIM / h_test_full, MAX_EDGE_DIM / w_test_full, 1.0)
        if ref_scale < 1.0:
            new_ref_w = int(w_ref_full * ref_scale)
            new_ref_h = int(h_ref_full * ref_scale)
            ref_edges = cv2.resize(ref_edges, (new_ref_w, new_ref_h), interpolation=cv2.INTER_AREA)
        if test_scale < 1.0:
            new_test_w = int(w_test_full * test_scale)
            new_test_h = int(h_test_full * test_scale)
            test_edges = cv2.resize(test_edges, (new_test_w, new_test_h), interpolation=cv2.INTER_AREA)
        if ref_scale < 1.0 or test_scale < 1.0:
            logging.info(
                f'GA_Optimizer: downsampled edges\n'
                f'  ref:  {w_ref_full}x{h_ref_full} -> {ref_edges.shape[1]}x{ref_edges.shape[0]} (scale={ref_scale:.3f})\n'
                f'  test: {w_test_full}x{h_test_full} -> {test_edges.shape[1]}x{test_edges.shape[0]} (scale={test_scale:.3f})'
            )

        h, w = ref_edges.shape[:2]

        # Extract initial model parameters and compute bounds
        initial_params = model.to_params()
        bounds = model.get_param_bounds(bounds_px=bounds_px)

        # Pre-compute reference pixel → geo lookup arrays (constant across all fitness calls).
        # Assumes ref_geo_transform is a linear mapping (valid for tile chips), so we can
        # evaluate only the 4 corners and interpolate — or simply evaluate all pixels using
        # numpy broadcasting after sampling the two corner values.
        ref_y_grid, ref_x_grid = np.mgrid[0:h, 0:w]
        ref_x_flat = ref_x_grid.ravel().astype(np.float64)
        ref_y_flat = ref_y_grid.ravel().astype(np.float64)
        # ref_geo_transform is defined over full-res chip pixels.
        # Sample at full-res corners; pixel coords in downsampled space are
        # scaled by 1/ref_scale to recover the full-res position.
        full_w = w_ref_full - 1.0
        full_h = h_ref_full - 1.0
        lon00, lat00 = ref_geo_transform(0.0,    0.0)
        lon10, lat10 = ref_geo_transform(full_w, 0.0)
        lon01, lat01 = ref_geo_transform(0.0,    full_h)
        # Derivatives per downsampled pixel
        d_lon_dx = (lon10 - lon00) / max(w - 1, 1)
        d_lon_dy = (lon01 - lon00) / max(h - 1, 1)
        d_lat_dx = (lat10 - lat00) / max(w - 1, 1)
        d_lat_dy = (lat01 - lat00) / max(h - 1, 1)
        ref_lons = lon00 + d_lon_dx * ref_x_flat + d_lon_dy * ref_y_flat
        ref_lats = lat00 + d_lat_dx * ref_x_flat + d_lat_dy * ref_y_flat
        ref_geo_coords = np.stack([ref_lons, ref_lats, np.ones(len(ref_lons))])  # (3, N)
        logging.info(
            f'GA_Optimizer: ref geo extent  lon=[{ref_lons.min():.5f}, {ref_lons.max():.5f}]'
            f'  lat=[{ref_lats.min():.5f}, {ref_lats.max():.5f}]'
        )

        def _warp_with_model( image: np.ndarray,
                              model: Projector,
                              output_size: tuple[int, int]) -> np.ndarray:
            """Warp test image into reference pixel space via geo coordinates.

            Current implementation (Affine-specific):
                - Uses pre-computed ref_geo_coords (3, N) array: ref pixel → geo
                - Applies model._inverse_matrix @ ref_geo_coords: geo → test pixel
                - Scales to downsampled test_edges pixel space
                - Uses cv2.remap with NaN border for out-of-bounds pixels

            Planned refactor (projector-agnostic):
                - Use model.world_to_pixel() instead of _inverse_matrix
                - Build per-crop geo coords on the fly using linear constants
                - Drop full ref_geo_coords array to save memory

            Args:
                image: Test edge image (H, W) float32.
                model: Projector model to use for the warp.
                output_size: Target (height, width) for the warped output.

            Returns:
                Warped image array with NaN values where the test image does not
                overlap the reference footprint.

            Note:
                For non-Affine models, this currently falls back to cv2.resize
                (stub implementation). TODO-02 in auto-gcp-solver.md.
            """
            h, w = output_size

            if model.transformation_type == Transformation_Type.AFFINE:
                if model._inverse_matrix is None:
                    raise ValueError("Model has no inverse matrix")

                if ref_geo_coords is not None:
                    # Step 1: ref pixel → geo (pre-computed)
                    # Step 2: geo → full-res test pixel via model inverse matrix
                    src_coords = model._inverse_matrix @ ref_geo_coords  # (3, N)
                    # Step 3: scale to downsampled test_edges pixel space
                    source_x = (src_coords[0].reshape(h, w) * test_scale).astype(np.float32)
                    source_y = (src_coords[1].reshape(h, w) * test_scale).astype(np.float32)
                else:
                    # Fallback: direct pixel-to-pixel (wrong coordinate space, but avoids crash)
                    y_coords, x_coords = np.mgrid[0:h, 0:w]
                    coords = np.stack([x_coords.ravel(), y_coords.ravel(), np.ones(h * w)])
                    src_coords = model._inverse_matrix @ coords
                    source_x = src_coords[0].reshape(h, w).astype(np.float32)
                    source_y = src_coords[1].reshape(h, w).astype(np.float32)

                warped = cv2.remap(image, source_x, source_y,
                                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                   borderValue=np.nan)
                return warped
            else:
                # For RPC models, fall back to identity for now (this needs proper implementation)
                return cv2.resize(image, (w, h))

        fitness_call_counter = [0]
        last_score = [0.0]

        def fitness(params: np.ndarray) -> float:
            fitness_call_counter[0] += 1
            call_n = fitness_call_counter[0]
            t_start = time.monotonic()

            # Create a temporary model variant with the new parameters
            temp_model = model.from_params(params)
            t_model = time.monotonic()

            # Bail early if the proposed matrix is numerically degenerate
            if temp_model._inverse_matrix is not None:
                cond = np.linalg.cond(temp_model._inverse_matrix)
                if cond > 1e12:
                    return 1.0  # Worst possible score (we minimize)

            # Edge alignment score
            warped = _warp_with_model(test_edges, temp_model, (w, h))
            t_warp = time.monotonic()

            edge_score = self._compute_ncc(warped, ref_edges)
            t_ncc = time.monotonic()

            # GCP projection error (if manual GCPs provided)
            gcp_score = 0.0
            if manual_gcps:
                gcp_errors = []
                for gcp in manual_gcps:
                    # Project test pixel using temporary model
                    projected_geo = temp_model.pixel_to_world(gcp.pixel)

                    # Compute error in geographic coordinates (meters)
                    geo_error = np.sqrt(
                        (projected_geo.longitude_deg - gcp.geographic.longitude_deg) ** 2 +
                        (projected_geo.latitude_deg - gcp.geographic.latitude_deg) ** 2
                    )
                    gcp_errors.append(geo_error)

                # Convert GCP errors to a score (lower error = higher score)
                # Use inverse of mean error, scaled to be comparable with edge score
                mean_gcp_error = np.mean(gcp_errors) if gcp_errors else 1.0
                gcp_score = 1.0 / (1.0 + mean_gcp_error)
            t_gcp = time.monotonic()

            if call_n <= 3 or call_n % 500 == 0:
                logging.debug(
                    f'fitness #{call_n}: from_params={1000*(t_model-t_start):.1f}ms, '
                    f'warp={1000*(t_warp-t_model):.1f}ms, '
                    f'ncc={1000*(t_ncc-t_warp):.1f}ms, '
                    f'gcps={1000*(t_gcp-t_ncc):.1f}ms ({len(manual_gcps) if manual_gcps else 0} pts), '
                    f'total={1000*(t_gcp-t_start):.1f}ms'
                )

            normalized_edge_score = (edge_score + 1.0) / 2.0
            if manual_gcps and gcp_weight > 0.0:
                combined_score = (1.0 - gcp_weight) * normalized_edge_score + gcp_weight * gcp_score
            else:
                combined_score = normalized_edge_score
            last_score[0] = combined_score
            return -combined_score

        iteration_counter = [0]

        def cb(xk, convergence):
            iteration_counter[0] += 1
            if iteration_counter[0] % 10 == 0:
                logging.info(f'GA_Optimizer: iteration {iteration_counter[0]}, convergence={convergence:.6f}, score={last_score[0]:.6f}')
            if callback:
                callback(xk, last_score[0])
            return False

        logging.info(f'GA_Optimizer: Starting DE with {len(initial_params)} model parameters, popsize={self._settings.popsize}, maxiter={self._settings.maxiter}')

        x0 = init_params if init_params is not None else initial_params
        logging.debug(f'GA_Optimizer: x0     = [{", ".join(f"{v:.10f}" for v in x0)}]')
        logging.debug(f'GA_Optimizer: bounds = [{", ".join(f"({lo:.10f}, {hi:.10f})" for lo, hi in bounds)}]')

        result = differential_evolution(
            fitness,
            bounds,
            x0=x0,
            maxiter=self._settings.maxiter,
            popsize=self._settings.popsize,
            mutation=self._settings.mutation,
            recombination=self._settings.recombination,
            workers=self._settings.workers,
            polish=self._settings.polish,
            tol=self._settings.tol,
            callback=cb,
            disp=False,
            init='latinhypercube',
        )

        logging.info(f'GA_Optimizer: DE finished after {result.nit} iterations, score={-result.fun:.4f}')

        # Create the final optimized model
        final_model = model.from_params(result.x)

        # Re-evaluate final params to extract component scores for reporting
        final_temp = model.from_params(result.x)
        final_warped = _warp_with_model(test_edges, final_temp, (w, h))
        final_edge_score = (self._compute_ncc(final_warped, ref_edges) + 1.0) / 2.0
        final_gcp_score = 0.0
        effective_gcp_weight = gcp_weight if (manual_gcps and gcp_weight > 0.0) else 0.0
        if manual_gcps:
            gcp_errors = []
            for gcp in manual_gcps:
                projected_geo = final_temp.pixel_to_world(gcp.pixel)
                geo_error = np.sqrt(
                    (projected_geo.longitude_deg - gcp.geographic.longitude_deg) ** 2 +
                    (projected_geo.latitude_deg  - gcp.geographic.latitude_deg)  ** 2
                )
                gcp_errors.append(geo_error)
            final_gcp_score = 1.0 / (1.0 + np.mean(gcp_errors))

        return GA_Result(
            success=result.success,
            transform=None,  # No longer using affine transform
            score=-result.fun,
            edge_score=final_edge_score,
            gcp_score=final_gcp_score,
            gcp_weight=effective_gcp_weight,
            optimized_model=final_model,
            n_iterations=result.nit,
            n_function_evals=result.nfev,
            message=result.message,
        )

    def _params_to_affine(self, params: np.ndarray) -> np.ndarray:
        """Convert 6 parameters to 3x3 affine matrix.

        params: [tx, ty, sx, sxy, syx, sy]
        """
        tx, ty, sx, sxy, syx, sy = params
        return np.array([
            [sx,  sxy, tx],
            [syx, sy,  ty],
            [0,   0,   1]
        ], dtype=np.float64)

    def _compute_ncc(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute normalized cross-correlation between two images.

        NaN pixels in img1 (warped test image border) are excluded so only
        the valid overlap region contributes to the score.

        Returns:
            NCC score in [-1, 1], higher is better match.
        """
        i1 = img1.astype(np.float64).flatten()
        i2 = img2.astype(np.float64).flatten()

        mask = np.isfinite(i1)
        if mask.sum() < 100:
            return 0.0

        i1 = i1[mask]
        i2 = i2[mask]

        i1 -= i1.mean()
        i2 -= i2.mean()

        denom = np.sqrt(np.sum(i1**2) * np.sum(i2**2))
        if denom < 1e-10:
            return 0.0

        return float(np.sum(i1 * i2) / denom)
