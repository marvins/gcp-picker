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
#    File:    types.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Output types for the automatic GCP matching pipeline.
"""

# Python Standard Libraries
from dataclasses import dataclass, field

# Third-Party Libraries
import numpy as np


@dataclass
class Match_Result:
    """Results returned by ``Auto_Matcher.run()``.

    Attributes:
        candidate_pixels: Nx2 array of pixel coords in the test image.
        candidate_geos:   Nx2 array of (lon, lat) from the reference chip.
        inlier_mask:      Boolean mask marking which candidates survived
                          outlier rejection.  Same length as candidates.
        n_raw_matches:    Total keypoints detected in the test image.
        n_ref_keypoints:  Total keypoints detected in the reference image.
        n_candidates:     Matches after ratio test (before outlier rejection).
        n_inliers:        Matches surviving outlier rejection.
        raw_match_pixels: Nx2 array of test image pixel coords for ratio-test candidates (before RANSAC).
        raw_match_ref_pixels: Nx2 array of reference image pixel coords for ratio-test candidates.
        homography:       3×3 homography matrix (test→ref), or None if failed.
        elapsed_sec:      Total wall-clock time for the run.
        error:            Non-empty string if the run failed, empty otherwise.
    """
    candidate_pixels: np.ndarray        = field(default_factory=lambda: np.empty((0, 2)))
    candidate_geos:   np.ndarray        = field(default_factory=lambda: np.empty((0, 2)))
    inlier_mask:      np.ndarray        = field(default_factory=lambda: np.empty(0, dtype=bool))
    n_raw_matches:    int               = 0
    n_ref_keypoints:  int               = 0
    n_candidates:     int               = 0
    n_inliers:        int               = 0
    raw_match_pixels: np.ndarray        = field(default_factory=lambda: np.empty((0, 2)))
    raw_match_ref_pixels: np.ndarray    = field(default_factory=lambda: np.empty((0, 2)))
    homography:       np.ndarray | None = None
    elapsed_sec:      float             = 0.0
    error:            str               = ''

    @property
    def success(self) -> bool:
        """True if the run completed without error and produced ≥4 inliers."""
        return not self.error and self.n_inliers >= 4
