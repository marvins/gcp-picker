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
#    File:    projector.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Projector API - Abstract coordinate transformation interface
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pointy.core.coordinate import Geographic, Pixel


class Transformation_Type(Enum):
    """Supported transformation types for coordinate projections."""
    IDENTITY = "identity"
    AFFINE = "affine"
    RPC = "rpc"
    TPS = "tps"


class Projector(ABC):
    """Abstract base class for coordinate transformation projectors."""

    def __init__(self):
        self._source_image_attrs: Dict[str, Any] = {}
        self._destination_image_attrs: Dict[str, Any] = {}

    @abstractmethod
    def source_to_geographic(self, pixel: Pixel) -> Geographic:
        """Transform source image pixel coordinates to geographic coordinates."""
        pass

    @abstractmethod
    def geographic_to_source(self, geo: Geographic) -> Pixel:
        """Transform geographic coordinates to source image pixel coordinates."""
        pass

    @abstractmethod
    def destination_to_geographic(self, pixel: Pixel) -> Geographic:
        """Transform destination image pixel coordinates to geographic coordinates."""
        pass

    @abstractmethod
    def geographic_to_destination(self, geo: Geographic) -> Pixel:
        """Transform geographic coordinates to destination image pixel coordinates."""
        pass

    @abstractmethod
    def update_model(self, **kwargs) -> None:
        """Update the transformation model with new parameters."""
        pass

    @property
    @abstractmethod
    def transformation_type(self) -> Transformation_Type:
        """Return the type of transformation (e.g., IDENTITY, RPC, AFFINE, TPS)."""
        pass

    @property
    @abstractmethod
    def is_identity(self) -> bool:
        """Return True if this is an identity transformation."""
        pass

    @property
    def source_image_attributes(self) -> Dict[str, Any]:
        """Get source image attributes."""
        return self._source_image_attrs.copy()

    @property
    def destination_image_attributes(self) -> Dict[str, Any]:
        """Get destination image attributes."""
        return self._destination_image_attrs.copy()

    def set_source_image_attributes(self, **attrs) -> None:
        """Set source image attributes."""
        self._source_image_attrs.update(attrs)

    def set_destination_image_attributes(self, **attrs) -> None:
        """Set destination image attributes."""
        self._destination_image_attrs.update(attrs)


class Identity_Projection(Projector):
    """Identity transformation - no coordinate change."""

    def __init__(self):
        super().__init__()

    def source_to_geographic(self, pixel: Pixel) -> Geographic:
        """Identity: pixel coordinates are treated as geographic (lat/lon)."""
        return Geographic(latitude_deg=pixel.x_px, longitude_deg=pixel.y_px)

    def geographic_to_source(self, geo: Geographic) -> Pixel:
        """Identity: geographic coordinates are treated as pixel coordinates."""
        return Pixel(x_px=geo.latitude_deg, y_px=geo.longitude_deg)

    def destination_to_geographic(self, pixel: Pixel) -> Geographic:
        """Identity: pixel coordinates are treated as geographic (lat/lon)."""
        return Geographic(latitude_deg=pixel.x_px, longitude_deg=pixel.y_px)

    def geographic_to_destination(self, geo: Geographic) -> Pixel:
        """Identity: geographic coordinates are treated as pixel coordinates."""
        return Pixel(x_px=geo.latitude_deg, y_px=geo.longitude_deg)

    def update_model(self, **kwargs) -> None:
        """Identity model doesn't need updates."""
        pass

    @property
    def transformation_type(self) -> Transformation_Type:
        return Transformation_Type.IDENTITY

    @property
    def is_identity(self) -> bool:
        return True


class Affine_Projection(Projector):
    """Affine transformation using transformation matrix."""

    def __init__(self):
        super().__init__()
        self._transform_matrix: Optional[List[List[float]]] = None
        self._inverse_matrix: Optional[List[List[float]]] = None

    def source_to_geographic(self, pixel: Pixel) -> Geographic:
        """Transform source pixel to geographic using affine matrix."""
        if self._transform_matrix is None:
            raise ValueError("Affine model not initialized")

        # Apply transformation: [x', y', 1] = M * [x, y, 1]
        x = pixel.x_px
        y = pixel.y_px
        m = self._transform_matrix

        x_new = m[0][0] * x + m[0][1] * y + m[0][2]
        y_new = m[1][0] * x + m[1][1] * y + m[1][2]

        return Geographic(latitude_deg=x_new, longitude_deg=y_new)

    def geographic_to_source(self, geo: Geographic) -> Pixel:
        """Transform geographic to source pixel using inverse affine matrix."""
        if self._inverse_matrix is None:
            raise ValueError("Affine model not initialized")

        # Apply inverse transformation
        x = geo.latitude_deg
        y = geo.longitude_deg
        m = self._inverse_matrix

        x_new = m[0][0] * x + m[0][1] * y + m[0][2]
        y_new = m[1][0] * x + m[1][1] * y + m[1][2]

        return Pixel(x_px=x_new, y_px=y_new)

    def destination_to_geographic(self, pixel: Pixel) -> Geographic:
        """For affine, destination and source use the same transformation."""
        return self.source_to_geographic(pixel)

    def geographic_to_destination(self, geo: Geographic) -> Pixel:
        """For affine, destination and source use the same transformation."""
        return self.geographic_to_source(geo)

    def update_model(self, transform_matrix: List[List[float]], **kwargs) -> None:
        """Update the affine transformation matrix."""
        self._transform_matrix = transform_matrix
        self._inverse_matrix = self._compute_inverse_matrix(transform_matrix)

    def _compute_inverse_matrix(self, matrix: List[List[float]]) -> List[List[float]]:
        """Compute 3x3 affine transformation inverse matrix."""
        # Extract affine components
        a, b, c = matrix[0][0], matrix[0][1], matrix[0][2]
        d, e, f = matrix[1][0], matrix[1][1], matrix[1][2]

        # Compute determinant of the 2x2 linear part
        det = a * e - b * d
        if abs(det) < 1e-10:
            raise ValueError("Singular affine transformation matrix")

        # Compute inverse matrix
        a_inv = e / det
        b_inv = -b / det
        c_inv = (b * f - c * e) / det
        d_inv = -d / det
        e_inv = a / det
        f_inv = (c * d - a * f) / det

        return [
            [a_inv, b_inv, c_inv],
            [d_inv, e_inv, f_inv],
            [0.0, 0.0, 1.0]
        ]

    @property
    def transformation_type(self) -> Transformation_Type:
        return Transformation_Type.AFFINE

    @property
    def is_identity(self) -> bool:
        return False
