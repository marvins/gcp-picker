"""
Main Sidebar - Container for all sidebar components
"""

from qtpy.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from qtpy.QtCore import Qt

from .components.gcp_panel import GCP_Panel
from .components.status_panel import Status_Panel
from .components.tools_panel import Tools_Panel
from .components.collection_nav_panel import Collection_Nav_Panel
from .components.view_control_panel import Image_View_Control_Panel
from .components.metadata_panel import Metadata_Panel


class Main_Sidebar(QWidget):
    """Main sidebar container with modular components."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the sidebar layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Create scroll area for sidebar content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Create sidebar content widget
        sidebar_content = QWidget()
        content_layout = QVBoxLayout(sidebar_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # Add sidebar components
        self.collection_nav_panel = Collection_Nav_Panel()
        content_layout.addWidget(self.collection_nav_panel)

        self.view_control_panel = Image_View_Control_Panel()
        content_layout.addWidget(self.view_control_panel)

        self.gcp_panel = GCP_Panel()
        content_layout.addWidget(self.gcp_panel)

        self.tools_panel = Tools_Panel()
        content_layout.addWidget(self.tools_panel)

        self.status_panel = Status_Panel()
        content_layout.addWidget(self.status_panel)

        self.metadata_panel = Metadata_Panel()
        content_layout.addWidget(self.metadata_panel)

        # Add stretch at bottom
        content_layout.addStretch()

        # Set up scroll area
        scroll_area.setWidget(sidebar_content)
        layout.addWidget(scroll_area)

        # Set sidebar styling
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
        """)

    def get_gcp_panel(self) -> GCP_Panel:
        """Get the GCP panel component."""
        return self.gcp_panel

    def get_tools_panel(self) -> Tools_Panel:
        """Get the tools panel component."""
        return self.tools_panel

    def get_status_panel(self) -> Status_Panel:
        """Get the status panel component."""
        return self.status_panel

    def get_collection_nav_panel(self) -> Collection_Nav_Panel:
        """Get the collection navigation panel component."""
        return self.collection_nav_panel

    def get_view_control_panel(self) -> Image_View_Control_Panel:
        """Get the image view control panel component."""
        return self.view_control_panel

    def get_metadata_panel(self) -> Metadata_Panel:
        """Get the metadata panel component."""
        return self.metadata_panel
