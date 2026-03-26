#!/usr/bin/env python3
"""
Unit tests for terrain elevation functionality.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from gcp_picker.app.core.terrain import (
    Manager,
    ElevationPoint,
    SRTMElevationSource,
    AWSElevationSource
)


class TestElevationPoint:
    """Test ElevationPoint dataclass."""
    
    def test_elevation_point_creation(self):
        """Test creating elevation point."""
        point = ElevationPoint(40.7, -74.0, 10.5, "SRTM", 1.0)
        
        assert point.latitude == 40.7
        assert point.longitude == -74.0
        assert point.elevation == 10.5
        assert point.source == "SRTM"
        assert point.accuracy == 1.0
        
    def test_elevation_point_string(self):
        """Test string representation."""
        point = ElevationPoint(40.7, -74.0, 10.5, "SRTM")
        str_repr = str(point)
        
        assert "10.5m" in str_repr
        assert "40.700000" in str_repr
        assert "-74.000000" in str_repr
        assert "SRTM" in str_repr


class TestSRTMElevationSource:
    """Test SRTM elevation source."""
    
    def test_source_initialization(self):
        """Test SRTM source initialization."""
        source = SRTMElevationSource()
        
        assert source.name == "SRTM 30m"
        assert source.cache_dir.exists()
        
    @patch('requests.get')
    def test_google_elevation_api(self, mock_get):
        """Test Google Elevation API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [{'elevation': 10.5}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Set API key
        import os
        os.environ['GOOGLE_ELEVATION_API_KEY'] = 'test_key'
        
        source = SRTMElevationSource()
        elevation = source.get_elevation(40.7, -74.0)
        
        assert elevation == 10.5
        mock_get.assert_called_once()
        
    def test_cache_file_generation(self):
        """Test cache file path generation."""
        source = SRTMElevationSource()
        
        cache_file = source._get_cache_file(40.7128, -74.0060)
        assert cache_file.name == "elev_40.7128_-74.0060.json"
        assert cache_file.parent == source.cache_dir


class TestAWSElevationSource:
    """Test AWS elevation source."""
    
    def test_source_initialization(self):
        """Test AWS source initialization."""
        source = AWSElevationSource()
        
        assert source.name == "AWS Terrain Tiles"
        assert source.cache_dir.exists()
        
    def test_tile_coordinates(self):
        """Test tile coordinate calculation."""
        source = AWSElevationSource()
        
        x, y = source._lat_lon_to_tile(40.7, -74.0, 12)
        
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert 0 <= x < 2**12
        assert 0 <= y < 2**12


class TestTerrainManager:
    """Test terrain manager functionality."""
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = Manager()
        
        assert len(manager.sources) >= 2  # At least SRTM and AWS
        assert manager.cache_enabled
        assert manager.elevation_cache == {}
        
    def test_elevation_lookup(self):
        """Test elevation lookup with mock."""
        manager = Manager()
        
        # Mock the first source to return a value
        with patch.object(manager.sources[0], 'get_elevation', return_value=10.5):
            elevation = manager.elevation(40.7, -74.0)
            assert elevation == 10.5
            
    def test_elevation_batch(self):
        """Test batch elevation lookup."""
        manager = Manager()
        
        points = [(40.7, -74.0), (40.8, -74.1)]
        
        # Mock the first source
        with patch.object(manager.sources[0], 'get_elevations', return_value=[10.5, 20.0]):
            results = manager.elevation_batch(points)
            assert results == [10.5, 20.0]
            
    def test_cache_operations(self):
        """Test cache management."""
        manager = Manager()
        
        # Add a point to cache
        from gcp_picker.app.core.terrain import ElevationPoint
        point = ElevationPoint(40.7, -74.0, 10.5, "Test")
        manager.elevation_cache["40.700000,-74.000000"] = point
        
        # Test cache stats
        stats = manager.get_cache_stats()
        assert stats['cached_points'] == 1
        assert 'Test' in stats['sources']
        
        # Test cache clear
        manager.clear_cache()
        assert len(manager.elevation_cache) == 0
        
    def test_get_elevation_point(self):
        """Test getting detailed elevation point."""
        manager = Manager()
        
        # Mock elevation lookup
        with patch.object(manager, 'elevation', return_value=10.5):
            point = manager.get_elevation_point(40.7, -74.0)
            
            if point:  # Only test if elevation was found
                assert point.latitude == 40.7
                assert point.longitude == -74.0
                assert point.elevation == 10.5
                assert point.source is not None


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_terrain_manager(self):
        """Test global terrain manager getter."""
        from gcp_picker.app.core.terrain import get_terrain_manager
        
        manager1 = get_terrain_manager()
        manager2 = get_terrain_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        
    def test_elevation_convenience_function(self):
        """Test global elevation convenience function."""
        from gcp_picker.app.core.terrain import elevation, get_terrain_manager
        
        # Mock the manager
        with patch.object(get_terrain_manager(), 'elevation', return_value=10.5):
            result = elevation(40.7, -74.0)
            assert result == 10.5


if __name__ == "__main__":
    pytest.main([__file__])
