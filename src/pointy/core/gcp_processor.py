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

#  Project Libraries
from tmns.geo.coord import Geographic, Pixel, UTM
from tmns.geo.terrain import elevation as get_elevation
from tmns.geo.projector import GCP

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
        self.projector = None

    def add_gcp(self, gcp: GCP):
        """Add a GCP to the collection."""
        self.gcps[gcp.id] = gcp
        if gcp.id >= self.next_gcp_id:
            self.next_gcp_id = gcp.id + 1

    def remove_gcp(self, gcp_id: int):
        """Remove a GCP by ID."""
        if gcp_id in self.gcps:
            del self.gcps[gcp_id]

    def get_gcp(self, gcp_id: int) -> GCP | None:
        """Get a GCP by ID."""
        return self.gcps.get(gcp_id)

    def get_gcps(self) -> List[GCP]:
        """Get all GCPs as a list."""
        return list(self.gcps.values())

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
        if self.projector is None:
            return x, y

        try:
            # Convert test pixel to geographic coordinates
            test_pixel = Pixel.create(x, y)
            geographic = self.projector.source_to_geographic(test_pixel)

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
        except Exception:
            # Elevation lookup failed, continue without elevation
            pass

        gcp = GCP(
            id=self.next_gcp_id,
            test_pixel=test_pixel,
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
                f.write(f"{gcp.id} {gcp.test_pixel.x_px:.6f} {gcp.test_pixel.y_px:.6f} "
                       f"{gcp.reference_pixel.x_px:.6f} {gcp.reference_pixel.y_px:.6f} "
                       f"{gcp.geographic.longitude_deg:.8f} {gcp.geographic.latitude_deg:.8f}\n")

    def _save_csv(self, file_path: Path):
        """Save GCPs as CSV."""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Test_X', 'Test_Y', 'Ref_X', 'Ref_Y', 'Longitude', 'Latitude'])

            for gcp in self.gcps.values():
                writer.writerow([
                    gcp.id, gcp.test_pixel.x_px, gcp.test_pixel.y_px,
                    gcp.reference_pixel.x_px, gcp.reference_pixel.y_px,
                    gcp.geographic.longitude_deg, gcp.geographic.latitude_deg
                ])

    def load_gcps(self, file_path: str):
        """Load GCPs from file."""
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

    def _load_json(self, file_path: Path):
        """Load GCPs from JSON."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        self.test_image_path = data.get('test_image_path')
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
                            test_pixel=test_pixel,
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
                        test_pixel=test_pixel,
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
                row=gcp.test_pixel.y,
                col=gcp.test_pixel.x,
                x=gcp.geographic.longitude,
                y=gcp.geographic.latitude,
                z=gcp.geographic.elevation or 0,
                id=str(gcp.id)
            )
            for gcp in self.gcps.values()
        ]
