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
#    File:    sobel_edges.py
#    Author:  Marvin Smith
#    Date:    04/17/2026
#
"""
Sobel edge detection with optional morphological dilation.

Provides edge images for edge-based genetic algorithm alignment.
"""

# Python Standard Libraries
from dataclasses import dataclass

# Third-Party Libraries
import cv2
import numpy as np


@dataclass
class Sobel_Edge_Settings:
    """Configuration for Sobel edge detection.

    Attributes:
        kernel_size:    Sobel kernel size (must be 1, 3, 5, or 7).
        dilation:       Morphological dilation iterations (0 = no dilation).
        threshold:       Optional threshold on normalized magnitude (0.0 = disabled, 0.0-1.0 scale).
        pre_blur_kernel: Gaussian blur kernel size applied before Sobel (0 = disabled,
                         must be odd). Use to suppress high-frequency noise in
                         high-resolution images before edge detection.
    """
    kernel_size:     int   = 3
    dilation:        int   = 3
    threshold:       float = 0.0
    pre_blur_kernel: int = 0


class Sobel_Edges:
    """Sobel gradient-based edge detector with optional dilation.

    Computes edge magnitude using Sobel operators in X and Y directions,
    optionally thresholds and dilates edges for robustness.
    """

    def __init__(self, settings: Sobel_Edge_Settings):
        self._settings = settings

    def detect(self, image: np.ndarray) -> np.ndarray:
        """Detect edges in grayscale or RGB image.

        Args:
            image: Input image (H, W) grayscale or (H, W, C) uint8.

        Returns:
            Edge magnitude image (H, W) float32, normalized to [0, 1].
        """
        gray = self._to_grayscale(image)
        gray = self._normalize(gray)

        if self._settings.pre_blur_kernel > 0:
            k = self._settings.pre_blur_kernel | 1  # ensure odd
            gray = cv2.GaussianBlur(gray, (k, k), 0)

        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=self._settings.kernel_size)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=self._settings.kernel_size)
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)

        edges = cv2.normalize(magnitude, None, 0.0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)

        if self._settings.threshold > 0.0:
            edges = (edges >= self._settings.threshold).astype(np.float32)

        if self._settings.dilation > 0:
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=self._settings.dilation)

        return edges

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale if needed."""
        if len(image.shape) == 3 and image.shape[2] >= 3:
            return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        if len(image.shape) == 3 and image.shape[2] == 1:
            return image.squeeze(axis=2)
        return image.copy()

    def _normalize(self, image: np.ndarray) -> np.ndarray:
        """Normalize to uint8 if needed."""
        if image.dtype != np.uint8:
            return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return image
