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
#    File:    collection_manager.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Collection Manager - Manage collection state and operations
"""

#  Python Standard Libraries
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

#  Third-Party Libraries
from qtpy.QtCore import QObject, Signal

#  Project Libraries
from tmns.geo.coord import Geographic


@dataclass
class Collection_Location:
    """Collection location information."""
    name: str
    location: Geographic


@dataclass
class Collection_Info:
    """Collection configuration information."""
    name: str
    description: str
    location: Collection_Location
    image_paths: List[str] = field(default_factory=list)
    base_directory: str = ""


class Collection_Manager(QObject):
    """Manages collection state and operations."""

    # Signals
    collection_loaded = Signal(Collection_Info)  # Emitted when collection is loaded
    image_loaded = Signal(str)  # Emitted when image is loaded, passes image path

    def __init__(self):
        super().__init__()
        self.current_collection: Collection_Info | None = None
        self.current_image_index: int = 0
        self.loaded_images: List[str] = []

    def load_collection(self, collection_path: str | Path) -> bool:
        """Load a collection from a TOML file.

        Args:
            collection_path: Path to the collection TOML file

        Returns:
            True if loaded successfully, False otherwise
        """
        collection_path = Path(collection_path)

        if not collection_path.exists():
            return False

        try:
            with open(collection_path, 'rb') as f:
                data = tomllib.load(f)

            # Parse collection location
            location_data = data.get('collection_location', {})
            location = Collection_Location(
                name=location_data.get('name', 'Unknown Location'),
                location=Geographic(
                    latitude_deg=location_data.get('latitude', 39.7392),
                    longitude_deg=location_data.get('longitude', -104.9903)
                )
            )

            # Parse image paths
            image_paths_data = data.get('image_paths', {})
            image_paths = image_paths_data.get('images', [])

            # Resolve base directory relative to collection file
            base_directory = str(collection_path.parent.resolve())

            # Resolve image paths to absolute paths
            resolved_images = []
            for img_path in image_paths:
                full_path = Path(base_directory) / img_path
                resolved_images.append(str(full_path))

            # Create collection info
            self.current_collection = Collection_Info(
                name=data.get('collection_name', 'Unnamed Collection'),
                description=data.get('description', ''),
                location=location,
                image_paths=resolved_images,
                base_directory=base_directory
            )

            self.loaded_images = resolved_images
            self.current_image_index = 0

            # Emit signal
            self.collection_loaded.emit(self.current_collection)

            return True

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading collection: {e}")
            return False

    def get_first_image(self) -> str | None:
        """Get the first image path from the collection.

        Returns:
            Path to first image, or None if no images
        """
        if self.current_collection and self.current_collection.image_paths:
            return self.current_collection.image_paths[0]
        return None

    def get_next_image(self) -> str | None:
        """Get the next image in the collection.

        Returns:
            Path to next image, or None if at end
        """
        if not self.current_collection:
            return None

        if self.current_image_index < len(self.current_collection.image_paths) - 1:
            self.current_image_index += 1
            return self.current_collection.image_paths[self.current_image_index]
        return None

    def get_previous_image(self) -> str | None:
        """Get the previous image in the collection.

        Returns:
            Path to previous image, or None if at beginning
        """
        if not self.current_collection:
            return None

        if self.current_image_index > 0:
            self.current_image_index -= 1
            return self.current_collection.image_paths[self.current_image_index]
        return None

    def get_collection_seed_location(self) -> Geographic | None:
        """Get the collection's seed location.

        Returns:
            Geographic coordinate or None if no collection loaded.
        """
        if self.current_collection:
            return self.current_collection.location.location
        return None

    def has_collection(self) -> bool:
        """Check if a collection is currently loaded."""
        return self.current_collection is not None

    def get_current_image(self) -> str | None:
        """Get the currently selected image path."""
        if self.current_collection and self.loaded_images:
            if 0 <= self.current_image_index < len(self.loaded_images):
                return self.loaded_images[self.current_image_index]
        return None

    def load_current_image(self) -> bool:
        """Load the current image and emit signal.

        Returns:
            True if image loaded successfully
        """
        image_path = self.get_current_image()
        if image_path:
            self.image_loaded.emit(image_path)
            return True
        return False
