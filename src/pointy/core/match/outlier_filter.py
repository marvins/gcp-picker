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
#    File:    outlier_filter.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Geometric outlier rejection filters for the automatic GCP matching pipeline.

Classes
-------
Outlier_Filter      — ABC defining the filter() interface
RANSAC_Filter       — cv2.findHomography with RANSAC
MAGSAC_Filter       — cv2.findHomography with USAC_MAGSAC (falls back to RANSAC)
make_outlier_filter — factory driven by Rejection_Method enum
"""

# Python Standard Libraries
import abc
import logging
from typing import Tuple

# Third-Party Libraries
import cv2
import numpy as np

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings, Rejection_Method


class Outlier_Filter(abc.ABC):
    """Abstract base for geometric outlier rejection filters."""

    @abc.abstractmethod
    def filter(self,
               pts_test: np.ndarray,
               pts_ref:  np.ndarray) -> Tuple[np.ndarray | None, np.ndarray]:
        """Remove geometrically inconsistent matches.

        Args:
            pts_test: Nx2 float32 keypoint coordinates in the test image.
            pts_ref:  Nx2 float32 keypoint coordinates in the reference chip.

        Returns:
            Tuple of (homography_3x3 | None, inlier_mask).
            ``inlier_mask`` is a boolean ndarray of length N.
        """


class RANSAC_Filter(Outlier_Filter):
    """Homography estimation with standard RANSAC via ``cv2.findHomography``.

    Args:
        inlier_threshold: Maximum reprojection error (px) for a point to be
                          considered an inlier.
    """

    def __init__(self, inlier_threshold: float):
        self._threshold = inlier_threshold

    def filter(self, pts_test: np.ndarray,
               pts_ref: np.ndarray) -> Tuple[np.ndarray | None, np.ndarray]:
        if len(pts_test) < 4:
            return None, np.zeros(len(pts_test), dtype=bool)
        H, mask = cv2.findHomography(pts_test, pts_ref,
                                     cv2.RANSAC, self._threshold)
        if mask is None:
            return None, np.zeros(len(pts_test), dtype=bool)
        return H, mask.ravel().astype(bool)


class MAGSAC_Filter(Outlier_Filter):
    """Homography estimation with MAGSAC++ via ``cv2.findHomography``.

    Uses ``cv2.USAC_MAGSAC`` when available (OpenCV ≥ 4.5.1).  Falls back
    to standard RANSAC on older builds and logs a warning.

    Args:
        inlier_threshold: Maximum reprojection error (px).
    """

    def __init__(self, inlier_threshold: float):
        self._threshold = inlier_threshold

    def filter(self, pts_test: np.ndarray,
               pts_ref: np.ndarray) -> Tuple[np.ndarray | None, np.ndarray]:
        if len(pts_test) < 4:
            return None, np.zeros(len(pts_test), dtype=bool)
        try:
            method = cv2.USAC_MAGSAC
        except AttributeError:
            logging.warning(
                'MAGSAC (cv2.USAC_MAGSAC) not available in this OpenCV build '
                '— falling back to RANSAC'
            )
            method = cv2.RANSAC
        H, mask = cv2.findHomography(pts_test, pts_ref, method, self._threshold)
        if mask is None:
            return None, np.zeros(len(pts_test), dtype=bool)
        return H, mask.ravel().astype(bool)


def make_outlier_filter(settings: Auto_Match_Settings) -> Outlier_Filter:
    """Factory: return the correct ``Outlier_Filter`` for ``settings.rejection_method``.

    Args:
        settings: Current ``Auto_Match_Settings`` from the panel.

    Returns:
        Concrete ``Outlier_Filter`` instance.

    Raises:
        ValueError: If ``settings.rejection_method`` is not supported.
    """
    if settings.rejection_method == Rejection_Method.RANSAC:
        return RANSAC_Filter(settings.inlier_threshold)
    if settings.rejection_method == Rejection_Method.MAGSAC:
        return MAGSAC_Filter(settings.inlier_threshold)
    raise ValueError(f'Unsupported rejection method: {settings.rejection_method}')
