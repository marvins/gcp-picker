"""
Status Panel - Application status and information display
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                           QTextEdit, QFrame)
from qtpy.QtGui import QFont, QTextCursor

from pointy.widgets.status_panel import Status_Panel as Original_Status_Panel


class Status_Panel(QWidget):
    """Status and information panel."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the status panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title_label = QLabel("Status & Information")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # Original status panel (reuse existing widget)
        self.original_status_panel = Original_Status_Panel()
        layout.addWidget(self.original_status_panel)
        
        # Additional information area
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("Current GCP")
        info_title.setFont(QFont("Arial", 9, QFont.Bold))
        info_layout.addWidget(info_title)
        
        self.gcp_info = QTextEdit()
        self.gcp_info.setMaximumHeight(100)
        self.gcp_info.setReadOnly(True)
        info_layout.addWidget(self.gcp_info)
        
        layout.addWidget(info_frame)
        
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
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 2px;
                padding: 3px;
                font-family: monospace;
                font-size: 8pt;
            }
        """)
    
    def update_status(self, message):
        """Update the status message."""
        self.original_status_panel.update_status(message)
        
    def update_gcp_info(self, gcp):
        """Update the GCP information display."""
        if gcp:
            info = f"""GCP ID: {gcp.id}
Test Pixel: ({gcp.test_pixel.x_px:.1f}, {gcp.test_pixel.y_px:.1f})
Reference Pixel: ({gcp.reference_pixel.x_px:.1f}, {gcp.reference_pixel.y_px:.1f})
Geographic: ({gcp.geographic.latitude_deg:.6f}, {gcp.geographic.longitude_deg:.6f})
Elevation: {gcp.geographic.altitude_m:.1f}m
Error: {gcp.error:.2f}m" if gcp.error else "N/A"
Enabled: {gcp.enabled}"""
        else:
            info = "No GCP selected"
            
        self.gcp_info.setText(info)
        self.gcp_info.moveCursor(QTextCursor.Start)
    
    def clear_gcp_info(self):
        """Clear the GCP information display."""
        self.gcp_info.clear()
        self.original_status_panel.clear_status()
