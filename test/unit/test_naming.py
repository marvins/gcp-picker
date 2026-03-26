#!/usr/bin/env python3
"""
Test script to verify naming conventions are working correctly.
"""

import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from gcp_picker.app.widgets.image_canvas import Image_Canvas
from gcp_picker.app.widgets.zoom_controls import Zoom_Controls
from gcp_picker.app.widgets.gcp_manager import GCP_Manager
from gcp_picker.app.widgets.status_panel import Status_Panel
from gcp_picker.app.viewers.test_image_viewer import Test_Image_Viewer
from gcp_picker.app.viewers.reference_viewer import Reference_Viewer
from gcp_picker.app.core.coordinate import Coordinate_Transformer
from gcp_picker.app.core.gcp_processor import GCP_Processor

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

if __name__ == "__main__":
    test_naming_conventions()
