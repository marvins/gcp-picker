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
#    File:    test_naming.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Test script to verify naming conventions are working correctly.
"""

import pytest

from pointy.widgets.image_canvas import Image_Canvas
from pointy.widgets.zoom_controls import Zoom_Controls
from pointy.widgets.gcp_manager import GCP_Manager
from pointy.widgets.status_panel import Status_Panel
from pointy.viewers.test_image_viewer import Test_Image_Viewer
from pointy.viewers.reference_viewer import Reference_Viewer
from pointy.core.coordinate import Coordinate_Transformer
from pointy.core.gcp_processor import GCP_Processor

def test_naming_conventions():
    """Test that classes follow Rust-style naming conventions."""

    # Test class names
    classes_to_test = [
        Image_Canvas,
        Zoom_Controls,
        GCP_Manager,
        Status_Panel,
        Test_Image_Viewer,
        Reference_Viewer,
        Coordinate_Transformer,
        GCP_Processor
    ]

    print("Testing Rust-style naming conventions:")
    print("=" * 50)

    for cls in classes_to_test:
        class_name = cls.__name__

        # Check if it follows Rust-style PascalCase_with_underscores
        has_underscores = '_' in class_name
        starts_with_upper = class_name[0].isupper()
        valid_chars = all(c.isalnum() or c == '_' for c in class_name)

        if has_underscores and starts_with_upper and valid_chars:
            print(f"✅ {class_name} - Follows Rust-style convention")
        else:
            print(f"❌ {class_name} - Does not follow Rust-style convention")

    print("\nTesting method naming (snake_case):")
    print("=" * 50)

    # Test some methods
    canvas = Image_Canvas()
    methods_to_test = [
        'set_pixmap',
        'set_zoom',
        'add_gcp_point',
        'pixel_to_image_coords'
    ]

    for method_name in methods_to_test:
        if hasattr(canvas, method_name):
            # Check if it follows snake_case
            is_snake_case = method_name.islower() and '_' in method_name or method_name.islower()

            if is_snake_case:
                print(f"✅ {method_name} - Follows snake_case convention")
            else:
                print(f"❌ {method_name} - Does not follow snake_case convention")

    print("\nNaming convention test complete!")
