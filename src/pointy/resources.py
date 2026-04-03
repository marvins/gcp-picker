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
#    File:    resources.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Qt Resources - Simple resource management for Pointy-McPointface
"""

#  Python Standard Libraries
import os
from pathlib import Path

#  Third-Party Libraries
from qtpy.QtCore import QResource, Qt
from qtpy.QtGui import QIcon, QPixmap

class Resources:
    """Resource manager for application assets."""

    def __init__(self):
        self._resource_root = Path(__file__).parent
        self._icons_loaded = False

    def get_icon_path(self, icon_name: str) -> Path:
        """Get the path to an icon resource."""
        return self._resource_root / "resources" / "images" / "logos" / icon_name

    def get_icon(self, icon_name: str) -> QIcon:
        """Get an QIcon resource."""
        icon_path = self.get_icon_path(icon_name)
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def get_pixmap(self, icon_name: str, size=None) -> QPixmap:
        """Get a QPixmap resource."""
        icon_path = self.get_icon_path(icon_name)
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if size and not pixmap.isNull():
                return pixmap.scaled(size[0], size[1],
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return pixmap
        return QPixmap()

    def get_app_icon(self) -> QIcon:
        """Get the main application icon."""
        return self.get_icon("Black-Stacked.png")

    def get_splash_logo(self) -> QPixmap:
        """Get the splash screen logo."""
        return self.get_pixmap("White-Stacked.png")

# Global resource instance
resources = Resources()
