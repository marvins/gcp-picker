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
#    File:    test_gcp_loading.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Unit tests for GCP loading and display workflow.

These tests verify that GCPs load correctly from file and that the processor
maintains the expected data structure (list, not dict) from get_gcps().
"""

#  Python Standard Libraries
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

#  Third-Party Libraries
import pytest

#  Project Libraries
from pointy.core.gcp_processor import GCP_Processor
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.proj import GCP


@pytest.fixture
def sample_gcp_json(tmp_path) -> Path:
    """Create a sample GCP JSON file for testing."""
    gcp_data = {
        "test_image_path": "/test/image.png",
        "reference_info": None,
        "gcps": [
            {
                "id": 1,
                "test_pixel": {"x_px": 100.0, "y_px": 200.0},
                "reference_pixel": {"x_px": 100.0, "y_px": 200.0},
                "geographic": {"latitude_deg": 35.3, "longitude_deg": -119.0, "altitude_m": 50.0},
                "projected": None,
                "error": None,
                "enabled": True
            },
            {
                "id": 2,
                "test_pixel": {"x_px": 500.0, "y_px": 600.0},
                "reference_pixel": {"x_px": 500.0, "y_px": 600.0},
                "geographic": {"latitude_deg": 35.4, "longitude_deg": -118.9, "altitude_m": 75.0},
                "projected": None,
                "error": None,
                "enabled": True
            }
        ]
    }
    gcp_file = tmp_path / "test_gcps.json"
    gcp_file.write_text(json.dumps(gcp_data))
    return gcp_file


@pytest.fixture
def processor() -> GCP_Processor:
    """Create a fresh GCP_Processor instance."""
    return GCP_Processor()


class Test_GCP_Processor_Loading:
    """Tests for GCP_Processor file loading behavior."""

    def test_load_gcps_from_json_returns_correct_count(self, processor, sample_gcp_json):
        """Verify the correct number of GCPs are loaded from a JSON file."""
        processor.load_gcps(str(sample_gcp_json))
        assert processor.gcp_count() == 2

    def test_load_gcps_get_gcps_returns_list(self, processor, sample_gcp_json):
        """Verify get_gcps() returns a list, not a dict or dict_values."""
        processor.load_gcps(str(sample_gcp_json))
        result = processor.get_gcps()

        assert isinstance(result, list), f"Expected list, got {type(result)}"

    def test_load_gcps_list_is_iterable_without_values_call(self, processor, sample_gcp_json):
        """Regression: Verify iterating over get_gcps() doesn't require .values()."""
        processor.load_gcps(str(sample_gcp_json))

        # This should not raise AttributeError
        count = 0
        for gcp in processor.get_gcps():
            assert isinstance(gcp, GCP)
            count += 1

        assert count == 2

    def test_load_gcps_preserves_gcp_ids(self, processor, sample_gcp_json):
        """Verify loaded GCPs have correct IDs."""
        processor.load_gcps(str(sample_gcp_json))
        gcps = processor.get_gcps()

        ids = {gcp.id for gcp in gcps}
        assert ids == {1, 2}

    def test_load_gcps_preserves_geographic_coordinates(self, processor, sample_gcp_json):
        """Verify loaded GCPs have correct geographic coordinates."""
        processor.load_gcps(str(sample_gcp_json))

        gcp1 = processor.get_gcp(1)
        assert gcp1 is not None
        assert abs(gcp1.geographic.latitude_deg - 35.3) < 1e-6
        assert abs(gcp1.geographic.longitude_deg - (-119.0)) < 1e-6

    def test_load_gcps_preserves_pixel_coordinates(self, processor, sample_gcp_json):
        """Verify loaded GCPs have correct pixel coordinates."""
        processor.load_gcps(str(sample_gcp_json))

        gcp1 = processor.get_gcp(1)
        assert gcp1 is not None
        assert abs(gcp1.test_pixel.x_px - 100.0) < 1e-6
        assert abs(gcp1.test_pixel.y_px - 200.0) < 1e-6

    def test_load_gcps_missing_file_raises(self, processor):
        """Verify FileNotFoundError raised for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            processor.load_gcps("/nonexistent/path/gcps.json")

    def test_load_gcps_increments_next_id(self, processor, sample_gcp_json):
        """Verify next_gcp_id is set beyond the max loaded ID."""
        processor.load_gcps(str(sample_gcp_json))
        assert processor.next_gcp_id == 3


class Test_GCP_Processor_Management:
    """Tests for GCP add/remove/clear operations."""

    def test_add_gcp_increments_count(self, processor):
        """Verify add_gcp increases the GCP count."""
        gcp = GCP(
            id=1,
            test_pixel=Pixel.create(10.0, 20.0),
            reference_pixel=Pixel.create(10.0, 20.0),
            geographic=Geographic.create(35.0, -119.0)
        )
        processor.add_gcp(gcp)
        assert processor.gcp_count() == 1

    def test_remove_gcp_decrements_count(self, processor):
        """Verify remove_gcp decreases the GCP count."""
        gcp = GCP(
            id=1,
            test_pixel=Pixel.create(10.0, 20.0),
            reference_pixel=Pixel.create(10.0, 20.0),
            geographic=Geographic.create(35.0, -119.0)
        )
        processor.add_gcp(gcp)
        processor.remove_gcp(1)
        assert processor.gcp_count() == 0

    def test_remove_nonexistent_gcp_is_safe(self, processor):
        """Verify removing a nonexistent GCP ID doesn't raise."""
        processor.remove_gcp(999)  # Should not raise

    def test_clear_gcps_resets_count_and_id(self, processor, sample_gcp_json):
        """Verify clear_gcps resets both count and next_gcp_id."""
        processor.load_gcps(str(sample_gcp_json))
        processor.clear_gcps()

        assert processor.gcp_count() == 0
        assert processor.next_gcp_id == 1

    def test_has_gcps_returns_false_when_empty(self, processor):
        """Verify has_gcps returns False for empty processor."""
        assert processor.has_gcps() is False

    def test_has_gcps_returns_true_after_add(self, processor):
        """Verify has_gcps returns True after adding a GCP."""
        gcp = GCP(
            id=1,
            test_pixel=Pixel.create(10.0, 20.0),
            reference_pixel=Pixel.create(10.0, 20.0),
            geographic=Geographic.create(35.0, -119.0)
        )
        processor.add_gcp(gcp)
        assert processor.has_gcps() is True
