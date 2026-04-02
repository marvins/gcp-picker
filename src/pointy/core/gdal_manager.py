"""
GDAL Manager - Centralized raster operations interface using rasterio

Provides a singleton manager for all raster operations with:
- Centralized import error handling
- Connection pooling for datasets
- Cached metadata extraction
- Unified API for raster operations
"""

import logging
from pathlib import Path
from typing import Any
from dataclasses import dataclass

import numpy as np
import rasterio

from app.core.constants import (
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_REFERENCE_EXTENSIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class DatasetInfo:
    """Metadata about a GDAL dataset."""
    path: Path
    width: int
    height: int
    band_count: int
    has_geotransform: bool
    has_projection: bool
    has_gcps: bool
    gcp_count: int
    has_rpc: bool
    driver: str
    data_type: str
    epsg: int | None = None
    geotransform: tuple | None = None


class GDALManager:
    """Singleton manager for raster operations using rasterio."""

    _instance: "GDALManager | None" = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if GDALManager._initialized:
            return

        self._rasterio_available = False

        # Cache for opened datasets
        self._dataset_cache: dict[Path, Any] = {}
        self._info_cache: dict[Path, DatasetInfo] = {}

        self._try_import_rasterio()
        GDALManager._initialized = True

    def _try_import_rasterio(self) -> bool:
        """Try to import rasterio and set availability flag."""
        try:
            import rasterio
            self._rasterio_available = True
            logger.info("Rasterio initialized successfully")
            return True
        except ImportError:
            logger.warning("Rasterio not available - geospatial features disabled")
            self._rasterio_available = False
            return False

    def is_available(self) -> bool:
        """Check if rasterio is available."""
        return self._rasterio_available

    def ensure_available(self) -> None:
        """Raise error if rasterio is not available."""
        if not self._rasterio_available:
            raise ImportError("Rasterio is required for this operation but is not available")

    def can_load(self, file_path: str | Path) -> bool:
        """Check if file can be loaded by rasterio."""
        if not self._rasterio_available:
            return False

        path = Path(file_path)
        ext = path.suffix.lower()

        # Check supported extensions
        if ext not in SUPPORTED_IMAGE_EXTENSIONS and ext not in SUPPORTED_REFERENCE_EXTENSIONS:
            return False

        # Try to open with rasterio
        try:
            with rasterio.open(path):
                return True
        except Exception:
            return False

    def get_info(self, file_path: str | Path) -> DatasetInfo | None:
        """Get metadata about a dataset (cached)."""
        if not self._rasterio_available:
            return None

        path = Path(file_path)

        # Check cache
        if path in self._info_cache:
            return self._info_cache[path]

        try:
            with rasterio.open(path) as src:
                # Get geotransform from transform
                transform = src.transform
                has_geotransform = transform.is_rectilinear

                # Get projection
                has_projection = src.crs is not None
                src.crs.to_wkt() if src.crs else None

                # Get EPSG code
                epsg = src.crs.to_epsg() if src.crs else None

                # Check for GCPs
                gcps = src.gcps
                has_gcps = gcps is not None and len(gcps[0]) > 0 if isinstance(gcps, tuple) else gcps is not None and len(gcps) > 0
                gcp_count = len(gcps[0]) if has_gcps and isinstance(gcps, tuple) else len(gcps) if has_gcps else 0

                # Check for RPC metadata
                rpc_metadata = src.tags().get('RPC_METADATA')
                has_rpc = rpc_metadata is not None and len(rpc_metadata) > 0

                # Get first band info
                data_type = str(src.dtypes[0]) if src.dtypes else 'unknown'

                # Build geotransform array
                geotransform = [
                    transform.c,     # origin x
                    transform.a,     # pixel width
                    transform.b,     # rotation (0 for north-up)
                    transform.f,     # origin y
                    transform.d,     # rotation (0 for north-up)
                    transform.e,     # pixel height (negative)
                ] if has_geotransform else None

                info = DatasetInfo(
                    path=path,
                    width=src.width,
                    height=src.height,
                    band_count=src.count,
                    has_geotransform=has_geotransform,
                    has_projection=has_projection,
                    has_gcps=has_gcps,
                    gcp_count=gcp_count,
                    has_rpc=has_rpc,
                    driver=src.driver,
                    data_type=data_type,
                    epsg=epsg,
                    geotransform=geotransform
                )

                # Cache
                self._info_cache[path] = info

                return info

        except Exception as e:
            logger.error(f"Error getting dataset info for {path}: {e}")
            return None

    def read_image(self, file_path: str | Path, bands: list[int] | None = None) -> np.ndarray | None:
        """Read image data as numpy array."""
        if not self._rasterio_available:
            raise ImportError("Rasterio is required for reading raster files")

        path = Path(file_path)

        try:
            with rasterio.open(path) as src:
                # Default to all bands if not specified
                if bands is None:
                    bands = list(range(1, src.count + 1))

                # Read bands
                band_data = []
                for band_num in bands:
                    data = src.read(band_num)
                    band_data.append(data)

                # Stack bands
                if len(band_data) == 1:
                    return band_data[0]
                else:
                    return np.stack(band_data, axis=-1)

        except Exception as e:
            logger.error(f"Error reading image {path}: {e}")
            return None

    def read_as_rgb(self, file_path: str | Path) -> np.ndarray | None:
        """Read image as 3-channel RGB."""
        data = self.read_image(file_path)
        if data is None:
            return None

        # Handle different band configurations
        if len(data.shape) == 2:
            # Single band - convert to RGB
            return np.stack([data] * 3, axis=-1)
        elif len(data.shape) == 3:
            if data.shape[2] == 1:
                # Single band in 3D array
                return np.repeat(data, 3, axis=2)
            elif data.shape[2] >= 3:
                # Multi-band, take first 3 as RGB
                return data[:, :, :3]
            else:
                # 2-band (unusual) - duplicate last band
                rgb = np.zeros((*data.shape[:2], 3), dtype=data.dtype)
                rgb[:, :, :data.shape[2]] = data
                return rgb

        return data

    def get_geotransform(self, file_path: str | Path) -> tuple | None:
        """Get geotransform for a dataset."""
        if not self._rasterio_available:
            return None

        info = self.get_info(file_path)
        if info and info.has_geotransform:
            return info.geotransform
        return None

    def get_gcps(self, file_path: str | Path) -> list[dict]:
        """Get GCPs as list of dictionaries."""
        if not self._rasterio_available:
            return []

        try:
            with rasterio.open(file_path) as src:
                gcps_data = src.gcps

                # gcps returns tuple (gcps_list, crs) or just list
                if isinstance(gcps_data, tuple):
                    gcps_list = gcps_data[0]
                else:
                    gcps_list = gcps_data

                if not gcps_list:
                    return []

                result = []
                for gcp in gcps_list:
                    result.append({
                        'id': gcp.id,
                        'pixel': (gcp.col, gcp.row),
                        'geo': (gcp.x, gcp.y, gcp.z)
                    })

                return result

        except Exception as e:
            logger.error(f"Error getting GCPs: {e}")
            return []

    def get_rpc_data(self, file_path: str | Path) -> dict | None:
        """Get RPC metadata if available."""
        if not self._rasterio_available:
            return None

        try:
            with rasterio.open(file_path) as src:
                rpc_metadata = src.tags().get('RPC_METADATA')

                if rpc_metadata:
                    import json
                    try:
                        return json.loads(rpc_metadata)
                    except json.JSONDecodeError:
                        return {'raw': rpc_metadata}
                return None

        except Exception as e:
            logger.error(f"Error getting RPC data: {e}")
            return None

    def pixel_to_geo(self, file_path: str | Path, x: float, y: float) -> tuple[float, float] | None:
        """Convert pixel coordinates to geographic coordinates."""
        transform = self.get_geotransform(file_path)
        if transform is None:
            return None

        # GDAL geotransform: [origin_x, pixel_width, rotation_x, origin_y, rotation_y, pixel_height]
        geo_x = transform[0] + x * transform[1] + y * transform[2]
        geo_y = transform[3] + x * transform[4] + y * transform[5]
        return (geo_x, geo_y)

    def geo_to_pixel(self, file_path: str | Path, geo_x: float, geo_y: float) -> tuple[float, float] | None:
        """Convert geographic coordinates to pixel coordinates."""
        transform = self.get_geotransform(file_path)
        if transform is None:
            return None

        # Simplified inverse (assumes no rotation)
        # For full solution, would need matrix inversion
        x = (geo_x - transform[0]) / transform[1]
        y = (geo_y - transform[3]) / transform[5]
        return (x, y)

    def has_spatial_info(self, file_path: str | Path) -> bool:
        """Check if file has geospatial information (geotransform, projection, or GCPs)."""
        info = self.get_info(file_path)
        if info is None:
            return False
        return info.has_geotransform or info.has_projection or info.has_gcps

    def clear_cache(self):
        """Clear all cached datasets and info."""
        self._dataset_cache.clear()
        self._info_cache.clear()
        logger.info("GDAL cache cleared")


# Global instance getter
def get_gdal_manager() -> GDALManager:
    """Get the singleton GDAL manager instance."""
    return GDALManager()
