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
#    File:    test_coordinate_comparisons.py
#    Author:  Marvin Smith
#    Date:    04/03/2026
#
"""
Integration tests comparing bearing and distance calculations across coordinate types.
"""

# Standard Library Imports
import math

# Third-Party Imports
import numpy as np
import pytest

# Project Imports
from pointy.core.coordinate import (
    Geographic,
    UTM,
    UPS,
    Web_Mercator,
    ECEF,
    Transformer,
)


class Test_Coordinate_Type_Comparisons:
    """Integration tests comparing bearing and distance across coordinate types."""

    @pytest.fixture
    def boston_geographic(self):
        """Boston geographic coordinate."""
        return Geographic.create(42.3601, -71.0589, 10.0)  # Boston, MA

    @pytest.fixture
    def nyc_geographic(self):
        """NYC geographic coordinate."""
        return Geographic.create(40.7128, -74.0060, 10.0)  # NYC, NY

    @pytest.fixture
    def london_geographic(self):
        """London geographic coordinate."""
        return Geographic.create(51.5074, -0.1278, 50.0)  # London, UK

    @pytest.fixture
    def miami_geographic(self):
        """Miami geographic coordinate."""
        return Geographic.create(25.7617, -80.1918, 5.0)  # Miami, FL

    def test_boston_to_nyc_comparison(self, boston_geographic, nyc_geographic):
        """Compare bearing and distance calculations from Boston to NYC."""
        transformer = Transformer()

        # Convert to different coordinate systems
        boston_utm = transformer.geo_to_utm(boston_geographic)
        nyc_utm = transformer.geo_to_utm(nyc_geographic)

        # Calculate bearing and distance in each system
        geo_bearing = Geographic.bearing(boston_geographic, nyc_geographic)
        geo_distance = Geographic.distance(boston_geographic, nyc_geographic)

        # UTM coordinates might be in different zones, so handle reprojection
        try:
            utm_bearing = UTM.bearing(boston_utm, nyc_utm)
            utm_distance = UTM.distance(boston_utm, nyc_utm)
            utm_reprojected = False
        except ValueError:
            # Reproject NYC to Boston's zone
            nyc_reprojected = transformer.geographic_to_projected(nyc_geographic, boston_utm.crs)
            utm_bearing = UTM.bearing(boston_utm, nyc_reprojected)
            utm_distance = UTM.distance(boston_utm, nyc_reprojected)
            utm_reprojected = True

        # Print results for comparison
        print(f"\nBoston to NYC Comparison:")
        print(f"Geographic: Bearing={geo_bearing:.2f}°, Distance={geo_distance/1000:.2f} km")
        print(f"UTM:        Bearing={utm_bearing:.2f}°, Distance={utm_distance/1000:.2f} km")
        if utm_reprojected:
            print(f"UTM:        Note: NYC reprojected to {boston_utm.crs}")

        # Bearings should be similar (within reasonable tolerance for different calculation methods)
        # Note: The actual bearing from Boston to NYC is approximately southwest (~225°)
        assert abs(geo_bearing - utm_bearing) < 15.0  # Within 15 degrees (allowing for projection differences)

        # Distances should be very similar (within 1% for short distances)
        distance_diff_ratio = abs(geo_distance - utm_distance) / geo_distance
        assert distance_diff_ratio < 0.01  # Within 1%

    def test_london_to_miami_comparison(self, london_geographic, miami_geographic):
        """Compare bearing and distance calculations from London to Miami (long distance)."""
        transformer = Transformer()

        # Convert to different coordinate systems
        london_utm = transformer.geo_to_utm(london_geographic)
        miami_utm = transformer.geo_to_utm(miami_geographic)
        london_wm = transformer.geo_to_web_mercator(london_geographic)
        miami_wm = transformer.geo_to_web_mercator(miami_geographic)

        # Calculate bearing and distance in each system
        geo_bearing = Geographic.bearing(london_geographic, miami_geographic)
        geo_distance = Geographic.distance(london_geographic, miami_geographic)

        wm_bearing = Web_Mercator.bearing(london_wm, miami_wm)
        wm_distance = Web_Mercator.distance(london_wm, miami_wm)

        # UTM coordinates are in different zones, so we can't calculate bearing/distance directly
        # This demonstrates the validation working correctly
        try:
            utm_bearing = UTM.bearing(london_utm, miami_utm)
            utm_distance = UTM.distance(london_utm, miami_utm)
            utm_validation_failed = False
        except ValueError as e:
            utm_bearing = None
            utm_distance = None
            utm_validation_failed = True
            print(f"UTM validation correctly failed: {e}")

        # Print results for comparison
        print(f"\nLondon to Miami Comparison:")
        print(f"Geographic:   Bearing={geo_bearing:.2f}°, Distance={geo_distance/1000:.2f} km")
        print(f"Web Mercator: Bearing={wm_bearing:.2f}°, Distance={wm_distance/1000:.2f} km")
        if utm_validation_failed:
            print(f"UTM:          Validation failed (different zones - expected for long distances)")
        else:
            print(f"UTM:          Bearing={utm_bearing:.2f}°, Distance={utm_distance/1000:.2f} km")

        # Geographic distance should be most accurate for long distances
        # Web Mercator distance will have significant distortion for such a long distance
        assert geo_distance > 7000000  # Should be > 7,000 km (actual ~7,100 km)

        # UTM validation should fail for cross-zone coordinates
        assert utm_validation_failed, "UTM validation should fail for coordinates in different zones"

    def test_cross_zone_utm_reprojection(self):
        """Test UTM calculations across zone boundaries with reprojection."""
        transformer = Transformer()

        # Choose locations that cross UTM zone boundary but are relatively close
        # Zone 18N/19N boundary is at -72° longitude
        # Let's pick points on either side of this boundary
        point1_geo = Geographic.create(40.0, -71.5, 10.0)  # Just east of boundary (Zone 18N)
        point2_geo = Geographic.create(40.0, -72.5, 10.0)  # Just west of boundary (Zone 19N)

        # Convert to UTM (will be in different zones)
        point1_utm = transformer.geo_to_utm(point1_geo)  # Zone 18N
        point2_utm = transformer.geo_to_utm(point2_geo)  # Zone 19N

        print(f"\nCross-Zone UTM Reprojection Test:")
        print(f"Point 1: {point1_geo} -> {point1_utm.crs}")
        print(f"Point 2: {point2_geo} -> {point2_utm.crs}")

        # Direct calculation should fail
        try:
            direct_distance = UTM.distance(point1_utm, point2_utm)
            direct_validation_failed = False
        except ValueError as e:
            direct_distance = None
            direct_validation_failed = True
            print(f"Direct UTM calculation correctly failed: {e}")

        # Reproject point2 to point1's zone
        point2_reprojected = transformer.geographic_to_projected(point2_geo, point1_utm.crs)

        print(f"Point 2 reprojected to {point1_utm.crs}: {point2_reprojected}")

        # Now calculation should work
        reprojected_distance = UTM.distance(point1_utm, point2_reprojected)
        reprojected_bearing = UTM.bearing(point1_utm, point2_reprojected)

        # Compare with geographic calculation
        geo_distance = Geographic.distance(point1_geo, point2_geo)
        geo_bearing = Geographic.bearing(point1_geo, point2_geo)

        print(f"Geographic: Distance={geo_distance:.1f}m, Bearing={geo_bearing:.1f}°")
        print(f"UTM (reprojected): Distance={reprojected_distance:.1f}m, Bearing={reprojected_bearing:.1f}°")

        # Calculate differences
        distance_error = abs(reprojected_distance - geo_distance)
        bearing_error = abs(reprojected_bearing - geo_bearing)

        print(f"Distance error: {distance_error:.1f}m ({distance_error/geo_distance*100:.2f}%)")
        print(f"Bearing error: {bearing_error:.1f}°")

        # Validation checks
        assert direct_validation_failed, "Direct UTM calculation should fail"
        assert reprojected_distance > 0, "Reprojected distance should be positive"
        assert 0 <= reprojected_bearing < 360, "Reprojected bearing should be valid"

        # Error should be reasonable for nearby points (within a few percent)
        assert distance_error / geo_distance < 0.05, f"Distance error too large: {distance_error/geo_distance*100:.2f}%"

        # Bearing error should be reasonable (within a few degrees for nearby points)
        # Note: Bearing might wrap around 360°, so handle that
        bearing_diff = min(bearing_error, 360 - bearing_error)
        assert bearing_diff < 10, f"Bearing error too large: {bearing_diff:.1f}°"

    def test_cross_system_distance_accuracy(self, london_geographic, miami_geographic):
        """Test distance accuracy across different coordinate systems."""
        transformer = Transformer()

        # Geographic distance (most accurate)
        geo_distance = Geographic.distance(london_geographic, miami_geographic)

        # Convert to different systems
        london_utm = transformer.geo_to_utm(london_geographic)
        miami_utm = transformer.geo_to_utm(miami_geographic)
        london_wm = transformer.geo_to_web_mercator(london_geographic)
        miami_wm = transformer.geo_to_web_mercator(miami_geographic)
        london_ecef = transformer.geo_to_ecef(london_geographic)
        miami_ecef = transformer.geo_to_ecef(miami_geographic)

        # Calculate distances in each system
        wm_distance = Web_Mercator.distance(london_wm, miami_wm)
        ecef_distance = ECEF.distance(london_ecef, miami_ecef)

        # UTM coordinates are in different zones, so distance calculation should fail
        try:
            utm_distance = UTM.distance(london_utm, miami_utm)
            utm_validation_failed = False
        except ValueError as e:
            utm_distance = None
            utm_validation_failed = True
            print(f"UTM distance validation correctly failed: {e}")

        print(f"\nCross-System Distance Accuracy (London to Miami):")
        print(f"Geographic (Haversine): {geo_distance/1000:.2f} km")
        if utm_validation_failed:
            print(f"UTM:                    Validation failed (different zones - expected)")
        else:
            print(f"UTM:                    {utm_distance/1000:.2f} km")
        print(f"Web Mercator:           {wm_distance/1000:.2f} km")
        print(f"ECEF:                   {ecef_distance/1000:.2f} km")

        # Geographic should be most accurate
        # ECEF should be very close to geographic but may have some conversion differences
        # Web Mercator will have the most distortion
        assert abs(ecef_distance - geo_distance) / geo_distance < 0.05  # ECEF within 5%

        # UTM validation should fail for cross-zone coordinates
        assert utm_validation_failed, "UTM validation should fail for coordinates in different zones"

    def test_polar_region_comparison(self):
        """Compare bearing and distance in polar regions using UPS."""
        transformer = Transformer()

        # Create polar coordinates
        north_pole = Geographic.create(89.5, 0.0, 100.0)
        south_pole = Geographic.create(-89.5, 0.0, 100.0)

        # Convert to UPS
        north_ups = transformer.geo_to_ups(north_pole)
        south_ups = transformer.geo_to_ups(south_pole)

        # Create points slightly offset for bearing calculation
        north_offset = Geographic.create(89.0, 10.0, 100.0)  # 10° longitude offset
        south_offset = Geographic.create(-89.0, 10.0, 100.0)  # 10° longitude offset

        north_ups_offset = transformer.geo_to_ups(north_offset)
        south_ups_offset = transformer.geo_to_ups(south_offset)

        # Calculate in both systems
        geo_bearing_north = Geographic.bearing(north_pole, north_offset)
        geo_distance_north = Geographic.distance(north_pole, north_offset)

        ups_bearing_north = UPS.bearing(north_ups, north_ups_offset)
        ups_distance_north = UPS.distance(north_ups, north_ups_offset)

        geo_bearing_south = Geographic.bearing(south_pole, south_offset)
        geo_distance_south = Geographic.distance(south_pole, south_offset)

        ups_bearing_south = UPS.bearing(south_ups, south_ups_offset)
        ups_distance_south = UPS.distance(south_ups, south_ups_offset)

        # Print results for comparison
        print(f"\nPolar Region Comparison:")
        print(f"North Pole - Geographic: Bearing={geo_bearing_north:.2f}°, Distance={geo_distance_north/1000:.2f} km")
        print(f"North Pole - UPS:        Bearing={ups_bearing_north:.2f}°, Distance={ups_distance_north/1000:.2f} km")
        print(f"South Pole - Geographic: Bearing={geo_bearing_south:.2f}°, Distance={geo_distance_south/1000:.2f} km")
        print(f"South Pole - UPS:        Bearing={ups_bearing_south:.2f}°, Distance={ups_distance_south/1000:.2f} km")

        # Distances should be similar in polar regions
        assert abs(geo_distance_north - ups_distance_north) / geo_distance_north < 0.05  # Within 5%
        assert abs(geo_distance_south - ups_distance_south) / geo_distance_south < 0.05  # Within 5%

    def test_coordinate_system_consistency(self, nyc_geographic):
        """Test that conversions are consistent across coordinate systems."""
        transformer = Transformer()

        # Convert NYC to different systems and back
        nyc_utm = transformer.geo_to_utm(nyc_geographic)
        nyc_wm = transformer.geo_to_web_mercator(nyc_geographic)
        nyc_ecef = transformer.geo_to_ecef(nyc_geographic)

        # Convert back to geographic
        nyc_from_utm = transformer.utm_to_geo(nyc_utm)
        nyc_from_wm = transformer.web_mercator_to_geo(nyc_wm)
        nyc_from_ecef = transformer.ecef_to_geo(nyc_ecef)

        # All should be very close to original
        assert abs(nyc_from_utm.latitude_deg - nyc_geographic.latitude_deg) < 0.001
        assert abs(nyc_from_utm.longitude_deg - nyc_geographic.longitude_deg) < 0.001
        assert abs(nyc_from_wm.latitude_deg - nyc_geographic.latitude_deg) < 0.001
        assert abs(nyc_from_wm.longitude_deg - nyc_geographic.longitude_deg) < 0.001
        assert abs(nyc_from_ecef.latitude_deg - nyc_geographic.latitude_deg) < 0.001
        assert abs(nyc_from_ecef.longitude_deg - nyc_geographic.longitude_deg) < 0.001

    def test_bearing_radians_consistency(self, boston_geographic, nyc_geographic):
        """Test that bearing calculations are consistent in radians and degrees."""
        # Geographic
        geo_bearing_deg = Geographic.bearing(boston_geographic, nyc_geographic, as_deg=True)
        geo_bearing_rad = Geographic.bearing(boston_geographic, nyc_geographic, as_deg=False)

        # Convert between units for comparison
        geo_bearing_from_rad = np.degrees(geo_bearing_rad)

        assert abs(geo_bearing_deg - geo_bearing_from_rad) < 0.001

        # UTM - handle cross-zone reprojection
        transformer = Transformer()
        boston_utm = transformer.geo_to_utm(boston_geographic)
        nyc_utm = transformer.geo_to_utm(nyc_geographic)

        try:
            utm_bearing_deg = UTM.bearing(boston_utm, nyc_utm, as_deg=True)
            utm_bearing_rad = UTM.bearing(boston_utm, nyc_utm, as_deg=False)
            utm_reprojected = False
        except ValueError:
            # Reproject NYC to Boston's zone
            nyc_reprojected = transformer.geographic_to_projected(nyc_geographic, boston_utm.crs)
            utm_bearing_deg = UTM.bearing(boston_utm, nyc_reprojected, as_deg=True)
            utm_bearing_rad = UTM.bearing(boston_utm, nyc_reprojected, as_deg=False)
            utm_reprojected = True

        utm_bearing_from_rad = np.degrees(utm_bearing_rad)

        assert abs(utm_bearing_deg - utm_bearing_from_rad) < 0.001

    def test_epsg_system_integration(self, boston_geographic, nyc_geographic):
        """Test EPSG code integration across coordinate systems."""
        transformer = Transformer()

        # Test that all coordinates have valid EPSG codes
        assert boston_geographic.to_epsg() == 4326
        assert nyc_geographic.to_epsg() == 4326

        # Convert to UTM and check EPSG
        boston_utm = transformer.geo_to_utm(boston_geographic)
        nyc_utm = transformer.geo_to_utm(nyc_geographic)

        # Check what zones they're actually in
        print(f"Boston UTM zone: {boston_utm.crs}")
        print(f"NYC UTM zone: {nyc_utm.crs}")

        # They might be in different zones, which is fine
        # Just test that they have valid EPSG codes
        assert boston_utm.to_epsg() in [32618, 32619]  # Should be in zone 18N or 19N
        assert nyc_utm.to_epsg() in [32618, 32619]    # Should be in zone 18N or 19N

        # Test EPSG info retrieval for Boston's zone
        epsg_info = transformer.get_epsg_info(boston_utm.to_epsg())
        assert epsg_info['code'] == boston_utm.to_epsg()
        assert epsg_info['coordinate_type'].value == 'utm'
        assert 'UTM Zone' in epsg_info['description']

    def test_cross_system_distance_accuracy(self, london_geographic, miami_geographic):
        """Test distance accuracy across different coordinate systems."""
        transformer = Transformer()

        # Geographic distance (most accurate)
        geo_distance = Geographic.distance(london_geographic, miami_geographic)

        # Convert to different systems
        london_utm = transformer.geo_to_utm(london_geographic)
        miami_utm = transformer.geo_to_utm(miami_geographic)
        london_wm = transformer.geo_to_web_mercator(london_geographic)
        miami_wm = transformer.geo_to_web_mercator(miami_geographic)
        london_ecef = transformer.geo_to_ecef(london_geographic)
        miami_ecef = transformer.geo_to_ecef(miami_geographic)

        # Calculate distances in each system
        wm_distance = Web_Mercator.distance(london_wm, miami_wm)
        ecef_distance = ECEF.distance(london_ecef, miami_ecef)

        # UTM coordinates are in different zones, so distance calculation should fail
        try:
            utm_distance = UTM.distance(london_utm, miami_utm)
            utm_validation_failed = False
        except ValueError as e:
            utm_distance = None
            utm_validation_failed = True
            print(f"UTM distance validation correctly failed: {e}")

        print(f"\nCross-System Distance Accuracy (London to Miami):")
        print(f"Geographic (Haversine): {geo_distance/1000:.2f} km")
        if utm_validation_failed:
            print(f"UTM:                    Validation failed (different zones - expected)")
        else:
            print(f"UTM:                    {utm_distance/1000:.2f} km")
        print(f"Web Mercator:           {wm_distance/1000:.2f} km")
        print(f"ECEF:                   {ecef_distance/1000:.2f} km")

        # Geographic should be most accurate
        # ECEF should be very close to geographic but may have some conversion differences
        # Web Mercator will have the most distortion
        assert abs(ecef_distance - geo_distance) / geo_distance < 0.05  # ECEF within 5%

        # UTM validation should fail for cross-zone coordinates
        assert utm_validation_failed, "UTM validation should fail for coordinates in different zones"


if __name__ == "__main__":
    pytest.main([__file__])
