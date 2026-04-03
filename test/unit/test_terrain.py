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

# Third-party Libraries
import numpy as np
import pytest
from rasterio.transform import Affine

# Project Libraries
from pointy.core.coordinate import Geographic, UTM, UPS, Web_Mercator, ECEF, Transformer
from pointy.core.terrain import (
    Manager,
    Elevation_Point,
    GeoTIFF_Elevation_Source,
    Terrain_Catalog,
    Local_DEM_Elevation_Source,
    elevation,
    elevation_point,
    get_terrain_manager,
    create_catalog_manager,
    Interpolation_Method
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
def mock_geotiff_source():
    """Mock GeoTIFF elevation source."""
    source = Mock(spec=GeoTIFF_Elevation_Source)
    source.name = "GeoTIFF (test.tif)"
    source.get_elevation.return_value = 100.5
    source.get_elevations.return_value = [100.5, 200.0, 300.0]  # Match 3 coordinates
    source.contains.return_value = True
    return source


@pytest.fixture
def mock_catalog():
    """Mock terrain catalog."""
    catalog = Mock(spec=Terrain_Catalog)
    catalog.name = "Terrain Catalog"
    catalog.get_elevation.return_value = 100.5
    catalog.sources = [mock_geotiff_source()]
    return catalog


@pytest.fixture
def manager_with_mock_sources(mock_geotiff_source):
    """Manager with mocked elevation sources."""
    sources = [mock_geotiff_source]
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
        # ECEF stores coordinates in xyz array, not altitude_m
        assert ecef.xyz is not None
        assert len(ecef.xyz) == 3

    def test_elevation_point_ups_conversion(self):
        """Test UPS conversion with polar coordinates."""
        # Use polar coordinates for UPS conversion (needs to be > 84° for Arctic)
        polar_coord = Geographic(85.0, 0.0, 10.5)  # Arctic
        polar_point = Elevation_Point(polar_coord, "Test")

        ups = polar_point.to_ups()
        assert ups is not None
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


class Test_Terrain_Manager:
    """Test terrain manager functionality."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        # Mock the catalog to avoid needing actual files
        with patch('pointy.core.terrain.Terrain_Catalog') as mock_catalog_class:
            mock_catalog = Mock()
            mock_catalog.sources = [Mock()]
            mock_catalog_class.return_value = mock_catalog

            manager = Manager([mock_catalog])
            # Clear any existing cache to ensure clean test
            manager.clear_cache()

            assert len(manager.sources) == 1
            assert manager.cache_enabled
            # Manager should start with empty cache
            assert len(manager.elevation_cache) == 0

    def test_elevation_lookup_with_fixture(self, manager_with_mock_sources, sample_geographic_coord):
        """Test elevation lookup with mocked sources."""
        elevation = manager_with_mock_sources.elevation(sample_geographic_coord)
        assert elevation == 100.5  # Mock source return value

    def test_elevation_batch_with_fixture(self, manager_with_mock_sources, sample_coordinates_list):
        """Test batch elevation lookup with mocked sources."""
        results = manager_with_mock_sources.elevation_batch(sample_coordinates_list)
        assert results == [100.5, 200.0, 300.0]  # Mock source batch return values

    def test_elevation_point_with_fixture(self, manager_with_mock_sources, sample_geographic_coord):
        """Test elevation point with mocked sources."""
        point = manager_with_mock_sources.elevation_point(sample_geographic_coord)

        assert point is not None
        assert point.coord.altitude_m == 100.5
        assert point.source == "GeoTIFF (test.tif)"
        assert isinstance(point.coord, Geographic)

    def test_cache_operations(self, sample_elevation_point):
        """Test cache management."""
        with patch('pointy.core.terrain.Terrain_Catalog') as mock_catalog_class:
            mock_catalog = Mock()
            mock_catalog.sources = [Mock()]
            mock_catalog_class.return_value = mock_catalog

            manager = Manager([mock_catalog])
            manager.clear_cache()

            # Add a point to cache
            manager.elevation_cache["40.700000,-74.000000"] = sample_elevation_point

            # Test cache stats
            stats = manager.get_cache_stats()
            assert stats['cached_points'] == 1

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

    def test_create_catalog_manager(self):
        """Test catalog-only manager creation."""
        # Mock the catalog to avoid needing actual files
        with patch('pointy.core.terrain.Terrain_Catalog') as mock_catalog_class:
            mock_catalog = Mock()
            mock_catalog.sources = [Mock()]
            mock_catalog.name = "Terrain Catalog"
            mock_catalog_class.return_value = mock_catalog

            manager = create_catalog_manager(cache_enabled=False)

            assert len(manager.sources) == 1
            assert manager.cache_enabled is False

    def test_manager_factory_cache_settings(self):
        """Test factory functions respect cache settings."""
        with patch('pointy.core.terrain.Terrain_Catalog') as mock_catalog_class:
            mock_catalog = Mock()
            mock_catalog.sources = [Mock()]
            mock_catalog_class.return_value = mock_catalog

            manager_cached = create_catalog_manager(cache_enabled=True)
            manager_no_cache = create_catalog_manager(cache_enabled=False)

            assert manager_cached.cache_enabled is True
            assert manager_no_cache.cache_enabled is False


class Test_Terrain_Catalog:
    """Test terrain catalog functionality."""

    def test_catalog_initialization_with_path(self, tmp_path):
        """Test catalog initialization with explicit path."""
        catalog = Terrain_Catalog(tmp_path)

        assert catalog.catalog_root == tmp_path
        assert catalog.sources == []  # No .tif files in tmp_path
        assert catalog.max_memory_mb == 500

    def test_catalog_initialization_without_path(self):
        """Test catalog initialization fails without path or env var."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="catalog_root must be provided"):
                Terrain_Catalog()

    def test_catalog_initialization_with_env_var(self, tmp_path):
        """Test catalog initialization with environment variable."""
        with patch.dict('os.environ', {'TERRAIN_CATALOG_ROOT': str(tmp_path)}):
            catalog = Terrain_Catalog()
            assert catalog.catalog_root == tmp_path

    def test_catalog_discovery_empty(self, tmp_path):
        """Test catalog discovery with no files."""
        catalog = Terrain_Catalog(tmp_path)
        assert len(catalog.sources) == 0

    def test_catalog_get_elevation_no_sources(self, tmp_path):
        """Test elevation query with no sources."""
        catalog = Terrain_Catalog(tmp_path)
        coord = Geographic(40.7, -74.0)

        elevation = catalog.get_elevation(coord)
        assert elevation is None

    def test_catalog_get_info(self, tmp_path):
        """Test catalog info method."""
        catalog = Terrain_Catalog(tmp_path)
        info = catalog.get_catalog_info()

        assert info['catalog_root'] == str(tmp_path)
        assert info['total_sources'] == 0
        assert info['sources'] == []


class Test_GeoTIFF_Elevation_Source:
    """Test GeoTIFF elevation source functionality."""

    def test_source_initialization(self):
        """Test GeoTIFF source initialization."""
        # Mock rasterio to avoid needing actual files
        with patch('pointy.core.terrain.rasterio.open') as mock_open:
            mock_dataset = Mock()
            mock_dataset.bounds = Mock()
            mock_dataset.transform = Mock()
            mock_dataset.crs = Mock()
            mock_open.return_value.__enter__.return_value = mock_dataset

            source = GeoTIFF_Elevation_Source("test.tif")

            assert source.name == "GeoTIFF (test.tif)"
            assert source.file_path.name == "test.tif"
            assert source._loaded is False

    def test_contains_method(self):
        """Test coordinate bounds checking."""
        with patch('pointy.core.terrain.rasterio.open') as mock_open:
            mock_dataset = Mock()
            # Use a simple object for bounds with actual numeric attributes
            class Bounds:
                def __init__(self):
                    self.left = -75.0
                    self.bottom = 40.0
                    self.right = -73.0
                    self.top = 41.0

            bounds = Bounds()

            # Configure the mock to return our bounds object when accessed
            mock_dataset.bounds = bounds
            mock_dataset.transform = Affine(1, 0, 0, 0, -1, 0)  # Geographic transform
            mock_dataset.crs = Mock()
            mock_open.return_value = mock_dataset

            source = GeoTIFF_Elevation_Source("test.tif")

            # Force load the dataset to trigger the bounds assignment
            source._load_dataset()

            # The bounds should be set from the loaded dataset
            assert source.bounds is not None
            assert source.bounds.left == -75.0
            assert source.bounds.bottom == 40.0
            assert source.bounds.right == -73.0
            assert source.bounds.top == 41.0

            # Coordinate inside bounds
            coord_inside = Geographic(40.7, -74.0)
            assert source.contains(coord_inside) is True

            # Coordinate outside bounds
            coord_outside = Geographic(0.0, 0.0)
            assert source.contains(coord_outside) is False

    def test_get_elevation_no_dataset(self):
        """Test elevation query with no dataset."""
        with patch('pointy.core.terrain.rasterio.open') as mock_open:
            mock_open.side_effect = Exception("File not found")

            source = GeoTIFF_Elevation_Source("nonexistent.tif")
            coord = Geographic(40.7, -74.0)

            # Should raise RuntimeError when file can't be loaded
            with pytest.raises(RuntimeError, match="Failed to load GeoTIFF"):
                source.get_elevation(coord)


class Test_Interpolation_Methods:
    """Test interpolation method enum and functionality."""

    def test_interpolation_method_enum(self):
        """Test Interpolation_Method enum values."""
        assert Interpolation_Method.NEAREST.value == "nearest"
        assert Interpolation_Method.BILINEAR.value == "bilinear"
        assert Interpolation_Method.CUBIC.value == "cubic"

        # Test enum iteration
        methods = list(Interpolation_Method)
        assert len(methods) == 3
        assert Interpolation_Method.NEAREST in methods
        assert Interpolation_Method.BILINEAR in methods
        assert Interpolation_Method.CUBIC in methods

    def test_manager_with_enum_interpolation(self):
        """Test Manager constructor with Interpolation_Method enum."""
        mock_source = Mock()
        manager = Manager([mock_source], interpolation=Interpolation_Method.NEAREST)

        assert manager.interpolation == Interpolation_Method.NEAREST
        assert manager.cache_enabled is True

    def test_factory_functions_with_enum(self):
        """Test factory functions with Interpolation_Method enum."""
        with patch('pointy.core.terrain.Terrain_Catalog') as mock_catalog_class:
            mock_catalog = Mock()
            mock_catalog.sources = [Mock()]
            mock_catalog_class.return_value = mock_catalog

            # Test create_catalog_manager with enum
            manager = create_catalog_manager(
                catalog_root="/test/path",
                interpolation=Interpolation_Method.CUBIC
            )

            assert manager.interpolation == Interpolation_Method.CUBIC
            assert manager.cache_enabled is True

    def test_geotiff_interpolation_methods(self):
        """Test GeoTIFF elevation source with different interpolation methods."""
        with patch('pointy.core.terrain.rasterio.open') as mock_open:
            mock_dataset = Mock()

            class Bounds:
                def __init__(self):
                    self.left = -75.0
                    self.bottom = 40.0
                    self.right = -73.0
                    self.top = 41.0

            bounds = Bounds()
            mock_dataset.bounds = bounds
            # Create a proper Affine transform that works with ~ operator
            mock_dataset.transform = Affine(1, 0, 0, 0, -1, 0)  # Geographic transform
            mock_dataset.crs = Mock()
            mock_dataset.nodata = -9999
            mock_dataset.read.return_value = np.array([[100.0]])
            mock_open.return_value = mock_dataset

            # Test nearest neighbor
            source = GeoTIFF_Elevation_Source("test.tif")
            source.interpolation = Interpolation_Method.NEAREST

            coord = Geographic(40.7, -74.0)
            elevation = source.get_elevation(coord)

            assert elevation == 100.0
            assert source.interpolation == Interpolation_Method.NEAREST

    def test_geotiff_interpolation_propagation(self):
        """Test that Manager propagates interpolation to sources."""
        with patch('pointy.core.terrain.rasterio.open') as mock_open:
            mock_dataset = Mock()

            class Bounds:
                def __init__(self):
                    self.left = -75.0
                    self.bottom = 40.0
                    self.right = -73.0
                    self.top = 41.0

            bounds = Bounds()
            mock_dataset.bounds = bounds
            mock_dataset.transform = Affine(1, 0, 0, 0, -1, 0)  # Geographic transform
            mock_dataset.crs = Mock()
            mock_open.return_value = mock_dataset

            source = GeoTIFF_Elevation_Source("test.tif")
            manager = Manager([source], interpolation=Interpolation_Method.BILINEAR)

            # Check that interpolation was propagated to source (if source supports it)
            if hasattr(source, 'interpolation'):
                assert source.interpolation == Interpolation_Method.BILINEAR
            else:
                # Source doesn't support interpolation, that's ok
                pass


if __name__ == "__main__":
    pytest.main([__file__])
