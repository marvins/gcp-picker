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
#    File:    pipeline.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Top-level Auto_Matcher orchestrator for the automatic GCP pipeline.
"""

# Python Standard Libraries
import logging
import time
from typing import Callable, Tuple

# Third-Party Libraries
import numpy as np

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings
from pointy.core.match.candidate_set import GCP_Candidate_Set
from pointy.core.match.extractor import Feature_Extractor, make_extractor
from pointy.core.gcp import GCP
from pointy.core.match.matcher import Feature_Matcher
from pointy.core.match.outlier_filter import make_outlier_filter
from pointy.core.match.types import Match_Result


class GCP_Solver_Pipeline:
    """Feature-based GCP solving pipeline.

    Composes all four stages into a single ``.run()`` call:

    1. Feature extraction (AKAZE or ORB) on both images.
    2. kNN descriptor matching + Lowe ratio test.
    3. Geometric outlier rejection (RANSAC or MAGSAC).
    4. Spatial candidate GCP sampling (best match per grid cell).

    Usage::

        result = GCP_Solver_Pipeline(settings).run(test_image, ref_chip, geo_transform)
        if result.success:
            pixels = result.candidate_pixels   # Nx2 in test image space
            geos   = result.candidate_geos     # Nx2 (lon, lat)

    Args:
        settings: ``Auto_Match_Settings`` populated from the panel.
    """

    MIN_INLIERS: int = 4

    def __init__(self, settings: Auto_Match_Settings):
        self._settings = settings
        self._algo1_components: dict | None = None

        # Auto_Matcher is for feature-based matching only
        if settings.feature_settings is not None:
            self._algo1_components = {
                'test_extractor': make_extractor(settings, settings.feature_settings.test_extraction),
                'ref_extractor': make_extractor(settings, settings.feature_settings.ref_extraction),
                'matcher': Feature_Matcher(settings),
                'filter': make_outlier_filter(settings),
            }
        else:
            raise ValueError("Auto_Matcher requires feature_settings. Use Edge_Aligner for edge-based alignment.")

    def run(self,
            test_image:        np.ndarray,
            ref_chip:          np.ndarray,
            ref_geo_transform: Callable[[float, float], Tuple[float, float]],
            manual_gcps:        list[GCP] | None = None
            ) -> Match_Result:
        """Execute the ALGO1 pipeline and return a ``Match_Result``.

        Args:
            test_image:        Test image array, (H, W) or (H, W, C) uint8.
            ref_chip:          Reference basemap chip, same shape convention.
            ref_geo_transform: Callable ``(px_x, px_y) -> (lon, lat)`` mapping
                               reference chip pixel coordinates to geographic
                               coordinates.
            manual_gcps:       Optional list of GCP objects (not used in ALGO1).

        Returns:
            ``Match_Result`` with all stage outputs populated.
            Check ``result.success`` before using the candidate arrays.
        """
        return self._run_algo1(test_image, ref_chip, ref_geo_transform)

    def _run_algo1(self,
                   test_image: np.ndarray,
                   ref_chip: np.ndarray,
                   ref_geo_transform: Callable[[float, float], Tuple[float, float]]) -> Match_Result:
        """Execute ALGO1 keypoint-based pipeline."""
        t0     = time.perf_counter()
        result = Match_Result()

        comps = self._algo1_components

        # ── Stage 1: Feature Extraction ──────────────────────────────────────
        te = self._settings.algo1.test_extraction
        re = self._settings.algo1.ref_extraction
        logging.info(
            f'Auto_Matcher: extracting (keypoint_algo={self._settings.algo1.keypoint_algo.value}, '
            f'test[pyramid={te.pyramid_level}, clahe={te.clahe}, max={te.max_features}], '
            f'ref[pyramid={re.pyramid_level}, clahe={re.clahe}, max={re.max_features}])'
        )
        kps_test, desc_test = comps['test_extractor'].extract(test_image)
        kps_ref,  desc_ref  = comps['ref_extractor'].extract(ref_chip)
        logging.info(
            f'Auto_Matcher: {len(kps_test)} test kps, {len(kps_ref)} ref kps'
        )

        if not kps_test or not kps_ref:
            result.error       = 'No keypoints detected in one or both images'
            result.elapsed_sec = time.perf_counter() - t0
            return result

        # ── Stage 2: Descriptor Matching + Ratio Test ─────────────────────────
        good_matches         = comps['matcher'].match(desc_test, desc_ref)
        result.n_raw_matches  = len(kps_test)
        result.n_ref_keypoints = len(kps_ref)
        result.n_candidates   = len(good_matches)
        logging.info(f'Auto_Matcher: {len(good_matches)} matches after ratio test')

        if len(good_matches) < self.MIN_INLIERS:
            result.error       = f'Too few matches after ratio test ({len(good_matches)})'
            result.elapsed_sec = time.perf_counter() - t0
            return result

        scale    = 2 ** self._settings.algo1.test_extraction.pyramid_level
        pts_test = np.array(
            [kps_test[m.queryIdx].pt for m in good_matches], dtype=np.float32
        ) * scale
        pts_ref_px = np.array(
            [kps_ref[m.trainIdx].pt for m in good_matches], dtype=np.float32
        )

        # Store ratio-test candidate coordinates for visualization
        result.raw_match_pixels = pts_test
        result.raw_match_ref_pixels = pts_ref_px

        # ── Stage 3: Outlier Rejection ────────────────────────────────────────
        H, inlier_mask    = comps['filter'].filter(pts_test, pts_ref_px * scale)
        result.n_inliers  = int(inlier_mask.sum())
        result.homography = H
        logging.info(
            f'Auto_Matcher: {result.n_inliers} inliers after '
            f'{self._settings.feature_settings.outlier.rejection_method.value.upper()}'
        )

        if result.n_inliers < self.MIN_INLIERS:
            result.error       = f'Too few inliers ({result.n_inliers})'
            result.elapsed_sec = time.perf_counter() - t0
            return result

        # ── Stage 4: Candidate GCP Set ────────────────────────────────────────
        from pointy.core.match.extractor import Feature_Extractor
        scaled_img     = Feature_Extractor.downscale(test_image, self._settings.feature_settings.test_extraction.pyramid_level)
        h_test, w_test = scaled_img.shape[:2]
        candidates     = GCP_Candidate_Set((h_test, w_test))

        for i, m in enumerate(good_matches):
            if not inlier_mask[i]:
                continue
            candidates.add(pts_test[i], pts_ref_px[i], m.distance)

        cand_pixels, cand_ref_px = candidates.get_candidates()

        cand_geos = np.array(
            [ref_geo_transform(float(x), float(y)) for x, y in cand_ref_px],
            dtype=np.float64,
        )

        result.candidate_pixels = cand_pixels * scale
        result.candidate_geos   = cand_geos
        result.elapsed_sec      = time.perf_counter() - t0

        logging.info(
            f'Auto_Matcher: {len(cand_pixels)} candidates from {len(set(map(tuple, cand_ref_px.tolist())))} '
            f'unique ref points in {result.elapsed_sec:.2f}s'
        )

        return result


