"""
Imagery API - Rasterio-based imagery handling with metadata parsing
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

import rasterio
from pyproj import Transformer

from app.core.gdal_reader import GDALReader


@dataclass
class Imagery_Info:
    """Information about an imagery file."""
    file_path: str
    width: int
    height: int
    band_count: int
    has_geotransform: bool
    has_gcps: bool
    has_projection: bool
    epsg_code: Optional[int] = None
    gcp_count: int = 0
    geotransform: Optional[Tuple] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    metadata: Dict[str, Any] = None

    def has_spatial_info(self) -> bool:
        """Check if image has any spatial information (GCPs or geotransform)."""
        return self.has_gcps or self.has_geotransform


class Imagery_Loader:
    """API for handling imagery with GDAL-based metadata parsing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gdal_reader = GDALReader()

    def get_imagery_info(self, file_path: str | Path) -> Optional[Imagery_Info]:
        """Get comprehensive information about an imagery file.

        Args:
            file_path: Path to the imagery file

        Returns:
            Imagery_Info object or None if file cannot be read
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        try:
            # Load file with GDAL reader
            image_data, geotransform, metadata = self.gdal_reader.load_file(str(file_path))

            # Check for spatial info
            has_geotransform = geotransform is not None and geotransform != (0, 1, 0, 0, 0, 1)
            has_gcps = metadata.get('gcp_count', 0) > 0
            has_projection = 'projection' in metadata and metadata['projection']

            # Get EPSG code
            epsg_code = metadata.get('epsg')

            # Get center coordinates if geotransform exists
            center_lat = None
            center_lon = None

            if has_geotransform and metadata.get('width') and metadata.get('height'):
                width = metadata['width']
                height = metadata['height']
                gt = geotransform

                # Calculate center pixel coordinates
                center_x = gt[0] + (width / 2) * gt[1] + (height / 2) * gt[2]
                center_y = gt[3] + (width / 2) * gt[4] + (height / 2) * gt[5]

                # Convert to lat/lon if projection exists
                if has_projection and epsg_code:
                    try:
                        transformer = Transformer.from_crs(
                            f"EPSG:{epsg_code}",
                            "EPSG:4326",
                            always_xy=True
                        )
                        center_lon, center_lat = transformer.transform(center_x, center_y)
                    except Exception:
                        pass

            return Imagery_Info(
                file_path=str(file_path),
                width=metadata.get('width', 0),
                height=metadata.get('height', 0),
                band_count=metadata.get('band_count', 0),
                has_geotransform=has_geotransform,
                has_gcps=has_gcps,
                has_projection=has_projection,
                epsg_code=epsg_code,
                gcp_count=metadata.get('gcp_count', 0),
                geotransform=geotransform if has_geotransform else None,
                center_lat=center_lat,
                center_lon=center_lon,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Error reading imagery info: {e}")
            return None

    def needs_seed_location(self, file_path: str | Path) -> bool:
        """Check if an image needs a seed location (no GCPs or geotransform).

        Args:
            file_path: Path to the imagery file

        Returns:
            True if image lacks spatial info and needs seed location
        """
        info = self.get_imagery_info(file_path)
        if info is None:
            return True  # Can't read file, assume needs seed
        return not info.has_spatial_info()

    def load_gcp_file(self, gcp_file_path: str | Path) -> Optional[List[Dict]]:
        """Load GCP data from a JSON file.

        Args:
            gcp_file_path: Path to the GCP JSON file

        Returns:
            List of GCP dictionaries or None if file doesn't exist
        """
        gcp_file_path = Path(gcp_file_path)

        if not gcp_file_path.exists():
            return None

        try:
            with open(gcp_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different GCP file formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if 'gcps' in data:
                    return data['gcps']
                elif 'points' in data:
                    return data['points']
            return None

        except Exception as e:
            self.logger.error(f"Error loading GCP file: {e}")
            return None

    def get_image_dimensions(self, file_path: str | Path) -> Optional[Tuple[int, int]]:
        """Get image width and height.

        Args:
            file_path: Path to the imagery file

        Returns:
            Tuple of (width, height) or None
        """
        info = self.get_imagery_info(file_path)
        if info:
            return (info.width, info.height)
        return None

    def get_available_bands(self, file_path: str | Path) -> List[Dict]:
        """Get information about available bands.

        Args:
            file_path: Path to the imagery file

        Returns:
            List of band information dictionaries
        """
        info = self.get_imagery_info(file_path)
        if info and info.metadata:
            return info.metadata.get('bands', [])
        return []

    def supports_format(self, file_path: str | Path) -> bool:
        """Check if file format is supported by rasterio."""
        try:
            with rasterio.open(file_path) as src:
                return True
        except (ImportError, rasterio.RasterioIOError, Exception):
            return False
