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
#    File:    orthorectifier.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Orthorectifier - RPC-based orthorectification with progressive updates
"""

#  Python Standard Libraries
import os
from pathlib import Path
from typing import Dict, List

#  Third-Party Libraries

#  Project Libraries
from pointy.core.gcp import GCP

class Orthorectifier:
    """Handles RPC-based orthorectification using ground control points."""

    # Signals (would be Qt signals in actual implementation)
    def __init__(self):
        self.orthorectification_complete = None  # Would be Signal

    def orthorectify(self, image_path: str, gcps: List[GCP], rpc_data: Dict | None = None):
        """Perform orthorectification using GCPs and optional RPC data."""
        try:
            from osgeo import gdal, osr

            if not gcps:
                raise ValueError("No GCPs provided for orthorectification")

            if len(gcps) < 3:
                raise ValueError("At least 3 GCPs required for orthorectification")

            # Open the source image
            dataset = gdal.Open(image_path)
            if dataset is None:
                raise ValueError(f"Could not open image: {image_path}")

            # Create output file path
            output_path = self._get_output_path(image_path)

            # Get GCPs in GDAL format
            gdal_gcps = [gcp.to_gdal_format() for gcp in gcps]

            # Create output dataset
            driver = gdal.GetDriverByName('GTiff')

            # Determine output size (same as input for now)
            width = dataset.RasterXSize
            height = dataset.RasterYSize

            # Create output dataset
            output_ds = driver.Create(
                output_path, width, height, dataset.RasterCount,
                gdal.GDT_Float32  # Use float for better precision
            )

            # Set up georeferencing
            if rpc_data:
                # Use RPC data if available
                self._setup_rpc_georeferencing(output_ds, rpc_data, gdal_gcps)
            else:
                # Use GCPs only
                output_ds.SetGCPs(gdal_gcps, osr.SpatialReference().ExportToWkt())

            # Set projection (WGS84)
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)  # WGS84
            output_ds.SetProjection(srs.ExportToWkt())

            # Perform orthorectification
            self._perform_orthorectification(dataset, output_ds, gdal_gcps)

            # Clean up
            dataset = None
            output_ds = None

            # Emit completion signal
            if self.orthorectification_complete:
                self.orthorectification_complete.emit(output_path)

            return output_path

        except ImportError:
            raise ImportError("GDAL is required for orthorectification")
        except Exception as e:
            raise RuntimeError(f"Orthorectification failed: {str(e)}")

    def _get_output_path(self, image_path: str) -> str:
        """Generate output path for orthorectified image."""
        path = Path(image_path)
        output_name = f"{path.stem}_ortho{path.suffix}"
        return str(path.parent / output_name)

    def _setup_rpc_georeferencing(self, dataset, rpc_data: Dict, gcps):
        """Setup RPC-based georeferencing."""

        # Add RPC metadata
        rpc_metadata = {}
        for key, value in rpc_data.items():
            rpc_metadata[f'RPC_{key.upper()}'] = str(value)

        dataset.SetMetadata(rpc_metadata, 'RPC')

        # Also set GCPs for refinement
        dataset.SetGCPs(gcps, None)

    def _perform_orthorectification(self, input_ds, output_ds, gcps):
        """Perform the actual orthorectification."""
        from osgeo import gdal

        # Create transformer
        transformer = gdal.Transformer(input_ds, output_ds, [])

        # Process each band
        for band in range(1, input_ds.RasterCount + 1):
            input_band = input_ds.GetRasterBand(band)
            output_band = output_ds.GetRasterBand(band)

            # Read input data
            input_data = input_band.ReadAsArray()

            # Create output array
            output_data = self._transform_pixels(input_ds, output_ds, input_data, transformer)

            # Write output data
            output_band.WriteArray(output_data)

            # Copy band statistics if available
            if input_band.GetMinimum() is not None:
                output_band.SetStatistics(
                    input_band.GetMinimum(),
                    input_band.GetMaximum(),
                    input_band.GetMean(),
                    input_band.GetStdDev()
                )

    def _transform_pixels(self, input_ds, output_ds, input_data, transformer):
        """Transform pixel data using the transformer."""
        import numpy as np

        height, width = input_data.shape[:2]

        # Create coordinate grids
        x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))

        # Transform coordinates
        success, x_transformed, y_transformed = transformer.TransformPoints(
            0, x_coords.flatten(), y_coords.flatten()
        )

        # Reshape back to 2D
        x_transformed = x_transformed.reshape(height, width)
        y_transformed = y_transformed.reshape(height, width)

        # Create output array
        if len(input_data.shape) == 3:
            output_data = np.zeros_like(input_data)
            for band in range(input_data.shape[2]):
                output_data[:, :, band] = self._resample_band(
                    input_data[:, :, band], x_transformed, y_transformed
                )
        else:
            output_data = self._resample_band(input_data, x_transformed, y_transformed)

        return output_data

    def _resample_band(self, band_data, x_coords, y_coords):
        """Resample a single band using transformed coordinates."""
        import numpy as np
        from scipy import ndimage

        # For now, use nearest neighbor resampling
        # In a production implementation, you'd use bilinear or cubic

        height, width = band_data.shape

        # Create coordinate grids for interpolation
        x_grid, y_grid = np.meshgrid(np.arange(width), np.arange(height))

        # Map coordinates (inverse mapping)
        # Note: This is simplified - proper implementation would handle
        # coordinate systems and edge cases better
        try:
            # Use map_coordinates for resampling
            coords = np.array([y_coords, x_coords])

            # Clip coordinates to valid range
            coords[0] = np.clip(coords[0], 0, height - 1)
            coords[1] = np.clip(coords[1], 0, width - 1)

            # Perform interpolation
            resampled = ndimage.map_coordinates(
                band_data, coords, order=1, mode='nearest'
            )

            return resampled

        except ImportError:
            # Fallback to simple nearest neighbor
            resampled = np.zeros_like(band_data)

            for y in range(height):
                for x in range(width):
                    src_x = int(np.clip(x_coords[y, x], 0, width - 1))
                    src_y = int(np.clip(y_coords[y, x], 0, height - 1))
                    resampled[y, x] = band_data[src_y, src_x]

            return resampled

    def calculate_rms_error(self, gcps: List[GCP]) -> float:
        """Calculate RMS error for GCPs."""
        if len(gcps) < 3:
            return float('inf')

        # This is a simplified RMS calculation
        # In a real implementation, you'd calculate the transformation
        # and then compute residuals

        total_error = 0.0
        for gcp in gcps:
            # For now, use a placeholder error
            # In reality, this would be the residual after transformation
            error = 0.1  # Placeholder
            total_error += error ** 2

        return (total_error / len(gcps)) ** 0.5

    def update_progressive(self, image_path: str, gcps: List[GCP], output_path: str):
        """Perform progressive orthorectification (updates existing file)."""
        try:

            # Check if output file exists
            if os.path.exists(output_path):
                # Update existing orthorectified image
                return self._update_existing(image_path, gcps, output_path)
            else:
                # Create new orthorectified image
                return self.orthorectify(image_path, gcps)

        except Exception as e:
            raise RuntimeError(f"Progressive orthorectification failed: {str(e)}")

    def _update_existing(self, image_path: str, gcps: List[GCP], output_path: str):
        """Update existing orthorectified image with new GCPs."""
        # This would implement incremental updates
        # For now, just recreate the entire image

        # Remove existing output
        if os.path.exists(output_path):
            os.remove(output_path)

        # Recreate with new GCPs
        return self.orthorectify(image_path, gcps)
