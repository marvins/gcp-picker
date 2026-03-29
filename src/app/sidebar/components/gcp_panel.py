"""
GCP Panel - Ground Control Point management panel
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QSpinBox, QDoubleSpinBox, QCheckBox)
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QFont, QColor

from app.widgets.gcp_manager import GCP_Manager


class GCP_Panel(QWidget):
    """Ground Control Point management panel."""
    
    # Signals
    gcp_added = Signal(object)  # GCP object
    gcp_removed = Signal(int)  # gcp_id
    gcp_selected = Signal(int)  # gcp_id
    gcp_updated = Signal(object)  # GCP object
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the GCP panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title_label = QLabel("Ground Control Points")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # GCP Manager (reuse existing widget)
        self.gcp_manager = GCP_Manager()
        layout.addWidget(self.gcp_manager)
        
        # Connect signals
        self.gcp_manager.gcp_added.connect(self.gcp_added)
        self.gcp_manager.gcp_removed.connect(self.gcp_removed)
        self.gcp_manager.gcp_selected.connect(self.gcp_selected)
        self.gcp_manager.gcp_updated.connect(self.gcp_updated)
        
        # Panel styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
        """)
    
    def add_gcp(self, gcp):
        """Add a GCP to the panel."""
        self.gcp_manager.add_gcp(gcp)
        
    def remove_gcp(self, gcp_id):
        """Remove a GCP from the panel."""
        self.gcp_manager.remove_gcp(gcp_id)
        
    def select_gcp(self, gcp_id):
        """Select a GCP in the panel."""
        self.gcp_manager.select_gcp(gcp_id)
        
    def get_gcps(self):
        """Get all GCPs from the panel."""
        return self.gcp_manager.get_gcps()
