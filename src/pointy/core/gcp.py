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
#    File:    gcp.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Ground Control Point (GCP) data structure with GUI-specific metadata.
"""

#  Python Standard Libraries
from dataclasses import dataclass, field
from typing import Any

#  Third-Party Libraries
from rasterio.control import GroundControlPoint

#  Project Libraries
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.proj.gcp import GCP as Base_GCP

@dataclass
class GCP(Base_GCP):
    """Ground Control Point with GUI-specific metadata.

    Extends the terminus-core GCP with additional fields for GUI workflows:
    - reference_pixel: Pixel coordinates in a reference image (for image-to-image registration)
    - source: Origin of the GCP ('manual', 'auto', or algorithm identifier)
    - metadata: Additional algorithm-specific data
    """

    reference_pixel: Pixel | None = None
    source: str = 'manual'
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation."""
        if self.id <= 0:
            raise ValueError("GCP ID must be positive")

    def to_dict(self):
        """Convert GCP to dictionary."""
        base_dict = super().to_dict()
        base_dict['source'] = self.source
        base_dict['metadata'] = self.metadata
        if self.reference_pixel is not None:
            base_dict['reference_pixel'] = {
                'x': self.reference_pixel.x_px,
                'y': self.reference_pixel.y_px
            }
        return base_dict

    @classmethod
    def from_dict(cls, data):
        """Create GCP from dictionary."""

        pixel_data = data['pixel']
        pixel = Pixel.create(
            pixel_data.get('x', pixel_data.get('x_px')),
            pixel_data.get('y', pixel_data.get('y_px'))
        )

        geo_data = data['geographic']
        geographic = Geographic.create(
            geo_data.get('latitude', geo_data.get('latitude_deg')),
            geo_data.get('longitude', geo_data.get('longitude_deg')),
            geo_data.get('elevation', geo_data.get('altitude_m'))
        )

        # Handle optional reference_pixel
        reference_pixel = None
        if data.get('reference_pixel'):
            rp = data['reference_pixel']
            reference_pixel = Pixel.create(
                rp.get('x', rp.get('x_px')),
                rp.get('y', rp.get('y_px'))
            )

        return cls(
            id=data['id'],
            pixel=pixel,
            reference_pixel=reference_pixel,
            geographic=geographic,
            error=data.get('error'),
            enabled=data.get('enabled', True),
            source=data.get('source', 'manual'),
            metadata=data.get('metadata', {})
        )

    def to_gdal_format(self):
        """Convert to rasterio GCP format."""
        return GroundControlPoint(
            row=self.pixel.y_px,
            col=self.pixel.x_px,
            x=self.geographic.longitude_deg,
            y=self.geographic.latitude_deg,
            z=self.geographic.altitude_m or 0,
            id=str(self.id)
        )

    def __str__(self):
        """String representation."""
        return f"GCP {self.id}: Test{self.pixel} → Geo{self.geographic}"

    @property
    def test_x(self) -> float:
        """Get test X coordinate (backward compatibility)."""
        return self.pixel.x_px

    @property
    def test_y(self) -> float:
        """Get test Y coordinate (backward compatibility)."""
        return self.pixel.y_px

    @property
    def ref_x(self) -> float | None:
        """Get reference X coordinate (backward compatibility)."""
        return self.reference_pixel.x_px if self.reference_pixel else None

    @property
    def ref_y(self) -> float | None:
        """Get reference Y coordinate (backward compatibility)."""
        return self.reference_pixel.y_px if self.reference_pixel else None

    @property
    def longitude(self) -> float:
        """Get longitude (backward compatibility)."""
        return self.geographic.longitude_deg

    @property
    def latitude(self) -> float:
        """Get latitude (backward compatibility)."""
        return self.geographic.latitude_deg
