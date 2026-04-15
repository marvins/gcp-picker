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
#    File:    imagery_api.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Imagery API - Rasterio-based imagery handling with metadata parsing.
"""

# Python Standard Libraries
import logging
from dataclasses import dataclass
from pathlib import Path

# Third-Party Libraries
import rasterio


@dataclass
class Imagery_Info:
    """Information about an imagery file."""
    file_path:        str
    width:            int
    height:           int
    band_count:       int
    has_geotransform: bool
    has_gcps:         bool

    def has_spatial_info(self) -> bool:
        """Check if image has any spatial information (GCPs or geotransform)."""
        return self.has_gcps or self.has_geotransform


class Imagery_Loader:
    """Lightweight imagery metadata loader backed by rasterio."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_imagery_info(self, file_path: str | Path) -> Imagery_Info | None:
        """Return spatial metadata for an imagery file, or None on failure."""
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        try:
            with rasterio.open(file_path) as src:
                identity = rasterio.transform.IDENTITY
                has_geotransform = (src.transform != identity
                                    and src.transform is not None)
                has_gcps = len(src.gcps[1]) > 0 if src.gcps else False
                return Imagery_Info(
                    file_path        = str(file_path),
                    width            = src.width,
                    height           = src.height,
                    band_count       = src.count,
                    has_geotransform = has_geotransform,
                    has_gcps         = has_gcps,
                )
        except Exception as exc:
            self.logger.error(f'imagery_api: failed to read {file_path}: {exc}')
            return None

    def needs_seed_location(self, file_path: str | Path) -> bool:
        """Return True if the image has no embedded spatial info."""
        info = self.get_imagery_info(file_path)
        if info is None:
            return True
        return not info.has_spatial_info()
