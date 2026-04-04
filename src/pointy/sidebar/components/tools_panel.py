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
#    File:    tools_panel.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Tools Panel - Application tools and controls
"""

# Third-Party Libraries
from qtpy.QtCore import Signal
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QCheckBox, QComboBox, QGroupBox)


class Tools_Panel(QWidget):
    """Tools and controls panel."""

    # Signals
    tool_selected = Signal(str)  # tool_name
    setting_changed = Signal(str, object)  # setting_name, value

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the tools panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_label = QLabel("Tools & Settings")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Processing Settings Group
        processing_group = QGroupBox("Processing Settings")
        processing_layout = QVBoxLayout(processing_group)

        # Auto-elevation checkbox
        self.auto_elevation_cb = QCheckBox("Auto-fetch Elevation")
        self.auto_elevation_cb.setChecked(True)
        self.auto_elevation_cb.toggled.connect(lambda checked: self.setting_changed.emit("auto_elevation", checked))
        processing_layout.addWidget(self.auto_elevation_cb)

        # Elevation source
        elev_layout = QHBoxLayout()
        elev_layout.addWidget(QLabel("Elevation Source:"))
        self.elevation_source_combo = QComboBox()
        self.elevation_source_combo.addItems(["Google Elevation API", "OpenTopography", "Local DEM"])
        self.elevation_source_combo.currentTextChanged.connect(lambda text: self.setting_changed.emit("elevation_source", text))
        elev_layout.addWidget(self.elevation_source_combo)
        processing_layout.addLayout(elev_layout)

        layout.addWidget(processing_group)

        # Display Settings Group
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout(display_group)

        # Show GCP IDs
        self.show_gcp_ids_cb = QCheckBox("Show GCP IDs")
        self.show_gcp_ids_cb.setChecked(True)
        self.show_gcp_ids_cb.toggled.connect(lambda checked: self.setting_changed.emit("show_gcp_ids", checked))
        display_layout.addWidget(self.show_gcp_ids_cb)

        layout.addWidget(display_group)

        # Advanced Tools Group
        advanced_group = QGroupBox("Advanced Tools")
        advanced_layout = QVBoxLayout(advanced_group)

        self.rectify_btn = QPushButton("Rectify Image")
        self.rectify_btn.clicked.connect(lambda: self.tool_selected.emit("rectify"))
        advanced_layout.addWidget(self.rectify_btn)

        self.validate_gcps_btn = QPushButton("Validate GCPs")
        self.validate_gcps_btn.clicked.connect(lambda: self.tool_selected.emit("validate_gcps"))
        advanced_layout.addWidget(self.validate_gcps_btn)

        layout.addWidget(advanced_group)

        # Add stretch at bottom
        layout.addStretch()

        # Panel styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bbb;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #e3f2fd;
                border: 1px solid #1976d2;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
            QPushButton:pressed {
                background-color: #90caf9;
            }
        """)

    def get_setting(self, setting_name):
        """Get a setting value."""
        settings_map = {
            "auto_elevation": self.auto_elevation_cb.isChecked(),
            "elevation_source": self.elevation_source_combo.currentText(),
            "show_gcp_ids": self.show_gcp_ids_cb.isChecked()
        }
        return settings_map.get(setting_name)

    def set_setting(self, setting_name, value):
        """Set a setting value."""
        if setting_name == "auto_elevation":
            self.auto_elevation_cb.setChecked(value)
        elif setting_name == "elevation_source":
            self.elevation_source_combo.setCurrentText(str(value))
        elif setting_name == "show_gcp_ids":
            self.show_gcp_ids_cb.setChecked(value)
