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
#    File:    datum.py
#    Author:  Marvin Smith
#    Date:    04/03/2026
#
"""
Geodetic datum definitions and utilities.
"""

#  Python Standard Libraries
from enum import Enum


class Datum(Enum):
    """Geodetic datum definitions."""
    WGS84 = "EPSG:4326"      # World Geodetic System 1984
    NAD83 = "EPSG:4269"      # North American Datum 1983
    EGM96 = "EPSG:5773"      # Earth Gravitational Model 1996
    NAVD88 = "EPSG:5703"     # North American Vertical Datum 1988


class Vertical_Datum(Enum):
    """Vertical datum definitions."""
    EGM96 = "EPSG:5773"      # Earth Gravitational Model 1996
    NAVD88 = "EPSG:5703"     # North American Vertical Datum 1988
    MSL = "EPSG:5714"        # Mean Sea Level
