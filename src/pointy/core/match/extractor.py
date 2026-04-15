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
#    File:    extractor.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Feature extractor wrappers for the automatic GCP matching pipeline.

Classes
-------
Feature_Extractor   — ABC defining the extract() interface + shared image utilities
AKAZE_Extractor     — cv2.AKAZE_create() wrapper
ORB_Extractor       — cv2.ORB_create() wrapper
make_extractor()    — factory function driven by Match_Algo enum
"""

# Python Standard Libraries
import abc
from typing import List, Tuple

# Third-Party Libraries
import cv2
import numpy as np

# Project Libraries
from pointy.core.auto_match import Auto_Match_Settings, Feature_Extraction_Settings, Match_Algo


class Feature_Extractor(abc.ABC):
    """Abstract base class for detector/descriptor wrappers.

    Subclasses wrap a single OpenCV feature extractor and expose a uniform
    ``extract`` interface.  All parameters come from ``Auto_Match_Settings``.
    """

    @abc.abstractmethod
    def extract(self, image: np.ndarray,
                pyramid_override: int | None = None,
                clahe_override: bool | None = None) -> Tuple[List, np.ndarray | None]:
        """Detect keypoints and compute descriptors.

        Args:
            image:            uint8 array, (H, W) grayscale or (H, W, C) colour.
            pyramid_override: If set, overrides the instance pyramid level for
                              this call only (used for the reference chip).
            clahe_override:   If set, overrides the instance CLAHE flag for
                              this call only.

        Returns:
            Tuple of (keypoints, descriptors).
            descriptors is an (N, D) ndarray, or None if no keypoints found.
        """

    @staticmethod
    def apply_clahe(image: np.ndarray) -> np.ndarray:
        """Apply CLAHE contrast enhancement to a grayscale uint8 image."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    @staticmethod
    def to_gray(image: np.ndarray) -> np.ndarray:
        """Convert to single-channel grayscale if needed."""
        if image.ndim == 3 and image.shape[2] > 1:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.ndim == 3 and image.shape[2] == 1:
            # Squeeze the single channel dimension
            return image.squeeze(axis=2)
        return image

    @staticmethod
    def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
        """Normalize any numeric dtype to uint8 using the actual data range.

        For uint8 input, returns as-is.  For higher bit-depth (e.g. uint16,
        float32), stretches the actual min/max to [0, 255].  This preserves
        all visible contrast while producing a dtype that OpenCV feature
        detectors expect.

        Note: pixel *coordinates* reported by the detector are unaffected by
        this normalization — only the radiometric values change.
        """
        if image.dtype == np.uint8:
            return image
        arr = image.astype(np.float32)
        lo, hi = float(arr.min()), float(arr.max())
        if hi <= lo:
            return np.zeros_like(arr, dtype=np.uint8)
        return ((arr - lo) / (hi - lo) * 255.0).astype(np.uint8)

    @staticmethod
    def downscale(image: np.ndarray, level: int) -> np.ndarray:
        """Downscale by 2^level using INTER_AREA (pyramid-style).

        Args:
            image: Input array.
            level: 0 = full resolution; 1 = 1/2; 2 = 1/4; 3 = 1/8.
        """
        if level <= 0:
            return image
        factor = 2 ** level
        h, w = image.shape[:2]
        return cv2.resize(image, (w // factor, h // factor),
                          interpolation=cv2.INTER_AREA)


class AKAZE_Extractor(Feature_Extractor):
    """AKAZE detector + descriptor wrapper.

    Uses ``cv2.AKAZE_create()`` with parameters drawn from
    ``Auto_Match_Settings.akaze`` and ``Auto_Match_Settings.max_features``.

    AKAZE constructor signature (cv2 4.x)::

        cv2.AKAZE_create([, descriptor_type[, descriptor_size[,
            descriptor_channels[, threshold[, nOctaves[, nOctaveLayers[,
            diffusivity[, max_points]]]]]]]]]) -> retval
    """

    def __init__(self, extraction: Feature_Extraction_Settings):
        p = extraction.akaze
        self._det = cv2.AKAZE_create(
            threshold     = p.threshold,
            nOctaves      = p.n_octaves,
            nOctaveLayers = p.n_octave_layers,
            max_points    = extraction.max_features,
        )
        self._clahe         = extraction.clahe
        self._pyramid_level = extraction.pyramid_level

    def extract(self, image: np.ndarray,
                pyramid_override: int | None = None,
                clahe_override: bool | None = None) -> Tuple[List, np.ndarray | None]:
        pyramid = self._pyramid_level if pyramid_override is None else pyramid_override
        use_clahe = self._clahe if clahe_override is None else clahe_override
        img = self.to_gray(image)
        img = self.normalize_to_uint8(img)
        img = self.downscale(img, pyramid)
        if use_clahe:
            img = self.apply_clahe(img)
        kps, desc = self._det.detectAndCompute(img, None)
        if not kps:
            return [], None
        return list(kps), desc


class ORB_Extractor(Feature_Extractor):
    """ORB detector + descriptor wrapper.

    Uses ``cv2.ORB_create()`` with parameters drawn from
    ``Auto_Match_Settings.orb`` and ``Auto_Match_Settings.max_features``.

    ORB constructor signature (cv2 4.x)::

        cv2.ORB_create([, nfeatures[, scaleFactor[, nlevels[, edgeThreshold[,
            firstLevel[, WTA_K[, scoreType[, patchSize[, fastThreshold]]]]]]]]])
            -> retval
    """

    def __init__(self, extraction: Feature_Extraction_Settings):
        p = extraction.orb
        self._det = cv2.ORB_create(
            nfeatures     = extraction.max_features,
            scaleFactor   = p.scale_factor,
            nlevels       = p.n_levels,
            edgeThreshold = p.edge_threshold,
            patchSize     = p.patch_size,
            WTA_K         = p.wta_k,
        )
        self._clahe         = extraction.clahe
        self._pyramid_level = extraction.pyramid_level

    def extract(self, image: np.ndarray,
                pyramid_override: int | None = None,
                clahe_override: bool | None = None) -> Tuple[List, np.ndarray | None]:
        pyramid = self._pyramid_level if pyramid_override is None else pyramid_override
        use_clahe = self._clahe if clahe_override is None else clahe_override
        img = self.to_gray(image)
        img = self.normalize_to_uint8(img)
        img = self.downscale(img, pyramid)
        if use_clahe:
            img = self.apply_clahe(img)
        kps, desc = self._det.detectAndCompute(img, None)
        if not kps:
            return [], None
        return list(kps), desc


def make_extractor(settings: Auto_Match_Settings,
                   extraction: Feature_Extraction_Settings) -> Feature_Extractor:
    """Factory: return a ``Feature_Extractor`` for the given algo and extraction settings.

    Args:
        settings:   Top-level ``Auto_Match_Settings`` (provides the algo enum).
        extraction: Per-source ``Feature_Extraction_Settings`` (test or ref).

    Returns:
        Concrete ``Feature_Extractor`` instance.

    Raises:
        ValueError: If ``settings.algo`` is not a supported ``Match_Algo``.
    """
    if settings.algo == Match_Algo.AKAZE:
        return AKAZE_Extractor(extraction)
    if settings.algo == Match_Algo.ORB:
        return ORB_Extractor(extraction)
    raise ValueError(f'Unsupported algorithm: {settings.algo}')
