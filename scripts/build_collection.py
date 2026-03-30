#!/usr/bin/env python3
"""
Collection Config Builder Script

Scans a directory for image files and generates a collection TOML config.

Usage:
    python build_collection.py -c <collection_directory> [options]

Example:
    python build_collection.py -c /path/to/images --name "My Dataset" -o collection.toml
"""

import argparse
import os
import sys
from pathlib import Path

# Supported image extensions
IMAGE_EXTENSIONS = {'.png', '.tif', '.tiff', '.rawl', '.jpg', '.jpeg', '.raw'}


def find_images(base_dir: str) -> list[str]:
    """Recursively find all image files in the base directory."""
    base_path = Path(base_dir).resolve()
    images = []

    for ext in IMAGE_EXTENSIONS:
        # Case-insensitive search
        for pattern in [f'*{ext}', f'*{ext.upper()}']:
            images.extend(base_path.rglob(pattern))

    # Convert to relative paths and sort
    return sorted([str(p.relative_to(base_path)) for p in images])


def build_toml(
    collection_name: str,
    description: str,
    location_name: str,
    latitude: float,
    longitude: float,
    images: list[str],
    gcp_file: str = "./gcps/collection_gcps.json"
) -> str:
    """Build the TOML config content."""
    # Format image paths as TOML array
    if images:
        images_toml = ',\n    '.join([f'"{img}"' for img in images])
        images_section = f'''images = [
    {images_toml}
]'''
    else:
        images_section = '''images = [
    # No images found - add paths manually
]'''

    toml_content = f'''# GCP Picker Collection Profile
# Auto-generated collection configuration file

collection_name = "{collection_name}"
description = "{description}"

[collection_location]
name = "{location_name}"
latitude = {latitude}
longitude = {longitude}

[image_paths]
# List of test imagery files to process
# Paths are relative to this collection file location
{images_section}

[gcp_data]
# Path to the GCP data file (JSON format)
# Contains ground control point coordinates and metadata
gcp_file = "{gcp_file}"
'''

    return toml_content


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a collection config TOML from a directory of images"
    )
    parser.add_argument(
        "--collection-dir", "-c",
        required=True,
        help="Collection directory to scan for images"
    )
    parser.add_argument(
        "--name", "-n",
        default="My Collection",
        help="Collection name (default: My Collection)"
    )
    parser.add_argument(
        "--description", "-d",
        default="Image collection for GCP processing",
        help="Collection description"
    )
    parser.add_argument(
        "--location", "-l",
        default="Unknown Location",
        help="Collection location name"
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=39.7392,
        help="Collection latitude (default: 39.7392 - Denver, CO)"
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=-104.9903,
        help="Collection longitude (default: -104.9903 - Denver, CO)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output TOML file path (default: <collection_dir>/collection_config.toml)"
    )
    parser.add_argument(
        "--gcp-file", "-g",
        default="./gcps/collection_gcps.json",
        help="Path to GCP JSON file (default: ./gcps/collection_gcps.json)"
    )

    args = parser.parse_args()

    # Validate collection directory
    if not os.path.isdir(args.collection_dir):
        print(f"Error: '{args.collection_dir}' is not a valid directory", file=sys.stderr)
        return 1

    # Set default output path inside the collection directory if not specified
    if args.output is None:
        args.output = os.path.join(args.collection_dir, "collection_config.toml")

    # Find images
    print(f"Scanning {args.collection_dir} for images...")
    images = find_images(args.collection_dir)
    print(f"Found {len(images)} image(s)")

    # Build TOML
    toml_content = build_toml(
        collection_name=args.name,
        description=args.description,
        location_name=args.location,
        latitude=args.lat,
        longitude=args.lon,
        images=images,
        gcp_file=args.gcp_file
    )

    # Write output
    output_path = Path(args.output)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(toml_content)
        print(f"Collection config written to: {output_path.absolute()}")
        return 0
    except IOError as e:
        print(f"Error writing config file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
