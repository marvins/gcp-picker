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

#  Project Libraries
from ._version import (
    __version__,
    __build_date__,
    __git_hash__,
    get_version_info,
)

from .main_window import MainWindow

__all__ = ["MainWindow", "get_version_info", "__version__", "__build_date__", "__git_hash__"]
