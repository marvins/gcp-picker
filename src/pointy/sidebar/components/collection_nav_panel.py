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
#    File:    collection_nav_panel.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Collection Navigation Panel - Sidebar widget for collection image navigation
"""

# Third-Party Libraries
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QFrame)

class Collection_Nav_Panel(QWidget):
    """Collection navigation panel with image navigation buttons."""

    # Signals
    first_image_requested = Signal()
    previous_image_requested = Signal()
    next_image_requested = Signal()
    last_image_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the collection navigation panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title_label = QLabel("Collection Navigation")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Image counter
        self.counter_label = QLabel("No collection loaded")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet("font-size: 10px; color: #666; font-weight: bold;")
        layout.addWidget(self.counter_label)

        # Navigation buttons row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # First image button
        self.first_btn = QPushButton("<<")
        self.first_btn.setToolTip("First image (Home)")
        self.first_btn.setMaximumWidth(40)
        self.first_btn.clicked.connect(self.first_image_requested.emit)
        button_layout.addWidget(self.first_btn)

        # Previous image button
        self.prev_btn = QPushButton("<")
        self.prev_btn.setToolTip("Previous image (Ctrl+P)")
        self.prev_btn.setMaximumWidth(40)
        self.prev_btn.clicked.connect(self.previous_image_requested.emit)
        button_layout.addWidget(self.prev_btn)

        # Next image button
        self.next_btn = QPushButton(">")
        self.next_btn.setToolTip("Next image (Ctrl+N)")
        self.next_btn.setMaximumWidth(40)
        self.next_btn.clicked.connect(self.next_image_requested.emit)
        button_layout.addWidget(self.next_btn)

        # Last image button
        self.last_btn = QPushButton(">>")
        self.last_btn.setToolTip("Last image (End)")
        self.last_btn.setMaximumWidth(40)
        self.last_btn.clicked.connect(self.last_image_requested.emit)
        button_layout.addWidget(self.last_btn)

        layout.addLayout(button_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

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
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #999;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
                border-color: #ddd;
            }
        """)

        # Initially disabled until collection loaded
        self.set_enabled(False)

    def set_enabled(self, enabled: bool):
        """Enable or disable navigation buttons."""
        self.first_btn.setEnabled(enabled)
        self.prev_btn.setEnabled(enabled)
        self.next_btn.setEnabled(enabled)
        self.last_btn.setEnabled(enabled)

    def update_counter(self, current: int, total: int):
        """Update the image counter display.

        Args:
            current: Current image index (1-based)
            total: Total number of images
        """
        if total == 0:
            self.counter_label.setText("No images")
            self.set_enabled(False)
        else:
            self.counter_label.setText(f"Image {current} / {total}")
            self.set_enabled(True)

    def set_collection_name(self, name: str):
        """Display the collection name."""
        self.counter_label.setText(name)
