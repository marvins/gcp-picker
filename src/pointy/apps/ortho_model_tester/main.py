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
#    File:    main.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Model Tester CLI - Standalone tool for testing transformation models.

This tool allows testing affine, TPS, and RPC transformation models
without the GUI, useful for debugging and analysis.
"""

# Python Standard Libraries
import argparse
import logging
import sys
from pathlib import Path

# Third-Party Libraries
import cv2
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS as Rasterio_CRS

# Project Libraries
from pointy.core.collection_manager import Collection_Manager, Collection_Info
from pointy.core.gcp_processor import GCP_Processor
from pointy.core.ortho_model_persistence import save_ortho_model
from pointy.core.transformation import fit_transformation_model, warp_image
from tmns.geo.coord import Geographic, Pixel
from tmns.geo.coord.crs import CRS
from tmns.geo.coord.transformer import Transformer
from tmns.geo.proj import Transformation_Type


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        stream=sys.stdout
    )
    return logging.getLogger(__name__)


def load_collection(collection_path: str) -> tuple[Collection_Manager, Collection_Info]:
    """Load a collection from the given path."""
    coll_mgr = Collection_Manager()
    success = coll_mgr.load_collection(collection_path)
    if not success:
        raise ValueError(f'Failed to load collection: {collection_path}')
    return coll_mgr, coll_mgr.current_collection


def find_gcp_file(image_path: Path) -> Path | None:
    """Find a GCP sidecar file for the given image.

    Looks for <image_path>.gcps.json alongside the image.
    """
    gcp_path = image_path.parent / (image_path.name + '.gcps.json')
    return gcp_path if gcp_path.exists() else None


def load_gcps(gcp_file: Path, gcp_proc: GCP_Processor) -> int:
    """Load GCPs from a JSON file."""
    if not gcp_file.exists():
        raise FileNotFoundError(f'GCP file not found: {gcp_file}')
    return gcp_proc.load_gcps(str(gcp_file))


def check_gcp_count(gcp_count: int, model_type: Transformation_Type) -> bool:
    """Check if we have enough GCPs for the model."""
    min_gcps = 9 if model_type == Transformation_Type.RPC else 3
    if gcp_count < min_gcps:
        print(f'ERROR: Need at least {min_gcps} GCPs for {model_type.value} (have {gcp_count})')
        return False
    return True


def fit_model(gcp_proc: GCP_Processor, model_type: Transformation_Type):
    """Fit the transformation model to the GCPs."""
    gcps = gcp_proc.get_gcps()
    projector, residuals_info = fit_transformation_model(gcps, model_type)
    return projector, residuals_info


def print_model_info(projector, gcp_proc: GCP_Processor):
    """Print detailed information about the fitted model."""
    gcps = gcp_proc.get_gcps()

    print(f'\n=== Model Information ===')
    print(f'Transformation Type: {projector.transformation_type.value}')
    print(f'Is Identity: {projector.is_identity}')
    print(f'Number of GCPs: {len(gcps)}')

    if not projector.is_identity:
        print(f'\n=== Residuals ===')
        total_rmse = 0.0
        for i, gcp in enumerate(gcps, 1):
            # Forward: source pixel -> geo
            geo_pred = projector.pixel_to_world(gcp.pixel)
            geo_error = np.sqrt(
                (geo_pred.latitude_deg - gcp.geographic.latitude_deg) ** 2 +
                (geo_pred.longitude_deg - gcp.geographic.longitude_deg) ** 2
            )

            # Inverse: geo -> source pixel
            pixel_pred = projector.world_to_pixel(gcp.geographic)
            pixel_error = np.sqrt(
                (pixel_pred.x_px - gcp.pixel.x_px) ** 2 +
                (pixel_pred.y_px - gcp.pixel.y_px) ** 2
            )

            print(f'GCP {i:2d}: Geo error={geo_error:.6f}°, Pixel error={pixel_error:.2f}px')
            total_rmse += pixel_error ** 2

        rmse = np.sqrt(total_rmse / len(gcps))
        print(f'\n=== Overall RMSE ===')
        print(f'Pixel RMSE: {rmse:.2f} pixels')

    if hasattr(projector, '_inverse_matrix'):
        print(f'\n=== Affine Matrix ===')
        print(projector._inverse_matrix)


def warp_and_save_geotiff(
    image_path: str,
    projector,
    output_path: str | None = None,
    output_crs: CRS | None = None,
    gsd: float | None = None
):
    """Warp the image using the fitted projector and optionally write a GeoTIFF."""
    if output_path is None:
        print('\n=== Image Warping ===')
        print('No output path specified, skipping GeoTIFF generation')
        return

    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f'Could not load image: {image_path}')

    h, w = image.shape[:2]
    print(f'\n=== Image Warping ===')
    print(f'Source image size: {w}x{h}')

    # Default to WGS84 if not specified
    if output_crs is None:
        output_crs = CRS.wgs84_geographic()

    # Use the pure warping function
    warped, extent = warp_image(image, projector, output_crs, gsd=gsd)

    print(f'Output size: {warped.shape[1]}x{warped.shape[0]}')
    print(f'Geo extent: lon=[{extent.min_point.longitude_deg:.6f}, {extent.max_point.longitude_deg:.6f}], '
          f'lat=[{extent.min_point.latitude_deg:.6f}, {extent.max_point.latitude_deg:.6f}]')

    # Write GeoTIFF

    # Convert to RGB if needed (OpenCV uses BGR)
    if warped.shape[2] == 3:
        warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)

    # Write with georeferencing
    # Transform must be in output CRS units
    x_min, y_min, x_max, y_max = output_crs.compute_transform_bounds(extent.min_point, extent.max_point)
    transform = from_bounds(x_min, y_min, x_max, y_max, warped.shape[1], warped.shape[0])

    with rasterio.open(
        output_path, 'w',
        driver='GTiff',
        width=warped.shape[1],
        height=warped.shape[0],
        count=3,
        dtype=warped.dtype,
        crs=Rasterio_CRS.from_epsg(output_crs.epsg_code),
        transform=transform,
        nodata=0
    ) as dst:
        dst.write(warped.transpose(2, 0, 1))

    print(f'GeoTIFF written to: {output_path}')


def main():
    """Main entry point for the model tester CLI."""
    parser = argparse.ArgumentParser(
        description='Test transformation models without the GUI'
    )
    parser.add_argument(
        '-c', '--collection',
        required=True,
        help='Path to collection config file'
    )
    parser.add_argument(
        '-i', '--image-id',
        type=int,
        default=0,
        help='Image ID to use (0 for first image, default: 0)'
    )
    parser.add_argument(
        '-m', '--model',
        required=True,
        choices=['affine', 'tps', 'rpc'],
        help='Model type to fit'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for warped GeoTIFF (optional)'
    )
    parser.add_argument(
        '--output-crs',
        choices=['WGS84', 'UTM'],
        default='WGS84',
        help='Output CRS for GeoTIFF (default: WGS84)'
    )
    parser.add_argument(
        '--gsd',
        type=float,
        default=None,
        help='Ground sample distance in meters (UTM) or degrees (WGS84). If provided, computes output size from extent.'
    )
    parser.add_argument(
        '--save-model',
        action='store_true',
        help='Save fitted model as ortho sidecar (<image>.ortho.json)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    try:
        # Load collection
        logger.info(f'Loading collection from: {args.collection}')
        coll_mgr, collection = load_collection(args.collection)
        logger.info(f'Loaded collection: {collection.name}')
        logger.info(f'Number of images: {len(collection.image_paths)}')

        # Get the specified image
        if args.image_id >= len(collection.image_paths):
            raise ValueError(f'Image ID {args.image_id} out of range (have {len(collection.image_paths)} images)')
        image_path = collection.image_paths[args.image_id]
        logger.info(f'Using image: {Path(image_path).name}')

        # Load GCPs
        gcp_proc = GCP_Processor()
        gcp_file = find_gcp_file(Path(image_path))
        if gcp_file is None:
            raise FileNotFoundError(
                f'No GCP sidecar found for: {Path(image_path).name}. '
                f'Expected: {Path(image_path).name}.gcps.json'
            )
        logger.info(f'Loading GCPs from: {gcp_file}')
        gcp_count = load_gcps(gcp_file, gcp_proc)
        logger.info(f'Loaded {gcp_count} GCPs')

        # Check model type
        model_type = Transformation_Type(args.model)
        if not check_gcp_count(gcp_count, model_type):
            sys.exit(1)

        # Fit model
        logger.info(f'Fitting {model_type.value} model...')
        projector, residuals_info = fit_model(gcp_proc, model_type)
        logger.info('Model fitting complete')

        # Print model information
        print_model_info(projector, gcp_proc)

        # Save ortho model sidecar if requested
        if args.save_model:
            image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if image is None:
                raise ValueError(f'Could not load image: {image_path}')
            h, w = image.shape[:2]
            extent = projector.warp_extent(w, h)
            gcp_ids = [gcp.id for gcp in gcp_proc.get_gcps()]
            sidecar_path = save_ortho_model(
                image_path,
                model_type,
                projector,
                extent,
                CRS.wgs84_geographic(),
                gcp_ids,
                image_size=(w, h),
            )
            logger.info(f'Saved ortho model sidecar: {sidecar_path}')

        # Warp image if output path specified
        if args.output:
            # Compute CRS from string argument
            if args.output_crs.upper() == 'WGS84':
                crs = CRS.wgs84_geographic()
            else:
                # Load image to get actual dimensions for extent computation
                image = cv2.imread(image_path)
                if image is None:
                    raise ValueError(f'Could not load image: {image_path}')
                h, w = image.shape[:2]

                # Compute UTM zone from extent centroid
                extent = projector.warp_extent(w, h)
                cx = (extent.min_point.longitude_deg + extent.max_point.longitude_deg) / 2
                zone = int((cx + 180) / 6) + 1
                hemisphere = 'N' if extent.min_point.latitude_deg >= 0 else 'S'
                crs = CRS.utm_zone(zone, hemisphere)

            warp_and_save_geotiff(image_path, projector, args.output, crs, args.gsd)

        logger.info('Model testing complete')
        return 0

    except Exception as e:
        logger.error(f'Error: {e}', exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
