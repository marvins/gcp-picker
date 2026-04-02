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
#    File:    conftest.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Pytest configuration and fixtures for Pointy-McPointface tests.
"""

import pytest
from qtpy.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for GUI tests."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def qtbot(qapp):
    """Create QtBot for GUI testing."""
    from pytest_qt.qtbot import QtBot
    return QtBot(qapp)


@pytest.fixture
def sample_geographic_coordinates():
    """Sample geographic coordinates for testing."""
    return [
        (40.7128, -74.0060),  # New York City
        (34.0522, -118.2437),  # Los Angeles
        (51.5074, -0.1278),    # London
        (48.8566, 2.3522),     # Paris
        (35.6762, 139.6503),   # Tokyo
    ]


@pytest.fixture
def sample_pixel_coordinates():
    """Sample pixel coordinates for testing."""
    return [
        (100, 200),
        (256.5, 128.3),
        (512, 512),
        (1024, 768),
        (0, 0),
    ]


@pytest.fixture(autouse=True)
def mock_elevation_api():
    """Mock elevation API calls to avoid network dependencies."""
    from unittest.mock import patch

    # Mock elevation responses
    def mock_elevation(lat, lon):
        # Simple mock: return elevation based on latitude
        return max(0, lat * 100)  # Rough approximation

    # Patch the elevation function
    with patch('pointy.core.terrain.elevation', side_effect=mock_elevation):
        yield


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary directory for cache testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


# Test markers
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "gui: marks tests that require GUI"
    )
    config.addinivalue_line(
        "markers", "network: marks tests that require network access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add marks."""

    # Add GUI marker to tests that import Qt modules
    for item in items:
        if "qtpy" in str(item.fspath) or any("qt" in mark.name for mark in item.iter_markers()):
            item.add_marker(pytest.mark.gui)

        # Add network marker to tests that might make network calls
        if "terrain" in str(item.fspath) and "elevation" in str(item.fspath):
            item.add_marker(pytest.mark.network)
