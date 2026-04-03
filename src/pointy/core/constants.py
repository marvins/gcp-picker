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
#    File:    constants.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Constants - Centralized configuration values

All hardcoded values from across the application are defined here
for easy maintenance and configuration.
"""

#  Python Standard Libraries
import tempfile
from pathlib import Path

# =============================================================================
# VERSION
# =============================================================================

VERSION = "1.0.0"
APP_NAME = "Pointy-McPointface"
APP_USER_AGENT = "Pointy-McPointface/1.0"

# =============================================================================
# FILE EXTENSIONS
# =============================================================================

# Image formats supported by the application
SUPPORTED_IMAGE_EXTENSIONS = (
    '.tif', '.tiff',   # GeoTIFF
    '.jpg', '.jpeg',   # JPEG
    '.png',            # PNG
    '.img',            # ERDAS Imagine
    '.vrt',            # GDAL Virtual Raster
)

# Reference data formats
SUPPORTED_REFERENCE_EXTENSIONS = (
    '.vrt', '.tif', '.tiff', '.img',  # GDAL rasters
)

# GCP file formats
SUPPORTED_GCP_EXTENSIONS = (
    '.gcp', '.txt', '.json', '.csv'
)

# =============================================================================
# NETWORK TIMEOUTS (seconds)
# =============================================================================

TIMEOUT_WMS = 60
TIMEOUT_WMS_CAPABILITIES = 30
TIMEOUT_ELEVATION = 30
TIMEOUT_TILE_DOWNLOAD = 30
TIMEOUT_FEATURE_INFO = 30

# =============================================================================
# CACHE DIRECTORIES
# =============================================================================

CACHE_BASE_DIR = Path(tempfile.gettempdir()) / "pointy_mcpointface"
CACHE_ELEVATION_DIR = CACHE_BASE_DIR / "elevation_cache"
CACHE_TILE_DIR = CACHE_BASE_DIR / "aws_cache"
CACHE_SRTM_DIR = CACHE_BASE_DIR / "srtm_cache"

# =============================================================================
# ZOOM AND DISPLAY
# =============================================================================

# Default zoom levels
DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.1
MAX_ZOOM = 10.0
ZOOM_STEP_WHEEL = 0.1
ZOOM_STEP_BUTTON = 0.25

# AWS Terrain Tile zoom level (higher = more detail, more tiles)
AWS_TERRAIN_ZOOM = 12

# GCP point visualization
GCP_POINT_RADIUS = 6
GCP_POINT_HIGHLIGHT_RADIUS = 10
GCP_POINT_COLOR = (255, 0, 0)  # Red
GCP_POINT_HIGHLIGHT_COLOR = (255, 255, 0)  # Yellow

# =============================================================================
# IMAGE PROCESSING
# =============================================================================

# Histogram settings
HISTOGRAM_BINS = 256

# Default pixel ranges
DEFAULT_MIN_PIXEL = 0
DEFAULT_MAX_PIXEL_8BIT = 255
DEFAULT_MAX_PIXEL_16BIT = 65535

# Brightness/Contrast defaults
DEFAULT_BRIGHTNESS = 0  # -100 to 100
DEFAULT_CONTRAST = 100  # 0 to 200

# =============================================================================
# GCP PROCESSING
# =============================================================================

# Minimum GCPs required for orthorectification
MIN_GCP_FOR_ORTHO = 3

# Elevation precision (decimal places for lat/lon rounding)
ELEVATION_CACHE_PRECISION = 4  # ~10m precision

# =============================================================================
# LEAFLET MAP
# =============================================================================

# Default map center (Denver, CO as example)
DEFAULT_MAP_LAT = 39.7392
DEFAULT_MAP_LON = -104.9903
DEFAULT_MAP_ZOOM = 12

# Max zoom for imagery layers
MAX_MAP_ZOOM = 20

# =============================================================================
# COLLECTION NAVIGATION
# =============================================================================

# Navigation button states
NAV_FIRST = "first"
NAV_PREV = "prev"
NAV_NEXT = "next"
NAV_LAST = "last"

# Status text
STATUS_NO_COLLECTION = "No Collection Loaded"
STATUS_COLLECTION_LOADED = "Collection: {name}"
