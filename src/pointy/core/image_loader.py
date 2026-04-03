"""
Image Loading Strategy Pattern

Provides a unified interface for loading images from various sources
with automatic format detection and fallback handling.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from pointy.core.constants import SUPPORTED_IMAGE_EXTENSIONS


@dataclass
class LoadedImage:
    """Standardized result from image loading strategies."""

    data: np.ndarray  # Image data as numpy array (H, W, C) or (H, W)
    path: Path
    width: int
    height: int
    channels: int
    dtype: str
    metadata: dict[str, Any]
    source: str  # Which strategy loaded this (gdal, opencv, pil)

    # Optional geospatial info
    geotransform: tuple | None = None
    projection: str | None = None
    epsg: int | None = None
    gcps: list[dict] | None = None
    rpc_data: dict | None = None


class LoadStrategy(ABC):
    """Abstract base class for image loading strategies."""

    # Priority: lower = tried first
    priority: int = 100

    @abstractmethod
    def can_load(self, file_path: str | Path) -> bool:
        """Check if this strategy can load the given file."""
        pass

    @abstractmethod
    def load(self, file_path: str | Path) -> LoadedImage:
        """Load the image and return standardized LoadedImage."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging/debugging."""
        pass


class GDALStrategy(LoadStrategy):
    """Strategy for loading GeoTIFF and other GDAL-supported formats."""

    priority = 1  # Highest priority for geospatial images

    def __init__(self):
        self._gdal_available = None
        self.gdal = None

    def _check_gdal(self) -> bool:
        """Check if rasterio is available."""
        if self._gdal_available is None:
            try:
                self.gdal = rasterio
                self._gdal_available = True
            except ImportError:
                self._gdal_available = False
        return self._gdal_available

    @property
    def name(self) -> str:
        return "gdal"

    def can_load(self, file_path: str | Path) -> bool:
        """Check if rasterio can open this file."""
        if not self._check_gdal():
            return False

        path = Path(file_path)
        ext = path.suffix.lower()

        # Rasterio supports these extensions
        if ext not in ('.tif', '.tiff', '.vrt', '.img', '.png', '.jpg', '.jpeg'):
            return False

        try:
            with rasterio.open(path):
                return True
        except Exception:
            return False

    def load(self, file_path: str | Path) -> LoadedImage:
        """Load image using rasterio."""
        if not self._check_gdal():
            raise ImportError("rasterio is not available")

        path = Path(file_path)

        try:
            with rasterio.open(path) as src:
                # Read all bands
                image_data = src.read()

                # Convert from (bands, height, width) to (height, width, bands)
                if image_data.ndim == 3:
                    image_data = np.transpose(image_data, (1, 2, 0))

                # Get dimensions
                height, width = image_data.shape[:2]
                bands = src.count
                channels = bands

                # If single band, convert to 3-channel for display
                if bands == 1:
                    if image_data.ndim == 2:
                        image_data = np.stack([image_data] * 3, axis=-1)
                    else:
                        band = image_data[:, :, 0]
                        image_data = np.stack([band] * 3, axis=-1)
                    channels = 3

                # Get metadata
                metadata = {
                    'driver': src.driver,
                    'bands': bands,
                }

                # Get geotransform from transform
                transform = src.transform
                geotransform = [
                    transform.c,     # origin x
                    transform.a,     # pixel width
                    transform.b,     # rotation (0 for north-up)
                    transform.f,     # origin y
                    transform.d,     # rotation (0 for north-up)
                    transform.e,     # pixel height (negative)
                ]
                has_geotransform = transform.is_rectilinear

                # Get projection
                projection = src.crs.to_wkt() if src.crs else None

                # Get EPSG code
                epsg = src.crs.to_epsg() if src.crs else None

                # Get GCPs
                gcp_list = None
                if src.gcps:
                    gcp_list = [
                        {
                            'id': gcp.id,
                            'pixel': (gcp.col, gcp.row),
                            'geo': (gcp.x, gcp.y, gcp.z)
                        }
                        for gcp in src.gcps[0]  # gcps returns (gcps, crs)
                    ]

                # Get RPC data from tags
                rpc_data = src.tags().get('RPC_METADATA', None)
                if rpc_data and isinstance(rpc_data, str):
                    try:
                        rpc_data = json.loads(rpc_data)
                    except json.JSONDecodeError:
                        rpc_data = {'raw': rpc_data}

                return LoadedImage(
                    data=image_data,
                    path=path,
                    width=width,
                    height=height,
                    channels=channels,
                    dtype=str(image_data.dtype),
                    metadata=metadata,
                    source=self.name,
                    geotransform=geotransform if has_geotransform else None,
                    projection=projection,
                    epsg=epsg,
                    gcps=gcp_list,
                    rpc_data=rpc_data
                )

        except Exception as e:
            raise ValueError(f"Could not load image: {e}")


class OpenCVStrategy(LoadStrategy):
    """Strategy for loading standard image formats using OpenCV."""

    priority = 10  # Medium priority

    @property
    def name(self) -> str:
        return "opencv"

    def can_load(self, file_path: str | Path) -> bool:
        """Check if file extension is supported by OpenCV."""
        path = Path(file_path)
        ext = path.suffix.lower()
        return ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')

    def load(self, file_path: str | Path) -> LoadedImage:
        """Load image using OpenCV."""
        import cv2

        path = Path(file_path)
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

        if image is None:
            raise ValueError(f"OpenCV could not load: {path}")

        # OpenCV loads as BGR by default, convert to RGB/RGBA
        if len(image.shape) == 3:
            if image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                channels = 3
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
                channels = 4
            else:
                channels = image.shape[2]
        else:
            channels = 1

        height, width = image.shape[:2]

        return LoadedImage(
            data=image,
            path=path,
            width=width,
            height=height,
            channels=channels,
            dtype=str(image.dtype),
            metadata={'source': 'opencv'},
            source=self.name
        )


class PILStrategy(LoadStrategy):
    """Strategy for loading images using PIL/Pillow (fallback)."""

    priority = 100  # Lowest priority, universal fallback

    @property
    def name(self) -> str:
        return "pil"

    def can_load(self, file_path: str | Path) -> bool:
        """PIL can load almost any image format."""
        return True  # Universal fallback

    def load(self, file_path: str | Path) -> LoadedImage:
        """Load image using PIL."""
        from PIL import Image

        path = Path(file_path)
        pil_image = Image.open(path)

        # Convert to numpy array
        image = np.array(pil_image)

        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1

        return LoadedImage(
            data=image,
            path=path,
            width=width,
            height=height,
            channels=channels,
            dtype=str(image.dtype),
            metadata={
                'source': 'pil',
                'mode': pil_image.mode,
                'format': pil_image.format
            },
            source=self.name
        )


class ImageLoader:
    """Coordinator class that manages loading strategies."""

    def __init__(self):
        # Initialize strategies in priority order
        self._strategies: list[LoadStrategy] = [
            GDALStrategy(),
            OpenCVStrategy(),
            PILStrategy(),
        ]
        # Sort by priority
        self._strategies.sort(key=lambda s: s.priority)

    def load(self, file_path: str | Path) -> LoadedImage:
        """
        Load an image using the best available strategy.

        Tries strategies in priority order until one succeeds.

        Args:
            file_path: Path to the image file

        Returns:
            LoadedImage with standardized data

        Raises:
            ValueError: If no strategy can load the file
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        errors = []

        for strategy in self._strategies:
            try:
                if strategy.can_load(path):
                    return strategy.load(path)
            except Exception as e:
                errors.append(f"{strategy.name}: {e}")
                continue

        # No strategy succeeded
        error_msg = f"Could not load {path}\n"
        if errors:
            error_msg += "Errors:\n" + "\n".join(f"  {e}" for e in errors)
        raise ValueError(error_msg)

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file extensions."""
        return list(SUPPORTED_IMAGE_EXTENSIONS)

    def add_strategy(self, strategy: LoadStrategy):
        """Add a custom loading strategy."""
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority)


# Global singleton instance
_image_loader: ImageLoader | None = None


def get_image_loader() -> ImageLoader:
    """Get the global ImageLoader instance."""
    global _image_loader
    if _image_loader is None:
        _image_loader = ImageLoader()
    return _image_loader


def load_image(file_path: str | Path) -> LoadedImage:
    """Convenience function to load an image."""
    return get_image_loader().load(file_path)
