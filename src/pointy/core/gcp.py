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
Ground Control Point (GCP) data structure
"""

#  Python Standard Libraries
import os
from dataclasses import dataclass

#  Third-Party Libraries
from rasterio.control import GroundControlPoint

#  Project Libraries
from pointy.core.coordinate import Geographic, Pixel, UTM
from pointy.core.terrain import elevation

@dataclass
class GCP:
    """Ground Control Point with coordinates in multiple systems."""

    id: int
    test_pixel: Pixel
    reference_pixel: Pixel
    geographic: Geographic
    projected: UTM | None = None
    error: float | None = None
    enabled: bool = True

    def __post_init__(self):
        """Post-initialization validation and elevation lookup."""
        if self.id <= 0:
            raise ValueError("GCP ID must be positive")

        # Auto-populate elevation if not provided and not in test environment
        # Skip elevation lookup in tests to avoid terrain catalog dependency
        skip_elevation = os.environ.get('SKIP_ELEVATION_LOOKUP', 'false').lower() == 'true'

        if not skip_elevation and self.geographic.altitude_m is None:
            try:
                elev = elevation(self.geographic)
                if elev is not None:
                    self.geographic.altitude_m = elev
            except Exception:
                # Silently fail elevation lookup for testing
                pass

    def to_dict(self):
        """Convert GCP to dictionary."""
        return {
            'id': self.id,
            'test_pixel': {
                'x': self.test_pixel.x_px,
                'y': self.test_pixel.y_px
            },
            'reference_pixel': {
                'x': self.reference_pixel.x_px,
                'y': self.reference_pixel.y_px
            },
            'geographic': {
                'latitude': self.geographic.latitude_deg,
                'longitude': self.geographic.longitude_deg,
                'elevation': self.geographic.altitude_m
            },
            'projected': {
                'easting': self.projected.easting,
                'northing': self.projected.northing,
                'elevation': self.projected.elevation,
                'crs': self.projected.crs
            } if self.projected else None,
            'error': self.error,
            'enabled': self.enabled
        }

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
            enabled=data.get('enabled', True)
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
