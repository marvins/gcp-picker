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
    """Feature extraction algorithm for automatic GCP matching (ALGO1 only).

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
class Feature_Extraction_Settings:
    """Per-image-source feature extraction parameters (Stage 1).

    One instance is created for the test image and one for the reference chip;
    they can have independent pyramid levels, CLAHE, and feature counts.

    Attributes:
        max_features:  Maximum keypoints returned by the detector.
        pyramid_level: Downsampling before extraction (0 = full res,
                       1 = ½, 2 = ¼, 3 = ⅛).  Test images typically need
                       level 2; reference chips are already display-res so 0.
        clahe:         Apply CLAHE contrast enhancement before extraction.
                       Useful for 16-bit / IR imagery; disable for
                       pre-normalised tile imagery.
        akaze:         AKAZE-specific tunable parameters.
        orb:           ORB-specific tunable parameters.
    """
    max_features:  int          = 2000
    pyramid_level: int          = 0
    clahe:         bool         = False
    akaze:         AKAZE_Params = field(default_factory=AKAZE_Params)
    orb:           ORB_Params   = field(default_factory=ORB_Params)

    def to_log_string(self, keypoint_algo: 'Match_Algo') -> str:
        lines = [f'max_features={self.max_features}, pyramid={self.pyramid_level}, clahe={self.clahe}']
        if keypoint_algo == Match_Algo.AKAZE:
            p = self.akaze
            lines.append(f'akaze(threshold={p.threshold}, octaves={p.n_octaves}, layers={p.n_octave_layers})')
        else:
            p = self.orb
            lines.append(f'orb(scale={p.scale_factor}, levels={p.n_levels}, edge={p.edge_threshold}, patch={p.patch_size})')
        return ', '.join(lines)


@dataclass
class Matching_Settings:
    """Descriptor matching parameters (Stage 2).

    Attributes:
        ratio_test: Lowe ratio test threshold (0–1, lower = stricter).
        matcher:    Nearest-neighbour matcher backend.
    """
    ratio_test: float        = 0.75
    matcher:    Matcher_Type = Matcher_Type.FLANN

    def to_log_string(self) -> str:
        return f'matcher={self.matcher.value.upper()}, ratio={self.ratio_test}'


@dataclass
class Outlier_Settings:
    """Outlier rejection parameters (Stage 3).

    Attributes:
        rejection_method: Algorithm used (RANSAC or MAGSAC).
        inlier_threshold: Maximum reprojection error (pixels) to count as inlier.
    """
    rejection_method:  Rejection_Method = Rejection_Method.RANSAC
    inlier_threshold:  float            = 3.0

    def to_log_string(self) -> str:
        return f'rejection={self.rejection_method.value.upper()}, threshold={self.inlier_threshold}px'


@dataclass
class Algo1_Settings:
    """Settings for the keypoint-based ALGO1 pipeline.

    Attributes:
        keypoint_algo:    Feature extractor selection (AKAZE or ORB).
        test_extraction:  Feature extraction settings for the test image.
        ref_extraction:   Feature extraction settings for the reference chip.
        matching:         Descriptor matching settings.
        outlier:          Geometric outlier rejection settings.
    """
    keypoint_algo:   Match_Algo                = Match_Algo.AKAZE
    test_extraction: Feature_Extraction_Settings = field(
        default_factory=lambda: Feature_Extraction_Settings(
            max_features=2000, pyramid_level=0, clahe=True
        )
    )
    ref_extraction:  Feature_Extraction_Settings = field(
        default_factory=lambda: Feature_Extraction_Settings(
            max_features=2000, pyramid_level=0, clahe=False
        )
    )
    matching:        Matching_Settings         = field(default_factory=Matching_Settings)
    outlier:         Outlier_Settings          = field(default_factory=Outlier_Settings)

    def to_log_string(self) -> str:
        """Return a compact human-readable summary of ALGO1 settings."""
        return (
            f'keypoint={self.keypoint_algo.value.upper()} | '
            f'test[{self.test_extraction.to_log_string(self.keypoint_algo)}] | '
            f'ref[{self.ref_extraction.to_log_string(self.keypoint_algo)}] | '
            f'{self.matching.to_log_string()} | '
            f'{self.outlier.to_log_string()}'
        )


@dataclass
class Debug_Settings:
    """Debug settings for saving intermediate results.

    Attributes:
        save_test_sobel:      Whether to save the test image Sobel edge image to disk.
        save_ref_sobel:       Whether to save the reference chip Sobel edge image to disk.
        output_directory:     Directory path for debug output files.
        save_intermediate_steps: Save additional intermediate processing steps.
    """
    save_test_sobel:         bool   = False
    save_ref_sobel:          bool   = False
    output_directory:       str    = "temp/debug"
    save_intermediate_steps: bool   = False


@dataclass
class Edge_Alignment_Settings:
    """Settings for the edge-based GA pipeline.

    Attributes:
        sobel_kernel_size: Sobel operator kernel size (1, 3, 5, or 7).
        sobel_threshold:  Hard threshold on normalized magnitude (0.0 = disabled, 0.0-1.0 scale).
        test_pre_blur:    Gaussian blur kernel for test image before Sobel (0 = disabled).
                          Use to suppress pixel-level noise in high-res imagery.
        test_dilation:    Morphological dilation iterations for test edges (0 = disabled).
        ref_pre_blur:     Gaussian blur kernel for reference chip before Sobel (0 = disabled).
        ref_dilation:     Morphological dilation iterations for reference edges (0 = disabled).
        gcp_weight:       Weight [0.0-1.0] of GCP reprojection score in GA fitness.
                          0.0 = edges only (recommended); 1.0 = GCPs only.
        ga_popsize:       Population size for differential evolution.
        ga_maxiter:       Maximum iterations for differential evolution.
        ga_mutation:      Mutation factor tuple (min, max) for DE.
        ga_recombination: Recombination/crossover probability for DE.
        ga_max_edge_dim:  Maximum edge image dimension before downsampling for GA fitness.
                          Higher = more detail preserved but slower per-iteration.
        search_bounds_px: Search bounds in pixels for transform parameters.
        debug:            Debug settings for saving intermediate results.
    """
    sobel_kernel_size:  int           = 3
    sobel_threshold:    float         = 0.0
    test_pre_blur:      int           = 0
    test_dilation:      int           = 3
    ref_pre_blur:       int           = 0
    ref_dilation:       int           = 3
    gcp_weight:         float         = 0.0
    ga_popsize:       int           = 15
    ga_maxiter:       int           = 200
    ga_mutation:      tuple[float, float] = (0.5, 1.0)
    ga_recombination: float         = 0.7
    ga_max_edge_dim:  int           = 2048
    search_bounds_px: float         = 50.0  # Prior ±50px search range
    debug:            Debug_Settings = field(default_factory=Debug_Settings)

    def to_log_string(self) -> str:
        """Return a compact human-readable summary of edge alignment settings."""
        return (
            f'sobel_kernel={self.sobel_kernel_size}, sobel_threshold={self.sobel_threshold}, '
            f'test(pre_blur={self.test_pre_blur}, dilation={self.test_dilation}), '
            f'ref(pre_blur={self.ref_pre_blur}, dilation={self.ref_dilation}), '
            f'gcp_weight={self.gcp_weight}, '
            f'GA(popsize={self.ga_popsize}, maxiter={self.ga_maxiter}, '
            f'mutation={self.ga_mutation}, recombination={self.ga_recombination}) | '
            f'search_bounds=±{self.search_bounds_px}px'
        )


@dataclass
class Auto_Match_Settings:
    """Top-level settings composing all pipeline stage configurations.

    Attributes:
        feature_settings: Settings for feature-based matching (AKAZE/ORB).
        edge_settings:    Settings for edge-based alignment (Sobel + GA).
        use_manual_prior: Seed footprint and spatial filter from existing manual GCPs.
    """
    feature_settings: Algo1_Settings | None = field(default_factory=Algo1_Settings)
    edge_settings:    Edge_Alignment_Settings | None = field(default_factory=Edge_Alignment_Settings)
    use_manual_prior: bool          = True

    def to_log_string(self) -> str:
        """Return a compact human-readable summary of all settings."""
        base = f'manual_prior={self.use_manual_prior}'
        if self.feature_settings is not None:
            return f'{base} | Feature: {self.feature_settings.to_log_string()}'
        elif self.edge_settings is not None:
            return f'{base} | Edge: {self.edge_settings.to_log_string()}'
        return base
