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
#    File:    __init__.py
#    Author:  Marvin Smith
#    Date:    04/10/2026
#
"""
Application controllers.

Each controller owns a coherent cluster of business logic and the signal
connections that drive it.  Main_Window creates controller instances and
delegates to them — it does not contain logic itself.
"""

from pointy.controllers.auto_match_controller import Auto_Match_Controller
from pointy.controllers.gcp_controller import GCP_Controller
from pointy.controllers.image_controller import Image_Controller
from pointy.controllers.ortho_controller import Ortho_Controller
from pointy.controllers.sync_controller import Sync_Controller

__all__ = [
    'Auto_Match_Controller',
    'GCP_Controller',
    'Image_Controller',
    'Ortho_Controller',
    'Sync_Controller',
]
