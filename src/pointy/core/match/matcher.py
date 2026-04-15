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
#    File:    matcher.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Descriptor matching with Lowe ratio test for the automatic GCP pipeline.
"""

# Python Standard Libraries
import logging
from typing import List

# Third-Party Libraries
import cv2
import numpy as np

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings, Matcher_Type, Match_Algo


class Feature_Matcher:
    """Nearest-neighbour descriptor matching with Lowe ratio test.

    Handles both float descriptors (AKAZE default MLDB = uint8 binary,
    KAZE = float32) and binary descriptors (ORB) by detecting the dtype
    and selecting the appropriate distance metric and index type.

    For ORB with ``WTA_K`` = 3 or 4 the correct BF norm is ``NORM_HAMMING2``
    rather than ``NORM_HAMMING``.
    """

    def __init__(self, settings: Auto_Match_Settings):
        self._ratio        = settings.matching.ratio_test
        self._matcher_type = settings.matching.matcher
        self._algo         = settings.algo
        self._wta_k        = settings.test_extraction.orb.wta_k

    def match(self, desc_test: np.ndarray,
              desc_ref:  np.ndarray) -> List[cv2.DMatch]:
        """Run kNN(k=2) + Lowe ratio test.

        Args:
            desc_test: Descriptors from the test image  (N, D).
            desc_ref:  Descriptors from the reference chip (M, D).

        Returns:
            List of ``cv2.DMatch`` objects that pass the ratio test.
            Empty list if either descriptor array is None or matching fails.
        """
        if desc_test is None or desc_ref is None:
            return []

        cv_matcher = self._build_matcher(desc_test)
        try:
            knn_matches = cv_matcher.knnMatch(desc_test, desc_ref, k=2)
        except cv2.error as exc:
            logging.warning(f'Feature_Matcher.match failed: {exc}')
            return []

        good = []
        for pair in knn_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < self._ratio * n.distance:
                    good.append(m)
        return good

    def _build_matcher(self, desc: np.ndarray) -> cv2.DescriptorMatcher:
        """Instantiate the appropriate OpenCV matcher for the given descriptors.

        Selection logic:
        - Binary (uint8): BF with NORM_HAMMING (or NORM_HAMMING2 for WTA_K 3/4),
          or FLANN with LSH index.
        - Float (float32): BF with NORM_L2, or FLANN with KD-tree index.
        """
        is_binary = desc.dtype == np.uint8

        if self._matcher_type == Matcher_Type.BRUTE_FORCE:
            if is_binary:
                norm = cv2.NORM_HAMMING2 if self._wta_k in (3, 4) else cv2.NORM_HAMMING
            else:
                norm = cv2.NORM_L2
            return cv2.BFMatcher(norm, crossCheck=False)

        # FLANN — LSH index for binary descriptors, KD-tree for float
        if is_binary:
            index_params  = dict(algorithm=6, table_number=6,
                                 key_size=12, multi_probe_level=1)
            search_params = dict(checks=50)
        else:
            index_params  = dict(algorithm=1, trees=5)
            search_params = dict(checks=50)
        return cv2.FlannBasedMatcher(index_params, search_params)
