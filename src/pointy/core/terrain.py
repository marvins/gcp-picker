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

This module provides elevation data access from multiple sources including SRTM and AWS Terrain Tiles.
It supports caching and coordinate-based elevation queries.
"""

import os
import json
import pickle
import tempfile
from pathlib import Path
from dataclasses import dataclass
import logging

import numpy as np
import rasterio
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed



@dataclass
class ElevationPoint:
    """Elevation data point."""
    latitude: float
    longitude: float
    elevation: float
    source: str
    accuracy: float | None = None

    def __str__(self) -> str:
        """String representation."""
        return f"Elevation: {self.elevation:.1f}m at ({self.latitude:.6f}, {self.longitude:.6f}) [{self.source}]"


class ElevationSource:
    """Base class for elevation data sources."""

    def __init__(self, name: str):
        self.name = name

    def get_elevation(self, lat: float, lon: float) -> float | None:
        """Get elevation for a single point."""
        raise NotImplementedError

    def get_elevations(self, points: list[tuple[float, float]]) -> list[float | None]:
        """Get elevations for multiple points."""
        return [self.get_elevation(lat, lon) for lat, lon in points]


class SRTMElevationSource(ElevationSource):
    """SRTM (Shuttle Radar Topography Mission) elevation source."""

    def __init__(self):
        super().__init__("SRTM 30m")
        self.base_url = "https://earthengine.googleapis.com/dataset/export/USGS/SRTMGL1_003"
        self.cache_dir = Path(tempfile.gettempdir()) / "pointy_mcpointface" / "srtm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_elevation(self, lat: float, lon: float) -> float | None:
        """Get elevation from SRTM using Earth Engine API."""
        try:
            # Check cache first
            cache_file = self._get_cache_file(lat, lon)
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('elevation')

            # Query Earth Engine API
            url = "https://maps.googleapis.com/maps/api/elevation/json"
            params = {
                'locations': f'{lat},{lon}',
                'key': os.environ.get('GOOGLE_ELEVATION_API_KEY', '')
            }

            if not params['key']:
                # Fallback to OpenTopography API
                return self._get_opentopography_elevation(lat, lon)

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data['status'] == 'OK' and data['results']:
                elevation = data['results'][0]['elevation']

                # Cache the result
                cache_data = {
                    'latitude': lat,
                    'longitude': lon,
                    'elevation': elevation,
                    'source': 'google_elevation'
                }

                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)

                return elevation

        except (requests.RequestException, json.JSONDecodeError, KeyError, IOError):
            pass

        return None

    def _get_opentopography_elevation(self, lat: float, lon: float) -> float | None:
        """Fallback to OpenTopography API."""
        try:
            url = "https://portal.opentopography.org/API/otds"
            params = {
                'dataset': 'SRTMGL1',
                'location': f'{lon},{lat}',
                'outputFormat': 'json'
            }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                return float(data['data'][0]['elevation'])

        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError):
            pass

        return None

    def _get_cache_file(self, lat: float, lon: float) -> Path:
        """Get cache file path for coordinates."""
        # Round to 4 decimal places (~10m precision)
        lat_rounded = round(lat, 4)
        lon_rounded = round(lon, 4)

        filename = f"elev_{lat_rounded}_{lon_rounded}.json"
        return self.cache_dir / filename


class AWSElevationSource(ElevationSource):
    """AWS Terrain Tiles elevation source."""

    def __init__(self):
        super().__init__("AWS Terrain Tiles")
        self.base_url = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium"
        self.cache_dir = Path(tempfile.gettempdir()) / "pointy_mcpointface" / "aws_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_elevation(self, lat: float, lon: float) -> float | None:
        """Get elevation from AWS Terrain Tiles."""
        try:
            # Calculate tile coordinates
            zoom = 12  # Use zoom level 12 for ~30m resolution

            x, y = self._lat_lon_to_tile(lat, lon, zoom)

            # Check cache
            cache_file = self.cache_dir / f"tile_{zoom}_{x}_{y}.png"

            if not cache_file.exists():
                # Download tile
                tile_url = f"{self.base_url}/{zoom}/{x}/{y}.png"
                response = requests.get(tile_url, timeout=30)
                response.raise_for_status()

                with open(cache_file, 'wb') as f:
                    f.write(response.content)

            # Extract elevation from tile
            from PIL import Image

            tile_image = Image.open(cache_file)

            # Calculate pixel position within tile
            pixel_x = int((lon + 180) * (256 / 360) * (2 ** zoom)) % 256
            pixel_y = int((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) *
                         (256 / 2) * (2 ** zoom)) % 256

            # Get RGB values
            r, g, b = tile_image.getpixel((pixel_x, pixel_y))

            # Convert RGB to elevation (terrarium format)
            elevation = (r * 256 + g + b / 256) - 32768

            return elevation

        except (requests.RequestException, IOError, OSError, ValueError):
            pass

        return None

    def _lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> tuple[int, int]:
        """Convert lat/lon to tile coordinates."""
        x = int((lon + 180) / 360 * (2 ** zoom))
        y = int((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * (2 ** zoom))

        return x, y


class LocalDEMElevationSource(ElevationSource):
    """Local DEM file elevation source."""

    def __init__(self, dem_file: str | Path):
        super().__init__(f"Local DEM ({Path(dem_file).name})")
        self.dem_file = Path(dem_file)
        self.dataset = None
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

            logger.info(f"Loaded DEM: {self.dem_file}")
            logger.info(f"  Size: {self.dataset.width}x{self.dataset.height}")
            logger.info(f"  Bounds: {self.bounds}")
            if self.epsg_code:
                logger.info(f"  EPSG: {self.epsg_code}")

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


class Manager:
    """Terrain elevation manager with multiple data sources."""

    def __init__(self, cache_enabled: bool = True):
        """Initialize terrain manager."""
        self.cache_enabled = cache_enabled
        self.cache_file = Path(tempfile.gettempdir()) / "pointy_mcpointface" / "elevation_cache.pkl"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize elevation sources
        self.sources: list[ElevationSource] = [
            SRTMElevationSource(),
            AWSElevationSource(),
        ]

        # Load cache
        self.elevation_cache: dict[str, ElevationPoint] = {}
        if cache_enabled and self.cache_file.exists():
            self._load_cache()

        # Coordinate transformer
        self.coord_transformer = CoordinateTransformer()

    def add_local_dem(self, dem_file: str | Path):
        """Add a local DEM file as an elevation source."""
        try:
            local_source = LocalDEMElevationSource(dem_file)
            self.sources.insert(0, local_source)  # Prioritize local DEM
        except Exception as e:
            logging.warning(f"Could not add local DEM {dem_file}: {e}")

    def elevation(self, latitude: float, longitude: float) -> float | None:
        """Get elevation for a geographic coordinate."""
        # Check cache first
        cache_key = f"{latitude:.6f},{longitude:.6f}"

        if self.cache_enabled and cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key].elevation

        # Try each source in order
        for source in self.sources:
            try:
                elevation = source.get_elevation(latitude, longitude)
                if elevation is not None:
                    # Cache the result
                    if self.cache_enabled:
                        point = ElevationPoint(
                            latitude=latitude,
                            longitude=longitude,
                            elevation=elevation,
                            source=source.name
                        )
                        self.elevation_cache[cache_key] = point
                        self._save_cache()

                    return elevation

            except Exception as e:
                logging.warning(f"Elevation source {source.name} failed: {e}")
                continue

        return None

    def elevation_batch(self, points: list[tuple[float, float]]) -> list[float | None]:
        """Get elevations for multiple points (batch processing)."""
        # Check cache first
        cached_results = []
        uncached_points = []
        uncached_indices = []

        for i, (lat, lon) in enumerate(points):
            cache_key = f"{lat:.6f},{lon:.6f}"

            if self.cache_enabled and cache_key in self.elevation_cache:
                cached_results.append(self.elevation_cache[cache_key].elevation)
            else:
                cached_results.append(None)
                uncached_points.append((lat, lon))
                uncached_indices.append(i)

        # Process uncached points in parallel
        if uncached_points:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_index = {}

                for source in self.sources:
                    if not uncached_points:
                        break

                    # Submit batch request to this source
                    future = executor.submit(source.get_elevations, uncached_points)
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
                                lat, lon = uncached_points[i]
                                cached_results[idx] = elevation

                                # Cache the result
                                if self.cache_enabled:
                                    cache_key = f"{lat:.6f},{lon:.6f}"
                                    point = ElevationPoint(
                                        latitude=lat,
                                        longitude=lon,
                                        elevation=elevation,
                                        source=source.name
                                    )
                                    self.elevation_cache[cache_key] = point

                    except Exception as e:
                        logging.warning(f"Batch elevation request to {source.name} failed: {e}")

        # Save cache
        if self.cache_enabled:
            self._save_cache()

        return cached_results

    def get_elevation_point(self, latitude: float, longitude: float) -> ElevationPoint | None:
        """Get detailed elevation point with metadata."""
        cache_key = f"{latitude:.6f},{longitude:.6f}"

        if self.cache_enabled and cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]

        elevation = self.elevation(latitude, longitude)
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
        except (pickle.PickleError, IOError, EOFError):
            self.elevation_cache = {}

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
        _terrain_manager = Manager()
    return _terrain_manager


def elevation(latitude: float, longitude: float) -> float | None:
    """Convenience function to get elevation."""
    return get_terrain_manager().elevation(latitude, longitude)
