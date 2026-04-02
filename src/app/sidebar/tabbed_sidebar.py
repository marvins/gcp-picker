"""
Tabbed Sidebar - Sidebar with tabs for better organization
"""

#  Third-Party Libraries
from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea
from qtpy.QtCore import Qt

#  Project Libraries
from .components.gcp_panel import GCP_Panel
from .components.status_panel import Status_Panel
from .components.tools_panel import Tools_Panel
from .components.collection_nav_panel import Collection_Nav_Panel
from .components.view_control_panel import Image_View_Control_Panel
from .components.metadata_panel import Metadata_Panel


class Tabbed_Sidebar(QWidget):
    """Tabbed sidebar container with organized components."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the tabbed sidebar layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)

        # Create tabs

        # Image Controls Tab
        image_controls_widget = QWidget()
        image_controls_layout = QVBoxLayout(image_controls_widget)
        image_controls_layout.setContentsMargins(5, 5, 5, 5)
        image_controls_layout.setSpacing(10)

        self.view_control_panel = Image_View_Control_Panel()
        image_controls_layout.addWidget(self.view_control_panel)
        image_controls_layout.addStretch()

        self.tab_widget.addTab(image_controls_widget, "Image")

        # GCP Tab
        gcp_widget = QWidget()
        gcp_layout = QVBoxLayout(gcp_widget)
        gcp_layout.setContentsMargins(5, 5, 5, 5)
        gcp_layout.setSpacing(10)

        self.gcp_panel = GCP_Panel()
        gcp_layout.addWidget(self.gcp_panel)
        gcp_layout.addStretch()

        self.tab_widget.addTab(gcp_widget, "GCPs")

        # Navigation Tab
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(10)

        self.collection_nav_panel = Collection_Nav_Panel()
        nav_layout.addWidget(self.collection_nav_panel)

        self.tools_panel = Tools_Panel()
        nav_layout.addWidget(self.tools_panel)

        nav_layout.addStretch()

        self.tab_widget.addTab(nav_widget, "Navigation")

        # Info Tab
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(10)

        self.status_panel = Status_Panel()
        info_layout.addWidget(self.status_panel)

        self.metadata_panel = Metadata_Panel()
        info_layout.addWidget(self.metadata_panel)

        info_layout.addStretch()

        self.tab_widget.addTab(info_widget, "Info")

        # Add tab widget to layout
        layout.addWidget(self.tab_widget)

        # Set sidebar styling
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #ccc;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
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
