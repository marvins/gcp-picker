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
#    File:    test_ga_fitness_single.py
#    Author:  Marvin Smith
#    Date:    04/21/2026
#
"""
Single-shot GA fitness diagnostic test.

Loads the real test + reference imagery from the live config, runs Sobel edge
detection once, then evaluates the fitness function a single time at the known
x0 (initial model parameters from the log).  Prints a detailed breakdown so we
can verify the warp, NCC, and GCP components are working correctly before
running the full 100k-evaluation GA.

Run with:
    pytest test/integration/test_ga_fitness_single.py -s -v
"""

# Python Standard Libraries
import logging
import sys
import time
from pathlib import Path

# Third-Party Libraries
import cv2
import numpy as np
import pytest

# Project Libraries
from pointy.apps.auto_model_solver.config import Configuration
from pointy.apps.auto_model_solver.init_utilities import load_reference_imagery, load_test_image
from pointy.core.match.edge_alignment.edge_aligner import (
    Edge_Aligner,
    bootstrap_affine_from_projector,
    cold_start_affine_projector,
)
from pointy.core.match.edge_alignment.ga_optimizer import GA_Optimizer, GA_Settings
from pointy.core.match.edge_alignment.sobel_edges import Sobel_Edges, Sobel_Edge_Settings
from pointy.core.ortho_model_persistence import apply_model_to_projector, load_ortho_model
from tmns.geo.coord import Pixel
from tmns.geo.proj import Transformation_Type
from tmns.geo.proj.affine import Affine
from tmns.geo.proj.factory import create_projector

# Configure logging - filter rasterio noise
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    datefmt='%H:%M:%S'
)
# Suppress rasterio DEBUG logs
logging.getLogger('rasterio').setLevel(logging.WARNING)
logging.getLogger('rasterio._env').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CONFIG_PATH = 'options.auto-model-solver.cfg'


def _load_config_and_data():
    """Load config, test image, reference chip, and ortho model.

    Mirrors the setup in main.py but bypasses argparse so it can be called
    from pytest without sys.argv interference.
    """
    old_argv = sys.argv[:]
    sys.argv = ['test', '-c', CONFIG_PATH, '-v']
    try:
        config = Configuration.parse()
    finally:
        sys.argv = old_argv

    test_image = load_test_image(config, logger)

    ortho_sidecar = load_ortho_model(Path(config.test_image.path))
    ortho_model = None
    ortho_model_bounds = None
    if ortho_sidecar:
        model_type = Transformation_Type(ortho_sidecar.metadata.model_type)
        ortho_model = create_projector(model_type)
        apply_model_to_projector(ortho_model, ortho_sidecar.model_data,
                                 ortho_sidecar.metadata.model_type)
        ortho_model_bounds = config.get_ortho_model_bounds(
            config.test_image.path, test_image.shape[:2]
        )

    ref_chip, bounds, geo_transform = load_reference_imagery(config, logger, ortho_model_bounds)

    manual_gcps = []
    gcp_proc = config.load_manual_gcps()
    if gcp_proc:
        manual_gcps = list(gcp_proc.gcps.values())

    return config, test_image, ref_chip, bounds, geo_transform, ortho_model, manual_gcps


@pytest.mark.integration
def test_single_fitness_call():
    """Run one fitness evaluation and print the full breakdown."""
    config, test_image, ref_chip, bounds, geo_transform, ortho_model, manual_gcps = \
        _load_config_and_data()

    edge_settings = config.auto_match.edge_settings

    # --- Sobel edge detection ---
    t0 = time.perf_counter()
    test_detector = Sobel_Edges(Sobel_Edge_Settings(
        kernel_size=edge_settings.sobel_kernel_size,
        dilation=edge_settings.test_dilation,
        threshold=edge_settings.sobel_threshold,
        pre_blur_kernel=edge_settings.test_pre_blur,
    ))
    ref_detector = Sobel_Edges(Sobel_Edge_Settings(
        kernel_size=edge_settings.sobel_kernel_size,
        dilation=edge_settings.ref_dilation,
        threshold=edge_settings.sobel_threshold,
        pre_blur_kernel=edge_settings.ref_pre_blur,
    ))
    test_edges = test_detector.detect(test_image)
    ref_edges  = ref_detector.detect(ref_chip)
    t_sobel = time.perf_counter() - t0
    logger.info(
        f'Sobel detection complete in {t_sobel:.2f}s\n'
        f'  test_edges: shape={test_edges.shape}, min={test_edges.min():.4f}, '
        f'max={test_edges.max():.4f}, nonzero={np.count_nonzero(test_edges)}\n'
        f'  ref_edges:  shape={ref_edges.shape},  min={ref_edges.min():.4f}, '
        f'max={ref_edges.max():.4f}, nonzero={np.count_nonzero(ref_edges)}'
    )

    assert test_edges.max() > 0, "test_edges are all zero — Sobel produced no output"
    assert ref_edges.max()  > 0, "ref_edges are all zero — Sobel produced no output"

    # --- Build bootstrap Affine using the public helper functions ---
    h_test, w_test = test_image.shape[:2]
    h_ref,  w_ref  = ref_chip.shape[:2]
    if ortho_model is not None:
        logger.info(f'Bootstrapping Affine from {type(ortho_model).__name__} prior model')
        affine_model = bootstrap_affine_from_projector(ortho_model, w_test, h_test)
    else:
        logger.info('No prior model — cold-starting Affine from ref geo extent')
        affine_model = cold_start_affine_projector(w_test, h_test, w_ref, h_ref, geo_transform)
    assert affine_model is not None, "No projector resolved"
    assert isinstance(affine_model, Affine), f"Expected Affine, got {type(affine_model)}"

    x0 = affine_model.to_params()
    logger.info(
        f'Bootstrap Affine params (x0):\n'
        f'  [{", ".join(f"{v:.10f}" for v in x0)}]'
    )

    # --- Build geo coord lookup (same logic as GA optimizer) ---
    MAX_DIM = edge_settings.ga_max_edge_dim
    h_ref_full, w_ref_full   = ref_edges.shape[:2]
    h_test_full, w_test_full = test_edges.shape[:2]
    ref_scale  = min(MAX_DIM / h_ref_full,  MAX_DIM / w_ref_full,  1.0)
    test_scale = min(MAX_DIM / h_test_full, MAX_DIM / w_test_full, 1.0)
    t_resize = time.perf_counter()
    ref_edges_ds  = cv2.resize(ref_edges,  (int(w_ref_full * ref_scale),   int(h_ref_full * ref_scale)),   interpolation=cv2.INTER_AREA) if ref_scale < 1.0 else ref_edges
    test_edges_ds = cv2.resize(test_edges, (int(w_test_full * test_scale), int(h_test_full * test_scale)), interpolation=cv2.INTER_AREA) if test_scale < 1.0 else test_edges
    t_resize = time.perf_counter() - t_resize

    h_ds, w_ds = ref_edges_ds.shape[:2]
    n_pixels = h_ds * w_ds
    geo_coords_mb = n_pixels * 3 * 8 / 1024 / 1024  # 3 rows x float64
    logger.info(
        f'Downsampled edges ({t_resize*1000:.0f}ms resize):\n'
        f'  MAX_DIM={MAX_DIM}, ref_scale={ref_scale:.4f}, test_scale={test_scale:.4f}\n'
        f'  ref:  {w_ref_full}x{h_ref_full} -> {w_ds}x{h_ds}\n'
        f'  test: {w_test_full}x{h_test_full} -> {test_edges_ds.shape[1]}x{test_edges_ds.shape[0]}\n'
        f'  geo_coords array: {n_pixels:,} pixels x 3 x float64 = {geo_coords_mb:.0f} MB'
    )

    # Build ref geo coords for downsampled grid
    t_geo = time.perf_counter()
    full_w = w_ref_full - 1.0
    full_h = h_ref_full - 1.0
    lon00, lat00 = geo_transform(0.0,    0.0)
    lon10, lat10 = geo_transform(full_w, 0.0)
    lon01, lat01 = geo_transform(0.0,    full_h)
    d_lon_dx = (lon10 - lon00) / max(w_ds - 1, 1)
    d_lon_dy = (lon01 - lon00) / max(h_ds - 1, 1)
    d_lat_dx = (lat10 - lat00) / max(w_ds - 1, 1)
    d_lat_dy = (lat01 - lat00) / max(h_ds - 1, 1)

    ref_y_grid, ref_x_grid = np.mgrid[0:h_ds, 0:w_ds]
    ref_x_flat = ref_x_grid.ravel().astype(np.float64)
    ref_y_flat = ref_y_grid.ravel().astype(np.float64)
    ref_lons = lon00 + d_lon_dx * ref_x_flat + d_lon_dy * ref_y_flat
    ref_lats = lat00 + d_lat_dx * ref_x_flat + d_lat_dy * ref_y_flat
    ref_geo_coords = np.stack([ref_lons, ref_lats, np.ones(len(ref_lons))])
    t_geo = time.perf_counter() - t_geo

    logger.info(
        f'Ref geo coords built in {t_geo*1000:.0f}ms:\n'
        f'  lon=[{ref_lons.min():.6f}, {ref_lons.max():.6f}]\n'
        f'  lat=[{ref_lats.min():.6f}, {ref_lats.max():.6f}]'
    )

    # --- Single fitness evaluation at x0 ---
    inv_mat = affine_model._inverse_matrix
    assert inv_mat is not None, "Affine has no inverse matrix"
    logger.info(f'Inverse matrix:\n{inv_mat}')

    t_warp_start = time.perf_counter()
    src_coords = inv_mat @ ref_geo_coords
    source_x = (src_coords[0].reshape(h_ds, w_ds) * test_scale).astype(np.float32)
    source_y = (src_coords[1].reshape(h_ds, w_ds) * test_scale).astype(np.float32)
    warped = cv2.remap(test_edges_ds, source_x, source_y,
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                       borderValue=np.nan)
    t_warp = time.perf_counter() - t_warp_start

    valid_mask = np.isfinite(warped)
    valid_count = int(valid_mask.sum())
    total_count = warped.size

    logger.info(
        f'Warp result ({t_warp*1000:.1f}ms):\n'
        f'  source_x range: [{source_x.min():.1f}, {source_x.max():.1f}]\n'
        f'  source_y range: [{source_y.min():.1f}, {source_y.max():.1f}]\n'
        f'  valid pixels: {valid_count} / {total_count} ({100*valid_count/total_count:.1f}%)\n'
        f'  warped min/max (valid): {warped[valid_mask].min():.4f} / {warped[valid_mask].max():.4f}'
    )

    # NCC over valid overlap only
    optimizer = GA_Optimizer(GA_Settings())
    ncc = optimizer._compute_ncc(warped, ref_edges_ds)
    edge_score = (ncc + 1.0) / 2.0
    logger.info(f'NCC score: {ncc:.6f}  ->  edge_score (normalised): {edge_score:.6f}')

    assert valid_count > 1000, \
        f"Too few valid warp pixels ({valid_count}) — warp is likely mapping outside image"
    assert ncc != 0.0, \
        "NCC is exactly 0.0 — warp is producing a blank or constant image"

    logger.info("PASS — fitness function is producing real signal")
