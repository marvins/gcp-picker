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
#    File:    ortho_model_persistence.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Ortho model persistence - save/load fitted ortho models to sidecar files.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from tmns.geo.coord import CRS, Geographic
from tmns.geo.proj import Transformation_Type, Warp_Extent

logger = logging.getLogger(__name__)


@dataclass
class Ortho_Model_Metadata:
    """Metadata for a fitted ortho model."""
    model_type: str  # Transformation_Type value
    fitted_timestamp: str  # ISO format timestamp
    gcp_ids: list[int]  # GCP IDs used for fitting
    image_path: str  # Path to the source image
    output_crs: str  # CRS string representation


@dataclass
class Ortho_Model_Sidecar:
    """Complete ortho model sidecar data."""
    metadata: Ortho_Model_Metadata
    warp_extent: dict  # Warp_Extent as dict
    model_data: dict  # Model-specific data from projector.serialize_model_data()


def get_sidecar_path(image_path: str) -> Path:
    """Get the sidecar file path for an image.

    Args:
        image_path: Path to the source image.

    Returns:
        Path to the sidecar file (image_path + .ortho.json).
    """
    image_path = Path(image_path)
    return image_path.with_suffix(image_path.suffix + '.ortho.json')


def save_ortho_model(
    image_path: str,
    model_type: Transformation_Type,
    projector,
    warp_extent: Warp_Extent,
    output_crs: CRS,
    gcp_ids: list[int],
    image_size: tuple[int, int],
) -> Path:
    """Save ortho model data to a sidecar file.

    Args:
        image_path: Path to the source image.
        model_type: Type of transformation model fitted.
        projector: Fitted projector instance.
        warp_extent: Geographic extent of the warped output.
        output_crs: Output coordinate reference system.
        gcp_ids: List of GCP IDs used for fitting.
        image_size: (width, height) of the source image.

    Returns:
        Path to the saved sidecar file.
    """
    sidecar_path = get_sidecar_path(image_path)

    # Store image size on the projector before serializing
    projector._image_size = image_size

    # Build metadata dict
    metadata = {
        'model_type': model_type.value,
        'fitted_timestamp': datetime.utcnow().isoformat(),
        'gcp_ids': gcp_ids,
        'image_path': str(image_path),
        'output_crs': str(output_crs)
    }

    # Build warp extent dict
    warp_extent_dict = warp_extent.to_dict()

    # Build model-specific data using projector's serialization method
    model_data = projector.serialize_model_data()

    # Build complete sidecar dict
    sidecar_dict = {
        'metadata': metadata,
        'warp_extent': warp_extent_dict,
        'model_data': model_data
    }

    # Write to file
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sidecar_path, 'w') as f:
        json.dump(sidecar_dict, f, indent=2)

    logger.info(f'Saved ortho model sidecar: {sidecar_path}')
    return sidecar_path


def load_ortho_model(image_path: Path) -> Ortho_Model_Sidecar | None:
    """Load ortho model from a sidecar file.

    Args:
        image_path: Path to the source image.

    Returns:
        Ortho_Model_Sidecar if sidecar exists, None otherwise.
    """
    sidecar_path = get_sidecar_path(image_path)

    if not sidecar_path.exists():
        return None

    try:
        with open(sidecar_path, 'r') as f:
            sidecar_dict = json.load(f)

        # Reconstruct objects
        metadata = Ortho_Model_Metadata(**sidecar_dict['metadata'])
        warp_extent_dict = sidecar_dict['warp_extent']
        model_data = sidecar_dict['model_data']

        sidecar = Ortho_Model_Sidecar(
            metadata=metadata,
            warp_extent=warp_extent_dict,
            model_data=model_data
        )

        logger.info(f'Loaded ortho model sidecar: {sidecar_path}')
        return sidecar

    except Exception as e:
        logger.error(f'Failed to load ortho model sidecar {sidecar_path}: {e}')
        return None


def apply_model_to_projector(projector, model_data: dict, model_type: str):
    """Apply loaded model data to a projector instance.

    Args:
        projector: Projector instance to update.
        model_data: Model data dict from sidecar.
        model_type: Model type string.
    """
    projector.deserialize_model_data(model_data)
    logger.info(f'Applied {model_type} model data to projector')


def sidecar_exists(image_path: str) -> bool:
    """Check if an ortho model sidecar exists for an image.

    Args:
        image_path: Path to the source image.

    Returns:
        True if sidecar exists, False otherwise.
    """
    return get_sidecar_path(image_path).exists()
