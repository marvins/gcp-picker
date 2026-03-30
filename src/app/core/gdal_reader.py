"""
GDAL Reader - Read various raster formats using rasterio
"""

from pathlib import Path
from typing import Tuple, Dict, Any
import numpy as np

import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

class GDALReader:
    """Reader for GDAL-supported raster formats using rasterio."""

    def __init__(self):
        pass

    def load_file(self, file_path: str) -> Tuple[np.ndarray | None, list | None, Dict | None]:
        """Load a raster file using rasterio."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with rasterio.open(file_path) as src:
                # Read all bands
                image_data = src.read()

                # Convert from (bands, height, width) to (height, width, bands)
                if image_data.ndim == 3:
                    image_data = np.transpose(image_data, (1, 2, 0))

                # If single band, convert to 3-channel for display
                if image_data.ndim == 2 or image_data.shape[-1] == 1:
                    if image_data.ndim == 2:
                        image_data = np.stack([image_data] * 3, axis=-1)
                    else:
                        band = image_data[:, :, 0]
                        image_data = np.stack([band] * 3, axis=-1)

                # Get geotransform
                transform = src.transform
                geotransform = [
                    transform.c,     # origin x
                    transform.a,     # pixel width
                    transform.b,     # rotation (0 for north-up)
                    transform.f,     # origin y
                    transform.d,     # rotation (0 for north-up)
                    transform.e,     # pixel height (negative)
                ]

                # Get metadata
                metadata = self._extract_metadata(src)

            return image_data, geotransform, metadata

        except ImportError:
            raise ImportError("rasterio is required for reading raster files")
        except Exception as e:
            raise RuntimeError(f"Failed to load raster file: {str(e)}")

    def _extract_metadata(self, src: rasterio.DatasetReader) -> Dict[str, Any]:
        """Extract metadata from rasterio dataset."""
        metadata = {
            'driver': src.driver,
            'width': src.width,
            'height': src.height,
            'band_count': src.count,
        }

        # CRS/Projection
        if src.crs:
            metadata['projection'] = src.crs.to_wkt()
            epsg_code = src.crs.to_epsg()
            if epsg_code:
                metadata['epsg'] = epsg_code

        # Geotransform
        transform = src.transform
        metadata['geotransform'] = [
            transform.c, transform.a, transform.b,
            transform.f, transform.d, transform.e
        ]

        # Tags/metadata
        metadata['tags'] = src.tags()

        # Band-specific metadata
        band_metadata = []
        for i in range(1, src.count + 1):
            band = src.read(i)
            band_tags = src.tags(i)

            band_info = {
                'band': i,
                'data_type': str(src.dtypes[i-1]),
                'color_interpretation': str(src.colorinterp[i-1]) if i-1 < len(src.colorinterp) else 'unknown',
                'min': float(band.min()),
                'max': float(band.max()),
                'mean': float(band.mean()),
                'stddev': float(band.std()),
            }

            # No data value
            nodata = src.nodata
            if nodata is not None:
                band_info['nodata'] = nodata

            band_metadata.append(band_info)

        metadata['bands'] = band_metadata

        return metadata

    def create_vrt(self, input_files: list, output_vrt: str) -> str:
        """Create a virtual raster from multiple files."""
        try:
            # Use rasterio's build_vrt
            from rasterio.vrt import build_vrt

            build_vrt(output_vrt, input_files)

            return output_vrt

        except ImportError:
            raise ImportError("rasterio is required for creating virtual rasters")
        except Exception as e:
            raise RuntimeError(f"Failed to create VRT: {str(e)}")

    def get_overview_info(self, file_path: str) -> Dict[str, Any]:
        """Get overview (pyramid) information for a raster."""
        try:
            with rasterio.open(file_path) as src:
                overview_info = {}

                # Check for overviews
                if src.overviews(1):
                    overviews = src.overviews(1)
                    overview_info['overview_count'] = len(overviews)
                    overview_sizes = []

                    for ovr_idx in overviews:
                        # Calculate overview size
                        factor = 2 ** ovr_idx
                        width = src.width // factor
                        height = src.height // factor
                        overview_sizes.append((width, height))

                    overview_info['overview_sizes'] = overview_sizes
                else:
                    overview_info['overview_count'] = 0

                return overview_info

        except Exception as e:
            raise RuntimeError(f"Failed to get overview info: {str(e)}")

    def get_band_statistics(self, file_path: str, band: int = 1) -> Dict[str, float]:
        """Get statistics for a specific band."""
        try:
            with rasterio.open(file_path) as src:
                if band < 1 or band > src.count:
                    raise ValueError(f"Invalid band number: {band}")

                band_data = src.read(band)

                statistics = {
                    'min': float(band_data.min()),
                    'max': float(band_data.max()),
                    'mean': float(band_data.mean()),
                    'stddev': float(band_data.std()),
                }

                return statistics

        except Exception as e:
            raise RuntimeError(f"Failed to get band statistics: {str(e)}")
