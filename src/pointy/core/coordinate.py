#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2025 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    coordinate.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Coordinate Types and Transformations

This module defines coordinate types and transformations used throughout the Pointy-McPointface application.
It supports various coordinate systems and provides utilities for coordinate conversion.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

import numpy as np
from pyproj import Transformer, CRS


class Coordinate_System(Enum):
    """Supported coordinate systems."""
    WGS84 = "EPSG:4326"           # Geographic coordinates (lat/lon)
    WEB_MERCATOR = "EPSG:3857"     # Web Mercator (used by many web maps)
    UTM_NORTH = "EPSG:32600"       # UTM Northern hemisphere (base)
    UTM_SOUTH = "EPSG:32700"       # UTM Southern hemisphere (base)
    LOCAL_CARTESIAN = "local"      # Local coordinate system


@dataclass
class Geographic:
    """Geographic coordinate (latitude, longitude, elevation)."""
    latitude_deg: float
    longitude_deg: float
    altitude_m: Optional[float] = None

    def __post_init__(self):
        """Validate coordinate ranges."""
        if not -90 <= self.latitude_deg <= 90:
            raise ValueError(f"Latitude {self.latitude_deg} out of range [-90, 90]")
        if not -180 <= self.longitude_deg <= 180:
            raise ValueError(f"Longitude {self.longitude_deg} out of range [-180, 180]")

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (lon, lat) tuple."""
        return (self.longitude_deg, self.latitude_deg)

    def to_3d_tuple(self) -> tuple[float, float, float]:
        """Convert to (lon, lat, elevation) tuple."""
        return (self.longitude_deg, self.latitude_deg, self.altitude_m or 0.0)

    def __str__(self) -> str:
        """String representation."""
        if self.altitude_m is not None:
            return f"({self.latitude_deg:.6f}, {self.longitude_deg:.6f}, {self.altitude_m:.1f}m)"
        return f"({self.latitude_deg:.6f}, {self.longitude_deg:.6f})"

    @property
    def latitude(self) -> float:
        """Get latitude in degrees (backward compatibility)."""
        return self.latitude_deg

    @property
    def longitude(self) -> float:
        """Get longitude in degrees (backward compatibility)."""
        return self.longitude_deg

    @property
    def elevation(self) -> Optional[float]:
        """Get elevation in meters (backward compatibility)."""
        return self.altitude_m


@dataclass
class UTM:
    """UTM coordinate (easting, northing, elevation)."""
    easting_m: float
    northing_m: float
    altitude_m: Optional[float] = None
    crs: str = "EPSG:4326"  # Default to WGS84, should be set to appropriate UTM zone

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (easting, northing) tuple."""
        return (self.easting_m, self.northing_m)

    def to_3d_tuple(self) -> tuple[float, float, float]:
        """Convert to (easting, northing, elevation) tuple."""
        return (self.easting_m, self.northing_m, self.altitude_m or 0.0)

    def __str__(self) -> str:
        """String representation."""
        if self.altitude_m is not None:
            return f"({self.easting_m:.2f}, {self.northing_m:.2f}, {self.altitude_m:.1f}m) [{self.crs}]"
        return f"({self.easting_m:.2f}, {self.northing_m:.2f}) [{self.crs}]"

    @property
    def easting(self) -> float:
        """Get easting in meters (backward compatibility)."""
        return self.easting_m

    @property
    def northing(self) -> float:
        """Get northing in meters (backward compatibility)."""
        return self.northing_m

    @property
    def elevation(self) -> Optional[float]:
        """Get elevation in meters (backward compatibility)."""
        return self.altitude_m


@dataclass
class Pixel:
    """Pixel/image coordinate."""
    x_px: float
    y_px: float

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (x, y) tuple."""
        return (self.x_px, self.y_px)

    def to_int_tuple(self) -> tuple[int, int]:
        """Convert to integer pixel coordinates."""
        return (int(round(self.x_px)), int(round(self.y_px)))

    def __str__(self) -> str:
        """String representation."""
        return f"({self.x_px:.1f}, {self.y_px:.1f})"

    @property
    def x(self) -> float:
        """Get x coordinate in pixels (backward compatibility)."""
        return self.x_px

    @property
    def y(self) -> float:
        """Get y coordinate in pixels (backward compatibility)."""
        return self.y_px


@dataclass
class GCPPair:
    """Ground Control Point pair with coordinates in different systems."""
    id: int
    test_pixel: Pixel
    reference_pixel: Pixel
    geographic: Geographic
    projected: Optional[UTM] = None
    error: Optional[float] = None

    def __str__(self) -> str:
        """String representation."""
        return f"GCP {self.id}: Test{self.test_pixel} → Geo{self.geographic}"


class Coordinate_Transformer:
    """Handles coordinate transformations between different coordinate systems."""

    def __init__(self):
        """Initialize transformer with common transformations."""
        self._transformers: dict[tuple[str, str], Transformer] = {}

    def _get_transformer(self, from_crs: str, to_crs: str) -> Transformer:
        """Get or create a transformer for the given CRS pair."""
        key = (from_crs, to_crs)

        if key not in self._transformers:
            try:
                self._transformers[key] = Transformer.from_crs(
                    CRS(from_crs), CRS(to_crs), always_xy=True
                )
            except Exception as e:
                raise ValueError(f"Cannot create transformer from {from_crs} to {to_crs}: {e}")

        return self._transformers[key]

    def geographic_to_projected(
        self,
        geo: Geographic,
        target_crs: str = Coordinate_System.WEB_MERCATOR.value
    ) -> UTM:
        """Convert geographic to projected coordinates."""
        transformer = self._get_transformer(
            Coordinate_System.WGS84.value, target_crs
        )

        if geo.elevation is not None:
            easting, northing, elevation = transformer.transform(
                geo.longitude, geo.latitude, geo.elevation
            )
        else:
            easting, northing = transformer.transform(
                geo.longitude, geo.latitude
            )
            elevation = None

        return UTM(easting, northing, elevation, target_crs)

    def projected_to_geographic(
        self,
        proj: UTM
    ) -> Geographic:
        """Convert projected to geographic coordinates."""
        transformer = self._get_transformer(
            proj.crs, Coordinate_System.WGS84.value
        )

        if proj.elevation is not None:
            lon, lat, elevation = transformer.transform(
                proj.easting, proj.northing, proj.elevation
            )
        else:
            lon, lat = transformer.transform(proj.easting, proj.northing)
            elevation = None

        return Geographic(lat, lon, elevation)

    def get_utm_zone(self, longitude: float, latitude: float) -> str:
        """Get UTM zone for the given geographic coordinates."""
        # Calculate UTM zone
        zone = int((longitude + 180) / 6) + 1

        # Determine hemisphere
        if latitude >= 0:
            utm_crs = f"EPSG:{32600 + zone}"  # Northern hemisphere
        else:
            utm_crs = f"EPSG:{32700 + zone}"  # Southern hemisphere

        return utm_crs

    def to_utm(self, geo: Geographic) -> UTM:
        """Convert geographic coordinates to UTM."""
        utm_crs = self.get_utm_zone(geo.longitude, geo.latitude)
        return self.geographic_to_projected(geo, utm_crs)

    def calculate_distance(
        self,
        coord1: Geographic | UTM,
        coord2: Geographic | UTM
    ) -> float:
        """Calculate distance between two coordinates."""
        # Convert to projected coordinates for accurate distance calculation
        if isinstance(coord1, Geographic):
            proj1 = self.to_utm(coord1)
        else:
            proj1 = coord1

        if isinstance(coord2, Geographic):
            proj2 = self.to_utm(coord2)
        else:
            proj2 = coord2

        # Ensure both are in the same CRS
        if proj1.crs != proj2.crs:
            proj2 = self.geographic_to_projected(
                self.projected_to_geographic(proj2),
                proj1.crs
            )

        # Calculate Euclidean distance
        dx = proj2.easting - proj1.easting
        dy = proj2.northing - proj1.northing
        dz = (proj2.elevation or 0) - (proj1.elevation or 0)

        return np.sqrt(dx**2 + dy**2 + dz**2)

    def calculate_bearing(
        self,
        from_coord: Geographic,
        to_coord: Geographic
    ) -> float:
        """Calculate bearing from one geographic coordinate to another."""
        # Convert to radians
        lat1 = np.radians(from_coord.latitude)
        lon1 = np.radians(from_coord.longitude)
        lat2 = np.radians(to_coord.latitude)
        lon2 = np.radians(to_coord.longitude)

        # Calculate bearing
        dlon = lon2 - lon1

        y = np.sin(dlon) * np.cos(lat2)
        x = (np.cos(lat1) * np.sin(lat2) -
             np.sin(lat1) * np.cos(lat2) * np.cos(dlon))

        bearing = np.arctan2(y, x)

        # Convert to degrees and normalize to [0, 360]
        bearing = np.degrees(bearing)
        bearing = (bearing + 360) % 360

        return bearing


# Utility functions
def create_geographic(lat_deg: float, lon_deg: float, alt_m: Optional[float] = None) -> Geographic:
    """Create a geographic coordinate."""
    return Geographic(latitude_deg=lat_deg, longitude_deg=lon_deg, altitude_m=alt_m)


def create_projected(
    easting_m: float,
    northing_m: float,
    crs: str = "EPSG:4326",  # Default to WGS84, should be set to appropriate projected CRS
    alt_m: Optional[float] = None
) -> UTM:
    """Create a projected coordinate."""
    return UTM(easting_m=easting_m, northing_m=northing_m, crs=crs, altitude_m=alt_m)


def create_pixel(x_px: float, y_px: float) -> Pixel:
    """Create a pixel coordinate."""
    return Pixel(x_px=x_px, y_px=y_px)
