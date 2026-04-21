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
from tmns.geo.coord import Geographic, Pixel, UTM
from tmns.geo.proj.gcp import GCP as Base_GCP

@dataclass
class GCP(Base_GCP):
    """Ground Control Point with GUI-specific metadata.

    Extends the terminus-core GCP with additional fields for GUI workflows.
    """

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
        return base_dict

    @classmethod
    def from_dict(cls, data):
        """Create GCP from dictionary."""

        test_pixel = Pixel.create(data['test_pixel']['x'], data['test_pixel']['y'])
        ref_pixel = Pixel.create(data['reference_pixel']['x'], data['reference_pixel']['y'])

        geo_data = data['geographic']
        geographic = Geographic.create(
            geo_data['latitude'],
            geo_data['longitude'],
            geo_data.get('elevation')
        )

        projected = None
        if data.get('projected'):
            proj_data = data['projected']
            projected = UTM.create(
                proj_data['easting'],
                proj_data['northing'],
                proj_data.get('crs', 'EPSG:3857'),
                proj_data.get('elevation')
            )

        return cls(
            id=data['id'],
            test_pixel=test_pixel,
            reference_pixel=ref_pixel,
            geographic=geographic,
            projected=projected,
            error=data.get('error'),
            enabled=data.get('enabled', True),
            source=data.get('source', 'manual'),
            metadata=data.get('metadata', {})
        )

    def to_gdal_format(self):
        """Convert to rasterio GCP format."""
        return GroundControlPoint(
            row=self.test_pixel.y,
            col=self.test_pixel.x,
            x=self.geographic.longitude,
            y=self.geographic.latitude,
            z=self.geographic.elevation or 0,
            id=str(self.id)
        )

    def __str__(self):
        """String representation."""
        return f"GCP {self.id}: Test{self.test_pixel} → Geo{self.geographic}"

    @property
    def test_x(self) -> float:
        """Get test X coordinate (backward compatibility)."""
        return self.test_pixel.x

    @property
    def test_y(self) -> float:
        """Get test Y coordinate (backward compatibility)."""
        return self.test_pixel.y

    @property
    def ref_x(self) -> float:
        """Get reference X coordinate (backward compatibility)."""
        return self.reference_pixel.x

    @property
    def ref_y(self) -> float:
        """Get reference Y coordinate (backward compatibility)."""
        return self.reference_pixel.y

    @property
    def longitude(self) -> float:
        """Get longitude (backward compatibility)."""
        return self.geographic.longitude

    @property
    def latitude(self) -> float:
        """Get latitude (backward compatibility)."""
        return self.geographic.latitude
