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
#    File:    __init__.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
Pointy-McPointface
"""

#  Project Libraries
from ._version import (
    __version__,
    __build_date__,
    __git_hash__,
    get_version_info,
)

# Core functionality (no GUI dependencies)
from .core.coordinate import (
    Transformer,
    Geographic,
    Coordinate,
    Coordinate_Type,
    UTM,
    Web_Mercator,
    ECEF,
    Pixel,
)
from .core.datum import Datum, Vertical_Datum

from .core.terrain import (
    Manager,
    Elevation_Point,
    Elevation_Source,
    SRTM_Elevation_Source,
    AWS_Elevation_Source,
    elevation,
    get_terrain_manager,
    create_terrain_manager,
    create_srtm_manager,
    create_aws_manager,
)

def get_main_window():
    """Get MainWindow class (deferred import to avoid Qt initialization during tests)."""
    from .main_window import MainWindow
    return MainWindow

__all__ = [
    # Core functionality
    "Transformer",
    "Geographic",
    "Coordinate",
    "Coordinate_Type",
    "UTM",
    "Web_Mercator",
    "ECEF",
    "Pixel",
    "Datum",
    "Vertical_Datum",
    "Manager",
    "Elevation_Point",
    "Elevation_Source",
    "SRTM_Elevation_Source",
    "AWS_Elevation_Source",
    "elevation",
    "get_terrain_manager",
    "create_terrain_manager",
    "create_srtm_manager",
    "create_aws_manager",
    # GUI functionality (deferred)
    "get_main_window",
    # Version info
    "get_version_info",
    "__version__",
    "__build_date__",
    "__git_hash__"
]
