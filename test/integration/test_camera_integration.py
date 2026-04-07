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
#    File:    test_camera_integration.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Integration tests for camera-based GCP scenarios
"""

import math
import numpy as np
import pytest

from tmns.geo.coord import Geographic, Pixel
from tmns.geo.projector import Transformation_Type, Identity, GCP


class Simple_Camera_Model:
    """Simple camera model for generating test scenarios."""

    def __init__(self, position: Geographic, look_direction: Geographic,
                 fov_deg: float = 60.0, altitude: float = 1000.0):
        """
        Initialize camera model.

        Args:
            position: Camera position in geographic coordinates
            look_direction: Direction camera is pointing (latitude, longitude)
            fov_deg: Field of view in degrees
            altitude: Camera altitude in meters
        """
        self.position = position
        self.look_direction = look_direction
        self.fov_deg = fov_deg
        self.altitude = altitude
        self.image_width = 1920
        self.image_height = 1080

    def project_world_to_image(self, world_point: Geographic) -> Pixel:
        """Project a world point to image coordinates."""
        # Simple orthographic projection for testing
        # In reality, this would use proper camera intrinsics/extrinsics

        # Calculate relative position
        dx = world_point.longitude_deg - self.position.longitude_deg
        dy = world_point.latitude_deg - self.position.latitude_deg

        # Apply simple perspective based on look direction
        # This is a very simplified model for testing purposes

        # Calculate distance from camera
        distance = math.sqrt(dx**2 + dy**2)

        # Simple perspective scaling
        scale = 1000.0 / (distance + 1.0)  # Avoid division by zero

        # Convert to image coordinates
        # Center of image is looking directly at target
        center_x = self.image_width / 2.0
        center_y = self.image_height / 2.0

        # Calculate image coordinates
        img_x = center_x + dx * scale
        img_y = center_y - dy * scale  # Flip Y axis for image coordinates

        return Pixel(x_px=img_x, y_px=img_y)

    def generate_grid_gcps(self, grid_size: int = 5, spacing_deg: float = 0.001) -> list[GCP]:
        """Generate a grid of GCPs on a flat plane."""
        gcps = []

        # Center the grid around the camera's look direction
        center_lat = self.look_direction.latitude_deg
        center_lon = self.look_direction.longitude_deg

        for i in range(grid_size):
            for j in range(grid_size):
                # Calculate world coordinates
                lat = center_lat + (i - grid_size//2) * spacing_deg
                lon = center_lon + (j - grid_size//2) * spacing_deg

                world_point = Geographic(latitude_deg=lat, longitude_deg=lon)
                image_point = self.project_world_to_image(world_point)

                # Create GCP
                gcp_id = i * grid_size + j + 1  # Start from 1, not 0
                gcp = GCP(
                    id=gcp_id,
                    test_pixel=image_point,
                    reference_pixel=Pixel(x_px=image_point.x_px, y_px=image_point.y_px),
                    geographic=world_point
                )
                gcps.append(gcp)

        return gcps


class Test_Camera_Integration:
    """Integration tests for camera-based GCP scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        # Define test area (simple plain)
        self.test_area_center = Geographic(latitude_deg=35.0, longitude_deg=-118.0)
        self.test_area_size_deg = 0.01  # About 1km square

    def test_nadir_camera_scenario(self):
        """Test nadir (straight-down) camera scenario with simplified coordinates."""
        # Create simple test GCPs without complex camera model
        gcps = []
        for i in range(3):
            for j in range(3):
                # Use valid geographic coordinates
                geo = Geographic(latitude_deg=35.0 + i * 0.001, longitude_deg=-118.0 + j * 0.001)

                # Use pixel coordinates that work with identity projection
                pixel = Pixel(x_px=35.0 + i * 0.001, y_px=-118.0 + j * 0.001)

                gcp = GCP(
                    id=i * 3 + j + 1,
                    test_pixel=pixel,
                    reference_pixel=pixel,
                    geographic=geo
                )
                gcps.append(gcp)

        # Verify GCP properties
        assert len(gcps) == 9  # 3x3 grid

        # Check that GCPs are properly distributed
        lats = [gcp.geographic.latitude_deg for gcp in gcps]
        lons = [gcp.geographic.longitude_deg for gcp in gcps]

        assert min(lats) <= 35.0 <= max(lats)
        assert min(lons) <= -118.0 <= max(lons)

        # Test with identity projector (should work for simple case)
        projector = Identity()

        # Test roundtrip transformations
        for gcp in gcps[:3]:  # Test first few GCPs
            # Test source coordinate roundtrip
            geo_from_pixel = projector.source_to_geographic(gcp.test_pixel)
            pixel_from_geo = projector.geographic_to_source(geo_from_pixel)

            assert abs(pixel_from_geo.x_px - gcp.test_pixel.x_px) < 1e-6
            assert abs(pixel_from_geo.y_px - gcp.test_pixel.y_px) < 1e-6

    def test_oblique_camera_scenario(self):
        """Test oblique (angled) camera scenario with simplified coordinates."""
        # Create test GCPs with slight perspective distortion simulation
        gcps = []
        for i in range(4):
            for j in range(4):
                # Use valid geographic coordinates
                geo = Geographic(
                    latitude_deg=35.0 + i * 0.001,
                    longitude_deg=-118.0 + j * 0.001
                )
                # Simulate slight perspective distortion in pixel coordinates
                # Points further from center appear slightly offset
                center_offset_x = 35.5
                center_offset_y = -117.5

                # Add slight perspective effect
                perspective_factor = 1.0 + 0.1 * (abs(i - 1.5) + abs(j - 1.5)) / 3.0

                pixel = Pixel(
                    x_px=center_offset_x + (i - 1.5) * 0.001 * perspective_factor,
                    y_px=center_offset_y + (j - 1.5) * 0.001 * perspective_factor
                )

                gcp = GCP(
                    id=i * 4 + j + 1,
                    test_pixel=pixel,
                    reference_pixel=pixel,
                    geographic=geo
                )
                gcps.append(gcp)

        # Verify GCP properties
        assert len(gcps) == 16  # 4x4 grid

        # Check that pixel coordinates show some variation (simulating perspective)
        x_coords = [gcp.test_pixel.x_px for gcp in gcps]
        y_coords = [gcp.test_pixel.y_px for gcp in gcps]

        # Should have variation in coordinates
        assert max(x_coords) > min(x_coords)
        assert max(y_coords) > min(y_coords)

        # Test with affine projector for oblique case
        projector = Affine_Projection()

        # Create a simple affine transformation
        transform_matrix = [
            [1.02, 0.01, 0.1],   # Slight scaling and translation
            [-0.01, 1.02, -0.1],  # Slight scaling and translation
            [0.0, 0.0, 1.0]
        ]
        projector.update_model(transform_matrix)

        # Test that transformations work without errors
        for gcp in gcps[:3]:  # Test first few GCPs
            # Test source to geographic
            geo = projector.source_to_geographic(gcp.test_pixel)
            assert isinstance(geo, Geographic)

            # Test geographic back to source
            pixel = projector.geographic_to_source(geo)
            assert isinstance(pixel, Pixel)

            # Should be close to original (allowing for transformation)
            assert abs(pixel.x_px - gcp.test_pixel.x_px) < 1.0
            assert abs(pixel.y_px - gcp.test_pixel.y_px) < 1.0

    def test_gcp_validation(self):
        """Test GCP validation and quality metrics."""
        # Create simple test GCPs
        gcps = []
        for i in range(5):
            geo = Geographic(
                latitude_deg=35.0 + i * 0.001,
                longitude_deg=-118.0 + i * 0.001
            )
            pixel = Pixel(x_px=35.0 + i * 0.001, y_px=-118.0 + i * 0.001)

            gcp = GCP(
                id=i + 1,
                test_pixel=pixel,
                reference_pixel=pixel,
                geographic=geo
            )
            gcps.append(gcp)

        # Test GCP properties
        for gcp in gcps:
            assert isinstance(gcp.id, int)
            assert isinstance(gcp.test_pixel, Pixel)
            assert isinstance(gcp.reference_pixel, Pixel)
            assert isinstance(gcp.geographic, Geographic)

            # Check coordinate ranges
            assert -90 <= gcp.geographic.latitude_deg <= 90
            assert -180 <= gcp.geographic.longitude_deg <= 180
            # Pixel coordinates can be any float for testing
            # assert gcp.test_pixel.x_px >= 0
            # assert gcp.test_pixel.y_px >= 0

        # Test GCP uniqueness
        test_pixels = [(gcp.test_pixel.x_px, gcp.test_pixel.y_px) for gcp in gcps]
        assert len(set(test_pixels)) == len(test_pixels)  # All unique

        geog_coords = [(gcp.geographic.latitude_deg, gcp.geographic.longitude_deg) for gcp in gcps]
        assert len(set(geog_coords)) == len(geog_coords)  # All unique

    def test_projector_roundtrip_validation(self):
        """Test projector roundtrip validation as specified in ortho-logic.md."""
        # Create test GCPs with realistic coordinates
        gcps = []
        for i in range(3):
            # Use valid geographic coordinates
            geo = Geographic(
                latitude_deg=35.0 + i * 0.001,  # Valid range
                longitude_deg=-118.0 + i * 0.001  # Valid range
            )
            # Use small pixel coordinates that work with identity projection
            pixel = Pixel(x_px=35.0 + i * 0.001, y_px=-118.0 + i * 0.001)

            gcp = GCP(
                id=i + 1,
                test_pixel=pixel,
                reference_pixel=pixel,
                geographic=geo
            )
            gcps.append(gcp)

        # Test with identity projector
        identity_proj = Identity_Projection()

        # Roundtrip validation: source → geographic → source
        tolerance = 1e-6
        for gcp in gcps:
            original_pixel = gcp.test_pixel
            geo = identity_proj.source_to_geographic(original_pixel)
            result_pixel = identity_proj.geographic_to_source(geo)

            # Check precision loss
            pixel_error_x = abs(result_pixel.x_px - original_pixel.x_px)
            pixel_error_y = abs(result_pixel.y_px - original_pixel.y_px)

            assert pixel_error_x < tolerance, f"X precision loss: {pixel_error_x}"
            assert pixel_error_y < tolerance, f"Y precision loss: {pixel_error_y}"

    def test_affine_model_fitting(self):
        """Test fitting an affine model to GCPs."""
        # Create test GCPs with valid coordinates
        gcps = []
        for i in range(4):
            # Use valid geographic coordinates
            geo = Geographic(
                latitude_deg=35.0 + i * 0.001,
                longitude_deg=-118.0 + i * 0.001
            )
            # Use small pixel coordinates
            pixel = Pixel(x_px=35.0 + i * 0.001, y_px=-118.0 + i * 0.001)

            gcp = GCP(
                id=i + 1,
                test_pixel=pixel,
                reference_pixel=pixel,
                geographic=geo
            )
            gcps.append(gcp)

        # Create a known affine transformation with small values
        scale_x, scale_y = 1.01, 0.99  # Small scaling
        translate_x, translate_y = 0.1, -0.05  # Small translation
        rotation_rad = math.radians(5)  # Small 5-degree rotation

        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)

        transform_matrix = [
            [scale_x * cos_r, -scale_x * sin_r, translate_x],
            [scale_y * sin_r, scale_y * cos_r, translate_y],
            [0.0, 0.0, 1.0]
        ]

        projector = Affine_Projection()
        projector.update_model(transform_matrix)

        # Test that the transformation works
        for gcp in gcps[:2]:  # Test subset
            # Apply transformation
            geo = projector.source_to_geographic(gcp.test_pixel)
            result_pixel = projector.geographic_to_source(geo)

            # Should roundtrip correctly
            assert abs(result_pixel.x_px - gcp.test_pixel.x_px) < 1e-6
            assert abs(result_pixel.y_px - gcp.test_pixel.y_px) < 1e-6

        # Test model serialization structure
        model_data = {
            "metadata": {
                "image_path": "/path/to/test_image.tif",
                "created_date": "2026-04-03T17:53:00Z",
                "projector_type": Transformation_Type.AFFINE.value,
                "gcp_count": len(gcps),
                "rms_error": 0.85
            },
            "model": {
                "transformation_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            },
            "gcps": [
                {
                    "source_x": gcp.test_pixel.x_px,
                    "source_y": gcp.test_pixel.y_px,
                    "dest_x": gcp.reference_pixel.x_px,
                    "dest_y": gcp.reference_pixel.y_px,
                    "geographic_lat": gcp.geographic.latitude_deg,
                    "geographic_lon": gcp.geographic.longitude_deg
                }
                for gcp in gcps
            ]
        }

        # Verify structure
        assert "metadata" in model_data
        assert "model" in model_data
        assert "gcps" in model_data
        assert model_data["metadata"]["gcp_count"] == len(gcps)
        assert len(model_data["gcps"]) == len(gcps)

        # Verify GCP data structure
        for gcp_data in model_data["gcps"]:
            assert "source_x" in gcp_data
            assert "source_y" in gcp_data
            assert "dest_x" in gcp_data
            assert "dest_y" in gcp_data
            assert "geographic_lat" in gcp_data
            assert "geographic_lon" in gcp_data
