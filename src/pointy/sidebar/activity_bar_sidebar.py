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
#    File:    activity_bar_sidebar.py
#    Author:  Marvin Smith
#    Date:    4/21/2026
#
"""
Activity Bar Sidebar - Panel stack for sidebar content (icon bar is separate)
"""

# Third-Party Libraries
from qtpy.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

# Project Libraries
from pointy.sidebar.components.auto_gcp_solver_panel import Auto_GCP_Solver_Panel
from pointy.sidebar.components.auto_model_solver_panel import Auto_Model_Solver_Panel
from pointy.sidebar.components.collection_nav_panel import Collection_Nav_Panel
from pointy.sidebar.components.gcp_panel import GCP_Panel
from pointy.sidebar.components.metadata_panel import Metadata_Panel
from pointy.sidebar.components.tools_panel import Tools_Panel
from pointy.sidebar.components.transformation_status_panel import Transformation_Status_Panel
from pointy.sidebar.components.view_control_panel import Image_View_Control_Panel
from pointy.sidebar.icon_bar import Sidebar_Panel


class Activity_Bar_Sidebar(QWidget):
    """Panel stack for sidebar content (icon bar is separate widget)."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the panel stack layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create panel stack
        self.panel_stack = QStackedWidget()
        self.panel_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
        """)

        # Create panels
        self._create_panels()

        # Add panel stack to layout
        layout.addWidget(self.panel_stack)

        # Select default panel (Info)
        self.panel_stack.setCurrentIndex(Sidebar_Panel.INFO.value)

    def _create_panels(self):
        """Create all panels and add to the stack."""
        # Info panel
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(10)
        self.collection_nav_panel = Collection_Nav_Panel()
        info_layout.addWidget(self.collection_nav_panel)
        self.metadata_panel = Metadata_Panel()
        info_layout.addWidget(self.metadata_panel)
        info_layout.addStretch()
        self.panel_stack.addWidget(info_widget)

        # Image panel
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(5, 5, 5, 5)
        image_layout.setSpacing(10)
        self.view_control_panel = Image_View_Control_Panel()
        image_layout.addWidget(self.view_control_panel)
        image_layout.addStretch()
        self.panel_stack.addWidget(image_widget)

        # GCP panel
        gcp_widget = QWidget()
        gcp_layout = QVBoxLayout(gcp_widget)
        gcp_layout.setContentsMargins(5, 5, 5, 5)
        gcp_layout.setSpacing(10)
        self.gcp_panel = GCP_Panel()
        gcp_layout.addWidget(self.gcp_panel)
        gcp_layout.addStretch()
        self.panel_stack.addWidget(gcp_widget)

        # Ortho panel
        ortho_widget = QWidget()
        ortho_layout = QVBoxLayout(ortho_widget)
        ortho_layout.setContentsMargins(5, 5, 5, 5)
        ortho_layout.setSpacing(10)
        self.transformation_status_panel = Transformation_Status_Panel()
        ortho_layout.addWidget(self.transformation_status_panel)
        self.tools_panel = Tools_Panel()
        ortho_layout.addWidget(self.tools_panel)
        ortho_layout.addStretch()
        self.panel_stack.addWidget(ortho_widget)

        # Auto GCP Solver panel
        auto_gcp_widget = QWidget()
        auto_gcp_layout = QVBoxLayout(auto_gcp_widget)
        auto_gcp_layout.setContentsMargins(5, 5, 5, 5)
        auto_gcp_layout.setSpacing(0)
        self.auto_gcp_solver_panel = Auto_GCP_Solver_Panel()
        auto_gcp_layout.addWidget(self.auto_gcp_solver_panel, stretch=1)
        self.panel_stack.addWidget(auto_gcp_widget)

        # Auto Model Solver panel
        auto_model_widget = QWidget()
        auto_model_layout = QVBoxLayout(auto_model_widget)
        auto_model_layout.setContentsMargins(5, 5, 5, 5)
        auto_model_layout.setSpacing(0)
        self.auto_model_solver_panel = Auto_Model_Solver_Panel()
        auto_model_layout.addWidget(self.auto_model_solver_panel, stretch=1)
        self.panel_stack.addWidget(auto_model_widget)

    def set_active_panel(self, panel_id: Sidebar_Panel):
        """Set the active panel by ID."""
        self.panel_stack.setCurrentIndex(panel_id.value)

    def get_gcp_panel(self) -> GCP_Panel:
        """Get the GCP panel component."""
        return self.gcp_panel

    def get_tools_panel(self) -> Tools_Panel:
        """Get the tools panel component."""
        return self.tools_panel

    def get_collection_nav_panel(self) -> Collection_Nav_Panel:
        """Get the collection navigation panel component."""
        return self.collection_nav_panel

    def get_view_control_panel(self) -> Image_View_Control_Panel:
        """Get the image view control panel component."""
        return self.view_control_panel

    def get_metadata_panel(self) -> Metadata_Panel:
        """Get the metadata panel component."""
        return self.metadata_panel

    def get_transformation_status_panel(self) -> Transformation_Status_Panel:
        """Get the transformation status panel component."""
        return self.transformation_status_panel

    def get_auto_gcp_solver_panel(self) -> Auto_GCP_Solver_Panel:
        """Get the Auto GCP Solver panel component."""
        return self.auto_gcp_solver_panel

    def get_auto_model_solver_panel(self) -> Auto_Model_Solver_Panel:
        """Get the Auto Model Solver panel component."""
        return self.auto_model_solver_panel
