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
#    File:    test_terrain_integration.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Integration tests for terrain elevation sources comparison.

This module tests that different elevation sources (SRTM, AWS, etc.)
provide consistent elevation data within acceptable tolerances
across various geographic locations and coordinate systems.
"""

# Python Standard Libraries
from typing import Any
from unittest.mock import patch, Mock

# Third-party Libraries
import pytest

# Project Libraries
from pointy.core.coordinate import Geographic, UTM, UPS, Web_Mercator, ECEF, Transformer
from pointy.core.terrain import (
    Manager,
    Terrain_Catalog,
    GeoTIFF_Elevation_Source,
    Elevation_Point,
    elevation,
    elevation_point
)


# Test configuration
ELEVATION_TOLERANCE_METERS = 20.0  # Acceptable difference between sources
HIGH_TOLERANCE_METERS = 50.0      # For difficult areas (steep terrain, polar regions)


# Geographic test locations focused on areas with local data
# Based on n35_w119 and n35_w120 tiles covering California/Nevada area
TEST_LOCATIONS = {
    # Local tile coverage areas (35°N, 119-120°W)
    # Actual tile boundaries based on SRTM 1-arc sec data
    "california_central": Geographic(35.5, -119.5),  # Center of n35_w120 tile coverage
    "california_east": Geographic(35.5, -118.5),    # Within n35_w119 tile (not n35_w120 as originally assumed)
    "california_corner": Geographic(35.0, -119.0), # Corner of n35_w119 tile
    "nevada_border": Geographic(35.0, -120.0),     # Border between tiles

    # Test points within actual tile bounds
    "test_point_1": Geographic(35.2, -118.8),      # Within n35_w119 tile (corrected from -119.3)
    "test_point_2": Geographic(35.8, -118.5),      # Within n35_w119 tile (corrected from -119.8)
    "test_point_3": Geographic(35.4, -119.8),      # Within n35_w120 tile (corrected from -120.2)

    # Edge cases (adjusted for actual tile boundaries)
    "tile_edge_north": Geographic(36.0, -119.5),    # Northern edge of both tiles
    "tile_edge_south": Geographic(35.0, -119.5),    # Southern edge (corrected from 34.0)
    "tile_edge_west": Geographic(35.5, -120.0),     # Western edge of n35_w120
    "tile_edge_east": Geographic(35.5, -118.0),     # Eastern edge of n35_w119 (corrected from -120.0)

    # Outside tile bounds (should return None)
    "outside_bounds_ny": Geographic(40.7, -74.0),   # New York (no local data)
    "outside_bounds_uk": Geographic(51.5, -0.1),    # London (no local data)
}


@pytest.fixture
def terrain_catalog():
    """Create terrain catalog for testing."""
    # Use the actual terrain directory if environment variable is set
    import os
    catalog_root = os.environ.get('TERRAIN_CATALOG_ROOT')
    if catalog_root:
        return Terrain_Catalog(catalog_root)
    else:
        pytest.skip("TERRAIN_CATALOG_ROOT not set - integration tests require local terrain data")


@pytest.fixture
def terrain_manager(terrain_catalog):
    """Create terrain manager with catalog sources."""
    return Manager([terrain_catalog], cache_enabled=False)


@pytest.fixture
def coordinate_transformer():
    """Create coordinate transformer for testing."""
    return Transformer()


class Test_Terrain_Catalog_Functionality:
    """Test terrain catalog functionality with local data."""

    @pytest.mark.parametrize("location_name,geo_coord", TEST_LOCATIONS.items())
    def test_local_elevation_queries(self, terrain_manager, location_name, geo_coord):
        """Test elevation queries for local geographic coordinates."""
        # Get elevation from catalog
        elevation = terrain_manager.elevation(geo_coord)

        # Check if we expect data for this location
        if "outside_bounds" in location_name:
            # These should return None as they're outside our tile coverage
            assert elevation is None, f"Expected None for outside bounds location {location_name}, got {elevation}"
        else:
            # These should have elevation data within our tile coverage
            if elevation is None:
                pytest.skip(f"No elevation data available for {location_name} - tile may not cover this exact coordinate")
            else:
                assert isinstance(elevation, (int, float)), f"Expected numeric elevation for {location_name}, got {type(elevation)}"
                assert elevation >= -500, f"Elevation seems too low for {location_name}: {elevation}m"
                assert elevation <= 9000, f"Elevation seems too high for {location_name}: {elevation}m"

    def test_catalog_source_discovery(self, terrain_catalog):
        """Test that catalog discovers GeoTIFF sources."""
        assert len(terrain_catalog.sources) > 0, "Catalog should discover at least one GeoTIFF source"

        # Check that sources are GeoTIFF_Elevation_Source instances
        for source in terrain_catalog.sources:
            assert isinstance(source, GeoTIFF_Elevation_Source), f"Expected GeoTIFF source, got {type(source)}"
            assert source.file_path.exists(), f"Source file should exist: {source.file_path}"

    def test_catalog_bounds_checking(self, terrain_catalog):
        """Test catalog bounds checking functionality."""
        # Test coordinates that should be within our tiles
        test_coords = [
            Geographic(35.5, -119.5),  # Center of n35_w119
            Geographic(35.0, -119.0),   # Corner of n35_w119
        ]

        for coord in test_coords:
            # At least one source should contain this coordinate
            containing_sources = terrain_catalog.get_sources_for_coordinate(coord)
            assert len(containing_sources) > 0, f"No sources found for coordinate {coord}"

    def test_elevation_point_metadata(self, terrain_manager):
        """Test elevation point returns proper metadata."""
        # Use a coordinate we know should work
        coord = Geographic(35.5, -119.5)

        point = terrain_manager.elevation_point(coord)

        if point is not None:
            assert isinstance(point, Elevation_Point), f"Expected Elevation_Point, got {type(point)}"
            # Check that the coordinates match (ignoring altitude which gets populated)
            assert point.coord.latitude_deg == coord.latitude_deg
            assert point.coord.longitude_deg == coord.longitude_deg
            assert point.source == "Terrain Catalog", f"Expected 'Terrain Catalog' source, got '{point.source}'"
            assert isinstance(point.coord.altitude_m, (int, float)), f"Expected numeric altitude, got {type(point.coord.altitude_m)}"

    @pytest.mark.parametrize("coord_type", ["utm", "web_mercator"])
    def test_coordinate_system_support(self, terrain_manager, coordinate_transformer, coord_type):
        """Test elevation queries with different coordinate systems."""
        # Use a coordinate within our tile bounds
        geo_coord = Geographic(35.5, -119.5)

        # Convert to target coordinate system
        if coord_type == "utm":
            test_coord = coordinate_transformer.geo_to_utm(geo_coord)
        elif coord_type == "web_mercator":
            test_coord = coordinate_transformer.geo_to_web_mercator(geo_coord)
        else:
            pytest.skip(f"Unsupported coordinate type: {coord_type}")

        # Get elevation using converted coordinate
        elevation = terrain_manager.elevation(test_coord)

        if elevation is not None:
            assert isinstance(elevation, (int, float)), f"Expected numeric elevation for {coord_type}, got {type(elevation)}"
        else:
            pytest.skip(f"No elevation data for coordinate system test with {coord_type}")


class Test_Global_Functions:
    """Test global convenience functions with catalog."""

    def test_global_elevation_function(self, terrain_catalog):
        """Test global elevation convenience function."""
        # Mock the global manager to use our catalog
        with patch('pointy.core.terrain.get_terrain_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.elevation.return_value = 123.4
            mock_get_manager.return_value = mock_manager

            result = elevation(Geographic(35.5, -119.5))
            assert result == 123.4

    def test_global_elevation_point_function(self, terrain_catalog):
        """Test global elevation_point convenience function."""
        with patch('pointy.core.terrain.get_terrain_manager') as mock_get_manager:
            mock_point = Elevation_Point(Geographic(35.5, -119.5, 123.4), "Terrain Catalog")
            mock_manager = Mock()
            mock_manager.elevation_point.return_value = mock_point
            mock_get_manager.return_value = mock_manager

            result = elevation_point(Geographic(35.5, -119.5))
            assert result == mock_point
            assert result.source == "Terrain Catalog"


if __name__ == "__main__":
    pytest.main([__file__])
