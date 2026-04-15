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
#    File:    test_imports.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Smoke tests — verify that all top-level modules import without error.

These catch broken imports (missing files, deleted modules still referenced)
before the app is even launched.  No fixtures, no Qt, no display needed.
"""

# Project Libraries
from pointy.core import Collection_Manager, GCP_Processor, Imagery_Loader
from pointy.core.auto_match import (
    Auto_Match_Settings,
    Feature_Extraction_Settings,
    Matching_Settings,
    Outlier_Settings,
)
from pointy.core.match.extractor import AKAZE_Extractor, ORB_Extractor
from pointy.core.match.matcher import Feature_Matcher
from pointy.core.match.outlier_filter import make_outlier_filter
from pointy.core.match.pipeline import Auto_Matcher
from pointy.controllers.auto_match_controller import Auto_Match_Controller
from pointy.controllers.image_controller import Image_Controller
from pointy.controllers.sync_controller import Sync_Controller
from pointy.viewers.leaflet_reference_viewer import Leaflet_Reference_Viewer


def test_core_package_importable():
    assert Collection_Manager is not None
    assert GCP_Processor is not None
    assert Imagery_Loader is not None


def test_auto_match_settings_importable():
    assert Auto_Match_Settings is not None
    assert Feature_Extraction_Settings is not None
    assert Matching_Settings is not None
    assert Outlier_Settings is not None


def test_match_pipeline_importable():
    assert AKAZE_Extractor is not None
    assert ORB_Extractor is not None
    assert Feature_Matcher is not None
    assert make_outlier_filter is not None
    assert Auto_Matcher is not None


def test_controllers_importable():
    assert Auto_Match_Controller is not None
    assert Image_Controller is not None
    assert Sync_Controller is not None


def test_viewers_importable():
    assert Leaflet_Reference_Viewer is not None
