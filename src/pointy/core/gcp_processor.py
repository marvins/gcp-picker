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
#    File:    gcp_processor.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
GCP Processor - Core logic for managing ground control points
"""

#  Python Standard Libraries
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

#  Third-Party Libraries
import numpy as np

#  Project Libraries
from tmns.geo.coord import Geographic, Pixel, UTM
from tmns.geo.terrain import elevation as get_elevation
from tmns.geo.proj import Identity

from pointy.core.gcp import GCP

class GCP_Processor:
    """Core processor for ground control points."""

    def __init__(self):
        self.gcps: Dict[int, GCP] = {}
        self.next_gcp_id = 1
        self.test_image_path = None
        self.reference_info = None

        # Pending points for creating GCPs
        self.pending_test_point = None
        self.pending_reference_point = None

        # Projector for coordinate transformations
        self.projector = Identity()

        # Track unsaved changes
        self._dirty = False

    @property
    def is_dirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self._dirty

    def _mark_dirty(self):
        """Mark the processor as having unsaved changes."""
        self._dirty = True

    def _mark_clean(self):
        """Mark the processor as having no unsaved changes."""
        self._dirty = False

    def add_gcp(self, gcp: GCP):
        """Add a GCP to the collection."""
        self.gcps[gcp.id] = gcp
        if gcp.id >= self.next_gcp_id:
            self.next_gcp_id = gcp.id + 1
        self._mark_dirty()

    def remove_gcp(self, gcp_id: int):
        """Remove a GCP by ID."""
        if gcp_id in self.gcps:
            del self.gcps[gcp_id]
            self._mark_dirty()

    def get_gcp(self, gcp_id: int) -> GCP | None:
        """Get a GCP by ID."""
        return self.gcps.get(gcp_id)

    def get_gcps(self) -> List[GCP]:
        """Get all GCPs as a list."""
        return list(self.gcps.values())

    def get_gcps_for_image(self, image_path: str) -> List[GCP]:
        """Get GCPs whose test_image_path matches image_path by basename.

        Args:
            image_path: Path to the image to filter GCPs for.

        Returns:
            List of GCPs belonging to that image, or all GCPs if no
            test_image_path is set on the processor.
        """
        if not self.test_image_path:
            return list(self.gcps.values())
        if Path(self.test_image_path).name == Path(image_path).name:
            return list(self.gcps.values())
        return []

    def gcp_count(self) -> int:
        """Get the number of GCPs."""
        return len(self.gcps)

    def clear_gcps(self):
        """Clear all GCPs."""
        self.gcps.clear()
        self.next_gcp_id = 1

    def has_gcps(self) -> bool:
        """Check if there are any GCPs."""
        return len(self.gcps) > 0

    def set_test_image_path(self, path: str):
        """Set the test image path."""
        self.test_image_path = path

    def set_reference_info(self, info: Dict):
        """Set reference source information."""
        self.reference_info = info

    def set_pending_test_point(self, x: float, y: float):
        """Set pending test point."""
        self.pending_test_point = (x, y)

    def set_pending_reference_point(self, x: float, y: float, lon: float, lat: float):
        """Set pending reference point."""
        self.pending_reference_point = (x, y, lon, lat)

    def has_pending_test_point(self) -> bool:
        """Check if there's a pending test point."""
        return self.pending_test_point is not None

    def has_pending_reference_point(self) -> bool:
        """Check if there's a pending reference point."""
        return self.pending_reference_point is not None

    def get_pending_test_point(self) -> Tuple[float, float] | None:
        """Get pending test point."""
        return self.pending_test_point

    def get_pending_reference_point(self) -> Tuple[float, float, float, float] | None:
        """Get pending reference point."""
        return self.pending_reference_point

    def set_projector(self, projector):
        """Set the projector for coordinate transformations."""
        self.projector = projector

    def get_projector(self):
        """Get the current projector."""
        return self.projector

    def transform_test_coordinates(self, x: float, y: float) -> tuple[float, float]:
        """Transform test coordinates using current projector."""
        if self.projector.is_identity:
            return x, y

        try:
            # Convert test pixel to geographic coordinates
            test_pixel = Pixel.create(x, y)
            geographic = self.projector.pixel_to_world(test_pixel)

            # Convert geographic back to destination pixel (orthorectified)
            dest_pixel = self.projector.geographic_to_destination(geographic)

            return dest_pixel.x_px, dest_pixel.y_px
        except Exception as e:
            # If transformation fails, return original coordinates
            return x, y

    def clear_pending_points(self):
        """Clear pending points."""
        self.pending_test_point = None
        self.pending_reference_point = None

    def create_gcp_from_pending(self) -> GCP:
        """Create a GCP from pending points."""
        if not self.pending_test_point or not self.pending_reference_point:
            raise ValueError("Both test and reference points must be pending")

        test_x, test_y = self.pending_test_point
        ref_x, ref_y, lon, lat = self.pending_reference_point

        # Create coordinate objects
        test_pixel = Pixel.create(test_x, test_y)
        ref_pixel = Pixel.create(ref_x, ref_y)

        # Get elevation for the geographic coordinate
        geographic = Geographic.create(lat, lon)
        try:
            elev = get_elevation(geographic)
            if elev is not None:
                geographic.altitude_m = elev
            else:
                raise RuntimeError("Elevation lookup returned None")
        except Exception as e:
            raise RuntimeError(f"Elevation lookup failed for coordinates ({lon:.6f}, {lat:.6f}): {e}")

        gcp = GCP(
            id=self.next_gcp_id,
            pixel=test_pixel,
            reference_pixel=ref_pixel,
            geographic=geographic
        )

        self.next_gcp_id += 1
        return gcp

    def save_gcps(self, file_path: str):
        """Save GCPs to file."""
        file_path = Path(file_path)

        if file_path.suffix.lower() == '.json':
            self._save_json(file_path)
        elif file_path.suffix.lower() in ('.txt', '.gcp'):
            self._save_text(file_path)
        elif file_path.suffix.lower() == '.csv':
            self._save_csv(file_path)
        else:
            # Default to JSON
            self._save_json(file_path.with_suffix('.json'))

        self._mark_clean()

    def _save_json(self, file_path: Path):
        """Save GCPs as JSON."""
        data = {
            'test_image_path': self.test_image_path,
            'reference_info': self.reference_info,
            'gcps': [gcp.to_dict() for gcp in self.gcps.values()]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_text(self, file_path: Path):
        """Save GCPs as text file (GDAL format)."""
        with open(file_path, 'w') as f:
            f.write("# Ground Control Points\n")
            f.write("# Format: ID test_x test_y ref_x ref_y longitude latitude\n")

            for gcp in self.gcps.values():
                f.write(f"{gcp.id} {gcp.pixel.x_px:.6f} {gcp.pixel.y_px:.6f} "
                       f"{gcp.reference_pixel.x_px:.6f} {gcp.reference_pixel.y_px:.6f} "
                       f"{gcp.geographic.longitude_deg:.8f} {gcp.geographic.latitude_deg:.8f}\n")

    def _save_csv(self, file_path: Path):
        """Save GCPs as CSV."""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Test_X', 'Test_Y', 'Ref_X', 'Ref_Y', 'Longitude', 'Latitude'])

            for gcp in self.gcps.values():
                writer.writerow([
                    gcp.id, gcp.pixel.x_px, gcp.pixel.y_px,
                    gcp.reference_pixel.x_px, gcp.reference_pixel.y_px,
                    gcp.geographic.longitude_deg, gcp.geographic.latitude_deg
                ])

    def load_gcps(self, file_path: str) -> int:
        """Load GCPs from file and return the count of loaded GCPs."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"GCP file not found: {file_path}")

        if file_path.suffix.lower() == '.json':
            self._load_json(file_path)
        elif file_path.suffix.lower() in ('.txt', '.gcp'):
            self._load_text(file_path)
        elif file_path.suffix.lower() == '.csv':
            self._load_csv(file_path)
        else:
            # Try JSON first, then text
            try:
                self._load_json(file_path)
            except:
                self._load_text(file_path)

        self._mark_clean()
        return len(self.gcps)

    def _load_json(self, file_path: Path):
        """Load GCPs from JSON (single-image object or first entry of array)."""
        data = json.loads(file_path.read_text())

        if isinstance(data, list):
            data = data[0] if data else {}

        # Resolve test_image_path relative to GCP file location
        test_image_path = data.get('test_image_path')
        if test_image_path and not Path(test_image_path).is_absolute():
            self.test_image_path = str(file_path.parent / test_image_path)
        else:
            self.test_image_path = test_image_path

        self.reference_info = data.get('reference_info')

        self.gcps.clear()
        for gcp_data in data.get('gcps', []):
            gcp = GCP.from_dict(gcp_data)
            self.gcps[gcp.id] = gcp
            if gcp.id >= self.next_gcp_id:
                self.next_gcp_id = gcp.id + 1

    def _load_text(self, file_path: Path):
        """Load GCPs from text file."""
        self.gcps.clear()

        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue

                parts = line.split()
                if len(parts) >= 7:
                    try:
                        gcp_id = int(parts[0])
                        test_x = float(parts[1])
                        test_y = float(parts[2])
                        ref_x = float(parts[3])
                        ref_y = float(parts[4])
                        longitude = float(parts[5])
                        latitude = float(parts[6])
                        elevation = float(parts[7]) if len(parts) > 7 else None

                        # Create coordinate objects
                        test_pixel = Pixel.create(test_x, test_y)
                        ref_pixel = Pixel.create(ref_x, ref_y)

                        # Get elevation if not provided
                        if elevation is None:
                            elevation = get_elevation(latitude, longitude)

                        geographic = Geographic.create(latitude, longitude, elevation)

                        gcp = GCP(
                            id=gcp_id,
                            pixel=test_pixel,
                            reference_pixel=ref_pixel,
                            geographic=geographic
                        )

                        self.gcps[gcp_id] = gcp
                        if gcp_id >= self.next_gcp_id:
                            self.next_gcp_id = gcp_id + 1

                    except ValueError:
                        continue

    def _load_csv(self, file_path: Path):
        """Load GCPs from CSV."""
        self.gcps.clear()

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    gcp_id = int(row['ID'])
                    test_x = float(row['Test_X'])
                    test_y = float(row['Test_Y'])
                    ref_x = float(row['Ref_X'])
                    ref_y = float(row['Ref_Y'])
                    longitude = float(row['Longitude'])
                    latitude = float(row['Latitude'])
                    elevation = float(row.get('Elevation', 0)) if row.get('Elevation') else None

                    # Create coordinate objects
                    test_pixel = Pixel.create(test_x, test_y)
                    ref_pixel = Pixel.create(ref_x, ref_y)

                    # Get elevation if not provided
                    if elevation is None:
                        elevation = get_elevation(latitude, longitude)

                    geographic = Geographic.create(latitude, longitude, elevation)

                    gcp = GCP(
                        id=gcp_id,
                        pixel=test_pixel,
                        reference_pixel=ref_pixel,
                        geographic=geographic
                    )

                    self.gcps[gcp_id] = gcp
                    if gcp_id >= self.next_gcp_id:
                        self.next_gcp_id = gcp_id + 1

                except (ValueError, KeyError):
                    continue

    def to_gdal_gcps(self):
        """Convert to rasterio GCP format."""
        from rasterio.control import GroundControlPoint

        return [
            GroundControlPoint(
                row=gcp.pixel.y_px,
                col=gcp.pixel.x_px,
                x=gcp.geographic.longitude_deg,
                y=gcp.geographic.latitude_deg,
                z=gcp.geographic.altitude_m or 0,
                id=str(gcp.id)
            )
            for gcp in self.gcps.values()
        ]

    def calculate_residuals(self, projector=None) -> dict:
        """Calculate residuals for all GCPs using the given projector.

        Args:
            projector: Optional projector to use. If None, uses self.projector.

        Returns:
            Dictionary with residual information:
            {
                'gcps': [
                    {
                        'id': gcp_id,
                        'geo_error_deg': forward error in degrees,
                        'pixel_error_px': inverse error in pixels,
                        'geo_pred_lat': predicted latitude,
                        'geo_pred_lon': predicted longitude,
                        'pixel_pred_x': predicted x pixel,
                        'pixel_pred_y': predicted y pixel
                    },
                    ...
                ],
                'rmse_px': overall pixel RMSE,
                'rmse_deg': overall degree RMSE
            }
        """
        if projector is None:
            projector = self.projector

        if projector.is_identity:
            return {
                'gcps': [],
                'rmse_px': 0.0,
                'rmse_deg': 0.0,
                'error': 'Projector is identity, no model fitted'
            }

        residuals = []
        total_pixel_error_sq = 0.0
        total_geo_error_sq = 0.0

        for gcp in self.gcps.values():
            # Forward: source pixel -> geo
            geo_pred = projector.pixel_to_world(gcp.pixel)
            geo_error_deg = np.sqrt(
                (geo_pred.latitude_deg - gcp.geographic.latitude_deg) ** 2 +
                (geo_pred.longitude_deg - gcp.geographic.longitude_deg) ** 2
            )

            # Inverse: geo -> source pixel
            pixel_pred = projector.world_to_pixel(gcp.geographic)
            pixel_error_px = np.sqrt(
                (pixel_pred.x_px - gcp.pixel.x_px) ** 2 +
                (pixel_pred.y_px - gcp.pixel.y_px) ** 2
            )

            residuals.append({
                'id': gcp.id,
                'geo_error_deg': geo_error_deg,
                'pixel_error_px': pixel_error_px,
                'geo_pred_lat': geo_pred.latitude_deg,
                'geo_pred_lon': geo_pred.longitude_deg,
                'pixel_pred_x': pixel_pred.x_px,
                'pixel_pred_y': pixel_pred.y_px
            })

            total_pixel_error_sq += pixel_error_px ** 2
            total_geo_error_sq += geo_error_deg ** 2

        rmse_px = np.sqrt(total_pixel_error_sq / len(self.gcps)) if self.gcps else 0.0
        rmse_deg = np.sqrt(total_geo_error_sq / len(self.gcps)) if self.gcps else 0.0

        return {
            'gcps': residuals,
            'rmse_px': rmse_px,
            'rmse_deg': rmse_deg
        }
