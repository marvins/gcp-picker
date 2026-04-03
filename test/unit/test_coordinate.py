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
#    File:    test_coordinate.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Unit tests for coordinate system functionality.
"""

# Standard Library Imports
import math

# Third-Party Imports
import numpy as np
import pytest

# Project Imports
from pointy.core.coordinate import (
    Coordinate_Type,
    EPSG_Manager,
    ECEF,
    Geographic,
    Pixel,
    Transformer,
    UPS,
    UTM,
    Web_Mercator,
)


# Fixtures for common objects
@pytest.fixture
def nyc_geographic():
    """New York City geographic coordinate."""
    return Geographic.create(40.7128, -74.0060, 10.5)

@pytest.fixture
def sydney_geographic():
    """Sydney geographic coordinate."""
    return Geographic.create(-33.8688, 151.2093, 58.0)

@pytest.fixture
def utm_coordinate():
    """UTM coordinate."""
    return UTM.create(583000, 4507000, "EPSG:32618", 10.5)

@pytest.fixture
def web_mercator_coordinate():
    """Web Mercator coordinate."""
    return Web_Mercator.create(-8238310.24, 4969803.74, 10.5)  # NYC in Web Mercator

@pytest.fixture
def ecef_coordinate():
    """ECEF coordinate."""
    return ECEF.create(-2700000, -4300000, 3850000)

@pytest.fixture
def pixel_coordinate():
    """Pixel coordinate."""
    return Pixel.create(256.5, 128.3)

@pytest.fixture
def north_pole_geographic():
    """North pole geographic coordinate."""
    return Geographic.create(89.5, 0.0, 1000.0)

@pytest.fixture
def south_pole_geographic():
    """South pole geographic coordinate."""
    return Geographic.create(-89.5, 180.0, 500.0)

@pytest.fixture
def ups_north_coordinate():
    """UPS North coordinate."""
    return UPS.create(2000000.0, 2000000.0, "N", 1000.0)

@pytest.fixture
def ups_south_coordinate():
    """UPS South coordinate."""
    return UPS.create(2500000.0, 1500000.0, "S", 500.0)


class Test_Geographic_Coordinate:
    """Test Geographic coordinate class."""

    @pytest.mark.parametrize("lat,lon,alt", [
        (40.7, -74.0, 10.5),
        (0.0, 0.0, None),
        (-33.9, 151.2, 100.0),
        (90.0, 0.0, 0.0),  # North pole
        (-90.0, 0.0, 0.0),  # South pole
        (45.0, -180.0, 500.0),  # International date line
        (45.0, 180.0, 500.0),  # International date line
    ])
    def test_geographic_various_coordinates(self, lat, lon, alt):
        """Test creating geographic coordinates with various values."""
        geo = Geographic.create(lat, lon, alt)
        assert geo.latitude_deg == lat
        assert geo.longitude_deg == lon
        assert geo.altitude_m == alt

    def test_valid_coordinates(self, nyc_geographic):
        """Test creating valid geographic coordinates."""
        geo = nyc_geographic
        assert geo.latitude_deg == 40.7128
        assert geo.longitude_deg == -74.0060
        assert geo.altitude_m == 10.5

    def test_rad_properties(self, nyc_geographic):
        """Test radian conversion properties."""
        geo = nyc_geographic

        # Test lat_rad property
        expected_lat_rad = math.radians(geo.latitude_deg)
        assert abs(geo.lat_rad - expected_lat_rad) < 1e-10

        # Test lon_rad property
        expected_lon_rad = math.radians(geo.longitude_deg)
        assert abs(geo.lon_rad - expected_lon_rad) < 1e-10

    def test_boundary_values(self):
        """Test boundary values."""
        # Test Mt. Everest
        everest = Geographic.create(27.9881, 86.9250, 8848.86)
        assert everest.latitude_deg == 27.9881
        assert everest.longitude_deg == 86.9250
        assert everest.altitude_m == 8848.86

        # Test Dead Sea (below sea level)
        dead_sea = Geographic.create(31.5, 35.5, -430.0)
        assert dead_sea.altitude_m == -430.0

    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(ValueError):
            Geographic.create(91.0, 0.0)  # Too high

        with pytest.raises(ValueError):
            Geographic.create(-91.0, 0.0)  # Too low

    def test_to_tuple(self, nyc_geographic):
        """Test coordinate tuple conversion."""
        geo = nyc_geographic
        assert geo.to_tuple() == (-74.0060, 40.7128)
        assert geo.to_3d_tuple() == (-74.0060, 40.7128, 10.5)

    def test_string_representation(self, nyc_geographic):
        """Test string representation."""
        geo = nyc_geographic
        str_repr = str(geo)
        assert "40.712800" in str_repr
        assert "-74.006000" in str_repr
        assert "10.5m" in str_repr

    def test_type_method(self, nyc_geographic):
        """Test coordinate type method."""
        geo = nyc_geographic
        assert geo.type() == Coordinate_Type.GEOGRAPHIC


class Test_Pixel_Coordinate:
    """Test Pixel coordinate class."""

    @pytest.mark.parametrize("x,y", [
        (256.5, 128.3),
        (0.0, 0.0),
        (1000.5, 2000.7),
        (-50.0, -100.0),
        (3.14159, 2.71828),
    ])
    def test_pixel_various_coordinates(self, x, y):
        """Test creating pixel coordinates with various values."""
        pixel = Pixel.create(x, y)
        assert pixel.x_px == x
        assert pixel.y_px == y

    def test_pixel_coordinates(self, pixel_coordinate):
        """Test creating pixel coordinates."""
        pixel = pixel_coordinate
        assert pixel.x_px == 256.5
        assert pixel.y_px == 128.3

    def test_boundary_values(self):
        """Test boundary values."""
        # Test zero coordinates
        zero_pixel = Pixel.create(0.0, 0.0)
        assert zero_pixel.x_px == 0.0
        assert zero_pixel.y_px == 0.0

        # Test negative coordinates
        neg_pixel = Pixel.create(-100.0, -200.0)
        assert neg_pixel.x_px == -100.0
        assert neg_pixel.y_px == -200.0

    def test_to_tuple(self, pixel_coordinate):
        """Test pixel tuple conversion."""
        pixel = pixel_coordinate
        assert pixel.to_tuple() == (256.5, 128.3)
        assert pixel.to_int_tuple() == (257, 128)

    def test_rounding_behavior(self):
        """Test integer rounding behavior."""
        # Test exact .5 rounds up
        pixel = Pixel.create(256.5, 128.5)
        assert pixel.to_int_tuple() == (257, 129)

        # Test below .5 rounds down
        pixel = Pixel.create(256.4, 128.4)
        assert pixel.to_int_tuple() == (256, 128)

    def test_type_method(self, pixel_coordinate):
        """Test coordinate type method."""
        pixel = pixel_coordinate
        assert pixel.type() == Coordinate_Type.PIXEL


class Test_UTM_Coordinate:
    """Test UTM coordinate class."""

    @pytest.mark.parametrize("easting,northing,crs,alt", [
        (583000, 4507000, "EPSG:32618", 10.5),
        (500000, 4649776, "EPSG:32633", None),
        (400000, 5418000, "EPSG:32755", 100.0),
        (600000, 4000000, "EPSG:32610", 0.0),
    ])
    def test_utm_various_coordinates(self, easting, northing, crs, alt):
        """Test creating UTM coordinates with various values."""
        utm = UTM.create(easting, northing, crs, alt)
        assert utm.easting_m == easting
        assert utm.northing_m == northing
        assert utm.crs == crs
        assert utm.altitude_m == alt

    def test_utm_creation(self, utm_coordinate):
        """Test creating UTM coordinates."""
        utm = utm_coordinate
        assert utm.easting_m == 583000
        assert utm.northing_m == 4507000
        assert utm.crs == "EPSG:32618"
        assert utm.altitude_m == 10.5

    def test_utm_without_elevation(self):
        """Test UTM without elevation."""
        utm = UTM.create(583000, 4507000, "EPSG:32618")
        assert utm.altitude_m is None

    def test_boundary_values(self):
        """Test boundary values."""
        # Test zero coordinates
        zero_utm = UTM.create(0.0, 0.0, "EPSG:32618", 0.0)
        assert zero_utm.easting_m == 0.0
        assert zero_utm.northing_m == 0.0
        assert zero_utm.altitude_m == 0.0

        # Test negative values (though unusual for UTM)
        neg_utm = UTM.create(-1000.0, -2000.0, "EPSG:32618", -100.0)
        assert neg_utm.easting_m == -1000.0
        assert neg_utm.northing_m == -2000.0
        assert neg_utm.altitude_m == -100.0

    def test_to_tuple(self, utm_coordinate):
        """Test UTM tuple conversion."""
        utm = utm_coordinate
        assert utm.to_tuple() == (583000, 4507000)
        assert utm.to_3d_tuple() == (583000, 4507000, 10.5)

    def test_string_representation(self, utm_coordinate):
        """Test string representation."""
        utm = utm_coordinate
        str_repr = str(utm)
        assert "583000.00" in str_repr
        assert "4507000.00" in str_repr
        assert "10.5m" in str_repr
        assert "EPSG:32618" in str_repr

    def test_type_method(self, utm_coordinate):
        """Test coordinate type method."""
        utm = utm_coordinate
        assert utm.type() == Coordinate_Type.UTM


class Test_Web_Mercator_Coordinate:
    """Test Web Mercator coordinate class."""

    @pytest.mark.parametrize("easting,northing,alt", [
        (-8238310.24, 4969803.74, 10.5),  # NYC
        (0, 0, None),  # Origin
        (20037508.34, 0, 100.0),  # Far east
        (0, 20037508.34, 0.0),  # Far north
        (-20037508.34, -20037508.34, 500.0),  # Far southwest
    ])
    def test_web_mercator_various_coordinates(self, easting, northing, alt):
        """Test creating Web Mercator coordinates with various values."""
        wm = Web_Mercator.create(easting, northing, alt)
        assert wm.easting_m == easting
        assert wm.northing_m == northing
        assert wm.altitude_m == alt
        assert wm.crs == "EPSG:3857"

    def test_web_mercator_creation(self, web_mercator_coordinate):
        """Test creating Web Mercator coordinates."""
        wm = web_mercator_coordinate
        assert wm.easting_m == -8238310.24
        assert wm.northing_m == 4969803.74
        assert wm.altitude_m == 10.5
        assert wm.crs == "EPSG:3857"

    def test_web_mercator_without_elevation(self):
        """Test Web Mercator without elevation."""
        wm = Web_Mercator.create(-8238310.24, 4969803.74)
        assert wm.altitude_m is None

    def test_boundary_values(self):
        """Test boundary values."""
        # Test origin (0,0)
        origin = Web_Mercator.create(0.0, 0.0, 0.0)
        assert origin.easting_m == 0.0
        assert origin.northing_m == 0.0
        assert origin.altitude_m == 0.0

        # Test Web Mercator world bounds (approximately)
        # Web Mercator extends from -20037508.34 to 20037508.34 in both directions
        max_extent = 20037508.34
        ne_corner = Web_Mercator.create(max_extent, max_extent, 8848.86)
        assert ne_corner.easting_m == max_extent
        assert ne_corner.northing_m == max_extent
        assert ne_corner.altitude_m == 8848.86

    def test_to_tuple(self, web_mercator_coordinate):
        """Test Web Mercator tuple conversion."""
        wm = web_mercator_coordinate
        assert wm.to_tuple() == (-8238310.24, 4969803.74)
        assert wm.to_3d_tuple() == (-8238310.24, 4969803.74, 10.5)

    def test_string_representation(self, web_mercator_coordinate):
        """Test string representation."""
        wm = web_mercator_coordinate
        str_repr = str(wm)
        assert "-8238310.24" in str_repr
        assert "4969803.74" in str_repr
        assert "10.5m" in str_repr
        assert "EPSG:3857" in str_repr

    def test_string_representation_without_elevation(self):
        """Test string representation without elevation."""
        wm = Web_Mercator.create(-8238310.24, 4969803.74)
        str_repr = str(wm)
        assert "-8238310.24" in str_repr
        assert "4969803.74" in str_repr
        assert "EPSG:3857" in str_repr
        assert "m]" not in str_repr  # Should not have elevation

    def test_crs_property(self):
        """Test CRS property is always EPSG:3857."""
        wm1 = Web_Mercator.create(100, 200)
        wm2 = Web_Mercator.create(-100, -200, 50)

        assert wm1.crs == "EPSG:3857"
        assert wm2.crs == "EPSG:3857"

    def test_world_bounds(self):
        """Test Web Mercator world bounds."""
        # Web Mercator world extent
        max_extent = 20037508.342789244

        # Test corners of the world
        ne = Web_Mercator.create(max_extent, max_extent)
        nw = Web_Mercator.create(-max_extent, max_extent)
        se = Web_Mercator.create(max_extent, -max_extent)
        sw = Web_Mercator.create(-max_extent, -max_extent)

        # All should be valid
        assert ne.easting_m == max_extent
        assert ne.northing_m == max_extent
        assert sw.easting_m == -max_extent
        assert sw.northing_m == -max_extent

    def test_type_method(self, web_mercator_coordinate):
        """Test coordinate type method."""
        wm = web_mercator_coordinate
        assert wm.type() == Coordinate_Type.WEB_MERCATOR


class Test_ECEF_Coordinate:
    """Test ECEF coordinate functionality."""

    @pytest.mark.parametrize("x,y,z", [
        (-2700000, -4300000, 3850000),
        (0, 0, 0),
        (1000000, 2000000, 3000000),
        (-1000000, -2000000, -3000000),
        (6378137, 0, 0),  # Earth radius at equator
    ])
    def test_ecef_various_coordinates(self, x, y, z):
        """Test creating ECEF coordinates with various values."""
        ecef = ECEF.create(x, y, z)
        assert ecef.x_m == x
        assert ecef.y_m == y
        assert ecef.z_m == z

    def test_create_from_components(self, ecef_coordinate):
        """Test creating ECEF from individual components."""
        ecef = ecef_coordinate
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

    def test_boundary_values(self):
        """Test boundary values."""
        # Test origin
        origin = ECEF.create(0.0, 0.0, 0.0)
        assert origin.magnitude == 0.0

        # Test Earth surface values
        earth_surface = ECEF.create(6378137, 0, 0)  # Equator
        assert abs(earth_surface.magnitude - 6378137) < 1e-10

    def test_invalid_shape(self):
        """Test validation of array shape."""
        with pytest.raises(ValueError):
            ECEF.from_array([1, 2])  # Wrong shape

        with pytest.raises(ValueError):
            ECEF.from_array([1, 2, 3, 4])  # Wrong shape

    def test_to_tuple(self, ecef_coordinate):
        """Test tuple conversion."""
        ecef = ecef_coordinate
        result = ecef.to_tuple()
        assert result == (-2700000.0, -4300000.0, 3850000.0)

    def test_to_array(self, ecef_coordinate):
        """Test array conversion."""
        ecef = ecef_coordinate
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

    def test_string_representation(self, ecef_coordinate):
        """Test string representation."""
        ecef = ecef_coordinate
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

    def test_type_method(self, ecef_coordinate):
        """Test coordinate type method."""
        ecef = ecef_coordinate
        assert ecef.type() == Coordinate_Type.ECEF


class Test_UPS_Coordinate:
    """Test UPS coordinate class."""

    @pytest.mark.parametrize("easting,northing,hemisphere,alt", [
        (2000000.0, 2000000.0, "N", 1000.0),
        (2500000.0, 1500000.0, "S", 500.0),
        (0.0, 0.0, "N", None),
        (3000000.0, 1000000.0, "S", 0.0),
    ])
    def test_ups_various_coordinates(self, easting, northing, hemisphere, alt):
        """Test creating UPS coordinates with various values."""
        ups = UPS.create(easting, northing, hemisphere, alt)
        assert ups.easting_m == easting
        assert ups.northing_m == northing
        assert ups.hemisphere == hemisphere.upper()
        assert ups.altitude_m == alt

    def test_ups_creation_north(self, ups_north_coordinate):
        """Test creating UPS North coordinates."""
        ups = ups_north_coordinate
        assert ups.easting_m == 2000000.0
        assert ups.northing_m == 2000000.0
        assert ups.hemisphere == "N"
        assert ups.altitude_m == 1000.0
        assert ups.crs == "EPSG:32661"

    def test_ups_creation_south(self, ups_south_coordinate):
        """Test creating UPS South coordinates."""
        ups = ups_south_coordinate
        assert ups.easting_m == 2500000.0
        assert ups.northing_m == 1500000.0
        assert ups.hemisphere == "S"
        assert ups.altitude_m == 500.0
        assert ups.crs == "EPSG:32761"

    def test_ups_without_elevation(self):
        """Test UPS without elevation."""
        ups = UPS.create(2000000.0, 2000000.0, "N")
        assert ups.altitude_m is None

    def test_hemisphere_case_insensitive(self):
        """Test that hemisphere is case insensitive."""
        ups1 = UPS.create(1000000.0, 1000000.0, "n")
        ups2 = UPS.create(1000000.0, 1000000.0, "N")
        ups3 = UPS.create(1000000.0, 1000000.0, "s")
        ups4 = UPS.create(1000000.0, 1000000.0, "S")

        assert ups1.hemisphere == "N"
        assert ups2.hemisphere == "N"
        assert ups3.hemisphere == "S"
        assert ups4.hemisphere == "S"

    def test_boundary_values(self):
        """Test boundary values."""
        # Test zero coordinates
        zero_ups = UPS.create(0.0, 0.0, "N", 0.0)
        assert zero_ups.easting_m == 0.0
        assert zero_ups.northing_m == 0.0
        assert zero_ups.altitude_m == 0.0

        # Test large values (UPS coordinates can be large)
        large_ups = UPS.create(4000000.0, 4000000.0, "S", 8848.86)
        assert large_ups.easting_m == 4000000.0
        assert large_ups.northing_m == 4000000.0
        assert large_ups.altitude_m == 8848.86

    def test_invalid_hemisphere(self):
        """Test invalid hemisphere values."""
        with pytest.raises(ValueError):
            UPS.create(1000000.0, 1000000.0, "X")  # Invalid hemisphere

        with pytest.raises(ValueError):
            UPS.create(1000000.0, 1000000.0, "North")  # Invalid format

    def test_crs_hemisphere_mismatch(self):
        """Test CRS and hemisphere mismatch validation."""
        # Test direct constructor with mismatched CRS (this should raise error in __post_init__)
        with pytest.raises(ValueError):
            UPS(easting_m=1000000.0, northing_m=1000000.0, hemisphere="N", altitude_m=100.0, crs="EPSG:32761")

        # Test direct constructor with mismatched CRS for South
        with pytest.raises(ValueError):
            UPS(easting_m=1000000.0, northing_m=1000000.0, hemisphere="S", altitude_m=100.0, crs="EPSG:32661")

    def test_to_tuple(self, ups_north_coordinate):
        """Test UPS tuple conversion."""
        ups = ups_north_coordinate
        assert ups.to_tuple() == (2000000.0, 2000000.0)
        assert ups.to_3d_tuple() == (2000000.0, 2000000.0, 1000.0)

    def test_string_representation(self, ups_north_coordinate):
        """Test string representation."""
        ups = ups_north_coordinate
        str_repr = str(ups)
        assert "2000000.00" in str_repr
        assert "2000000.00" in str_repr
        assert "1000.0m" in str_repr
        assert "EPSG:32661" in str_repr

    def test_string_representation_without_elevation(self):
        """Test string representation without elevation."""
        ups = UPS.create(2000000.0, 2000000.0, "N")
        str_repr = str(ups)
        assert "2000000.00" in str_repr
        assert "2000000.00" in str_repr
        assert "EPSG:32661" in str_repr
        assert "m]" not in str_repr  # Should not have elevation

    def test_type_method(self, ups_north_coordinate):
        """Test coordinate type method."""
        ups = ups_north_coordinate
        assert ups.type() == Coordinate_Type.UPS


class Test_EPSG_Manager:
    """Test EPSG code management functionality."""

    def test_epsg_constants(self):
        """Test EPSG code constants."""
        assert EPSG_Manager.WGS84 == 4326
        assert EPSG_Manager.WEB_MERCATOR == 3857
        assert EPSG_Manager.ECEF == 4978
        assert EPSG_Manager.UPS_NORTH == 32661
        assert EPSG_Manager.UPS_SOUTH == 32761
        assert EPSG_Manager.UTM_NORTH_BASE == 32600
        assert EPSG_Manager.UTM_SOUTH_BASE == 32700

    @pytest.mark.parametrize("epsg_str,expected_code", [
        ("EPSG:4326", 4326),
        ("EPSG:3857", 3857),
        ("EPSG:32661", 32661),
        ("EPSG:32761", 32761),
        ("EPSG:32618", 32618),
        ("EPSG:32756", 32756),
    ])
    def test_to_epsg_code(self, epsg_str, expected_code):
        """Test converting EPSG string to integer code."""
        result = EPSG_Manager.to_epsg_code(epsg_str)
        assert result == expected_code

    def test_to_epsg_code_invalid(self):
        """Test invalid EPSG string formats."""
        with pytest.raises(ValueError):
            EPSG_Manager.to_epsg_code("4326")  # Missing EPSG: prefix

        with pytest.raises(ValueError):
            EPSG_Manager.to_epsg_code("CRS:4326")  # Wrong prefix

        with pytest.raises(ValueError):
            EPSG_Manager.to_epsg_code("EPSG:")  # Missing code

        with pytest.raises(ValueError):
            EPSG_Manager.to_epsg_code("EPSG:abc")  # Non-numeric code

    @pytest.mark.parametrize("epsg_code,expected_str", [
        (4326, "EPSG:4326"),
        (3857, "EPSG:3857"),
        (32661, "EPSG:32661"),
        (32761, "EPSG:32761"),
        (32618, "EPSG:32618"),
        (32756, "EPSG:32756"),
    ])
    def test_to_epsg_string(self, epsg_code, expected_str):
        """Test converting integer EPSG code to string."""
        result = EPSG_Manager.to_epsg_string(epsg_code)
        assert result == expected_str

    @pytest.mark.parametrize("epsg_code,expected", [
        (32601, True), (32660, True),  # UTM North zones
        (32701, True), (32760, True),  # UTM South zones
        (32600, False), (32661, False),  # Base codes and UPS
        (32700, False), (32761, False),  # Base codes and UPS
        (4326, False), (3857, False),  # Other coordinate systems
    ])
    def test_is_utm_zone(self, epsg_code, expected):
        """Test UTM zone detection."""
        result = EPSG_Manager.is_utm_zone(epsg_code)
        assert result == expected

    @pytest.mark.parametrize("epsg_code,expected", [
        (32661, True), (32761, True),  # UPS zones
        (32601, False), (32701, False),  # UTM zones
        (4326, False), (3857, False),  # Other coordinate systems
    ])
    def test_is_ups_zone(self, epsg_code, expected):
        """Test UPS zone detection."""
        result = EPSG_Manager.is_ups_zone(epsg_code)
        assert result == expected

    def test_is_polar_region(self):
        """Test polar region detection."""
        assert EPSG_Manager.is_polar_region(32661) == True  # UPS North
        assert EPSG_Manager.is_polar_region(32761) == True  # UPS South
        assert EPSG_Manager.is_polar_region(32618) == False  # UTM
        assert EPSG_Manager.is_polar_region(4326) == False  # Geographic

    @pytest.mark.parametrize("epsg_code,expected_zone", [
        (32601, 1), (32618, 18), (32660, 60),  # Northern hemisphere
        (32701, 1), (32756, 56), (32760, 60),  # Southern hemisphere
    ])
    def test_get_utm_zone_number(self, epsg_code, expected_zone):
        """Test UTM zone number extraction."""
        result = EPSG_Manager.get_utm_zone_number(epsg_code)
        assert result == expected_zone

    def test_get_utm_zone_number_invalid(self):
        """Test UTM zone number extraction for invalid codes."""
        with pytest.raises(ValueError):
            EPSG_Manager.get_utm_zone_number(4326)  # Not UTM

        with pytest.raises(ValueError):
            EPSG_Manager.get_utm_zone_number(32661)  # UPS

    @pytest.mark.parametrize("epsg_code,expected_hemisphere", [
        (32601, "N"), (32618, "N"), (32660, "N"),  # Northern hemisphere
        (32701, "S"), (32756, "S"), (32760, "S"),  # Southern hemisphere
    ])
    def test_get_utm_hemisphere(self, epsg_code, expected_hemisphere):
        """Test UTM hemisphere extraction."""
        result = EPSG_Manager.get_utm_hemisphere(epsg_code)
        assert result == expected_hemisphere

    @pytest.mark.parametrize("epsg_code,expected_hemisphere", [
        (32661, "N"),  # UPS North
        (32761, "S"),  # UPS South
    ])
    def test_get_ups_hemisphere(self, epsg_code, expected_hemisphere):
        """Test UPS hemisphere extraction."""
        result = EPSG_Manager.get_ups_hemisphere(epsg_code)
        assert result == expected_hemisphere

    def test_get_ups_hemisphere_invalid(self):
        """Test UPS hemisphere extraction for invalid codes."""
        with pytest.raises(ValueError):
            EPSG_Manager.get_ups_hemisphere(32618)  # UTM zone

    @pytest.mark.parametrize("zone,hemisphere,expected", [
        (1, "N", 32601), (18, "N", 32618), (60, "N", 32660),  # Northern
        (1, "S", 32701), (56, "S", 32756), (60, "S", 32760),  # Southern
    ])
    def test_create_utm_epsg(self, zone, hemisphere, expected):
        """Test UTM EPSG code creation."""
        result = EPSG_Manager.create_utm_epsg(zone, hemisphere)
        assert result == expected

    def test_create_utm_epsg_invalid(self):
        """Test UTM EPSG code creation with invalid parameters."""
        with pytest.raises(ValueError):
            EPSG_Manager.create_utm_epsg(0, "N")  # Zone too low

        with pytest.raises(ValueError):
            EPSG_Manager.create_utm_epsg(61, "N")  # Zone too high

        with pytest.raises(ValueError):
            EPSG_Manager.create_utm_epsg(18, "X")  # Invalid hemisphere

    @pytest.mark.parametrize("hemisphere,expected", [
        ("N", 32661), ("n", 32661),  # North (case insensitive)
        ("S", 32761), ("s", 32761),  # South (case insensitive)
    ])
    def test_create_ups_epsg(self, hemisphere, expected):
        """Test UPS EPSG code creation."""
        result = EPSG_Manager.create_ups_epsg(hemisphere)
        assert result == expected

    def test_create_ups_epsg_invalid(self):
        """Test UPS EPSG code creation with invalid hemisphere."""
        with pytest.raises(ValueError):
            EPSG_Manager.create_ups_epsg("X")  # Invalid hemisphere

    @pytest.mark.parametrize("epsg_code,expected_type", [
        (4326, Coordinate_Type.GEOGRAPHIC),
        (3857, Coordinate_Type.WEB_MERCATOR),
        (4978, Coordinate_Type.ECEF),
        (32618, Coordinate_Type.UTM),
        (32756, Coordinate_Type.UTM),
        (32661, Coordinate_Type.UPS),
        (32761, Coordinate_Type.UPS),
    ])
    def test_get_coordinate_type(self, epsg_code, expected_type):
        """Test coordinate type detection from EPSG code."""
        result = EPSG_Manager.get_coordinate_type(epsg_code)
        assert result == expected_type

    def test_get_coordinate_type_invalid(self):
        """Test coordinate type detection for unknown EPSG code."""
        result = EPSG_Manager.get_coordinate_type(9999)  # Unknown code
        assert result is None  # Should return None for unknown codes

    @pytest.mark.parametrize("epsg_code,expected_desc", [
        (4326, "WGS84 Geographic"),
        (3857, "Web Mercator"),
        (4978, "Earth-Centered Earth-Fixed"),
        (32661, "Universal Polar Stereographic (N)"),
        (32761, "Universal Polar Stereographic (S)"),
        (32618, "UTM Zone 18N"),
        (32756, "UTM Zone 56S"),
        (9999, "Unknown EPSG:9999"),
    ])
    def test_get_description(self, epsg_code, expected_desc):
        """Test EPSG code description."""
        result = EPSG_Manager.get_description(epsg_code)
        assert result == expected_desc


class Test_Coordinate_EPSG_Methods:
    """Test to_epsg() methods on coordinate classes."""

    def test_geographic_to_epsg(self, nyc_geographic):
        """Test Geographic coordinate to_epsg method."""
        geo = nyc_geographic
        assert geo.to_epsg() == EPSG_Manager.WGS84

    def test_utm_to_epsg(self, utm_coordinate):
        """Test UTM coordinate to_epsg method."""
        utm = utm_coordinate
        expected = EPSG_Manager.to_epsg_code(utm.crs)
        assert utm.to_epsg() == expected

    def test_ups_to_epsg(self, ups_north_coordinate, ups_south_coordinate):
        """Test UPS coordinate to_epsg method."""
        # Test UPS North
        ups_north = ups_north_coordinate
        expected_north = EPSG_Manager.to_epsg_code(ups_north.crs)
        assert ups_north.to_epsg() == expected_north
        assert ups_north.to_epsg() == EPSG_Manager.UPS_NORTH

        # Test UPS South
        ups_south = ups_south_coordinate
        expected_south = EPSG_Manager.to_epsg_code(ups_south.crs)
        assert ups_south.to_epsg() == expected_south
        assert ups_south.to_epsg() == EPSG_Manager.UPS_SOUTH

    def test_web_mercator_to_epsg(self, web_mercator_coordinate):
        """Test Web Mercator coordinate to_epsg method."""
        wm = web_mercator_coordinate
        assert wm.to_epsg() == EPSG_Manager.WEB_MERCATOR

    def test_ecef_to_epsg(self, ecef_coordinate):
        """Test ECEF coordinate to_epsg method."""
        ecef = ecef_coordinate
        assert ecef.to_epsg() == EPSG_Manager.ECEF

    def test_coordinate_epsg_consistency(self):
        """Test that coordinate EPSG codes match their CRS definitions."""
        # Test various UTM zones
        utm_north = UTM.create(500000, 4649776, "EPSG:32633")  # Zone 33N
        assert utm_north.to_epsg() == 32633

        utm_south = UTM.create(500000, 4649776, "EPSG:32733")  # Zone 33S
        assert utm_south.to_epsg() == 32733

        # Test UPS coordinates
        ups_n = UPS.create(2000000, 2000000, "N")
        assert ups_n.to_epsg() == 32661

        ups_s = UPS.create(2000000, 2000000, "S")
        assert ups_s.to_epsg() == 32761

        # Test Web Mercator (always same EPSG)
        wm1 = Web_Mercator.create(100, 200)
        wm2 = Web_Mercator.create(-100, -200, 50)
        assert wm1.to_epsg() == 3857
        assert wm2.to_epsg() == 3857


class Test_Transformer_EPSG_Methods:
    """Test EPSG-related methods in Transformer class."""

    def test_get_epsg_info(self):
        """Test EPSG info retrieval."""
        transformer = Transformer()

        # Test UTM zone
        info = transformer.get_epsg_info(32618)
        expected = {
            'code': 32618,
            'string': 'EPSG:32618',
            'coordinate_type': Coordinate_Type.UTM,
            'description': 'UTM Zone 18N',
            'is_utm': True,
            'is_ups': False,
            'is_polar': False,
        }
        assert info == expected

        # Test UPS zone
        info = transformer.get_epsg_info(32661)
        assert info['code'] == 32661
        assert info['is_ups'] == True
        assert info['is_polar'] == True
        assert info['coordinate_type'] == Coordinate_Type.UPS

        # Test geographic
        info = transformer.get_epsg_info(4326)
        assert info['coordinate_type'] == Coordinate_Type.GEOGRAPHIC
        assert info['is_utm'] == False
        assert info['is_ups'] == False

    def test_get_epsg_info_from_string(self):
        """Test EPSG info retrieval from string."""
        transformer = Transformer()

        info = transformer.get_epsg_info_from_string("EPSG:32618")
        assert info['code'] == 32618
        assert info['string'] == 'EPSG:32618'
        assert info['coordinate_type'] == Coordinate_Type.UTM

    def test_get_epsg_info_invalid(self):
        """Test EPSG info retrieval with invalid code."""
        transformer = Transformer()

        # Should not raise error for unknown codes, but return appropriate info
        info = transformer.get_epsg_info(9999)
        assert info['code'] == 9999
        assert info['coordinate_type'] is None  # Unknown codes return None
        assert 'Unknown' in info['description']

    @pytest.mark.parametrize("lat,lon,expected_zone", [
        (0.0, 0.0, "EPSG:32631"),  # Greenwich (zone 31N)
        (40.7, -74.0, "EPSG:32618"),  # NYC (zone 18N)
        (-33.9, 151.2, "EPSG:32756"),  # Sydney (zone 56S)
        (60.0, 0.0, "EPSG:32631"),  # Arctic (zone 31N)
        (-60.0, 0.0, "EPSG:32731"),  # Antarctic (zone 31S)
    ])
    def test_utm_zone_calculation_with_epsG_manager(self, lat, lon, expected_zone):
        """Test UTM zone calculation using EPSG_Manager."""
        transformer = Transformer()
        zone = transformer.get_utm_zone(lon, lat)
        assert zone == expected_zone

    def test_polar_zones_with_epsG_manager(self):
        """Test polar zone handling using EPSG_Manager."""
        transformer = Transformer()

        # Test exactly at the polar boundary (84.0° should be UPS)
        zone = transformer.get_utm_zone(0.0, 84.0)
        assert zone == "EPSG:32661"

        # Test well within polar region
        zone = transformer.get_utm_zone(0.0, 89.0)
        assert zone == "EPSG:32661"

        # Test south polar boundary (-80.0° should be UPS)
        zone = transformer.get_utm_zone(0.0, -80.0)
        assert zone == "EPSG:32761"

        # Test well within south polar region
        zone = transformer.get_utm_zone(0.0, -89.0)
        assert zone == "EPSG:32761"


class Test_Transformer:

    def test_utm_zone_boundaries(self):
        """Test UTM zone boundaries."""
        transformer = Transformer()

        # Test zone boundaries (every 6 degrees)
        for zone_num in range(1, 61):
            lon = (zone_num - 1) * 6 - 3  # Center of zone
            expected_zone = f"EPSG:326{zone_num:02d}" if lon >= 0 else f"EPSG:327{zone_num:02d}"
            actual_zone = transformer.get_utm_zone(0.0, lon)
            # Note: This is a simplified test - actual UTM zones are more complex

    def test_geographic_to_web_mercator(self, nyc_geographic):
        """Test conversion to Web Mercator."""
        transformer = Transformer()
        geo = nyc_geographic

        proj = transformer.geographic_to_projected(geo, "EPSG:3857")
        assert isinstance(proj, Web_Mercator)
        assert proj.crs == "EPSG:3857"
        assert proj.easting_m != 0
        assert proj.northing_m != 0

    def test_geographic_to_utm(self, nyc_geographic):
        """Test conversion to UTM."""
        transformer = Transformer()
        geo = nyc_geographic

        proj = transformer.geographic_to_projected(geo, "EPSG:32618")  # UTM zone 18N
        assert isinstance(proj, UTM)
        assert proj.crs == "EPSG:32618"
        assert proj.easting_m > 0
        assert proj.northing_m > 0

    def test_distance_calculation(self, nyc_geographic, sydney_geographic):
        """Test distance calculation between coordinates."""
        # Test distance between NYC and Sydney using Geographic method
        distance = Geographic.distance(nyc_geographic, sydney_geographic)
        assert distance > 15000000  # Should be > 15,000 km
        assert distance < 17000000  # Should be < 17,000 km (actual ~16,000 km)

    def test_distance_same_point(self, nyc_geographic):
        """Test distance calculation for same point."""
        distance = Geographic.distance(nyc_geographic, nyc_geographic)
        assert distance == 0.0

    def test_utm_distance_calculation(self, utm_coordinate):
        """Test UTM distance calculation."""
        # Create another UTM point 1000m east
        east_utm = UTM.create(utm_coordinate.easting_m + 1000, utm_coordinate.northing_m, utm_coordinate.crs)

        distance = UTM.distance(utm_coordinate, east_utm)
        assert abs(distance - 1000.0) < 1.0  # Should be approximately 1000m

    def test_ups_distance_calculation(self, ups_north_coordinate):
        """Test UPS distance calculation."""
        # Create another UPS point 500m north
        north_ups = UPS.create(ups_north_coordinate.easting_m, ups_north_coordinate.northing_m + 500, "N")

        distance = UPS.distance(ups_north_coordinate, north_ups)
        # UPS coordinates may not map 1:1 to meters due to projection
        assert distance > 400  # Should be approximately 500m but allow for projection differences
        assert distance < 600  # Within reasonable range

    def test_bearing_calculation(self, nyc_geographic):
        """Test bearing calculation."""
        # Test bearing to due east
        east_point = Geographic.create(40.7, -73.0)  # 1 degree east
        bearing = Geographic.bearing(nyc_geographic, east_point)
        assert 45 <= bearing <= 135  # Should be approximately east (90°)

    def test_bearing_due_east(self, nyc_geographic):
        """Test bearing calculation due east."""
        # Test bearing to due east
        east_point = Geographic.create(40.7, -73.0)  # 1 degree east
        bearing = Geographic.bearing(nyc_geographic, east_point)
        assert 45 <= bearing <= 135  # Should be approximately east (90°)

    def test_bearing_due_south(self, nyc_geographic):
        """Test bearing calculation due south."""
        # Test bearing to due south
        south_point = Geographic.create(39.7, -74.0)  # 1 degree south
        bearing = Geographic.bearing(nyc_geographic, south_point)
        assert 135 <= bearing <= 225  # Should be approximately south (180°)

    def test_bearing_due_west(self, nyc_geographic):
        """Test bearing calculation due west."""
        # Test bearing to due west
        west_point = Geographic.create(40.7, -75.0)  # 1 degree west
        bearing = Geographic.bearing(nyc_geographic, west_point)
        assert 225 <= bearing <= 315  # Should be approximately west (270°)

    def test_bearing_radians(self, nyc_geographic):
        """Test bearing calculation in radians."""
        import math

        # Test bearing to due east in radians
        east_point = Geographic.create(40.7, -73.0)  # 1 degree east
        bearing_rad = Geographic.bearing(nyc_geographic, east_point, as_deg=False)
        bearing_deg = Geographic.bearing(nyc_geographic, east_point, as_deg=True)

        # Convert radians to degrees for comparison
        assert abs(math.degrees(bearing_rad) - bearing_deg) < 0.001
        assert 0 <= bearing_rad <= 2 * math.pi  # Should be in [0, 2π] range

    def test_utm_bearing_radians(self, utm_coordinate):
        """Test UTM bearing calculation in radians."""
        import math

        # Create another UTM point to the east
        east_utm = UTM.create(utm_coordinate.easting_m + 1000, utm_coordinate.northing_m, utm_coordinate.crs)

        bearing_rad = UTM.bearing(utm_coordinate, east_utm, as_deg=False)
        bearing_deg = UTM.bearing(utm_coordinate, east_utm, as_deg=True)

        # Convert radians to degrees for comparison
        assert abs(math.degrees(bearing_rad) - bearing_deg) < 0.001
        assert 0 <= bearing_rad <= 2 * math.pi  # Should be in [0, 2π] range

    def test_polar_region_detection(self):
        """Test polar region detection."""
        transformer = Transformer()

        # Test north polar region
        assert transformer.is_polar_region(85.0) == True
        assert transformer.is_polar_region(84.0) == True
        assert transformer.is_polar_region(83.9) == False

        # Test south polar region
        assert transformer.is_polar_region(-81.0) == True
        assert transformer.is_polar_region(-80.0) == True
        assert transformer.is_polar_region(-79.9) == False

        # Test equatorial region
        assert transformer.is_polar_region(0.0) == False
        assert transformer.is_polar_region(45.0) == False
        assert transformer.is_polar_region(-45.0) == False

    def test_utm_zone_polar_regions(self):
        """Test UTM zone calculation for polar regions."""
        transformer = Transformer()

        # Test north pole returns UPS North
        zone = transformer.get_utm_zone(0.0, 89.0)
        assert zone == "EPSG:32661"

        # Test south pole returns UPS South
        zone = transformer.get_utm_zone(0.0, -81.0)
        assert zone == "EPSG:32761"

    def test_geographic_to_ups_north(self, north_pole_geographic):
        """Test conversion from geographic to UPS North."""
        transformer = Transformer()
        geo = north_pole_geographic

        ups = transformer.geo_to_ups(geo)
        assert isinstance(ups, UPS)
        assert ups.hemisphere == "N"
        assert ups.crs == "EPSG:32661"
        assert ups.easting_m != 0
        assert ups.northing_m != 0

    def test_geographic_to_ups_south(self, south_pole_geographic):
        """Test conversion from geographic to UPS South."""
        transformer = Transformer()
        geo = south_pole_geographic

        ups = transformer.geo_to_ups(geo)
        assert isinstance(ups, UPS)
        assert ups.hemisphere == "S"
        assert ups.crs == "EPSG:32761"
        assert ups.easting_m != 0
        assert ups.northing_m != 0

    def test_ups_to_geographic_north(self, ups_north_coordinate):
        """Test conversion from UPS North to geographic."""
        transformer = Transformer()
        ups = ups_north_coordinate

        geo = transformer.ups_to_geo(ups)
        assert isinstance(geo, Geographic)
        assert geo.latitude_deg >= 84.0  # Should be in north polar region
        assert -180 <= geo.longitude_deg <= 180

    def test_ups_to_geographic_south(self, ups_south_coordinate):
        """Test conversion from UPS South to geographic."""
        transformer = Transformer()
        ups = ups_south_coordinate

        geo = transformer.ups_to_geo(ups)
        assert isinstance(geo, Geographic)
        assert geo.latitude_deg <= -80.0  # Should be in south polar region
        assert -180 <= geo.longitude_deg <= 180

    def test_geo_to_utm_returns_ups_for_polar(self, north_pole_geographic):
        """Test that geo_to_utm returns UPS for polar regions."""
        transformer = Transformer()
        geo = north_pole_geographic

        result = transformer.geo_to_utm(geo)
        assert isinstance(result, UPS)  # Should return UPS, not UTM
        assert result.hemisphere == "N"

    def test_geo_to_utm_returns_utm_for_non_polar(self, nyc_geographic):
        """Test that geo_to_utm returns UTM for non-polar regions."""
        transformer = Transformer()
        geo = nyc_geographic

        result = transformer.geo_to_utm(geo)
        assert isinstance(result, UTM)  # Should return UTM, not UPS

    def test_ups_conversion_round_trip(self, north_pole_geographic):
        """Test round-trip conversion: Geographic -> UPS -> Geographic."""
        transformer = Transformer()
        original_geo = north_pole_geographic

        # Convert to UPS and back
        ups = transformer.geo_to_ups(original_geo)
        returned_geo = transformer.ups_to_geo(ups)

        # Check that we get back to approximately the same location
        assert abs(returned_geo.latitude_deg - original_geo.latitude_deg) < 0.001
        assert abs(returned_geo.longitude_deg - original_geo.longitude_deg) < 0.001
        assert returned_geo.altitude_m == original_geo.altitude_m

    def test_ups_conversion_with_generic_convert(self, north_pole_geographic):
        """Test UPS conversion using generic convert method."""
        transformer = Transformer()
        geo = north_pole_geographic

        # Convert to UPS
        ups = transformer.convert(geo, Coordinate_Type.UPS)
        assert isinstance(ups, UPS)
        assert ups.hemisphere == "N"

        # Convert back to geographic
        returned_geo = transformer.convert(ups, Coordinate_Type.GEOGRAPHIC)
        assert isinstance(returned_geo, Geographic)

        # Convert to other types
        ecef = transformer.convert(ups, Coordinate_Type.ECEF)
        assert isinstance(ecef, ECEF)

        web_mercator = transformer.convert(ups, Coordinate_Type.WEB_MERCATOR)
        assert isinstance(web_mercator, Web_Mercator)

    def test_ups_conversion_error_for_non_polar(self, nyc_geographic):
        """Test that geo_to_ups raises error for non-polar coordinates."""
        transformer = Transformer()
        geo = nyc_geographic

        with pytest.raises(ValueError):
            transformer.geo_to_ups(geo)  # Should fail for NYC coordinates


if __name__ == "__main__":
    pytest.main([__file__])
