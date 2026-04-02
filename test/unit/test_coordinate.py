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
#    File:    test_coordinate.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Unit tests for coordinate system functionality.
"""

import pytest
from pointy.core.coordinate import (
    Coordinate_Transformer,
    create_geographic,
    create_pixel
)


class Test_Geographic_Coordinate:
    """Test GeographicCoordinate class."""

    def test_valid_coordinates(self):
        """Test creating valid geographic coordinates."""
        geo = create_geographic(40.7128, -74.0060, 10.5)
        assert geo.latitude == 40.7128
        assert geo.longitude == -74.0060
        assert geo.elevation == 10.5

    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(ValueError):
            create_geographic(91.0, 0.0)  # Too high

        with pytest.raises(ValueError):
            create_geographic(-91.0, 0.0)  # Too low

    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        with pytest.raises(ValueError):
            create_geographic(0.0, 181.0)  # Too high

        with pytest.raises(ValueError):
            create_geographic(0.0, -181.0)  # Too low

    def test_to_tuple(self):
        """Test coordinate tuple conversion."""
        geo = create_geographic(40.7, -74.0, 10.0)
        assert geo.to_tuple() == (-74.0, 40.7)
        assert geo.to_3d_tuple() == (-74.0, 40.7, 10.0)

    def test_string_representation(self):
        """Test string representation."""
        geo = create_geographic(40.7, -74.0, 10.5)
        str_repr = str(geo)
        assert "40.700000" in str_repr
        assert "-74.000000" in str_repr
        assert "10.5m" in str_repr


class Test_Pixel_Coordinate:
    """Test PixelCoordinate class."""

    def test_pixel_coordinates(self):
        """Test creating pixel coordinates."""
        pixel = create_pixel(256.5, 128.3)
        assert pixel.x == 256.5
        assert pixel.y == 128.3

    def test_to_tuple(self):
        """Test pixel tuple conversion."""
        pixel = create_pixel(256.7, 128.3)
        assert pixel.to_tuple() == (256.7, 128.3)
        assert pixel.to_int_tuple() == (257, 128)


class Test_Coordinate_Transformer:
    """Test coordinate transformation functionality."""

    def test_utm_zone_calculation(self):
        """Test UTM zone calculation."""
        transformer = Coordinate_Transformer()

        # Test various locations
        assert transformer.get_utm_zone(0.0, 0.0) == "EPSG:32631"  # Greenwich
        assert transformer.get_utm_zone(40.7, -74.0) == "EPSG:32618"  # NYC
        assert transformer.get_utm_zone(-33.9, 151.2) == "EPSG:32656"  # Sydney

    def test_geographic_to_web_mercator(self):
        """Test conversion to Web Mercator."""
        transformer = Coordinate_Transformer()
        geo = create_geographic(40.7, -74.0)

        proj = transformer.geographic_to_projected(geo, "EPSG:3857")
        assert proj.crs == "EPSG:3857"
        assert proj.easting != 0
        assert proj.northing != 0

    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        transformer = Coordinate_Transformer()

        # Test distance between two points
        geo1 = create_geographic(40.7, -74.0)
        geo2 = create_geographic(40.8, -74.1)

        distance = transformer.calculate_distance(geo1, geo2)
        assert distance > 0
        assert distance < 20000  # Should be less than 20km

    def test_bearing_calculation(self):
        """Test bearing calculation."""
        transformer = Coordinate_Transformer()

        geo1 = create_geographic(40.7, -74.0)
        geo2 = create_geographic(40.8, -74.0)  # Due north

        bearing = transformer.calculate_bearing(geo1, geo2)
        assert 0 <= bearing <= 360  # Valid bearing range
        # Should be approximately north (0° or 360°)
        assert bearing < 45 or bearing > 315  # Allow some tolerance


if __name__ == "__main__":
    pytest.main([__file__])
