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
#    File:    terrain.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Terrain Elevation Module

This module provides elevation data access from local GeoTIFF files and AWS Terrain Tiles.
It supports a catalog-based approach for managing multiple elevation data sources with caching.
"""

# Python Standard Libraries
import json
import logging
import os
import pickle
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Third-Party Libraries
import numpy as np
import rasterio

# Project Libraries
from pointy.core.coordinate import Transformer, Geographic, Coordinate, Coordinate_Type, UTM, UPS, Web_Mercator, ECEF


class Interpolation_Method(Enum):
    """Elevation interpolation methods."""
    NEAREST = "nearest"
    BILINEAR = "bilinear"
    CUBIC = "cubic"


@dataclass
class Elevation_Point:
    """Elevation data point with coordinate and metadata."""
    coord: Geographic
    source: str
    accuracy: float | None = None
    _transformer: Transformer = field(default_factory=Transformer, init=False)

    def __post_init__(self):
        """Validate coordinate type."""
        if not isinstance(self.coord, Geographic):
            raise TypeError(f"Elevation_Point coord must be Geographic, got {type(self.coord)}")

    def coordinate(self) -> Geographic:
        """Get the geographic coordinate object."""
        return self.coord

    def geographic(self) -> Geographic:
        """Get coordinate as Geographic type (already is Geographic)."""
        return self.coord

    def to_utm(self) -> UTM:
        """Convert to UTM coordinate."""
        return self._transformer.geo_to_utm(self.coord)

    def to_ups(self) -> UPS:
        """Convert to UPS coordinate."""
        return self._transformer.geo_to_ups(self.coord)

    def to_web_mercator(self) -> Web_Mercator:
        """Convert to Web Mercator coordinate."""
        return self._transformer.geo_to_web_mercator(self.coord)

    def to_ecef(self) -> ECEF:
        """Convert to ECEF coordinate."""
        return self._transformer.geo_to_ecef(self.coord)

    @classmethod
    def create(cls, latitude: float, longitude: float, elevation: float, source: str, accuracy: float | None = None) -> 'Elevation_Point':
        """Create elevation point from individual components."""
        coord = Geographic(latitude, longitude, elevation)
        return cls(coord, source, accuracy)

    def __str__(self) -> str:
        """String representation."""
        return f"Elevation: {self.coord.altitude_m or 0.0:.1f}m at {self.coord} [{self.source}]"


class Elevation_Source:
    """Base class for elevation data sources."""

    def __init__(self, name: str):
        self.name = name

    def get_elevation(self, coord: Geographic) -> float | None:
        """Get elevation for a geographic coordinate."""
        raise NotImplementedError

    def get_elevations(self, coords: list[Geographic]) -> list[float | None]:
        """Get elevations for multiple points."""
        return [self.get_elevation(coord) for coord in coords]


class Local_DEM_Elevation_Source(Elevation_Source):
    """Local DEM file elevation source."""

    def __init__(self, dem_file: str | Path):
        super().__init__(f"Local DEM ({Path(dem_file).name})")
        self.dem_file = Path(dem_file)
        self.dataset = None
        self.logger = logging.getLogger(__name__)
        self._load_dataset()

    def _load_dataset(self):
        """Load DEM dataset using rasterio."""
        try:
            self.dataset = rasterio.open(str(self.dem_file))
            if self.dataset is None:
                raise RuntimeError(f"Could not open DEM file: {self.dem_file}")

            # Get basic info
            self.bounds = self.dataset.bounds
            self.transform = self.dataset.transform

            # Get CRS info
            self.crs = self.dataset.crs
            if self.crs:
                self.epsg_code = self.crs.to_epsg()
            else:
                self.epsg_code = None

            self.logger.info(f"Loaded DEM: {self.dem_file}")
            self.logger.info(f"  Size: {self.dataset.width}x{self.dataset.height}")
            self.logger.info(f"  Bounds: {self.bounds}")
            if self.epsg_code:
                self.logger.info(f"  EPSG: {self.epsg_code}")

        except ImportError as e:
            raise ImportError(f"rasterio is required for terrain loading: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load DEM {self.dem_file}: {e}")

    def get_elevation(self, lat: float, lon: float) -> float | None:
        """Get elevation from local DEM."""
        if self.dataset is None:
            return None

        try:
            # Convert lat/lon to pixel coordinates
            # This is simplified - proper implementation would handle coordinate transformations
            pixel_x = int((lon - self.transform[0]) / self.transform[1])
            pixel_y = int((lat - self.transform[3]) / self.transform[5])

            # Check bounds
            if (pixel_x < 0 or pixel_x >= self.dataset.width or
                pixel_y < 0 or pixel_y >= self.dataset.height):
                return None

            # Read elevation
            elevation = self.dataset.read(1, window=((pixel_y, pixel_y + 1), (pixel_x, pixel_x + 1)))[0, 0]

            # Check for no data values
            nodata = self.dataset.nodata
            if nodata is not None and elevation == nodata:
                return None

            return float(elevation)

        except (ValueError, IndexError, TypeError):
            pass

        return None


class GeoTIFF_Elevation_Source(Elevation_Source):
    """GeoTIFF file elevation source with lazy loading and caching."""

    def __init__(self, file_path: str | Path):
        super().__init__(f"GeoTIFF ({Path(file_path).name})")
        self.file_path = Path(file_path)
        self.dataset = None
        self.bounds = None
        self.transform = None
        self.crs = None
        self.epsg_code = None
        self.interpolation = Interpolation_Method.BILINEAR  # Default interpolation
        self.logger = logging.getLogger(__name__)
        self._loaded = False

    def _load_dataset(self):
        """Load GeoTIFF dataset using rasterio."""
        if self._loaded:
            return

        try:
            self.dataset = rasterio.open(str(self.file_path))
            if self.dataset is None:
                raise RuntimeError(f"Could not open GeoTIFF file: {self.file_path}")

            # Get basic info
            self.bounds = self.dataset.bounds
            self.transform = self.dataset.transform

            # Get CRS info
            self.crs = self.dataset.crs
            if self.crs:
                self.epsg_code = self.crs.to_epsg()
            else:
                self.epsg_code = None

            self._loaded = True
            self.logger.debug(f"Loaded GeoTIFF: {self.file_path}")

        except ImportError as e:
            raise ImportError(f"rasterio is required for GeoTIFF loading: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load GeoTIFF {self.file_path}: {e}")

    def contains(self, coord: Geographic) -> bool:
        """Check if this GeoTIFF contains the given coordinate."""
        if not self._loaded:
            self._load_dataset()

        if self.bounds is None:
            return False

        # Check if coordinate is within bounds (assuming geographic coordinates)
        # This is simplified - proper implementation would handle coordinate transformations
        return (self.bounds.left <= coord.longitude_deg <= self.bounds.right and
                self.bounds.bottom <= coord.latitude_deg <= self.bounds.top)

    def get_elevation(self, coord: Geographic) -> float | None:
        """Get elevation at coordinate using rasterio interpolation.

        Args:
            coord: Geographic coordinate

        Returns:
            Elevation in meters or None if no data
        """
        if not self._loaded:
            self._load_dataset()

        if self.dataset is None or self.bounds is None:
            return None

        # Check if coordinate is within bounds (assuming geographic coordinates)
        if not self.contains(coord):
            return None

        try:
            # Convert geographic to pixel coordinates
            # This is simplified - proper implementation would handle coordinate transformations
            col, row = self._geo_to_pixel(coord)

            # Get elevation using specified interpolation method
            if self.interpolation == Interpolation_Method.NEAREST:
                elevation = self.dataset.read(1, window=((row, row+1), (col, col+1)))[0, 0]
            elif self.interpolation == Interpolation_Method.BILINEAR:
                elevation = self._bilinear_interpolation(col, row)
            elif self.interpolation == Interpolation_Method.CUBIC:
                elevation = self._cubic_interpolation(col, row)
            else:
                raise ValueError(f"Unsupported interpolation method: {self.interpolation}")

            return float(elevation) if elevation != self.dataset.nodata else None

        except Exception as e:
            self.logger.error(f"Error reading elevation: {e}")
            return None

    def _geo_to_pixel(self, coord: Geographic) -> tuple[int, int]:
        """Convert geographic coordinates to pixel coordinates."""
        # This is simplified - proper implementation would handle coordinate transformations
        # For now, assume the dataset is in geographic coordinates
        transform = self.dataset.transform
        col, row = ~transform * (coord.longitude_deg, coord.latitude_deg)
        return int(col), int(row)

    def _bilinear_interpolation(self, col: float, row: float) -> float:
        """Perform bilinear interpolation."""
        # Get the 4 surrounding pixels
        col0, row0 = int(col), int(row)
        col1, row1 = col0 + 1, row0 + 1

        # Read the 2x2 window
        window = ((row0, row1 + 1), (col0, col1 + 1))
        data = self.dataset.read(1, window=window)

        if data.shape != (2, 2) or self.dataset.nodata in data:
            # Fall back to nearest neighbor
            return self.dataset.read(1, window=((row0, row0 + 1), (col0, col0 + 1)))[0, 0]

        # Bilinear interpolation
        fx, fy = col - col0, row - row0
        elevation = (
            data[0, 0] * (1 - fx) * (1 - fy) +
            data[0, 1] * fx * (1 - fy) +
            data[1, 0] * (1 - fx) * fy +
            data[1, 1] * fx * fy
        )

        return elevation

    def _cubic_interpolation(self, col: float, row: float) -> float:
        """Perform cubic interpolation (simplified)."""
        # For now, fall back to bilinear
        return self._bilinear_interpolation(col, row)


class Terrain_Catalog(Elevation_Source):
    """Catalog for managing local GeoTIFF elevation data sources."""

    def __init__(self, catalog_root: str | Path | None = None):
        """Initialize terrain catalog.

        Args:
            catalog_root: Root directory containing GeoTIFF files. If None, uses TERRAIN_CATALOG_ROOT env var.
        """
        super().__init__("Terrain Catalog")

        if catalog_root is None:
            catalog_root = os.environ.get('TERRAIN_CATALOG_ROOT')
            if catalog_root is None:
                raise ValueError("catalog_root must be provided or TERRAIN_CATALOG_ROOT environment variable must be set")

        self.catalog_root = Path(catalog_root)
        self.sources = []
        self.max_memory_mb = 500  # Maximum memory for cached tiles
        self.logger = logging.getLogger(__name__)

        # Discover GeoTIFF files
        self._discover_sources()

    def _discover_sources(self):
        """Discover all GeoTIFF files in the catalog directory."""
        if not self.catalog_root.exists():
            self.logger.warning(f"Catalog directory does not exist: {self.catalog_root}")
            return

        # Look for .tif files recursively
        for tif_file in self.catalog_root.rglob("*.tif"):
            try:
                source = GeoTIFF_Elevation_Source(tif_file)
                self.sources.append(source)
                self.logger.debug(f"Found GeoTIFF: {tif_file}")
            except Exception as e:
                self.logger.warning(f"Could not load GeoTIFF {tif_file}: {e}")

        self.logger.info(f"Discovered {len(self.sources)} GeoTIFF sources in {self.catalog_root}")

    def get_elevation(self, coord: Geographic) -> float | None:
        """Get elevation from the catalog.

        Args:
            coord: Geographic coordinate to query

        Returns:
            Elevation in meters or None if no data found
        """
        # Try each source that contains the coordinate
        for source in self.sources:
            if source.contains(coord):
                elevation = source.get_elevation(coord)
                if elevation is not None:
                    return elevation

        return None

    def get_sources_for_coordinate(self, coord: Geographic) -> list[GeoTIFF_Elevation_Source]:
        """Get all sources that contain the given coordinate."""
        return [source for source in self.sources if source.contains(coord)]

    def get_catalog_info(self) -> dict:
        """Get information about the catalog."""
        return {
            'catalog_root': str(self.catalog_root),
            'total_sources': len(self.sources),
            'sources': [
                {
                    'name': source.name,
                    'file_path': str(source.file_path),
                    'bounds': source.bounds._asdict() if source.bounds else None,
                    'epsg_code': source.epsg_code
                }
                for source in self.sources
            ]
        }

class Manager:
    """Manages multiple elevation sources with caching and coordinate transformations."""

    def __init__(
        self,
        sources: list[Elevation_Source],
        cache_enabled: bool = True,
        interpolation: Interpolation_Method = Interpolation_Method.BILINEAR
    ):
        """Initialize terrain manager.

        Args:
            sources: List of elevation sources to query
            cache_enabled: Enable elevation caching for performance
            interpolation: Interpolation method
        """
        if not sources:
            raise ValueError("At least one elevation source must be provided")

        self.cache_enabled = cache_enabled
        self.interpolation = interpolation
        self.cache_file = Path(tempfile.gettempdir()) / "pointy_mcpointface" / "elevation_cache.pkl"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize elevation sources
        self.sources: list[Elevation_Source] = sources

        # Set interpolation method on all sources that support it
        for source in self.sources:
            if hasattr(source, 'interpolation'):
                source.interpolation = self.interpolation

        # Load cache
        self.elevation_cache: dict[str, Elevation_Point] = {}
        if cache_enabled and self.cache_file.exists():
            self._load_cache()

        # Coordinate transformer
        self.coord_transformer = Transformer()

    @classmethod
    def create_default(cls, cache_enabled: bool = True, interpolation: Interpolation_Method = Interpolation_Method.BILINEAR) -> 'Manager':
        """Create a default terrain manager with catalog sources."""
        try:
            catalog = Terrain_Catalog()
            return cls([catalog], cache_enabled, interpolation)
        except Exception as e:
            raise ValueError("No terrain sources available. Please ensure GeoTIFF files are in the catalog directory.")

    @classmethod
    def create_catalog_only(cls, catalog_root: str | Path | None = None, cache_enabled: bool = True, interpolation: Interpolation_Method = Interpolation_Method.BILINEAR) -> 'Manager':
        """Create a terrain manager with only catalog sources."""
        catalog = Terrain_Catalog(catalog_root)
        if not catalog.sources:
            raise ValueError(f"No terrain sources found in catalog: {catalog.catalog_root}")
        return cls([catalog], cache_enabled, interpolation)

    def add_local_dem(self, dem_file: str | Path):
        """Add a local DEM file as an elevation source."""
        try:
            local_source = Local_DEM_Elevation_Source(dem_file)
            self.sources.insert(0, local_source)  # Prioritize local DEM
        except Exception as e:
            logging.warning(f"Could not add local DEM {dem_file}: {e}")

    @staticmethod
    def _cache_key(coord) -> str:
        """Generate consistent cache key for any coordinate type."""
        # Convert to geographic coordinates first
        if coord.type() == Coordinate_Type.GEOGRAPHIC:
            # Already geographic
            geo = coord
        elif coord.type() == Coordinate_Type.UTM:
            geo = Transformer().utm_to_geo(coord)
        elif coord.type() == Coordinate_Type.WEB_MERCATOR:
            geo = Transformer().web_mercator_to_geo(coord)
        elif coord.type() == Coordinate_Type.UPS:
            geo = Transformer().ups_to_geo(coord)
        elif coord.type() == Coordinate_Type.ECEF:
            geo = Transformer().ecef_to_geo(coord)
        else:
            # Other coordinate types - skip caching for now
            return f"{coord.type().name}_{id(coord)}"

        return f"{geo.latitude_deg:.6f},{geo.longitude_deg:.6f}"

    def _query_sources(self, coord: Geographic) -> Elevation_Point | None:
        """Common logic for querying all elevation sources.

        Args:
            coord: Geographic coordinate to query

        Returns:
            Elevation_Point with full metadata or None if no data found
        """
        # Try each source in order
        for source in self.sources:
            try:
                elevation = source.get_elevation(coord)
                if elevation is not None:
                    # Create elevation point
                    point = Elevation_Point(
                        coord=Geographic(coord.latitude_deg, coord.longitude_deg, elevation),
                        source=source.name
                    )
                    return point

            except Exception as e:
                logging.warning(f"Elevation source {source.name} failed: {e}")
                continue

        return None

    def elevation(self, coord: Coordinate) -> float | None:
        """Get elevation for any coordinate type."""
        # Convert to geographic coordinates first
        if coord.type() == Coordinate_Type.GEOGRAPHIC:
            geo_coord = coord
        else:
            geo_coord = self.coord_transformer.convert(coord, Coordinate_Type.GEOGRAPHIC)

        # Check cache first
        cache_key = self._cache_key(geo_coord)

        if self.cache_enabled and cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key].coord.altitude_m

        # Query sources
        point = self._query_sources(geo_coord)
        if point is not None:
            # Cache the result
            if self.cache_enabled:
                self.elevation_cache[cache_key] = point
                self._save_cache()

            return point.coord.altitude_m

        return None

    def elevation_point(self, coord: Coordinate) -> Elevation_Point | None:
        """Get elevation point with full metadata for any coordinate type."""
        # Convert to geographic coordinates first
        if coord.type() == Coordinate_Type.GEOGRAPHIC:
            geo_coord = coord
        else:
            geo_coord = self.coord_transformer.convert(coord, Coordinate_Type.GEOGRAPHIC)

        # Check cache first
        cache_key = self._cache_key(geo_coord)

        if self.cache_enabled and cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]

        # Query sources
        point = self._query_sources(geo_coord)
        if point is not None:
            # Cache the result
            if self.cache_enabled:
                self.elevation_cache[cache_key] = point
                self._save_cache()

            return point

        return None

    def elevation_batch(self, coords: list[Geographic]) -> list[float | None]:
        """Get elevations for multiple points (batch processing)."""
        # Check cache first
        cached_results = []
        uncached_coords = []
        uncached_indices = []

        for i, coord in enumerate(coords):
            cache_key = self._cache_key(coord)

            if self.cache_enabled and cache_key in self.elevation_cache:
                cached_results.append(self.elevation_cache[cache_key].coord.altitude_m)
            else:
                cached_results.append(None)
                uncached_coords.append(coord)
                uncached_indices.append(i)

        # Process uncached points in parallel
        if uncached_coords:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_index = {}

                for source in self.sources:
                    if not uncached_coords:
                        break

                    # Submit batch request to this source
                    future = executor.submit(source.get_elevations, uncached_coords)
                    future_to_index[future] = source

                # Process results as they complete
                for future in as_completed(future_to_index):
                    source = future_to_index[future]

                    try:
                        results = future.result()

                        # Update cached results
                        for i, elevation in enumerate(results):
                            if elevation is not None:
                                idx = uncached_indices[i]
                                coord = uncached_coords[i]
                                cached_results[idx] = elevation

                                # Cache the result
                                if self.cache_enabled:
                                    cache_key = self._cache_key(coord)
                                    point = Elevation_Point(
                                        coord=Geographic(coord.latitude_deg, coord.longitude_deg, elevation),
                                        source=source.name
                                    )
                                    self.elevation_cache[cache_key] = point

                    except Exception as e:
                        logging.warning(f"Batch elevation request to {source.name} failed: {e}")

        # Save cache
        if self.cache_enabled:
            self._save_cache()

        return cached_results

    def get_elevation_point(self, latitude: float, longitude: float) -> Elevation_Point | None:
        """Get detailed elevation point with metadata."""
        coord = Geographic(latitude, longitude)
        cache_key = self._cache_key(coord)

        if self.cache_enabled and cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]

        elevation = self.elevation(coord)
        if elevation is not None:
            return self.elevation_cache.get(cache_key)

        return None

    def clear_cache(self):
        """Clear elevation cache."""
        self.elevation_cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_points': len(self.elevation_cache),
            'cache_file': str(self.cache_file),
            'cache_size_mb': self.cache_file.stat().st_size / (1024 * 1024) if self.cache_file.exists() else 0,
            'sources': [source.name for source in self.sources]
        }

    def _load_cache(self):
        """Load elevation cache from file."""
        try:
            with open(self.cache_file, 'rb') as f:
                self.elevation_cache = pickle.load(f)
        except Exception as e:
            # Handle any pickle errors including class name changes
            logging.warning(f"Could not load cache due to: {e}. Starting with empty cache.")
            self.elevation_cache = {}
            # Remove the problematic cache file
            try:
                self.cache_file.unlink()
                logging.info("Removed problematic cache file")
            except:
                pass

    def _save_cache(self):
        """Save elevation cache to file."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.elevation_cache, f)
        except (IOError, pickle.PickleError) as e:
            logging.warning(f"Could not save elevation cache: {e}")


# Global terrain manager instance
_terrain_manager: Manager | None = None


def get_terrain_manager() -> Manager:
    """Get the global terrain manager instance."""
    global _terrain_manager
    if _terrain_manager is None:
        _terrain_manager = Manager.create_default()
    return _terrain_manager


def create_terrain_manager(sources: list[Elevation_Source], cache_enabled: bool = True, interpolation: Interpolation_Method = Interpolation_Method.BILINEAR) -> Manager:
    """Create a new terrain manager with specified sources."""
    return Manager(sources, cache_enabled, interpolation)


def create_catalog_manager(catalog_root: str | Path | None = None, cache_enabled: bool = True, interpolation: Interpolation_Method = Interpolation_Method.BILINEAR) -> Manager:
    """Create a terrain manager with only catalog sources."""
    return Manager.create_catalog_only(catalog_root, cache_enabled, interpolation)


def elevation(coord: Geographic) -> float | None:
    """Convenience function to get elevation.

    Args:
        coord: Geographic coordinate

    Returns:
        Elevation in meters or None if not found
    """
    manager = get_terrain_manager()
    return manager.elevation(coord)

def elevation_point(coord: Geographic) -> Elevation_Point | None:
    """Convenience function to get elevation point with metadata.

    Args:
        coord: Geographic coordinate

    Returns:
        Elevation point with metadata or None if not found
    """
    manager = get_terrain_manager()
    return manager.elevation_point(coord)
