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
#    File:    icon_bar.py
#    Author:  Marvin Smith
#    Date:    4/21/2026
#
"""
Icon Bar - Vertical icon selector for sidebar panels
"""

# Python Standard Libraries
from enum import Enum

# Third-Party Libraries
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton

class Sidebar_Panel(Enum):
    """Sidebar panel identifiers."""
    INFO = 0
    IMAGE = 1
    GCP = 2
    ORTHO = 3
    AUTO_GCP_SOLVER = 4
    AUTO_MODEL_SOLVER = 5


class Icon_Bar(QWidget):
    """Vertical icon bar for panel selection."""

    # Icon bar width constant - shared across UI components
    ICON_BAR_WIDTH = 40

    # Signal emitted when a panel is selected
    panel_selected = Signal(Sidebar_Panel)

    # Signal emitted when a panel is toggled (panel_id, should_expand)
    panel_toggled = Signal(Sidebar_Panel, bool)

    def __init__(self):
        super().__init__()
        self.icon_buttons = []
        self.current_panel = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the icon bar layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setFixedWidth(Icon_Bar.ICON_BAR_WIDTH)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
            }
        """)

        # Create icon buttons for each panel
        self._create_icon_button(layout, "ℹ️", "Info", Sidebar_Panel.INFO)
        self._create_icon_button(layout, "🖼️", "Image", Sidebar_Panel.IMAGE)
        self._create_icon_button(layout, "📍", "GCPs", Sidebar_Panel.GCP)
        self._create_icon_button(layout, "🗺️", "Ortho", Sidebar_Panel.ORTHO)
        self._create_icon_button(layout, "🔍", "GCP Solver", Sidebar_Panel.AUTO_GCP_SOLVER)
        self._create_icon_button(layout, "⚙️", "Model Fitter", Sidebar_Panel.AUTO_MODEL_SOLVER)

        layout.addStretch()

        # Select default panel (Info)
        self.set_active_panel(Sidebar_Panel.INFO)

    def _create_icon_button(self, parent_layout, icon: str, tooltip: str, panel_id: Sidebar_Panel):
        """Create an icon button for the activity bar."""
        btn = QPushButton(icon)
        btn.setFixedSize( Icon_Bar.ICON_BAR_WIDTH,
                          Icon_Bar.ICON_BAR_WIDTH )
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 20px;
                color: #888;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                color: #fff;
            }
            QPushButton:checked {
                background-color: #0078d4;
                color: #fff;
            }
        """)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.set_active_panel(panel_id))

        # Store button with its panel ID
        btn.panel_id = panel_id
        self.icon_buttons.append(btn)

        parent_layout.addWidget(btn)

    def set_active_panel(self, panel_id: Sidebar_Panel):
        """Set the active panel by ID and emit toggle signal."""
        # Check if this is the same panel - toggle collapse
        if self.current_panel == panel_id:
            # Collapse sidebar
            self.panel_toggled.emit(panel_id, False)
            # Uncheck all buttons
            for btn in self.icon_buttons:
                btn.setChecked(False)
            self.current_panel = None
        else:
            # Expand sidebar and switch to new panel
            self.current_panel = panel_id
            # Update button states
            for btn in self.icon_buttons:
                btn.setChecked(btn.panel_id == panel_id)
            # Emit signals
            self.panel_selected.emit(panel_id)
            self.panel_toggled.emit(panel_id, True)
