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
#    File:    candidate_set.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Spatial sampling and quality ranking of candidate GCP matches.
"""

# Python Standard Libraries
from typing import Tuple

# Third-Party Libraries
import numpy as np


class GCP_Candidate_Set:
    """Spatially-sampled, quality-ranked candidate GCP list.

    Divides the test image into an NxN grid and retains only the
    highest-quality match per cell.  This ensures that candidate GCPs
    span the full image extent rather than clustering around high-texture
    regions.

    Args:
        image_shape: (H, W) of the test image at extraction resolution.
        grid_size:   Side length of the grid (default 8 → 8x8 = 64 max candidates).
    """

    def __init__(self, image_shape: Tuple[int, int], grid_size: int = 8):
        self._h    = image_shape[0]
        self._w    = image_shape[1]
        self._grid = grid_size
        self._cells: dict = {}

    def add(self, pt_test: np.ndarray, pt_ref: np.ndarray, score: float):
        """Offer a candidate match to the set.

        The match is accepted into its grid cell only if the cell is empty
        or this match has a lower (better) descriptor distance than the
        current occupant.

        Args:
            pt_test: (x, y) pixel coordinate in test image space.
            pt_ref:  (x, y) pixel coordinate in reference chip space.
            score:   Quality score — lower descriptor distance is better.
        """
        cx  = int(pt_test[0] / self._w * self._grid)
        cy  = int(pt_test[1] / self._h * self._grid)
        key = (min(cx, self._grid - 1), min(cy, self._grid - 1))
        existing = self._cells.get(key)
        if existing is None or score < existing[2]:
            self._cells[key] = (pt_test, pt_ref, score)

    def get_candidates(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return the selected candidate coordinates.

        Returns:
            Tuple of (pts_test Nx2 float32, pts_ref Nx2 float32).
            Both arrays are empty (shape (0, 2)) if no candidates have been added.
        """
        if not self._cells:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32)
        pts_test = np.array([v[0] for v in self._cells.values()], dtype=np.float32)
        pts_ref  = np.array([v[1] for v in self._cells.values()], dtype=np.float32)
        return pts_test, pts_ref

    @property
    def count(self) -> int:
        """Number of occupied grid cells."""
        return len(self._cells)
