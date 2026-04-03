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
#    File:    zoom_controls.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
Zoom Controls Widget
"""

#  Python Standard Libraries

#  Third-Party Libraries
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget

class Zoom_Controls(QWidget):
    """Zoom control widget with buttons and slider."""

    # Signals
    zoom_changed = Signal(float)  # zoom_factor

    def __init__(self):
        super().__init__()
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Zoom out button
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(30, 25)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        layout.addWidget(self.zoom_out_btn)

        # Zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(int(self.min_zoom * 100))
        self.zoom_slider.setMaximum(int(self.max_zoom * 100))
        self.zoom_slider.setValue(int(self.zoom_factor * 100))
        self.zoom_slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.zoom_slider)

        # Zoom in button
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 25)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        layout.addWidget(self.zoom_in_btn)

        # Zoom percentage label
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFont(QFont("Arial", 9))
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.zoom_label)

        # Fit to window button
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setFixedSize(40, 25)
        self.fit_btn.clicked.connect(self.fit_to_window)
        layout.addWidget(self.fit_btn)

        # 100% button
        self.actual_btn = QPushButton("100%")
        self.actual_btn.setFixedSize(40, 25)
        self.actual_btn.clicked.connect(self.actual_size)
        layout.addWidget(self.actual_btn)

    def zoom_in(self):
        """Zoom in."""
        new_zoom = min(self.zoom_factor * 1.2, self.max_zoom)
        self.set_zoom(new_zoom)

    def zoom_out(self):
        """Zoom out."""
        new_zoom = max(self.zoom_factor / 1.2, self.min_zoom)
        self.set_zoom(new_zoom)

    def fit_to_window(self):
        """Fit to window (reset to 100%)."""
        self.set_zoom(1.0)

    def actual_size(self):
        """Set to actual size (100%)."""
        self.set_zoom(1.0)

    def on_slider_changed(self, value):
        """Handle slider change."""
        new_zoom = value / 100.0
        self.set_zoom(new_zoom)

    def set_zoom(self, zoom_factor):
        """Set zoom factor."""
        if self.min_zoom <= zoom_factor <= self.max_zoom:
            self.zoom_factor = zoom_factor
            self.zoom_slider.setValue(int(zoom_factor * 100))
            self.zoom_label.setText(f"{int(zoom_factor * 100)}%")
            self.zoom_changed.emit(zoom_factor)
