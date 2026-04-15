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
#    File:    config.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Configuration management for Auto-GCP Tester.
"""

# Python Standard Libraries
import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Third-Party Libraries
import rasterio
import tomli

# Project Libraries
from pointy.core.auto_match import (
    AKAZE_Params,
    Auto_Match_Settings,
    Feature_Extraction_Settings,
    Match_Algo,
    Matcher_Type,
    Matching_Settings,
    ORB_Params,
    Outlier_Settings,
    Rejection_Method,
)
from pointy.core.gcp_processor import GCP_Processor
from tmns.geo.coord import Geographic


@dataclass
class Test_Image_Config:
    """Test image configuration.

    Attributes:
        path: Path to the test image file.
    """
    path: str


@dataclass
class Reference_Config:
    """Reference imagery configuration.

    Attributes:
        type: Reference type, either "file" (local image) or "leaflet" (map tiles).
        service: Map tile service name (for leaflet type).
        bounds: Geographic bounds as {sw_lat, sw_lon, ne_lat, ne_lon}.
        center: Map center as {lat, lon} (for leaflet type).
        zoom: Map zoom level (for leaflet type).
        file_path: Path to reference image file (for file type).
    """
    type: str
    service: str | None = None
    bounds: dict[str, float] | None = None
    center: dict[str, float] | None = None
    zoom: int | None = None
    file_path: str | None = None


@dataclass
class GCPs_Config:
    """Manual GCP configuration (optional).

    Attributes:
        file: Path to manual GCP JSON file for use as a prior in matching.
    """
    file: str | None = None


@dataclass
class Configuration:
    """Complete configuration for Auto-GCP Tester.

    Attributes:
        cmd_args: Parsed command-line arguments.
        cfg_args: Parsed configuration file contents as dictionary.
        test_image: Test image configuration.
        reference: Reference imagery configuration.
        gcps: Manual GCP configuration.
        auto_match: Auto-match pipeline settings.
    """

    cmd_args: argparse.Namespace
    cfg_args: dict
    test_image: Test_Image_Config
    reference: Reference_Config
    gcps: GCPs_Config
    auto_match: Auto_Match_Settings

    @staticmethod
    def parse_command_line() -> argparse.Namespace:
        """Parse command line arguments.

        Returns:
            argparse.Namespace: Parsed command-line arguments including:
                - config_file: Path to configuration TOML file (default: options.toml)
                - gen_config: Whether to generate a sample configuration file
                - verbose: Whether to enable verbose logging
        """
        parser = argparse.ArgumentParser(
            description='Auto-GCP Tester - Standalone auto-match pipeline tool'
        )
        parser.add_argument(
            '-c', '--config-file',
            type=str,
            default='options.toml',
            help='Path to configuration file (default: options.toml)'
        )
        parser.add_argument(
            '-g', '--gen-config',
            action='store_true',
            help='Create a sample configuration file'
        )
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
        return parser.parse_args()

    @staticmethod
    def create_config(pathname: str) -> None:
        """Create a sample configuration file with comments.

        Writes a TOML configuration file with the IP header, section headers,
        inline comments, and default values for all configuration options.

        Args:
            pathname: Path where the configuration file should be written.
        """
        date_str = datetime.now().strftime("%m/%d/%Y")
        filename = Path(pathname).name
        with open(pathname, 'w') as f:
            f.write("#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#\n")
            f.write("#*                                                                                    *#\n")
            f.write("#*                           Copyright (c) 2026 Terminus LLC                          *#\n")
            f.write("#*                                                                                    *#\n")
            f.write("#*                                All Rights Reserved.                                *#\n")
            f.write("#*                                                                                    *#\n")
            f.write("#*          Use of this source code is governed by LICENSE in the repo root.          *#\n")
            f.write("#*                                                                                    *#\n")
            f.write("#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#\n")
            f.write("#\n")
            f.write(f"#    File:    {filename}\n")
            f.write("#    Author:  Marvin Smith\n")
            f.write(f"#    Date:    {date_str}\n")
            f.write("#\n")
            f.write("# Auto-GCP Tester Configuration\n")
            f.write("# Generated by pointy-auto-gcp-tester -g\n")
            f.write("\n")
            f.write("# Test image configuration\n")
            f.write("[test_image]\n")
            f.write("path = \"/path/to/test_image.png\"\n")
            f.write("\n")
            f.write("# Reference imagery configuration\n")
            f.write("# type can be 'file' (local image) or 'leaflet' (map tiles)\n")
            f.write("[reference]\n")
            f.write("type = \"file\"\n")
            f.write("file_path = \"/path/to/reference_image.png\"\n")
            f.write("\n")
            f.write("# Geographic bounds for the reference image (optional)\n")
            f.write("# If not provided, bounds will be auto-detected from image metadata\n")
            f.write("# sw_lat = 35.3\n")
            f.write("# sw_lon = -119.1\n")
            f.write("# ne_lat = 35.5\n")
            f.write("# ne_lon = -118.9\n")
            f.write("\n")
            f.write("# For web-based reference (leaflet type), use service name from imagery_services.json:\n")
            f.write("# type = \"leaflet\"\n")
            f.write("# service = \"Esri World Imagery\"\n")
            f.write("# center_lat = 35.4\n")
            f.write("# center_lon = -119.0\n")
            f.write("# zoom = 12\n")
            f.write("\n")
            f.write("# Manual GCP configuration (optional)\n")
            f.write("# If provided, these GCPs will be used as a prior for matching\n")
            f.write("[gcps]\n")
            f.write("file = \"/path/to/manual_gcps.json\"\n")
            f.write("\n")
            f.write("# Auto-match settings for test image\n")
            f.write("[auto_match.test_extraction]\n")
            f.write("# Feature detection algorithm: AKAZE or ORB\n")
            f.write("algo = \"AKAZE\"\n")
            f.write("max_features = 2000\n")
            f.write("pyramid_level = 2\n")
            f.write("clahe = true\n")
            f.write("# AKAZE-specific parameters\n")
            f.write("akaze_threshold = 0.001\n")
            f.write("akaze_n_octaves = 4\n")
            f.write("akaze_n_octave_layers = 4\n")
            f.write("\n")
            f.write("# Auto-match settings for reference image\n")
            f.write("[auto_match.ref_extraction]\n")
            f.write("max_features = 2000\n")
            f.write("pyramid_level = 0\n")
            f.write("clahe = false\n")
            f.write("\n")
            f.write("# Feature matching settings\n")
            f.write("[auto_match.matching]\n")
            f.write("matcher = \"FLANN\"\n")
            f.write("ratio_test = 0.75\n")
            f.write("\n")
            f.write("# Outlier rejection settings\n")
            f.write("[auto_match.outlier]\n")
            f.write("rejection_method = \"RANSAC\"\n")
            f.write("inlier_threshold = 3.0\n")

        print(f"Sample config written to: {pathname}")

    @staticmethod
    def parse_config_file(config_path: str) -> dict:
        """Parse configuration file using tomli.

        Args:
            config_path: Path to the TOML configuration file.

        Returns:
            dict: Parsed configuration file contents.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            tomli.TOMLDecodeError: If the file is not valid TOML.
        """
        with open(config_path, 'rb') as f:
            return tomli.load(f)

    @classmethod
    def parse(cls) -> Configuration:
        """Parse command line and config file, return Configuration.

        This method orchestrates the full configuration parsing process:
        1. Parse command-line arguments
        2. Handle -g flag to generate sample config (exits after generation)
        3. Load and parse the TOML configuration file
        4. Parse all configuration sections into typed objects
        5. Construct and return a Configuration instance

        Returns:
            Configuration: Fully parsed and validated configuration object.

        Raises:
            SystemExit: If -g/--gen-config flag is set (after generating config).
        """
        cmd_args = cls.parse_command_line()

        # Handle gen-config flag
        if cmd_args.gen_config:
            cls.create_config(cmd_args.config_file)
            sys.exit(0)

        # Parse config file
        cfg_args = cls.parse_config_file(cmd_args.config_file)

        # Parse test image
        test_image = Test_Image_Config(
            path=cfg_args['test_image']['path']
        )

        # Parse reference
        ref_data = cfg_args['reference']
        ref_type = ref_data['type']
        if ref_type == 'file':
            reference = Reference_Config(
                type=ref_type,
                file_path=ref_data['file_path'],
                bounds={
                    'sw_lat': ref_data['sw_lat'],
                    'sw_lon': ref_data['sw_lon'],
                    'ne_lat': ref_data['ne_lat'],
                    'ne_lon': ref_data['ne_lon'],
                } if 'sw_lat' in ref_data else None,
            )
        elif ref_type == 'leaflet':
            reference = Reference_Config(
                type=ref_type,
                service=ref_data.get('service'),
                center={
                    'lat': ref_data.get('center_lat'),
                    'lon': ref_data.get('center_lon'),
                } if 'center_lat' in ref_data else None,
                zoom=ref_data.get('zoom'),
            )
        else:
            reference = Reference_Config(
                type=ref_type,
                service=ref_data.get('service'),
            )

        # Parse GCPs
        gcp_data = cfg_args.get('gcps', {})
        gcps = GCPs_Config(
            file=gcp_data.get('file') if 'file' in gcp_data else None
        )

        # Parse auto-match settings
        test_ext_data = cfg_args['auto_match']['test_extraction']
        test_algo_str = test_ext_data['algo'].lower()
        test_algo = Match_Algo(test_algo_str)

        if test_algo == Match_Algo.AKAZE:
            test_akaze = AKAZE_Params(
                threshold=test_ext_data.get('akaze_threshold', 0.001),
                n_octaves=test_ext_data.get('akaze_n_octaves', 4),
                n_octave_layers=test_ext_data.get('akaze_n_octave_layers', 4),
            )
            test_orb = ORB_Params()
        else:
            test_orb = ORB_Params(
                scale_factor=test_ext_data.get('orb_scale_factor', 1.2),
                n_levels=test_ext_data.get('orb_n_levels', 8),
                edge_threshold=test_ext_data.get('orb_edge_threshold', 31),
                patch_size=test_ext_data.get('orb_patch_size', 31),
            )
            test_akaze = AKAZE_Params()

        test_extraction = Feature_Extraction_Settings(
            max_features=test_ext_data.get('max_features', 2000),
            pyramid_level=test_ext_data.get('pyramid_level', 2),
            clahe=test_ext_data.get('clahe', True),
            akaze=test_akaze,
            orb=test_orb,
        )

        ref_ext_data = cfg_args['auto_match']['ref_extraction']
        ref_extraction = Feature_Extraction_Settings(
            max_features=ref_ext_data.get('max_features', 2000),
            pyramid_level=ref_ext_data.get('pyramid_level', 0),
            clahe=ref_ext_data.get('clahe', False),
            akaze=test_akaze,
            orb=test_orb,
        )

        match_data = cfg_args['auto_match']['matching']
        matching = Matching_Settings(
            ratio_test=match_data.get('ratio_test', 0.75),
            matcher=Matcher_Type(match_data.get('matcher', 'FLANN').lower()),
        )

        outlier_data = cfg_args['auto_match']['outlier']
        outlier = Outlier_Settings(
            rejection_method=Rejection_Method(outlier_data.get('rejection_method', 'RANSAC').lower()),
            inlier_threshold=outlier_data.get('inlier_threshold', 3.0),
        )

        auto_match = Auto_Match_Settings(
            algo=test_algo,
            use_manual_prior=gcps.file is not None,
            test_extraction=test_extraction,
            ref_extraction=ref_extraction,
            matching=matching,
            outlier=outlier,
        )

        return cls(
            cmd_args=cmd_args,
            cfg_args=cfg_args,
            test_image=test_image,
            reference=reference,
            gcps=gcps,
            auto_match=auto_match,
        )

    def validate(self) -> bool:
        """Validate the configuration.

        Checks that:
        - Test image file exists
        - Reference configuration is valid based on type
        - Reference file exists (for file type)
        - Reference service is specified (for leaflet type)
        - GCP file exists (if specified)

        Returns:
            bool: True if configuration is valid, False otherwise.

        Note:
            Prints error/warning messages to stdout for any validation failures.
        """
        # Check test image exists
        if not Path(self.test_image.path).exists():
            print(f"ERROR: Test image not found: {self.test_image.path}")
            return False

        # Check reference config
        if self.reference.type == "file":
            if self.reference.file_path is None:
                print("ERROR: reference.file_path required when type='file'")
                return False
            if not Path(self.reference.file_path).exists():
                print(f"ERROR: Reference file not found: {self.reference.file_path}")
                return False
            # Bounds are optional for file type - will be auto-detected if missing
        elif self.reference.type == "leaflet":
            if self.reference.service is None:
                print("ERROR: reference.service required when type='leaflet'")
                return False
            if self.reference.center is None or self.reference.zoom is None:
                print("ERROR: reference.center+zoom required for leaflet type")
                return False
        else:
            print(f"ERROR: Unknown reference type: {self.reference.type}")
            return False

        # Check GCP file if specified
        if self.gcps.file is not None and not Path(self.gcps.file).exists():
            print(f"WARNING: GCP file not found: {self.gcps.file}")

        return True

    def load_manual_gcps(self) -> GCP_Processor | None:
        """Load manual GCPs if configured.

        If a GCP file is specified in the configuration, loads the GCPs
        and returns a GCP_Processor instance. Returns None if no GCP file
        is configured or if loading fails.

        Returns:
            GCP_Processor | None: GCP processor with loaded GCPs, or None if
                no GCP file is configured or loading fails.
        """
        if self.gcps.file is None:
            return None

        gcp_proc = GCP_Processor()
        count = gcp_proc.load_gcps(self.gcps.file)
        if count == 0:
            print(f"WARNING: No GCPs loaded from {self.gcps.file}")
            return None

        print(f"Loaded {count} manual GCPs from {self.gcps.file}")
        return gcp_proc

    def auto_detect_bounds(self) -> dict[str, float] | None:
        """Auto-detect geographic bounds from reference image metadata.

        Attempts to extract bounds from:
        1. Embedded GeoTIFF metadata
        2. World file sidecar (.wld, .tfw, etc.)
        3. Other georeferencing metadata

        Returns:
            dict[str, float] | None: Bounds as {sw_lat, sw_lon, ne_lat, ne_lon},
                or None if bounds cannot be auto-detected.
        """
        if self.reference.type != "file" or self.reference.file_path is None:
            return None

        if self.reference.bounds is not None:
            return self.reference.bounds

        try:
            with rasterio.open(self.reference.file_path) as src:
                if src.crs is not None and src.transform is not None:
                    bounds = src.bounds  # left, bottom, right, top
                    return {
                        'sw_lat': bounds.bottom,
                        'sw_lon': bounds.left,
                        'ne_lat': bounds.top,
                        'ne_lon': bounds.right,
                    }
        except Exception as e:
            print(f"WARNING: Failed to auto-detect bounds from image metadata: {e}")

        return None

    def check_ortho_sidecar(self, image_path: str) -> dict[str, float] | None:
        """Check for ortho sidecar files and extract bounds.

        Looks for world files (.wld, .tfw, .jgw, .pgw) alongside the image
        and extracts geographic bounds if found.

        Args:
            image_path: Path to the image file to check for sidecars.

        Returns:
            dict[str, float] | None: Bounds as {sw_lat, sw_lon, ne_lat, ne_lon},
                or None if no ortho sidecar found or bounds cannot be extracted.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            return None

        # Check for common world file extensions
        world_extensions = ['.wld', '.tfw', '.jgw', '.pgw', '.j2w', '.aux.xml']
        base_name = image_path.stem

        for ext in world_extensions:
            world_file = image_path.parent / f"{base_name}{ext}"
            if world_file.exists():
                try:
                    # Try to open the image with rasterio which will auto-load the world file
                    with rasterio.open(image_path) as src:
                        if src.crs is not None and src.transform is not None:
                            bounds = src.bounds
                            print(f"Found ortho sidecar: {world_file.name}")
                            return {
                                'sw_lat': bounds.bottom,
                                'sw_lon': bounds.left,
                                'ne_lat': bounds.top,
                                'ne_lon': bounds.right,
                            }
                except Exception as e:
                    print(f"WARNING: Failed to extract bounds from sidecar {world_file}: {e}")

        return None
