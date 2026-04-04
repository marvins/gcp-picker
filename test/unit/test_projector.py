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
#    File:    test_projector.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Unit tests for Projector API
"""

import pytest
import numpy as np

from pointy.core.coordinate import Geographic, Pixel
from pointy.core.projector import Identity_Projection, Affine_Projection, Transformation_Type


class TestIdentity_Projection:
    """Test the identity projection implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.projector = Identity_Projection()

    def test_transformation_type(self):
        """Test transformation type property."""
        assert self.projector.transformation_type == Transformation_Type.IDENTITY

    def test_is_identity(self):
        """Test is_identity property."""
        assert self.projector.is_identity is True

    def test_source_to_geographic(self):
        """Test source to geographic transformation."""
        pixel = Pixel(x_px=35.0, y_px=-118.0)  # Valid lat/lon ranges
        geo = self.projector.source_to_geographic(pixel)

        assert geo.latitude_deg == 35.0
        assert geo.longitude_deg == -118.0
        assert geo.altitude_m is None

    def test_geographic_to_source(self):
        """Test geographic to source transformation."""
        geo = Geographic(latitude_deg=35.0, longitude_deg=-118.0)  # Valid ranges
        pixel = self.projector.geographic_to_source(geo)

        assert pixel.x_px == 35.0
        assert pixel.y_px == -118.0

    def test_destination_to_geographic(self):
        """Test destination to geographic transformation."""
        pixel = Pixel(x_px=34.5, y_px=-117.5)  # Valid lat/lon ranges
        geo = self.projector.destination_to_geographic(pixel)

        assert geo.latitude_deg == 34.5
        assert geo.longitude_deg == -117.5

    def test_geographic_to_destination(self):
        """Test geographic to destination transformation."""
        geo = Geographic(latitude_deg=34.5, longitude_deg=-117.5)  # Valid ranges
        pixel = self.projector.geographic_to_destination(geo)

        assert pixel.x_px == 34.5
        assert pixel.y_px == -117.5

    def test_roundtrip_source(self):
        """Test roundtrip transformation for source coordinates."""
        original_pixel = Pixel(x_px=35.123, y_px=-118.456)  # Valid ranges
        geo = self.projector.source_to_geographic(original_pixel)
        result_pixel = self.projector.geographic_to_source(geo)

        assert result_pixel.x_px == original_pixel.x_px
        assert result_pixel.y_px == original_pixel.y_px

    def test_roundtrip_destination(self):
        """Test roundtrip transformation for destination coordinates."""
        original_pixel = Pixel(x_px=34.987, y_px=-117.654)  # Valid ranges
        geo = self.projector.destination_to_geographic(original_pixel)
        result_pixel = self.projector.geographic_to_destination(geo)

        assert result_pixel.x_px == original_pixel.x_px
        assert result_pixel.y_px == original_pixel.y_px

    def test_update_model(self):
        """Test update_model method (no-op for identity)."""
        # Should not raise any exceptions
        self.projector.update_model(any_param="value")

    def test_image_attributes(self):
        """Test image attribute methods."""
        # Test setting and getting source attributes
        self.projector.set_source_image_attributes(width=1000, height=800)
        attrs = self.projector.source_image_attributes
        assert attrs["width"] == 1000
        assert attrs["height"] == 800

        # Test setting and getting destination attributes
        self.projector.set_destination_image_attributes(width=500, height=400)
        attrs = self.projector.destination_image_attributes
        assert attrs["width"] == 500
        assert attrs["height"] == 400


class TestAffine_Projection:
    """Test the affine projection implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.projector = Affine_Projection()
        # Simple translation matrix: x' = x + 0.01, y' = y - 0.01 (small geographic offset)
        self.translation_matrix = [
            [1.0, 0.0, 0.01],
            [0.0, 1.0, -0.01],
            [0.0, 0.0, 1.0]
        ]
        # Simple scaling matrix: x' = 1.1*x, y' = 0.9*y (small scaling)
        self.scaling_matrix = [
            [1.1, 0.0, 0.0],
            [0.0, 0.9, 0.0],
            [0.0, 0.0, 1.0]
        ]

    def test_transformation_type(self):
        """Test transformation type property."""
        assert self.projector.transformation_type == Transformation_Type.AFFINE

    def test_is_identity(self):
        """Test is_identity property."""
        assert self.projector.is_identity is False

    def test_update_model(self):
        """Test updating the transformation model."""
        self.projector.update_model(self.translation_matrix)
        assert self.projector._transform_matrix == self.translation_matrix
        assert self.projector._inverse_matrix is not None

    def test_uninitialized_model_raises_error(self):
        """Test that uninitialized model raises appropriate errors."""
        with pytest.raises(ValueError, match="Affine model not initialized"):
            self.projector.source_to_geographic(Pixel(x_px=0, y_px=0))

    def test_translation_transformation(self):
        """Test simple translation transformation."""
        self.projector.update_model(self.translation_matrix)

        # Test source to geographic - use valid coordinate ranges
        pixel = Pixel(x_px=35.0, y_px=-118.0)
        geo = self.projector.source_to_geographic(pixel)

        assert geo.latitude_deg == 35.01  # 35 + 0.01
        assert geo.longitude_deg == -118.01  # -118 + (-0.01)

        # Test inverse transformation
        result_pixel = self.projector.geographic_to_source(geo)
        assert result_pixel.x_px == 35.0
        assert result_pixel.y_px == -118.0

    def test_scaling_transformation(self):
        """Test simple scaling transformation."""
        self.projector.update_model(self.scaling_matrix)

        # Test source to geographic - use small coordinates to stay in range
        pixel = Pixel(x_px=30.0, y_px=-100.0)
        geo = self.projector.source_to_geographic(pixel)

        assert geo.latitude_deg == 33.0  # 30 * 1.1
        assert geo.longitude_deg == -90.0  # -100 * 0.9

        # Test inverse transformation
        result_pixel = self.projector.geographic_to_source(geo)
        assert result_pixel.x_px == 30.0
        assert result_pixel.y_px == -100.0

    def test_complex_transformation(self):
        """Test complex transformation with rotation and scaling."""
        # Small 15-degree rotation + scaling to stay in range
        cos_15 = np.cos(np.pi / 12)  # 15 degrees
        sin_15 = np.sin(np.pi / 12)
        rotation_matrix = [
            [1.1 * cos_15, -1.1 * sin_15, 0.5],   # Small translation
            [0.9 * sin_15, 0.9 * cos_15, -0.3],  # Small translation
            [0.0, 0.0, 1.0]
        ]

        self.projector.update_model(rotation_matrix)

        # Test roundtrip transformation with small coordinates
        original_pixel = Pixel(x_px=35.0, y_px=-118.0)
        geo = self.projector.source_to_geographic(original_pixel)
        result_pixel = self.projector.geographic_to_source(geo)

        # Should be very close to original (allowing for floating point error)
        assert abs(result_pixel.x_px - original_pixel.x_px) < 1e-10
        assert abs(result_pixel.y_px - original_pixel.y_px) < 1e-10

    def test_singular_matrix_raises_error(self):
        """Test that singular matrix raises appropriate error."""
        singular_matrix = [
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],  # This makes the matrix singular
            [0.0, 0.0, 1.0]
        ]

        with pytest.raises(ValueError, match="Singular affine transformation matrix"):
            self.projector.update_model(singular_matrix)

    def test_destination_transformation(self):
        """Test that destination transformations work the same as source."""
        self.projector.update_model(self.translation_matrix)

        pixel = Pixel(x_px=50.0, y_px=75.0)
        geo = self.projector.destination_to_geographic(pixel)
        result_pixel = self.projector.geographic_to_destination(geo)

        assert result_pixel.x_px == 50.0
        assert result_pixel.y_px == 75.0

    def test_roundtrip_precision(self):
        """Test roundtrip transformation precision."""
        self.projector.update_model(self.scaling_matrix)

        # Test multiple roundtrips with small coordinates
        original_pixel = Pixel(x_px=35.123, y_px=-118.456)

        for _ in range(10):
            geo = self.projector.source_to_geographic(original_pixel)
            original_pixel = self.projector.geographic_to_source(geo)

        # Should maintain precision
        assert abs(original_pixel.x_px - 35.123) < 1e-10
        assert abs(original_pixel.y_px - (-118.456)) < 1e-10
