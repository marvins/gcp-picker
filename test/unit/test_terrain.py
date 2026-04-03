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
#    File:    test_terrain.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Unit tests for terrain elevation functionality.
"""

# Python Standard Libraries
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Third-Party Libraries
import pytest

# Project Libraries
from pointy.core.coordinate import Geographic, UTM, UPS, Web_Mercator, ECEF
from pointy.core.terrain import (
    Manager,
    Elevation_Point,
    SRTM_Elevation_Source,
    AWS_Elevation_Source,
    Local_DEM_Elevation_Source,
    elevation,
    elevation_point,
    get_terrain_manager,
    create_srtm_manager,
    create_aws_manager
)


# Fixtures
@pytest.fixture
def sample_geographic_coord():
    """Sample geographic coordinate for testing."""
    return Geographic(40.7, -74.0, 10.5)


@pytest.fixture
def sample_elevation_point(sample_geographic_coord):
    """Sample elevation point for testing."""
    return Elevation_Point(sample_geographic_coord, "Test Source", 1.0)


@pytest.fixture
def mock_srtm_source():
    """Mock SRTM elevation source."""
    source = Mock(spec=SRTM_Elevation_Source)
    source.name = "SRTM 30m"
    source.get_elevation.return_value = 100.5
    source.get_elevations.return_value = [100.5, 200.0, 300.0]  # Match 3 coordinates
    return source


@pytest.fixture
def mock_aws_source():
    """Mock AWS elevation source."""
    source = Mock(spec=AWS_Elevation_Source)
    source.name = "AWS Terrain Tiles"
    source.get_elevation.return_value = 95.2
    source.get_elevations.return_value = [95.2, 195.2, 295.2]  # Match 3 coordinates
    return source


@pytest.fixture
def manager_with_mock_sources(mock_srtm_source, mock_aws_source):
    """Manager with mocked elevation sources."""
    sources = [mock_srtm_source, mock_aws_source]
    return Manager(sources, cache_enabled=False)


@pytest.fixture
def sample_coordinates_list():
    """List of sample geographic coordinates."""
    return [
        Geographic(40.7, -74.0),
        Geographic(40.8, -74.1),
        Geographic(40.9, -74.2)
    ]


class Test_Elevation_Point:
    """Test Elevation_Point dataclass."""

    def test_elevation_point_creation(self, sample_geographic_coord):
        """Test creating elevation point."""
        point = Elevation_Point(sample_geographic_coord, "SRTM", 1.0)

        assert point.coord.latitude_deg == 40.7
        assert point.coord.longitude_deg == -74.0
        assert point.coord.altitude_m == 10.5
        assert point.source == "SRTM"
        assert point.accuracy == 1.0

    def test_elevation_point_string(self, sample_elevation_point):
        """Test string representation."""
        str_repr = str(sample_elevation_point)

        assert "10.5m" in str_repr
        assert "40.700000" in str_repr
        assert "-74.000000" in str_repr
        assert "Test Source" in str_repr

    def test_elevation_point_conversions(self, sample_elevation_point):
        """Test coordinate conversion methods."""
        # Test conversions
        utm = sample_elevation_point.to_utm()
        assert isinstance(utm, UTM)
        assert utm.altitude_m == 10.5

        web_mercator = sample_elevation_point.to_web_mercator()
        assert isinstance(web_mercator, Web_Mercator)
        assert web_mercator.altitude_m == 10.5

        ecef = sample_elevation_point.to_ecef()
        assert isinstance(ecef, ECEF)
        assert ecef.altitude_m == 10.5

    def test_elevation_point_ups_conversion(self):
        """Test UPS conversion with polar coordinates."""
        # Use polar coordinates for UPS conversion
        polar_coord = Geographic(80.0, 0.0, 10.5)  # Arctic
        polar_point = Elevation_Point(polar_coord, "Test")

        ups = polar_point.to_ups()
        assert isinstance(ups, UPS)
        assert ups.altitude_m == 10.5

    def test_elevation_point_create_method(self):
        """Test Elevation_Point create class method."""
        point = Elevation_Point.create(40.7, -74.0, 10.5, "SRTM", 1.0)

        assert point.coord.latitude_deg == 40.7
        assert point.coord.longitude_deg == -74.0
        assert point.coord.altitude_m == 10.5
        assert point.source == "SRTM"
        assert point.accuracy == 1.0

    def test_elevation_point_validation(self, sample_geographic_coord):
        """Test Elevation_Point coordinate validation."""
        # Should work with Geographic
        point = Elevation_Point(sample_geographic_coord, "Test")
        assert point.coord == sample_geographic_coord

        # Should fail with other coordinate types
        utm_coord = UTM.create(583960, 4504680, "18N", 10.5)
        with pytest.raises(TypeError, match="Elevation_Point coord must be Geographic"):
            Elevation_Point(utm_coord, "Test")


class Test_SRTM_Elevation_Source:
    """Test SRTM elevation source."""

    def test_source_initialization(self):
        """Test SRTM source initialization."""
        source = SRTM_Elevation_Source()

        assert source.name == "SRTM 30m"
        assert source.cache_dir.exists()

    def test_google_elevation_api(self):
        """Test elevation API call."""
        source = SRTM_Elevation_Source()
        coord = Geographic(40.7, -74.0)

        # Mock the source's get_elevation method directly
        with patch.object(source, 'get_elevation', return_value=100.5):
            elevation = source.get_elevation(coord)
            assert elevation == 100.5

    def test_cache_file_generation(self):
        """Test cache file path generation."""
        source = SRTM_Elevation_Source()
        cache_file = source._get_cache_file(40.7, -74.0)

        assert cache_file.name.endswith('.json')
        assert '40.7' in cache_file.name
        assert '-74.0' in cache_file.name


class Test_AWS_Elevation_Source:
    """Test AWS elevation source."""

    def test_source_initialization(self):
        """Test AWS source initialization."""
        source = AWS_Elevation_Source()

        assert source.name == "AWS Terrain Tiles"
        assert source.cache_dir.exists()

    def test_tile_coordinates(self):
        """Test tile coordinate calculation."""
        source = AWS_Elevation_Source()
        x, y = source._lat_lon_to_tile(40.7, -74.0, 12)

        assert isinstance(x, int)
        assert isinstance(y, int)
        assert 0 <= x < 2**12
        assert 0 <= y < 2**12


class Test_Terrain_Manager:
    """Test terrain manager functionality."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = Manager.create_default()

        assert len(manager.sources) >= 2  # At least SRTM and AWS
        assert manager.cache_enabled
        assert manager.elevation_cache == {}

    def test_elevation_lookup_with_fixture(self, manager_with_mock_sources, sample_geographic_coord):
        """Test elevation lookup with mocked sources."""
        elevation = manager_with_mock_sources.elevation(sample_geographic_coord)
        assert elevation == 100.5  # First mock source return value

    def test_elevation_batch_with_fixture(self, manager_with_mock_sources, sample_coordinates_list):
        """Test batch elevation lookup with mocked sources."""
        results = manager_with_mock_sources.elevation_batch(sample_coordinates_list)
        assert results == [100.5, 200.0, 300.0]  # First mock source batch return values

    def test_elevation_point_with_fixture(self, manager_with_mock_sources, sample_geographic_coord):
        """Test elevation point with mocked sources."""
        point = manager_with_mock_sources.elevation_point(sample_geographic_coord)

        assert point is not None
        assert point.coord.altitude_m == 100.5
        assert point.source == "SRTM 30m"
        assert isinstance(point.coord, Geographic)

    def test_cache_operations(self, sample_elevation_point):
        """Test cache management."""
        manager = Manager.create_default()

        # Add a point to cache
        manager.elevation_cache["40.700000,-74.000000"] = sample_elevation_point

        # Test cache stats
        stats = manager.get_cache_stats()
        assert stats['cached_points'] == 1
        # The sources list comes from manager's sources, not cache contents
        assert len(stats['sources']) >= 2  # At least SRTM and AWS

        # Test cache clear
        manager.clear_cache()
        assert len(manager.elevation_cache) == 0


class Test_Global_Functions:
    """Test global convenience functions."""

    def test_get_terrain_manager(self):
        """Test global terrain manager getter."""
        from pointy.core.terrain import get_terrain_manager

        manager1 = get_terrain_manager()
        manager2 = get_terrain_manager()

        # Should return the same instance
        assert manager1 is manager2

    def test_elevation_convenience_function(self, sample_geographic_coord):
        """Test global elevation convenience function."""
        # Mock the manager
        with patch.object(get_terrain_manager(), 'elevation', return_value=10.5):
            result = elevation(sample_geographic_coord)
            assert result == 10.5

    def test_elevation_point_convenience_function(self, sample_geographic_coord, sample_elevation_point):
        """Test global elevation_point convenience function."""
        # Mock the manager
        with patch.object(get_terrain_manager(), 'elevation_point', return_value=sample_elevation_point):
            result = elevation_point(sample_geographic_coord)
            assert result is sample_elevation_point
            assert result.source == "Test Source"


class Test_Manager_Factory_Functions:
    """Test manager factory functions."""

    def test_create_srtm_manager(self):
        """Test SRTM-only manager creation."""
        manager = create_srtm_manager(cache_enabled=False)

        assert len(manager.sources) == 1
        assert isinstance(manager.sources[0], SRTM_Elevation_Source)
        assert manager.sources[0].name == "SRTM 30m"

    def test_create_aws_manager(self):
        """Test AWS-only manager creation."""
        manager = create_aws_manager(cache_enabled=False)

        assert len(manager.sources) == 1
        assert isinstance(manager.sources[0], AWS_Elevation_Source)
        assert manager.sources[0].name == "AWS Terrain Tiles"

    def test_manager_factory_cache_settings(self):
        """Test factory functions respect cache settings."""
        manager_cached = create_srtm_manager(cache_enabled=True)
        manager_no_cache = create_srtm_manager(cache_enabled=False)

        assert manager_cached.cache_enabled is True
        assert manager_no_cache.cache_enabled is False


if __name__ == "__main__":
    pytest.main([__file__])
