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
#    File:    __init__.py
#    Author:  Marvin Smith
#    Date:    04/17/2026
#
"""
pointy.core.match.algo1 — Keypoint-based automatic GCP matching (ALGO1).

This module contains the keypoint-based matching pipeline using AKAZE or ORB
descriptors with kNN matching, Lowe ratio test, and RANSAC outlier rejection.

Public API
----------
Feature_Extractor   — ABC for detector/descriptor wrappers
AKAZE_Extractor     — cv2.AKAZE_create() wrapper
ORB_Extractor       — cv2.ORB_create() wrapper
make_extractor      — factory driven by Match_Algo enum
Feature_Matcher     — kNN + Lowe ratio test
Outlier_Filter      — ABC for geometric outlier filters
RANSAC_Filter       — cv2.findHomography RANSAC
MAGSAC_Filter       — cv2.findHomography USAC_MAGSAC
make_outlier_filter — factory driven by Rejection_Method enum
Pipeline            — GCP_Solver_Pipeline.run() implementation for feature matching
"""

from pointy.core.match.extractor import (
    Feature_Extractor,
    AKAZE_Extractor,
    ORB_Extractor,
    make_extractor,
)
from pointy.core.match.matcher import Feature_Matcher
from pointy.core.match.outlier_filter import (
    Outlier_Filter,
    RANSAC_Filter,
    MAGSAC_Filter,
    make_outlier_filter,
)
from pointy.core.match.gcp_solver_pipeline import GCP_Solver_Pipeline as _Pipeline

__all__ = [
    'Feature_Extractor',
    'AKAZE_Extractor',
    'ORB_Extractor',
    'make_extractor',
    'Feature_Matcher',
    'Outlier_Filter',
    'RANSAC_Filter',
    'MAGSAC_Filter',
    'make_outlier_filter',
]
