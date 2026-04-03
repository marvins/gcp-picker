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

# Standard Library Imports
from dataclasses import dataclass
from typing import Union
from enum import Enum
import math

# Third-Party Imports
import numpy as np
from pyproj import Transformer, CRS


# Union type for any coordinate type
Coordinate = Union['Geographic', 'UTM', 'ECEF', 'Pixel']


class Coordinate_System(Enum):
    """Supported coordinate systems."""
    WGS84           = "EPSG:4326"           # Geographic coordinates (lat/lon)
    WEB_MERCATOR    = "EPSG:3857"     # Web Mercator (used by many web maps)
    UTM_NORTH       = "EPSG:32600"       # UTM Northern hemisphere (base)
    UTM_SOUTH       = "EPSG:32700"       # UTM Southern hemisphere (base)
    LOCAL_CARTESIAN = "local"      # Local coordinate system


@dataclass
class Geographic:
    """Geographic coordinate (latitude, longitude, elevation)."""
    latitude_deg: float
    longitude_deg: float
    altitude_m: float | None = None

    @staticmethod
    def create(lat_deg: float, lon_deg: float, alt_m: float | None = None) -> 'Geographic':
        """Create a geographic coordinate."""
        return Geographic(latitude_deg=lat_deg, longitude_deg=lon_deg, altitude_m=alt_m)

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
    def lat_deg(self) -> float:
        """Get latitude in degrees (backward compatibility)."""
        return self.latitude_deg

    @property
    def lat_rad(self) -> float:
        """Get latitude in radians."""
        return math.radians(self.latitude_deg)

    @property
    def lon_deg(self) -> float:
        """Get longitude in degrees (backward compatibility)."""
        return self.longitude_deg

    @property
    def lon_rad(self) -> float:
        """Get longitude in radians."""
        return math.radians(self.longitude_deg)

    @property
    def elevation(self) -> float | None:
        """Get elevation in meters."""
        return self.altitude_m


@dataclass
class UTM:
    """UTM coordinate (easting, northing, elevation)."""
    easting_m: float
    northing_m: float
    altitude_m: float | None = None
    crs: str = "EPSG:4326"  # Default to WGS84, should be set to appropriate UTM zone

    @staticmethod
    def create(easting_m: float, northing_m: float, crs: str = "EPSG:4326", alt_m: float | None = None) -> 'UTM':
        """Create a UTM coordinate."""
        return UTM(easting_m=easting_m, northing_m=northing_m, crs=crs, altitude_m=alt_m)

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
    def easting_m(self) -> float:
        """Get easting in meters."""
        return self.easting_m

    @property
    def northing_m(self) -> float:
        """Get northing in meters."""
        return self.northing_m

    @property
    def elevation_m(self) -> float | None:
        """Get elevation in meters."""
        return self.altitude_m


@dataclass
class ECEF:
    """ECEF (Earth-Centered, Earth-Fixed) coordinate (X, Y, Z)."""
    xyz: np.ndarray  # Shape (3,) for [X, Y, Z] in meters

    def __post_init__(self):
        """Validate the numpy array."""
        if not isinstance(self.xyz, np.ndarray):
            self.xyz = np.array(self.xyz, dtype=float)

        if self.xyz.shape != (3,):
            raise ValueError(f"ECEF coordinates must have shape (3,), got {self.xyz.shape}")

    @staticmethod
    def create(x_m: float, y_m: float, z_m: float) -> 'ECEF':
        """Create an ECEF coordinate from individual components."""
        return ECEF(xyz=np.array([x_m, y_m, z_m], dtype=float))

    @staticmethod
    def from_array(xyz: np.ndarray | list[float]) -> 'ECEF':
        """Create an ECEF coordinate from array or list."""
        return ECEF(xyz=np.array(xyz, dtype=float))

    @property
    def x_m(self) -> float:
        """Get X coordinate in meters."""
        return float(self.xyz[0])

    @property
    def y_m(self) -> float:
        """Get Y coordinate in meters."""
        return float(self.xyz[1])

    @property
    def z_m(self) -> float:
        """Get Z coordinate in meters."""
        return float(self.xyz[2])

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert to (X, Y, Z) tuple."""
        return (float(self.xyz[0]), float(self.xyz[1]), float(self.xyz[2]))

    def to_array(self) -> np.ndarray:
        """Get coordinate as numpy array."""
        return self.xyz.copy()

    def __str__(self) -> str:
        """String representation."""
        return f"({self.x_m:.2f}, {self.y_m:.2f}, {self.z_m:.2f})"

    @property
    def magnitude(self) -> float:
        """Get magnitude of the position vector."""
        return float(np.linalg.norm(self.xyz))


@dataclass
class Pixel:
    """Pixel/image coordinate."""
    x_px: float
    y_px: float

    @staticmethod
    def create(x_px: float, y_px: float) -> 'Pixel':
        """Create a pixel coordinate."""
        return Pixel(x_px=x_px, y_px=y_px)

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


class Transformer:
    """Handles coordinate transformations between different coordinate systems."""

    def __init__(self):
        """Initialize transformer with common transformations."""
        self._transformers: dict[tuple[str, str], pyproj.Transformer] = {}

    def _get_transformer(self, from_crs: str, to_crs: str) -> pyproj.Transformer:
        """Get or create a transformer for the given CRS pair."""
        key = (from_crs, to_crs)

        if key not in self._transformers:
            try:
                self._transformers[key] = pyproj.Transformer.from_crs(
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
        utm_crs = self.get_utm_zone(geo.longitude_deg, geo.latitude_deg)
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
        lat1 = from_coord.lat_rad()
        lon1 = from_coord.lon_rad()
        lat2 = to_coord.lat_rad()
        lon2 = to_coord.lon_rad()

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
