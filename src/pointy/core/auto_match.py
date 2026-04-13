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
#    File:    auto_match.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Auto-match types and settings for the automatic GCP picker pipeline.
"""

# Python Standard Libraries
from dataclasses import dataclass, field
from enum import Enum


class Match_Algo(Enum):
    """Feature extraction algorithm for automatic GCP matching.

    Classical algorithms only at this stage.  Deep-learning variants
    (SuperPoint, LightGlue) are reserved for Phase 4 and require an
    optional ``torch`` dependency.

    Values:
        AKAZE: Non-linear scale-space detector/descriptor built into
            OpenCV.  Performs well on aerial and IR imagery.  Default.
        ORB:   Binary descriptor, very fast, no extra dependencies.
            Less robust at large scale or viewpoint changes.
    """
    AKAZE = 'akaze'
    ORB   = 'orb'


class Rejection_Method(Enum):
    """Outlier rejection strategy applied after feature matching."""
    RANSAC = 'ransac'
    MAGSAC = 'magsac'


class Matcher_Type(Enum):
    """Nearest-neighbour descriptor matcher."""
    BRUTE_FORCE = 'bf'
    FLANN       = 'flann'


@dataclass
class AKAZE_Params:
    """Tunable parameters for ``cv2.AKAZE_create()``.

    Attributes:
        threshold:         Detector response threshold to accept a point (default 0.001).
                           Lower → more keypoints detected; higher → fewer, more stable.
        n_octaves:         Maximum octave evolution of the image (default 4).
        n_octave_layers:   Default number of sublevels per scale level (default 4).
        max_points:        Maximum keypoints returned; highest-response kept.
                           -1 means no limit (``max_features`` from ``Auto_Match_Settings``
                           is passed here at runtime).
    """
    threshold:        float = 0.001
    n_octaves:        int   = 4
    n_octave_layers:  int   = 4
    max_points:       int   = -1


@dataclass
class ORB_Params:
    """Tunable parameters for ``cv2.ORB_create()``.

    Attributes:
        scale_factor:   Pyramid decimation ratio > 1 (default 1.2).
                        Smaller values → more pyramid levels needed to cover the same
                        scale range; larger values → faster but coarser scale steps.
        n_levels:       Number of pyramid levels (default 8).
        edge_threshold: Border size (px) where features are not detected (default 31).
                        Should roughly match ``patch_size``.
        patch_size:     Patch size used by the oriented BRIEF descriptor (default 31).
        wta_k:          Points that produce each BRIEF element (2, 3, or 4).
                        2 → NORM_HAMMING; 3 or 4 → NORM_HAMMING2.
    """
    scale_factor:   float = 1.2
    n_levels:       int   = 8
    edge_threshold: int   = 31
    patch_size:     int   = 31
    wta_k:          int   = 2


@dataclass
class Auto_Match_Settings:
    """All configurable parameters for a single auto-match run.

    Attributes:
        algo:              Feature extraction algorithm.
        use_manual_prior:  Seed footprint and spatial filter from existing manual GCPs.
        max_features:      Maximum keypoints detected per image (both algos).
        pyramid_level:     Downsampling level before extraction (0 = full res,
                           1 = 1/2, 2 = 1/4, 3 = 1/8).
        clahe:             Apply CLAHE contrast enhancement before extraction.
        ratio_test:        Lowe ratio test threshold (0–1, lower = stricter).
        matcher:           Nearest-neighbour matcher type.
        rejection_method:  Outlier rejection algorithm.
        inlier_threshold:  RANSAC / MAGSAC inlier distance in pixels.
        akaze:             AKAZE-specific tunable parameters.
        orb:               ORB-specific tunable parameters.
    """
    algo:              Match_Algo       = Match_Algo.AKAZE
    use_manual_prior:  bool             = True
    max_features:      int              = 2000
    pyramid_level:     int              = 2
    clahe:             bool             = True
    ratio_test:        float            = 0.75
    matcher:           Matcher_Type     = Matcher_Type.FLANN
    rejection_method:  Rejection_Method = Rejection_Method.RANSAC
    inlier_threshold:  float            = 3.0
    akaze:             AKAZE_Params     = field(default_factory=AKAZE_Params)
    orb:               ORB_Params       = field(default_factory=ORB_Params)
