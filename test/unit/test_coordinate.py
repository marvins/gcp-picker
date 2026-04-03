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
import numpy as np
from pointy.core.coordinate import (
    Transformer,
    Geographic,
    Pixel,
    UTM,
    ECEF,
)


class Test_Geographic_Coordinate:
    """Test GeographicCoordinate class."""

    def test_valid_coordinates(self):
        """Test creating valid geographic coordinates."""
        geo = Geographic.create(40.7128, -74.0060, 10.5)
        assert geo.latitude_deg == 40.7128
        assert geo.longitude_deg == -74.0060
        assert geo.altitude_m == 10.5

    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(ValueError):
            Geographic.create(91.0, 0.0)  # Too high

        with pytest.raises(ValueError):
            Geographic.create(-91.0, 0.0)  # Too low

    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        with pytest.raises(ValueError):
            Geographic.create(0.0, 181.0)  # Too high

        with pytest.raises(ValueError):
            Geographic.create(0.0, -181.0)  # Too low

    def test_to_tuple(self):
        """Test coordinate tuple conversion."""
        geo = Geographic.create(40.7, -74.0, 10.0)
        assert geo.to_tuple() == (-74.0, 40.7)
        assert geo.to_3d_tuple() == (-74.0, 40.7, 10.0)

    def test_string_representation(self):
        """Test string representation."""
        geo = Geographic.create(40.7, -74.0, 10.5)
        str_repr = str(geo)
        assert "40.700000" in str_repr
        assert "-74.000000" in str_repr
        assert "10.5m" in str_repr


class Test_Pixel_Coordinate:
    """Test PixelCoordinate class."""

    def test_pixel_coordinates(self):
        """Test creating pixel coordinates."""
        pixel = Pixel.create(256.5, 128.3)
        assert pixel.x_px == 256.5
        assert pixel.y_px == 128.3

    def test_to_tuple(self):
        """Test pixel tuple conversion."""
        pixel = Pixel.create(256.7, 128.3)
        assert pixel.to_tuple() == (256.7, 128.3)
        assert pixel.to_int_tuple() == (257, 128)


class Test_Transformer:
    """Test coordinate transformation functionality."""

    def test_utm_zone_calculation(self):
        """Test UTM zone calculation."""
        transformer = Transformer()

        # Test various locations
        assert transformer.get_utm_zone(0.0, 0.0) == "EPSG:32631"  # Greenwich
        assert transformer.get_utm_zone(40.7, -74.0) == "EPSG:32737"  # NYC
        assert transformer.get_utm_zone(-33.9, 151.2) == "EPSG:32625"  # Sydney

    def test_geographic_to_web_mercator(self):
        """Test conversion to Web Mercator."""
        transformer = Transformer()
        geo = Geographic.create(40.7, -74.0)

        proj = transformer.geographic_to_projected(geo, "EPSG:3857")
        assert proj.crs == "EPSG:3857"
        assert proj.easting != 0
        assert proj.northing != 0

    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        transformer = Transformer()

        # Test distance between two points
        geo1 = Geographic.create(40.7, -74.0)
        geo2 = Geographic.create(40.8, -74.1)

        distance = transformer.calculate_distance(geo1, geo2)
        assert distance > 0
        assert distance < 20000  # Should be less than 20km

    def test_bearing_calculation(self):
        """Test bearing calculation."""
        transformer = Transformer()

        geo1 = Geographic.create(40.7, -74.0)
        geo2 = Geographic.create(40.8, -74.0)  # Due north

        bearing = transformer.calculate_bearing(geo1, geo2)
        assert 0 <= bearing <= 360  # Valid bearing range
        # Should be approximately north (0° or 360°)
        assert bearing < 45 or bearing > 315  # Allow some tolerance


class Test_ECEF_Coordinate:
    """Test ECEF coordinate functionality."""

    def test_create_from_components(self):
        """Test creating ECEF from individual components."""
        ecef = ECEF.create(-2700000, -4300000, 3850000)

        assert ecef.x_m == -2700000.0
        assert ecef.y_m == -4300000.0
        assert ecef.z_m == 3850000.0

    def test_create_from_array(self):
        """Test creating ECEF from array."""
        # From list
        ecef1 = ECEF.from_array([-2700000, -4300000, 3850000])
        assert ecef1.x_m == -2700000.0
        assert ecef1.y_m == -4300000.0
        assert ecef1.z_m == 3850000.0

        # From numpy array
        arr = np.array([-2700000, -4300000, 3850000])
        ecef2 = ECEF.from_array(arr)
        assert ecef2.x_m == -2700000.0
        assert ecef2.y_m == -4300000.0
        assert ecef2.z_m == 3850000.0

    def test_invalid_shape(self):
        """Test validation of array shape."""
        with pytest.raises(ValueError):
            ECEF.from_array([1, 2])  # Wrong shape

        with pytest.raises(ValueError):
            ECEF.from_array([1, 2, 3, 4])  # Wrong shape

    def test_to_tuple(self):
        """Test tuple conversion."""
        ecef = ECEF.create(-2700000, -4300000, 3850000)
        result = ecef.to_tuple()
        assert result == (-2700000.0, -4300000.0, 3850000.0)

    def test_to_array(self):
        """Test array conversion."""
        ecef = ECEF.create(-2700000, -4300000, 3850000)
        arr = ecef.to_array()

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (3,)
        assert arr[0] == -2700000.0
        assert arr[1] == -4300000.0
        assert arr[2] == 3850000.0

    def test_magnitude(self):
        """Test magnitude calculation."""
        ecef = ECEF.create(3, 4, 12)  # 3-4-5-12 triangle, magnitude = 13
        magnitude = ecef.magnitude
        assert abs(magnitude - 13.0) < 1e-10

    def test_string_representation(self):
        """Test string representation."""
        ecef = ECEF.create(-2700000, -4300000, 3850000)
        str_repr = str(ecef)
        assert "-2700000.00" in str_repr
        assert "-4300000.00" in str_repr
        assert "3850000.00" in str_repr

    def test_array_conversion_in_post_init(self):
        """Test that list is converted to numpy array in post_init."""
        ecef = ECEF(xyz=[-2700000, -4300000, 3850000])
        assert isinstance(ecef.xyz, np.ndarray)
        assert ecef.x_m == -2700000.0

    def test_copy_independence(self):
        """Test that to_array returns a copy, not reference."""
        ecef = ECEF.create(-2700000, -4300000, 3850000)
        arr1 = ecef.to_array()
        arr2 = ecef.to_array()

        # Modify one array
        arr1[0] = 9999999

        # Other should be unchanged
        assert arr2[0] == -2700000.0
        assert ecef.x_m == -2700000.0


if __name__ == "__main__":
    pytest.main([__file__])
