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
from __future__ import annotations
from dataclasses import dataclass
from typing import Union
from enum import Enum
import math

# Third-Party Imports
import numpy as np
import pyproj
from pyproj import CRS


# Union type for any coordinate type
Coordinate = Union['Geographic', 'UTM', 'UPS', 'Web_Mercator', 'ECEF', 'Pixel']


class Coordinate_Type(Enum):
    """Supported coordinate types."""
    GEOGRAPHIC = "geographic"
    UTM = "utm"
    UPS = "ups"
    WEB_MERCATOR = "web_mercator"
    ECEF = "ecef"
    PIXEL = "pixel"


class EPSG_Manager:
    """Centralized EPSG code management and utilities."""

    # EPSG code constants
    WGS84 = 4326
    WEB_MERCATOR = 3857
    ECEF = 4978

    # UPS codes
    UPS_NORTH = 32661
    UPS_SOUTH = 32761

    # UTM zone base codes
    UTM_NORTH_BASE = 32600
    UTM_SOUTH_BASE = 32700

    @staticmethod
    def to_epsg_code(epsg_str: str) -> int:
        """Convert EPSG string (e.g., 'EPSG:4326') to integer code."""
        if not epsg_str.startswith('EPSG:'):
            raise ValueError(f"Invalid EPSG format: {epsg_str}")

        try:
            return int(epsg_str.split(':')[1])
        except (IndexError, ValueError):
            raise ValueError(f"Invalid EPSG format: {epsg_str}")

    @staticmethod
    def to_epsg_string(epsg_code: int) -> str:
        """Convert integer EPSG code to string format (e.g., 4326 -> 'EPSG:4326')."""
        return f"EPSG:{epsg_code}"

    @staticmethod
    def is_utm_zone(epsg_code: int) -> bool:
        """Check if EPSG code represents a UTM zone."""
        # UTM zones are 32601-32660 (North) and 32701-32760 (South)
        return (32601 <= epsg_code <= 32660) or (32701 <= epsg_code <= 32760)

    @staticmethod
    def is_ups_zone(epsg_code: int) -> bool:
        """Check if EPSG code represents a UPS zone."""
        return epsg_code in [EPSG_Manager.UPS_NORTH, EPSG_Manager.UPS_SOUTH]

    @staticmethod
    def is_polar_region(epsg_code: int) -> bool:
        """Check if EPSG code represents a polar region (UPS)."""
        return EPSG_Manager.is_ups_zone(epsg_code)

    @staticmethod
    def get_utm_zone_number(epsg_code: int) -> int:
        """Get UTM zone number from EPSG code."""
        if not EPSG_Manager.is_utm_zone(epsg_code):
            raise ValueError(f"EPSG code {epsg_code} is not a UTM zone")

        if 32601 <= epsg_code <= 32660:  # Northern hemisphere
            return epsg_code - EPSG_Manager.UTM_NORTH_BASE
        else:  # Southern hemisphere
            return epsg_code - EPSG_Manager.UTM_SOUTH_BASE

    @staticmethod
    def get_utm_hemisphere(epsg_code: int) -> str:
        """Get UTM hemisphere from EPSG code ('N' or 'S')."""
        if not EPSG_Manager.is_utm_zone(epsg_code):
            raise ValueError(f"EPSG code {epsg_code} is not a UTM zone")

        return "N" if 32601 <= epsg_code <= 32660 else "S"

    @staticmethod
    def get_ups_hemisphere(epsg_code: int) -> str:
        """Get UPS hemisphere from EPSG code ('N' or 'S')."""
        if not EPSG_Manager.is_ups_zone(epsg_code):
            raise ValueError(f"EPSG code {epsg_code} is not a UPS zone")

        return "N" if epsg_code == EPSG_Manager.UPS_NORTH else "S"

    @staticmethod
    def create_utm_epsg(zone: int, hemisphere: str) -> int:
        """Create EPSG code for UTM zone."""
        if not 1 <= zone <= 60:
            raise ValueError(f"UTM zone must be 1-60, got {zone}")

        hemisphere = hemisphere.upper()
        if hemisphere == "N":
            return EPSG_Manager.UTM_NORTH_BASE + zone
        elif hemisphere == "S":
            return EPSG_Manager.UTM_SOUTH_BASE + zone
        else:
            raise ValueError(f"Hemisphere must be 'N' or 'S', got {hemisphere}")

    @staticmethod
    def create_ups_epsg(hemisphere: str) -> int:
        """Create EPSG code for UPS zone."""
        hemisphere = hemisphere.upper()
        if hemisphere == "N":
            return EPSG_Manager.UPS_NORTH
        elif hemisphere == "S":
            return EPSG_Manager.UPS_SOUTH
        else:
            raise ValueError(f"Hemisphere must be 'N' or 'S', got {hemisphere}")

    @staticmethod
    def get_coordinate_type(epsg_code: int) -> Coordinate_Type:
        """Get coordinate type from EPSG code."""
        if epsg_code == EPSG_Manager.WGS84:
            return Coordinate_Type.GEOGRAPHIC
        elif epsg_code == EPSG_Manager.WEB_MERCATOR:
            return Coordinate_Type.WEB_MERCATOR
        elif epsg_code == EPSG_Manager.ECEF:
            return Coordinate_Type.ECEF
        elif EPSG_Manager.is_utm_zone(epsg_code):
            return Coordinate_Type.UTM
        elif EPSG_Manager.is_ups_zone(epsg_code):
            return Coordinate_Type.UPS
        else:
            # Return None for unknown codes instead of raising error
            return None

    @staticmethod
    def get_description(epsg_code: int) -> str:
        """Get human-readable description of EPSG code."""
        if epsg_code == EPSG_Manager.WGS84:
            return "WGS84 Geographic"
        elif epsg_code == EPSG_Manager.WEB_MERCATOR:
            return "Web Mercator"
        elif epsg_code == EPSG_Manager.ECEF:
            return "Earth-Centered Earth-Fixed"
        elif EPSG_Manager.is_ups_zone(epsg_code):
            hemisphere = EPSG_Manager.get_ups_hemisphere(epsg_code)
            return f"Universal Polar Stereographic ({hemisphere})"
        elif EPSG_Manager.is_utm_zone(epsg_code):
            zone = EPSG_Manager.get_utm_zone_number(epsg_code)
            hemisphere = EPSG_Manager.get_utm_hemisphere(epsg_code)
            return f"UTM Zone {zone}{hemisphere}"
        else:
            return f"Unknown EPSG:{epsg_code}"


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

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.GEOGRAPHIC

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

    def to_epsg(self) -> int:
        """Get EPSG code for this coordinate."""
        return EPSG_Manager.WGS84

    @staticmethod
    def bearing(from_coord: Geographic, to_coord: Geographic, as_deg: bool = True) -> float:
        """Calculate bearing from one geographic coordinate to another.

        Args:
            from_coord: Starting geographic coordinate
            to_coord: Ending geographic coordinate
            as_deg: If True, return bearing in degrees; if False, return bearing in radians

        Returns:
            Bearing measured clockwise from true north:
            - If as_deg=True: degrees (0° = north, 90° = east, 180° = south, 270° = west)
            - If as_deg=False: radians (0 = north, π/2 = east, π = south, 3π/2 = west)
            Range is always [0, 360] degrees or [0, 2π] radians regardless of coordinate positions.
        """
        # Convert to radians
        lat1 = from_coord.lat_rad
        lon1 = from_coord.lon_rad
        lat2 = to_coord.lat_rad
        lon2 = to_coord.lon_rad

        # Calculate bearing
        dlon = lon2 - lon1

        y = np.sin(dlon) * np.cos(lat2)
        x = (np.cos(lat1) * np.sin(lat2) -
             np.sin(lat1) * np.cos(lat2) * np.cos(dlon))

        bearing = np.arctan2(y, x)

        # Normalize to [0, 2π] radians
        bearing = (bearing + 2 * np.pi) % (2 * np.pi)

        # Convert to degrees if requested
        if as_deg:
            bearing = np.degrees(bearing)

        return bearing

    @staticmethod
    def distance(coord1: Geographic, coord2: Geographic) -> float:
        """Calculate great circle distance between two geographic coordinates.

        Uses the Haversine formula to calculate the great circle distance
        between two points on the Earth's surface.

        Args:
            coord1: First geographic coordinate
            coord2: Second geographic coordinate

        Returns:
            Distance in meters between the two coordinates.
        """
        # Earth's radius in meters (mean radius)
        R = 6371000.0

        # Convert to radians
        lat1 = coord1.lat_rad
        lon1 = coord1.lon_rad
        lat2 = coord2.lat_rad
        lon2 = coord2.lon_rad

        # Differences
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine formula
        a = (np.sin(dlat/2)**2 +
             np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        distance = R * c
        return distance

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

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.UTM

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

    def to_epsg(self) -> int:
        """Get EPSG code for this coordinate."""
        return EPSG_Manager.to_epsg_code(self.crs)

    @staticmethod
    def bearing(from_coord: UTM, to_coord: UTM, as_deg: bool = True) -> float:
        """Calculate bearing from one UTM coordinate to another.

        Args:
            from_coord: Starting UTM coordinate
            to_coord: Ending UTM coordinate
            as_deg: If True, return bearing in degrees; if False, return bearing in radians

        Returns:
            Bearing measured clockwise from true north:
            - If as_deg=True: degrees (0° = north, 90° = east, 180° = south, 270° = west)
            - If as_deg=False: radians (0 = north, π/2 = east, π = south, 3π/2 = west)
            Range is always [0, 360] degrees or [0, 2π] radians regardless of coordinate positions.

        Raises:
            ValueError: If coordinates are in different UTM zones
        """
        # Validate coordinates are in the same UTM zone
        if from_coord.crs != to_coord.crs:
            raise ValueError(f"Cannot calculate bearing between coordinates in different UTM zones: {from_coord.crs} vs {to_coord.crs}")

        # Calculate bearing in UTM coordinate system
        dx = to_coord.easting_m - from_coord.easting_m
        dy = to_coord.northing_m - from_coord.northing_m

        bearing = np.arctan2(dx, dy)  # Note: dx/easting, dy/northing for bearing

        # Normalize to [0, 2π] radians
        bearing = (bearing + 2 * np.pi) % (2 * np.pi)

        # Convert to degrees if requested
        if as_deg:
            bearing = np.degrees(bearing)

        return bearing

    @staticmethod
    def distance(coord1: UTM, coord2: UTM) -> float:
        """Calculate Euclidean distance between two UTM coordinates.

        Calculates the straight-line Euclidean distance between two points
        in the same UTM coordinate system.

        Args:
            coord1: First UTM coordinate
            coord2: Second UTM coordinate

        Returns:
            Distance in meters between the two coordinates.

        Raises:
            ValueError: If coordinates are in different UTM zones
        """
        # Validate coordinates are in the same UTM zone
        if coord1.crs != coord2.crs:
            raise ValueError(f"Cannot calculate distance between coordinates in different UTM zones: {coord1.crs} vs {coord2.crs}")

        # Calculate differences
        dx = coord2.easting_m - coord1.easting_m
        dy = coord2.northing_m - coord1.northing_m
        dz = (coord2.altitude_m or 0) - (coord1.altitude_m or 0)

        # Euclidean distance
        distance = np.sqrt(dx**2 + dy**2 + dz**2)
        return distance


@dataclass
class UPS:
    """Universal Polar Stereographic coordinate (easting, northing, elevation)."""
    easting_m: float
    northing_m: float
    altitude_m: float | None = None
    hemisphere: str = "N"  # "N" for North pole, "S" for South pole
    crs: str = "EPSG:32661"  # Default to UPS North

    @staticmethod
    def create(easting_m: float, northing_m: float, hemisphere: str = "N", alt_m: float | None = None) -> 'UPS':
        """Create a UPS coordinate."""
        crs = "EPSG:32661" if hemisphere.upper() == "N" else "EPSG:32761"
        return UPS(easting_m=easting_m, northing_m=northing_m, hemisphere=hemisphere.upper(), crs=crs, altitude_m=alt_m)

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.UPS

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

    def to_epsg(self) -> int:
        """Get EPSG code for this coordinate."""
        return EPSG_Manager.to_epsg_code(self.crs)

    @staticmethod
    def distance(coord1: UPS, coord2: UPS) -> float:
        """Calculate Euclidean distance between two UPS coordinates.

        Calculates the straight-line Euclidean distance between two points
        in the UPS coordinate system.

        Args:
            coord1: First UPS coordinate
            coord2: Second UPS coordinate

        Returns:
            Distance in meters between the two coordinates.

        Raises:
            ValueError: If coordinates are in different hemispheres
        """
        # Validate coordinates are in the same hemisphere
        if coord1.hemisphere != coord2.hemisphere:
            raise ValueError(f"Cannot calculate distance between coordinates in different hemispheres: {coord1.hemisphere} vs {coord2.hemisphere}")

        # Calculate differences
        dx = coord2.easting_m - coord1.easting_m
        dy = coord2.northing_m - coord1.northing_m
        dz = (coord2.altitude_m or 0) - (coord1.altitude_m or 0)

        # Euclidean distance
        distance = np.sqrt(dx**2 + dy**2 + dz**2)
        return distance

    @staticmethod
    def bearing(from_coord: UPS, to_coord: UPS, as_deg: bool = True) -> float:
        """Calculate bearing from one UPS coordinate to another.

        Args:
            from_coord: Starting UPS coordinate
            to_coord: Ending UPS coordinate
            as_deg: If True, return bearing in degrees; if False, return bearing in radians

        Returns:
            Bearing measured clockwise from true north:
            - If as_deg=True: degrees (0° = north, 90° = east, 180° = south, 270° = west)
            - If as_deg=False: radians (0 = north, π/2 = east, π = south, 3π/2 = west)
            Range is always [0, 360] degrees or [0, 2π] radians regardless of coordinate positions.

        Raises:
            ValueError: If coordinates are in different hemispheres
        """
        # Validate coordinates are in the same hemisphere
        if from_coord.hemisphere != to_coord.hemisphere:
            raise ValueError(f"Cannot calculate bearing between coordinates in different hemispheres: {from_coord.hemisphere} vs {to_coord.hemisphere}")

        # Calculate bearing in UPS coordinate system
        dx = to_coord.easting_m - from_coord.easting_m
        dy = to_coord.northing_m - from_coord.northing_m

        bearing = np.arctan2(dx, dy)  # Note: dx/easting, dy/northing for bearing

        # Normalize to [0, 2π] radians
        bearing = (bearing + 2 * np.pi) % (2 * np.pi)

        # Convert to degrees if requested
        if as_deg:
            bearing = np.degrees(bearing)

        return bearing

    def __post_init__(self):
        """Validate UPS coordinate parameters."""
        if self.hemisphere not in ["N", "S"]:
            raise ValueError(f"Hemisphere must be 'N' or 'S', got {self.hemisphere}")

        # Validate CRS matches hemisphere
        expected_crs = "EPSG:32661" if self.hemisphere == "N" else "EPSG:32761"
        if self.crs != expected_crs:
            raise ValueError(f"CRS {self.crs} does not match hemisphere {self.hemisphere}, expected {expected_crs}")


@dataclass
class Web_Mercator:
    """Web Mercator coordinate (easting, northing, elevation)."""
    easting_m: float
    northing_m: float
    altitude_m: float | None = None
    crs: str = "EPSG:3857"  # Web Mercator coordinate system

    @staticmethod
    def create(easting_m: float, northing_m: float, alt_m: float | None = None) -> 'Web_Mercator':
        """Create a Web Mercator coordinate."""
        return Web_Mercator(easting_m=easting_m, northing_m=northing_m, crs="EPSG:3857", altitude_m=alt_m)

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.WEB_MERCATOR

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

    def to_epsg(self) -> int:
        """Get EPSG code for this coordinate."""
        return EPSG_Manager.WEB_MERCATOR

    @staticmethod
    def distance(coord1: Web_Mercator, coord2: Web_Mercator) -> float:
        """Calculate Euclidean distance between two Web Mercator coordinates.

        Calculates the straight-line Euclidean distance between two points
        in the Web Mercator coordinate system.

        Args:
            coord1: First Web Mercator coordinate
            coord2: Second Web Mercator coordinate

        Returns:
            Distance in meters between the two coordinates.
            Note: This distance is in Web Mercator projection space, not
            true great circle distance on the Earth's surface.

        Raises:
            ValueError: If coordinates are in different coordinate systems
        """
        # Web Mercator coordinates should all use the same CRS (EPSG:3857)
        # But we validate for consistency
        if coord1.crs != coord2.crs:
            raise ValueError(f"Cannot calculate distance between coordinates in different coordinate systems: {coord1.crs} vs {coord2.crs}")

        # Calculate differences
        dx = coord2.easting_m - coord1.easting_m
        dy = coord2.northing_m - coord1.northing_m
        dz = (coord2.altitude_m or 0) - (coord1.altitude_m or 0)

        # Euclidean distance
        distance = np.sqrt(dx**2 + dy**2 + dz**2)
        return distance

    @staticmethod
    def bearing(from_coord: Web_Mercator, to_coord: Web_Mercator, as_deg: bool = True) -> float:
        """Calculate bearing from one Web Mercator coordinate to another.

        Args:
            from_coord: Starting Web Mercator coordinate
            to_coord: Ending Web Mercator coordinate
            as_deg: If True, return bearing in degrees; if False, return bearing in radians

        Returns:
            Bearing measured clockwise from true north:
            - If as_deg=True: degrees (0° = north, 90° = east, 180° = south, 270° = west)
            - If as_deg=False: radians (0 = north, π/2 = east, π = south, 3π/2 = west)
            Range is always [0, 360] degrees or [0, 2π] radians regardless of coordinate positions.

        Raises:
            ValueError: If coordinates are in different coordinate systems
        """
        # Web Mercator coordinates should all use the same CRS (EPSG:3857)
        # But we validate for consistency
        if from_coord.crs != to_coord.crs:
            raise ValueError(f"Cannot calculate bearing between coordinates in different coordinate systems: {from_coord.crs} vs {to_coord.crs}")

        # Calculate bearing in Web Mercator coordinate system
        dx = to_coord.easting_m - from_coord.easting_m
        dy = to_coord.northing_m - from_coord.northing_m

        bearing = np.arctan2(dx, dy)  # Note: dx/easting, dy/northing for bearing

        # Normalize to [0, 2π] radians
        bearing = (bearing + 2 * np.pi) % (2 * np.pi)

        # Convert to degrees if requested
        if as_deg:
            bearing = np.degrees(bearing)

        return bearing


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

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.ECEF

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

    def to_epsg(self) -> int:
        """Get EPSG code for this coordinate."""
        return EPSG_Manager.ECEF

    @staticmethod
    def distance(coord1: ECEF, coord2: ECEF) -> float:
        """Calculate Euclidean distance between two ECEF coordinates.

        Calculates the straight-line Euclidean distance between two points
        in the Earth-Centered Earth-Fixed coordinate system.

        Args:
            coord1: First ECEF coordinate
            coord2: Second ECEF coordinate

        Returns:
            Distance in meters between the two coordinates.
        """
        # Calculate difference vector
        diff = coord2.xyz - coord1.xyz

        # Euclidean distance
        distance = np.linalg.norm(diff)
        return distance

    @staticmethod
    def bearing(from_coord: ECEF, to_coord: ECEF, as_deg: bool = True) -> float:
        """Calculate bearing from one ECEF coordinate to another.

        Note: Bearing calculation in ECEF space is not straightforward since
        ECEF coordinates are in 3D Cartesian space. This method converts
        to geographic coordinates first, then calculates bearing.

        Args:
            from_coord: Starting ECEF coordinate
            to_coord: Ending ECEF coordinate
            as_deg: If True, return bearing in degrees; if False, return bearing in radians

        Returns:
            Bearing measured clockwise from true north:
            - If as_deg=True: degrees (0° = north, 90° = east, 180° = south, 270° = west)
            - If as_deg=False: radians (0 = north, π/2 = east, π = south, 3π/2 = west)
            Range is always [0, 360] degrees or [0, 2π] radians regardless of coordinate positions.
        """
        # Convert ECEF to geographic coordinates first
        transformer = Transformer()
        from_geo = transformer.ecef_to_geo(from_coord)
        to_geo = transformer.ecef_to_geo(to_coord)

        # Use geographic bearing calculation
        return Geographic.bearing(from_geo, to_geo, as_deg)

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

    def type(self) -> Coordinate_Type:
        """Get the coordinate type."""
        return Coordinate_Type.PIXEL

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (x, y) tuple."""
        return (self.x_px, self.y_px)

    def to_int_tuple(self) -> tuple[int, int]:
        """Convert to integer pixel coordinates."""
        return (int(self.x_px + 0.5), int(self.y_px + 0.5))

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

    # Explicit converters (type-safe)
    def geo_to_utm(self, geo: Geographic, zone: int | None = None) -> UTM | UPS:
        """Convert geographic to UTM or UPS coordinates."""
        if zone is not None:
            target_crs = f"EPSG:{32600 + zone}" if geo.latitude_deg >= 0 else f"EPSG:{32700 + zone}"
        else:
            target_crs = self.get_utm_zone(geo.longitude_deg, geo.latitude_deg)

        return self.geographic_to_projected(geo, target_crs)

    def geo_to_web_mercator(self, geo: Geographic) -> Web_Mercator:
        """Convert geographic to Web Mercator coordinates."""
        return self.geographic_to_projected(geo, "EPSG:3857")

    def geo_to_ecef(self, geo: Geographic) -> ECEF:
        """Convert geographic to ECEF coordinates."""
        transformer = self._get_transformer("EPSG:4326", "EPSG:4978")  # WGS84 to ECEF

        if geo.altitude_m is not None:
            x, y, z = transformer.transform(
                geo.longitude_deg, geo.latitude_deg, geo.altitude_m
            )
        else:
            x, y, z = transformer.transform(
                geo.longitude_deg, geo.latitude_deg, 0.0
            )

        return ECEF.create(x, y, z)

    def geo_to_ups(self, geo: Geographic) -> UPS:
        """Convert geographic to UPS coordinates."""
        if not self.is_polar_region(geo.latitude_deg):
            raise ValueError(f"Latitude {geo.latitude_deg} is not in polar region for UPS")

        target_crs = self.get_utm_zone(geo.longitude_deg, geo.latitude_deg)  # This returns UPS CRS for polar regions
        return self.geographic_to_projected(geo, target_crs)

    def ups_to_geo(self, ups: UPS) -> Geographic:
        """Convert UPS to geographic coordinates."""
        return self.projected_to_geographic(ups)

    def utm_to_geo(self, utm: UTM) -> Geographic:
        """Convert UTM to geographic coordinates."""
        return self.projected_to_geographic(utm)

    def web_mercator_to_geo(self, wm: Web_Mercator) -> Geographic:
        """Convert Web Mercator to geographic coordinates."""
        return self.projected_to_geographic(wm)

    def ecef_to_geo(self, ecef: ECEF) -> Geographic:
        """Convert ECEF to geographic coordinates."""
        transformer = self._get_transformer("EPSG:4978", "EPSG:4326")  # ECEF to WGS84

        lon, lat, alt = transformer.transform(ecef.x_m, ecef.y_m, ecef.z_m)
        return Geographic.create(lat, lon, alt)

    # Generic converter (flexible)
    def convert(self, coord: Coordinate, dest_type: Coordinate_Type) -> Coordinate:
        """Convert any coordinate to any other coordinate type."""
        # Source type detection
        source_type = coord.type()

        # Early return if same type
        if source_type == dest_type:
            return coord

        # Geographic as source
        if source_type == Coordinate_Type.GEOGRAPHIC:
            geo = coord  # type: ignore
            if dest_type == Coordinate_Type.UTM:
                return self.geo_to_utm(geo)
            elif dest_type == Coordinate_Type.UPS:
                return self.geo_to_ups(geo)
            elif dest_type == Coordinate_Type.WEB_MERCATOR:
                return self.geo_to_web_mercator(geo)
            elif dest_type == Coordinate_Type.ECEF:
                return self.geo_to_ecef(geo)
            elif dest_type == Coordinate_Type.PIXEL:
                raise ValueError("Cannot convert directly from Geographic to Pixel")

        # UTM as source
        elif source_type == Coordinate_Type.UTM:
            utm = coord  # type: ignore
            if dest_type == Coordinate_Type.GEOGRAPHIC:
                return self.utm_to_geo(utm)
            elif dest_type == Coordinate_Type.UPS:
                geo = self.utm_to_geo(utm)
                return self.geo_to_ups(geo)
            elif dest_type == Coordinate_Type.WEB_MERCATOR:
                geo = self.utm_to_geo(utm)
                return self.geo_to_web_mercator(geo)
            elif dest_type == Coordinate_Type.ECEF:
                geo = self.utm_to_geo(utm)
                return self.geo_to_ecef(geo)
            elif dest_type == Coordinate_Type.PIXEL:
                raise ValueError("Cannot convert directly from UTM to Pixel")

        # UPS as source
        elif source_type == Coordinate_Type.UPS:
            ups = coord  # type: ignore
            if dest_type == Coordinate_Type.GEOGRAPHIC:
                return self.ups_to_geo(ups)
            elif dest_type == Coordinate_Type.UTM:
                geo = self.ups_to_geo(ups)
                return self.geo_to_utm(geo)
            elif dest_type == Coordinate_Type.WEB_MERCATOR:
                geo = self.ups_to_geo(ups)
                return self.geo_to_web_mercator(geo)
            elif dest_type == Coordinate_Type.ECEF:
                geo = self.ups_to_geo(ups)
                return self.geo_to_ecef(geo)
            elif dest_type == Coordinate_Type.PIXEL:
                raise ValueError("Cannot convert directly from UPS to Pixel")

        # Web Mercator as source
        elif source_type == Coordinate_Type.WEB_MERCATOR:
            wm = coord  # type: ignore
            if dest_type == Coordinate_Type.GEOGRAPHIC:
                return self.web_mercator_to_geo(wm)
            elif dest_type == Coordinate_Type.UTM:
                geo = self.web_mercator_to_geo(wm)
                return self.geo_to_utm(geo)
            elif dest_type == Coordinate_Type.UPS:
                geo = self.web_mercator_to_geo(wm)
                return self.geo_to_ups(geo)
            elif dest_type == Coordinate_Type.ECEF:
                geo = self.web_mercator_to_geo(wm)
                return self.geo_to_ecef(geo)
            elif dest_type == Coordinate_Type.PIXEL:
                raise ValueError("Cannot convert directly from Web Mercator to Pixel")

        # ECEF as source
        elif source_type == Coordinate_Type.ECEF:
            ecef = coord  # type: ignore
            if dest_type == Coordinate_Type.GEOGRAPHIC:
                return self.ecef_to_geo(ecef)
            elif dest_type == Coordinate_Type.UTM:
                geo = self.ecef_to_geo(ecef)
                return self.geo_to_utm(geo)
            elif dest_type == Coordinate_Type.UPS:
                geo = self.ecef_to_geo(ecef)
                return self.geo_to_ups(geo)
            elif dest_type == Coordinate_Type.WEB_MERCATOR:
                geo = self.ecef_to_geo(ecef)
                return self.geo_to_web_mercator(geo)
            elif dest_type == Coordinate_Type.PIXEL:
                raise ValueError("Cannot convert directly from ECEF to Pixel")

        # Pixel as source
        elif source_type == Coordinate_Type.PIXEL:
            raise ValueError("Cannot convert from Pixel coordinates to other types")

        raise ValueError(f"Unsupported conversion from {source_type} to {dest_type}")

    def geographic_to_projected(
        self,
        geo: Geographic,
        target_crs: str = "EPSG:3857"  # Web Mercator default
    ) -> UTM | UPS | Web_Mercator:
        """Convert geographic to projected coordinates."""
        transformer = self._get_transformer(
            "EPSG:4326", target_crs  # WGS84 to target CRS
        )

        if geo.altitude_m is not None:
            easting, northing, elevation = transformer.transform(
                geo.longitude_deg, geo.latitude_deg, geo.altitude_m
            )
        else:
            easting, northing = transformer.transform(
                geo.longitude_deg, geo.latitude_deg
            )
            elevation = None

        # Return appropriate type based on target CRS
        epsg_code = EPSG_Manager.to_epsg_code(target_crs)

        if epsg_code == EPSG_Manager.WEB_MERCATOR:
            return Web_Mercator(easting, northing, elevation)
        elif EPSG_Manager.is_ups_zone(epsg_code):  # UPS North/South
            hemisphere = EPSG_Manager.get_ups_hemisphere(epsg_code)
            return UPS(easting, northing, elevation, hemisphere, target_crs)
        else:
            return UTM(easting, northing, elevation, target_crs)

    def projected_to_geographic(
        self,
        proj: UTM | UPS | Web_Mercator,
    ) -> Geographic:
        """Convert projected to geographic coordinates."""
        transformer = self._get_transformer(
            proj.crs, "EPSG:4326"  # Projected CRS to WGS84
        )

        if proj.altitude_m is not None:
            lon, lat, elevation = transformer.transform(
                proj.easting_m, proj.northing_m, proj.altitude_m
            )
        else:
            lon, lat = transformer.transform(proj.easting_m, proj.northing_m)
            elevation = None

        return Geographic(lat, lon, elevation)

    def get_utm_zone(self, longitude: float, latitude: float) -> str:
        """Get UTM zone for the given geographic coordinates."""
        # Handle polar regions (UTM doesn't work well at poles)
        if latitude >= 84.0:  # North pole region
            return EPSG_Manager.to_epsg_string(EPSG_Manager.UPS_NORTH)
        elif latitude <= -80.0:  # South pole region
            return EPSG_Manager.to_epsg_string(EPSG_Manager.UPS_SOUTH)

        # Calculate UTM zone (1-60)
        zone = int((longitude + 180) / 6) + 1
        if zone > 60:
            zone = 60
        elif zone < 1:
            zone = 1

        # Determine hemisphere and create EPSG code
        hemisphere = "N" if latitude >= 0 else "S"
        epsg_code = EPSG_Manager.create_utm_epsg(zone, hemisphere)

        return EPSG_Manager.to_epsg_string(epsg_code)

    def is_polar_region(self, latitude: float) -> bool:
        """Check if latitude is in polar region where UPS should be used."""
        return latitude >= 84.0 or latitude <= -80.0

    def get_epsg_info(self, epsg_code: int) -> dict:
        """Get comprehensive information about an EPSG code."""
        return {
            'code': epsg_code,
            'string': EPSG_Manager.to_epsg_string(epsg_code),
            'coordinate_type': EPSG_Manager.get_coordinate_type(epsg_code),
            'description': EPSG_Manager.get_description(epsg_code),
            'is_utm': EPSG_Manager.is_utm_zone(epsg_code),
            'is_ups': EPSG_Manager.is_ups_zone(epsg_code),
            'is_polar': EPSG_Manager.is_polar_region(epsg_code),
        }

    def get_epsg_info_from_string(self, epsg_str: str) -> dict:
        """Get comprehensive information about an EPSG code from string."""
        epsg_code = EPSG_Manager.to_epsg_code(epsg_str)
        return self.get_epsg_info(epsg_code)

    def to_utm(self, geo: Geographic) -> UTM:
        """Convert geographic coordinates to UTM."""
        utm_crs = self.get_utm_zone(geo.longitude_deg, geo.latitude_deg)
        return self.geographic_to_projected(geo, utm_crs)
