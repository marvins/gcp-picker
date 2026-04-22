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
Configuration management for Auto Model Solver.
"""

# Python Standard Libraries
import argparse
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Third-Party Libraries
import rasterio
import tomli

# Project Libraries
from pointy.core.auto_match import (
    Auto_Match_Settings,
    Debug_Settings,
    Edge_Alignment_Settings,
)
from pointy.core.gcp_processor import GCP_Processor
from pointy.core.ortho_model_persistence import apply_model_to_projector, load_ortho_model, sidecar_exists
from tmns.geo.proj import Transformation_Type
from tmns.geo.proj.factory import create_projector


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
    max_zoom: int = 17
    num_threads: int = 8
    file_path: str | None = None


@dataclass
class GCPs_Config:
    """Manual GCP configuration (optional).

    Attributes:
        file: Path to manual GCP JSON file for use as a prior in matching.
    """
    file: str | None = None


@dataclass
class Output_Config:
    """Output configuration (optional).

    Attributes:
        model_output_path:  Path to save the fitted model.
        ref_chip_output_path: Path to save the stitched reference chip as GeoTiff.
        visualization_path: Path to save visualization results.
        output_model_type:  Model type to solve for after GA alignment
                            ('affine' or 'rpc'). Affine is always used for the
                            GA optimization stage; this controls whether a
                            secondary RPC solve is attempted post-alignment.
    """
    model_output_path:    str | None = None
    ref_chip_output_path: str | None = None
    visualization_path:   str | None = None
    output_model_type:    str        = 'affine'


@dataclass
class Configuration:
    """Complete configuration for Auto Model Solver.

    Attributes:
        cmd_args: Parsed command-line arguments.
        cfg_args: Parsed configuration file contents as dictionary.
        test_image: Test image configuration.
        reference: Reference imagery configuration.
        gcps: Manual GCP configuration.
        auto_match: Auto-match pipeline settings (Edge-based alignment only).
    """

    cmd_args: argparse.Namespace
    cfg_args: dict
    test_image: Test_Image_Config
    reference: Reference_Config
    gcps: GCPs_Config
    auto_match: Auto_Match_Settings
    output: Output_Config

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
            description='Auto Model Solver - Sobel edge-based model fitting tool'
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
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear the tile cache before running'
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
            f.write("# Auto Model Solver Configuration\n")
            f.write("# Generated by pointy-auto-model-solver -g\n")
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
            f.write("# zoom = 14          # Starting zoom (auto-upgraded to match test image GSD)\n")
            f.write("# max_zoom = 17      # Cap on zoom level to limit tile fetching.\n")
            f.write("#                    # Approximate GSD at mid-latitudes (~35N) per zoom level:\n")
            f.write("#                    #   zoom 14 -> ~9.6 m/px  ( ~5x5   tiles for 10km footprint)\n")
            f.write("#                    #   zoom 15 -> ~4.8 m/px  ( ~7x7   tiles)\n")
            f.write("#                    #   zoom 16 -> ~2.4 m/px  (~11x11  tiles)\n")
            f.write("#                    #   zoom 17 -> ~1.2 m/px  (~21x21  tiles)  <-- recommended\n")
            f.write("#                    #   zoom 18 -> ~0.6 m/px  (~41x41  tiles)\n")
            f.write("# num_threads = 8    # Concurrent threads for tile fetching (8 is a safe default;\n")
            f.write("#                    # 16-32 can help on fast connections for cold-cache runs)\n")
            f.write("\n")
            f.write("# Manual GCP configuration (optional)\n")
            f.write("# If provided, these GCPs will be used as a prior for matching\n")
            f.write("[gcps]\n")
            f.write("file = \"/path/to/manual_gcps.json\"\n")
            f.write("\n")
            f.write("# Auto-match algorithm settings (Edge-based GA alignment)\n")
            f.write("[auto_match]\n")
            f.write("sobel_kernel_size  = 3  # Sobel kernel size (1, 3, 5, or 7)\n")
            f.write("sobel_threshold    = 0.0  # Hard threshold on edge magnitude (0.0=off, 0.0-1.0 scale)\n")
            f.write("test_pre_blur      = 0  # Gaussian blur before Sobel for test image (0=off, try 5-15 for high-res imagery)\n")
            f.write("test_dilation      = 3  # Morphological dilation iterations for test edges (0 = disabled)\n")
            f.write("ref_pre_blur       = 0  # Gaussian blur before Sobel for reference chip (0=off)\n")
            f.write("ref_dilation       = 3  # Morphological dilation iterations for reference edges (0 = disabled)\n")
            f.write("gcp_weight         = 0.0  # GCP score weight in GA fitness (0.0=edges only, recommended)\n")
            f.write("ga_popsize = 15\n")
            f.write("ga_maxiter = 200\n")
            f.write("ga_recombination = 0.7\n")
            f.write("ga_mutation = 0.7\n")
            f.write("ga_max_edge_dim = 2048  # Max edge image dimension for GA (higher=more detail, slower)\n")
            f.write("search_bounds_px = 50.0\n")
            f.write("\n")
            f.write("# Debug settings for saving intermediate results\n")
            f.write("[auto_match.debug]\n")
            f.write("save_test_sobel = false          # Save test image Sobel edges\n")
            f.write("save_ref_sobel = false           # Save reference chip Sobel edges\n")
            f.write("output_directory = \"temp/debug\"  # Directory for debug output\n")
            f.write("save_intermediate_steps = false  # Save additional intermediate steps\n")
            f.write("\n")
            f.write("# Output configuration\n")
            f.write("[output]\n")
            f.write("# model_output_path    = \"temp/fitted_model.json\"    # Path to save the fitted model\n")
            f.write("# ref_chip_output_path = \"temp/reference_chip.tif\"   # Stitched reference chip as GeoTiff\n")
            f.write("# visualization_path   = \"temp/results.html\"         # Path to save visualization\n")
            f.write("# output_model_type    = \"affine\"                     # Model type to output: 'affine' or 'rpc'\n")

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
                max_zoom=ref_data.get('max_zoom', 17),
                num_threads=ref_data.get('num_threads', 8),
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
        auto_match_data = cfg_args['auto_match']

        # Parse debug settings
        debug_data = auto_match_data.get('debug', {})
        debug_settings = Debug_Settings(
            save_test_sobel=debug_data.get('save_test_sobel', False),
            save_ref_sobel=debug_data.get('save_ref_sobel', False),
            output_directory=debug_data.get('output_directory', 'temp/debug'),
            save_intermediate_steps=debug_data.get('save_intermediate_steps', False),
        )

        edge_settings = Edge_Alignment_Settings(
            sobel_kernel_size=auto_match_data.get('sobel_kernel_size', 3),
            sobel_threshold=float(auto_match_data.get('sobel_threshold', 0.0)),
            test_pre_blur=auto_match_data.get('test_pre_blur', 0),
            test_dilation=auto_match_data.get('test_dilation', 3),
            ref_pre_blur=auto_match_data.get('ref_pre_blur', 0),
            ref_dilation=auto_match_data.get('ref_dilation', 3),
            gcp_weight=float(auto_match_data.get('gcp_weight', 0.0)),
            ga_popsize=auto_match_data.get('ga_popsize', 15),
            ga_maxiter=auto_match_data.get('ga_maxiter', 200),
            ga_recombination=auto_match_data.get('ga_recombination', 0.7),
            ga_mutation=auto_match_data.get('ga_mutation', 0.7),
            ga_max_edge_dim=auto_match_data.get('ga_max_edge_dim', 2048),
            search_bounds_px=auto_match_data.get('search_bounds_px', 50.0),
            debug=debug_settings,
        )

        auto_match = Auto_Match_Settings(
            feature_settings=None,
            edge_settings=edge_settings,
            use_manual_prior=gcps.file is not None,
        )

        # Parse output settings
        output_data = cfg_args.get('output', {})
        output = Output_Config(
            model_output_path=output_data.get('model_output_path'),
            ref_chip_output_path=output_data.get('ref_chip_output_path'),
            visualization_path=output_data.get('visualization_path'),
            output_model_type=output_data.get('output_model_type', 'affine'),
        )

        return cls(
            cmd_args=cmd_args,
            cfg_args=cfg_args,
            test_image=test_image,
            reference=reference,
            gcps=gcps,
            auto_match=auto_match,
            output=output,
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

    def get_ortho_model_bounds(self, image_path: str, image_shape: tuple[int, int]) -> dict[str, float] | None:
        """Load Ortho model from sidecar and get full test image geographic bounds.

        This uses the fitted Ortho model (TPS/RPC) to compute the full geographic
        footprint of the test image via projector.warp_extent(), which provides
        the actual bounds of the image after transformation.

        Args:
            image_path: Path to the test image file.
            image_shape: (height, width) of the test image in pixels.

        Returns:
            dict[str, float] | None: Bounds as {sw_lat, sw_lon, ne_lat, ne_lon},
                or None if no ortho model sidecar exists or bounds cannot be computed.
        """
        logger = logging.getLogger(__name__)

        if not sidecar_exists(image_path):
            return None

        try:
            sidecar = load_ortho_model(Path(image_path))
            if sidecar is None:
                return None

            # Create appropriate projector based on model type
            model_type = Transformation_Type(sidecar.metadata.model_type)
            projector = create_projector(model_type)

            # Apply model data to projector
            apply_model_to_projector(projector, sidecar.model_data, sidecar.metadata.model_type)

            # Get warp extent for full image
            height, width = image_shape
            warp_extent = projector.warp_extent(width, height)

            # Convert Warp_Extent to bounds dict
            bounds = {
                'sw_lat': warp_extent.min_point.latitude_deg,
                'sw_lon': warp_extent.min_point.longitude_deg,
                'ne_lat': warp_extent.max_point.latitude_deg,
                'ne_lon': warp_extent.max_point.longitude_deg,
            }

            logger.info(f"Loaded Ortho model ({type(projector).__name__}) and computed bounds: {bounds}")
            return bounds

        except Exception as e:
            logger.warning(f"Failed to load Ortho model or compute bounds: {e}")
            logger.debug(traceback.format_exc())
            return None
