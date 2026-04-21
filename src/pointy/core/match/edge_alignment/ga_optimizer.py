#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#*
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
from typing import Any, Callable

# Third-Party Libraries
import cv2
import numpy as np
from scipy.optimize import differential_evolution

# Project Libraries
from tmns.geo.coord import Pixel
from tmns.geo.proj.affine import Affine
from tmns.geo.proj.factory import create_projector
from tmns.geo.proj.base import Transformation_Type

@dataclass
class GA_Result:
    """Result container for genetic algorithm optimization.

    Attributes:
        success:          Whether optimization converged.
        transform:        3x3 homography or affine matrix (best fit) - deprecated.
        score:            Final correlation score (higher is better).
        n_iterations:     Number of iterations performed.
        n_function_evals: Number of fitness evaluations.
        message:          Optimizer exit message.
        optimized_model:  The optimized projector model (Affine or RPC).
    """
    success:          bool
    transform:        np.ndarray | None
    score:            float
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


def _affine_param_bounds(model: Affine, bounds_px: float = 50.0) -> list[tuple[float, float]]:
    """Compute differential-evolution bounds for an Affine model's 6 parameters.

    Projects the 4 image corners to geographic space and derives per-coefficient
    bounds scaled by bounds_px (in pixels).

    Args:
        model:     Fitted Affine projector with _image_size set.
        bounds_px: Translation search radius in pixels.

    Returns:
        List of (min, max) bounds for [m00, m01, m02, m10, m11, m12].
    """
    if model._image_size is None:
        raise ValueError("Affine model has no image_size — cannot derive param bounds.")

    params = model.to_params()
    w, h = model._image_size

    corners = [
        Pixel(x_px=0,     y_px=0),
        Pixel(x_px=w - 1, y_px=0),
        Pixel(x_px=w - 1, y_px=h - 1),
        Pixel(x_px=0,     y_px=h - 1),
    ]
    geos = [model.source_to_geographic(c) for c in corners]
    lons = [g.longitude_deg for g in geos]
    lats = [g.latitude_deg  for g in geos]

    d_lon_per_px = (max(lons) - min(lons)) / w
    d_lat_per_px = (max(lats) - min(lats)) / h

    return [
        (params[0] - d_lon_per_px * 0.2, params[0] + d_lon_per_px * 0.2),                # m00
        (params[1] - d_lon_per_px * 0.2, params[1] + d_lon_per_px * 0.2),                # m01
        (min(lons) - d_lon_per_px * bounds_px, max(lons) + d_lon_per_px * bounds_px),    # m02 (tx)
        (params[3] - d_lat_per_px * 0.2, params[3] + d_lat_per_px * 0.2),                # m10
        (params[4] - d_lat_per_px * 0.2, params[4] + d_lat_per_px * 0.2),                # m11
        (min(lats) - d_lat_per_px * bounds_px, max(lats) + d_lat_per_px * bounds_px),    # m12 (ty)
    ]


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
                       bounds_px: float = 50.0,
                       callback: Callable | None = None,
                       init_params: np.ndarray | None = None,
                       manual_gcps: list | None = None) -> GA_Result:
        """Optimize model parameters using differential evolution.

        Args:
            test_edges: Test edge image (H, W) uint8.
            ref_edges:  Reference edge image (H, W) uint8.
            model:      Projector model (Affine or RPC) to optimize.
            bounds_px:  Search bounds for parameter variations.
            callback:   Optional callback(params, score) for progress.
            init_params: Optional initial model parameters for warm-starting.
            manual_gcps: Optional list of manual GCPs to include in fitness evaluation.

        Returns:
            GA_Result with best model parameters and optimization info.
        """
        # Downsample edge images for faster fitness evaluation
        MAX_EDGE_DIM = 512
        h_full, w_full = ref_edges.shape[:2]
        scale = min(MAX_EDGE_DIM / h_full, MAX_EDGE_DIM / w_full, 1.0)
        if scale < 1.0:
            new_w = int(w_full * scale)
            new_h = int(h_full * scale)
            test_edges = cv2.resize(test_edges, (new_w, new_h), interpolation=cv2.INTER_AREA)
            ref_edges  = cv2.resize(ref_edges,  (new_w, new_h), interpolation=cv2.INTER_AREA)
            logging.info(f'GA_Optimizer: downsampled edges {w_full}x{h_full} -> {new_w}x{new_h} (scale={scale:.3f})')

        h, w = ref_edges.shape[:2]

        # Extract initial model parameters and compute bounds
        initial_params = model.to_params()
        bounds = _affine_param_bounds(model, bounds_px=bounds_px)

        def _warp_with_model(image: np.ndarray, model: Projector, output_size: tuple[int, int]) -> np.ndarray:
            """Warp image using the provided model."""
            h, w = output_size

            model_type = model.transformation_type

            if model_type == Transformation_Type.AFFINE:
                # Use affine warp
                if model._inverse_matrix is None:
                    raise ValueError("Model has no inverse matrix")

                # Create coordinate grids for output image
                y_coords, x_coords = np.mgrid[0:h, 0:w]

                # Create pixel coordinate arrays
                coords = np.stack([x_coords.ravel(), y_coords.ravel(), np.ones_like(x_coords.ravel())])

                # Apply inverse transform to get source coordinates
                source_coords = model._inverse_matrix @ coords
                source_x = source_coords[0].reshape(h, w)
                source_y = source_coords[1].reshape(h, w)

                # Warp using OpenCV
                warped = cv2.remap(image, source_x.astype(np.float32), source_y.astype(np.float32),
                                 cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                return warped
            else:
                # For RPC models, fall back to identity for now (this needs proper implementation)
                return cv2.resize(image, (w, h))

        fitness_call_counter = [0]

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
                    projected_geo = temp_model.source_to_geographic(gcp.test_pixel)

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
            combined_score = 0.7 * normalized_edge_score + 0.3 * gcp_score
            return -combined_score

        iteration_counter = [0]

        def cb(xk, convergence):
            iteration_counter[0] += 1
            if iteration_counter[0] % 10 == 0:
                score = -fitness(xk)
                logging.info(f'GA_Optimizer: iteration {iteration_counter[0]}, convergence={convergence:.6f}, score={score:.6f}')
            if callback:
                callback(xk, -fitness(xk))
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

        return GA_Result(
            success=result.success,
            transform=None,  # No longer using affine transform
            score=-result.fun,
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

        Returns:
            NCC score in [-1, 1], higher is better match.
        """
        i1 = img1.astype(np.float64).flatten()
        i2 = img2.astype(np.float64).flatten()

        i1 -= i1.mean()
        i2 -= i2.mean()

        denom = np.sqrt(np.sum(i1**2) * np.sum(i2**2))
        if denom < 1e-10:
            return 0.0

        return np.sum(i1 * i2) / denom
