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
from pointy.core.auto_match import Auto_Match_Settings, Match_Algo


class Feature_Extractor(abc.ABC):
    """Abstract base class for detector/descriptor wrappers.

    Subclasses wrap a single OpenCV feature extractor and expose a uniform
    ``extract`` interface.  All parameters come from ``Auto_Match_Settings``.
    """

    @abc.abstractmethod
    def extract(self, image: np.ndarray) -> Tuple[List, np.ndarray | None]:
        """Detect keypoints and compute descriptors.

        Args:
            image: uint8 array, (H, W) grayscale or (H, W, C) colour.

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
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

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

    def __init__(self, settings: Auto_Match_Settings):
        p = settings.akaze
        self._det = cv2.AKAZE_create(
            threshold     = p.threshold,
            nOctaves      = p.n_octaves,
            nOctaveLayers = p.n_octave_layers,
            max_points    = settings.max_features,
        )
        self._clahe         = settings.clahe
        self._pyramid_level = settings.pyramid_level

    def extract(self, image: np.ndarray) -> Tuple[List, np.ndarray | None]:
        img = self.to_gray(image)
        img = self.downscale(img, self._pyramid_level)
        if self._clahe:
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

    def __init__(self, settings: Auto_Match_Settings):
        p = settings.orb
        self._det = cv2.ORB_create(
            nfeatures     = settings.max_features,
            scaleFactor   = p.scale_factor,
            nlevels       = p.n_levels,
            edgeThreshold = p.edge_threshold,
            patchSize     = p.patch_size,
            WTA_K         = p.wta_k,
        )
        self._clahe         = settings.clahe
        self._pyramid_level = settings.pyramid_level

    def extract(self, image: np.ndarray) -> Tuple[List, np.ndarray | None]:
        img = self.to_gray(image)
        img = self.downscale(img, self._pyramid_level)
        if self._clahe:
            img = self.apply_clahe(img)
        kps, desc = self._det.detectAndCompute(img, None)
        if not kps:
            return [], None
        return list(kps), desc


def make_extractor(settings: Auto_Match_Settings) -> Feature_Extractor:
    """Factory: return the correct ``Feature_Extractor`` for ``settings.algo``.

    Args:
        settings: Current ``Auto_Match_Settings`` from the panel.

    Returns:
        Concrete ``Feature_Extractor`` instance.

    Raises:
        ValueError: If ``settings.algo`` is not a supported ``Match_Algo``.
    """
    if settings.algo == Match_Algo.AKAZE:
        return AKAZE_Extractor(settings)
    if settings.algo == Match_Algo.ORB:
        return ORB_Extractor(settings)
    raise ValueError(f'Unsupported algorithm: {settings.algo}')
