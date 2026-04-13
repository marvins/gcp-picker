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
#    Date:    04/12/2026
#
"""
pointy.core.match — automatic GCP matching pipeline.

Public API
----------
Auto_Matcher        — top-level orchestrator; call .run(test, ref, geo_xform)
Match_Result        — output dataclass from Auto_Matcher.run()

Feature_Extractor   — ABC for detector/descriptor wrappers
AKAZE_Extractor     — cv2.AKAZE_create() wrapper
ORB_Extractor       — cv2.ORB_create() wrapper
make_extractor      — factory driven by Match_Algo enum

Feature_Matcher     — kNN + Lowe ratio test

Outlier_Filter      — ABC for geometric outlier filters
RANSAC_Filter       — cv2.findHomography RANSAC
MAGSAC_Filter       — cv2.findHomography USAC_MAGSAC
make_outlier_filter — factory driven by Rejection_Method enum

GCP_Candidate_Set   — spatial-grid candidate sampler
"""

from pointy.core.match.types import Match_Result
from pointy.core.match.extractor import (Feature_Extractor, AKAZE_Extractor,
                                          ORB_Extractor, make_extractor)
from pointy.core.match.matcher import Feature_Matcher
from pointy.core.match.outlier_filter import (Outlier_Filter, RANSAC_Filter,
                                               MAGSAC_Filter, make_outlier_filter)
from pointy.core.match.candidate_set import GCP_Candidate_Set
from pointy.core.match.pipeline import Auto_Matcher

__all__ = [
    'Auto_Matcher',
    'Match_Result',
    'Feature_Extractor',
    'AKAZE_Extractor',
    'ORB_Extractor',
    'make_extractor',
    'Feature_Matcher',
    'Outlier_Filter',
    'RANSAC_Filter',
    'MAGSAC_Filter',
    'make_outlier_filter',
    'GCP_Candidate_Set',
]
