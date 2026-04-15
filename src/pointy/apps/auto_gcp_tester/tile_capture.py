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
#    File:    tile_capture.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Tile capture utilities for web-based imagery services.
"""

# Python Standard Libraries
import logging
from typing import Any

# Third-Party Libraries
import numpy as np
import requests
from PIL import Image
from io import BytesIO

# Project Libraries
from pointy.core.config_manager import Config_Manager


def estimate_gsd(image_shape: tuple[int, int], bounds: dict[str, float]) -> dict[str, float]:
    """Estimate Ground Sample Distance (GSD) from image bounds.

    Args:
        image_shape: (height, width) of image in pixels.
        bounds: Geographic bounds {sw_lat, sw_lon, ne_lat, ne_lon}.

    Returns:
        dict[str, float]: GSD in meters per pixel for latitude and longitude.
    """
    # Calculate ground distance in degrees
    lat_span = bounds['ne_lat'] - bounds['sw_lat']
    lon_span = bounds['ne_lon'] - bounds['sw_lon']

    # Convert degrees to meters (approximate at center latitude)
    center_lat = (bounds['sw_lat'] + bounds['ne_lat']) / 2
    lat_meters_per_degree = 111320.0  # Approximate meters per degree of latitude
    lon_meters_per_degree = 111320.0 * np.cos(np.radians(center_lat))  # Meters per degree of longitude at center

    # Calculate ground distance in meters
    lat_meters = lat_span * lat_meters_per_degree
    lon_meters = lon_span * lon_meters_per_degree

    # Calculate GSD in meters per pixel
    gsd_lat = lat_meters / image_shape[0] if image_shape[0] > 0 else 0
    gsd_lon = lon_meters / image_shape[1] if image_shape[1] > 0 else 0

    return {
        'gsd_lat': gsd_lat,
        'gsd_lon': gsd_lon,
        'gsd_avg': (gsd_lat + gsd_lon) / 2,
    }


def calculate_tile_grid_radius(center_tx: int, center_ty: int, zoom: int, target_bounds: dict[str, float]) -> int:
    """Calculate tile grid radius needed to cover target geographic bounds.

    Args:
        center_tx: Center tile X coordinate.
        center_ty: Center tile Y coordinate.
        zoom: Zoom level.
        target_bounds: Geographic bounds to cover {sw_lat, sw_lon, ne_lat, ne_lon}.

    Returns:
        int: Grid radius (number of tiles from center to edge in each direction).
    """
    n = 2 ** zoom

    def latlon_to_tile(lat: float, lon: float) -> tuple[int, int]:
        """Convert lat/lon to tile coordinates."""
        tx = int((lon + 180) / 360 * n)
        ty = int((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n)
        return tx, ty

    # Convert target bounds to tile coordinates
    sw_tx, sw_ty = latlon_to_tile(target_bounds['sw_lat'], target_bounds['sw_lon'])
    ne_tx, ne_ty = latlon_to_tile(target_bounds['ne_lat'], target_bounds['ne_lon'])

    # Calculate the tile range needed
    min_tx_needed = min(sw_tx, ne_tx)
    max_tx_needed = max(sw_tx, ne_tx)
    min_ty_needed = min(sw_ty, ne_ty)
    max_ty_needed = max(sw_ty, ne_ty)

    # Calculate required radius in each direction
    x_radius = max(abs(center_tx - min_tx_needed), abs(center_tx - max_tx_needed))
    y_radius = max(abs(center_ty - min_ty_needed), abs(center_ty - max_ty_needed))

    # Return the larger radius, with a minimum of 1
    return max(x_radius, y_radius, 1)


def capture_tiles(service_name: str, center_lat: float, center_lon: float, zoom: int,
                  tile_size: int = 256, target_bounds: dict[str, float] | None = None) -> tuple[np.ndarray, dict[str, float]]:
    """Capture tiles from web imagery service.

    Args:
        service_name: Name of the imagery service from config.
        center_lat: Center latitude in decimal degrees.
        center_lon: Center longitude in decimal degrees.
        zoom: Zoom level for tile capture.
        tile_size: Size of each tile in pixels (default 256).
        target_bounds: Optional geographic bounds to cover {sw_lat, sw_lon, ne_lat, ne_lon}.
                      If provided, will expand tile grid to ensure coverage.

    Returns:
        tuple[np.ndarray, dict[str, float]]: (captured image array, bounds dict)
    """
    config_mgr = Config_Manager()
    service = config_mgr.get_imagery_service(service_name)

    if service is None:
        raise ValueError(f"Imagery service not found: {service_name}")

    logger = logging.getLogger(__name__)
    logger.info(f"Capturing tiles from {service_name} at zoom {zoom}")

    # Cap zoom level to prevent excessive tile fetching
    max_zoom = 16
    if zoom > max_zoom:
        logger.warning(f"Zoom {zoom} exceeds max {max_zoom}, capping to prevent excessive tile requests")
        zoom = max_zoom

    # Convert lat/lon to tile coordinates (after zoom cap)
    n = 2 ** zoom
    # x is longitude (east-west), y is latitude (north-south)
    # Standard Web Mercator tile formulas
    x = int((center_lon + 180) / 360 * n)
    lat_rad = np.radians(center_lat)
    y = int((1 - np.log(np.tan(lat_rad) + 1 / np.cos(lat_rad)) / np.pi) / 2 * n)
    logger.info(f"Center ({center_lat}, {center_lon}) -> Tile ({x}, {y}) at zoom {zoom}")

    # Determine tile grid size
    if target_bounds is not None:
        # Calculate required tile grid to cover target bounds
        grid_radius = calculate_tile_grid_radius(x, y, zoom, target_bounds)
        # Cap grid radius to prevent excessive requests (max 7x7 grid = 49 tiles)
        max_grid_radius = 3
        if grid_radius > max_grid_radius:
            logger.warning(f"Grid radius {grid_radius} exceeds max {max_grid_radius}, capping to prevent excessive tile requests")
            grid_radius = max_grid_radius
        logger.info(f"Target bounds: {target_bounds}")
        logger.info(f"Using tile grid radius {grid_radius} ({2*grid_radius+1}x{2*grid_radius+1} tiles)")
    else:
        # Default 3x3 grid
        grid_radius = 1

    # Capture tiles in expanding grid around center
    tiles = []
    for dx in range(-grid_radius, grid_radius + 1):
        for dy in range(-grid_radius, grid_radius + 1):
            tx = x + dx
            ty = y + dy

            # URL template replacement
            url = service.url
            url = url.replace('{z}', str(zoom))
            url = url.replace('{x}', str(tx))  # x is longitude (east-west)
            url = url.replace('{y}', str(ty))  # y is latitude (north-south)
            url = url.replace('{s}', 'a')  # Subdomain

            logger.debug(f"Fetching tile: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))
            tiles.append((dx, dy, np.array(img)))

    # Stitch tiles together
    # Sort by dy (row) then dx (col)
    tiles.sort(key=lambda t: (t[1], t[0]))

    # Create stitched image with dynamic grid size
    grid_size = 2 * grid_radius + 1
    stitched = np.zeros((grid_size * tile_size, grid_size * tile_size, 3), dtype=np.uint8)

    for i, (dx, dy, tile) in enumerate(tiles):
        row = (dy + grid_radius)  # Offset by grid_radius
        col = (dx + grid_radius)
        stitched[row * tile_size:(row + 1) * tile_size, col * tile_size:(col + 1) * tile_size] = tile

    # Calculate bounds for the stitched image
    # Convert tile coordinates back to lat/lon for corners
    def tile_to_latlon(tx, ty, zoom):
        n = 2 ** zoom
        lon = tx / n * 360 - 180
        lat = np.arctan(np.sinh(np.pi * (1 - 2 * ty / n)))
        lat = np.degrees(lat)
        return lat, lon

    # Get bounds of the dynamic grid
    min_tx, min_ty = x - grid_radius, y - grid_radius
    max_tx, max_ty = x + grid_radius, y + grid_radius

    # Correct bounds: sw = min_x (west) + max_y (south), ne = max_x (east) + min_y (north)
    sw_lat, sw_lon = tile_to_latlon(min_tx, max_ty, zoom)
    ne_lat, ne_lon = tile_to_latlon(max_tx, min_ty, zoom)

    bounds = {
        'sw_lat': sw_lat,
        'sw_lon': sw_lon,
        'ne_lat': ne_lat,
        'ne_lon': ne_lon,
    }

    logger.info(f"Captured image shape: {stitched.shape}, bounds: {bounds}")

    return stitched, bounds


def calculate_zoom_for_resolution(test_image_shape: tuple[int, int], center_lat: float, bounds: dict[str, float]) -> int:
    """Calculate appropriate zoom level to match test image resolution.

    Args:
        test_image_shape: (height, width) of test image in pixels.
        center_lat: Center latitude for tile calculations.
        bounds: Geographic bounds of the test image area {sw_lat, sw_lon, ne_lat, ne_lon}.

    Returns:
        int: Recommended zoom level for tile capture.
    """
    # Estimate GSD from test image
    gsd_info = estimate_gsd(test_image_shape, bounds)
    target_gsd = gsd_info['gsd_avg']

    logger = logging.getLogger(__name__)
    logger.info(f"Estimated test image GSD: {target_gsd:.3f} meters/pixel")

    # Calculate GSD for each zoom level
    # At zoom level z, each tile is 256x256 pixels
    # The ground distance covered by a tile depends on zoom level
    tile_pixels = 256

    for zoom in range(1, 20):
        # Calculate ground distance per tile at this zoom level
        # At zoom level z, the world is divided into 2^z tiles in each dimension
        n = 2 ** zoom

        # Ground distance per tile in degrees
        lat_per_tile = 180.0 / n
        lon_per_tile = 360.0 / n / np.cos(np.radians(center_lat))

        # Convert to meters
        lat_meters_per_degree = 111320.0
        lon_meters_per_degree = 111320.0 * np.cos(np.radians(center_lat))

        lat_meters_per_tile = lat_per_tile * lat_meters_per_degree
        lon_meters_per_tile = lon_per_tile * lon_meters_per_degree

        # GSD at this zoom level (meters per pixel)
        gsd_lat = lat_meters_per_tile / tile_pixels
        gsd_lon = lon_meters_per_tile / tile_pixels
        gsd_avg = (gsd_lat + gsd_lon) / 2

        # If tile GSD is close to or better than target GSD
        # We want tile GSD <= target GSD (higher resolution)
        if gsd_avg <= target_gsd:
            logger.info(f"Zoom {zoom}: Tile GSD = {gsd_avg:.3f} m/pixel (target: {target_gsd:.3f} m/pixel)")
            return zoom

    # Default to zoom 12 if no good match found
    logger.warning("No zoom level matched target GSD, using default zoom 12")
    return 12
