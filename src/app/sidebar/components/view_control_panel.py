"""
Image View Control Panel - Sidebar widget for test imagery display controls
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox,
                           QSlider, QGroupBox, QGridLayout)
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QFont

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class Image_View_Control_Panel(QWidget):
    """Panel for controlling test image display parameters."""

    # Signals
    min_pixel_changed = Signal(int)
    max_pixel_changed = Signal(int)
    brightness_changed = Signal(float)  # -1.0 to 1.0
    contrast_changed = Signal(float)  # 0.0 to 2.0
    auto_stretch_toggled = Signal(bool)
    reset_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the image view control panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("Image Display")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Auto-stretch checkbox
        self.auto_stretch_checkbox = QCheckBox("Auto-stretch (DRA)")
        self.auto_stretch_checkbox.setToolTip("Automatically stretch pixel values to full range")
        self.auto_stretch_checkbox.toggled.connect(self._on_auto_stretch_toggled)
        layout.addWidget(self.auto_stretch_checkbox)

        # Pixel range group
        range_group = QGroupBox("Pixel Range")
        range_layout = QGridLayout(range_group)

        # Min pixel
        range_layout.addWidget(QLabel("Min:"), 0, 0)
        self.min_pixel_spin = QSpinBox()
        self.min_pixel_spin.setRange(0, 65535)
        self.min_pixel_spin.setValue(0)
        self.min_pixel_spin.setEnabled(False)
        self.min_pixel_spin.valueChanged.connect(self._on_min_pixel_changed)
        range_layout.addWidget(self.min_pixel_spin, 0, 1)

        # Max pixel
        range_layout.addWidget(QLabel("Max:"), 1, 0)
        self.max_pixel_spin = QSpinBox()
        self.max_pixel_spin.setRange(0, 65535)
        self.max_pixel_spin.setValue(255)
        self.max_pixel_spin.setEnabled(False)
        self.max_pixel_spin.valueChanged.connect(self._on_max_pixel_changed)
        range_layout.addWidget(self.max_pixel_spin, 1, 1)

        layout.addWidget(range_group)

        # Brightness slider
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self._on_brightness_slider_changed)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_label = QLabel("0%")
        self.brightness_label.setMinimumWidth(35)
        brightness_layout.addWidget(self.brightness_label)
        layout.addLayout(brightness_layout)

        # Contrast slider
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Contrast:"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self._on_contrast_slider_changed)
        contrast_layout.addWidget(self.contrast_slider)
        self.contrast_label = QLabel("100%")
        self.contrast_label.setMinimumWidth(35)
        contrast_layout.addWidget(self.contrast_label)
        layout.addLayout(contrast_layout)

        # Histogram plot
        hist_group = QGroupBox("Histogram")
        hist_layout = QVBoxLayout(hist_group)

        self.hist_figure = Figure(figsize=(4, 2), dpi=100)
        self.hist_canvas = FigureCanvas(self.hist_figure)
        self.hist_canvas.setMinimumHeight(100)
        hist_layout.addWidget(self.hist_canvas)

        layout.addWidget(hist_group)

        # Reset button
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset)
        layout.addWidget(self.reset_btn)

        # Add stretch
        layout.addStretch()

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
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #999;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                background: #666;
                border-radius: 7px;
                margin: -4px 0;
            }
        """)

    def _on_auto_stretch_toggled(self, enabled: bool):
        """Handle auto-stretch toggle."""
        # Disable manual pixel range controls when auto-stretch is on
        self.min_pixel_spin.setEnabled(not enabled)
        self.max_pixel_spin.setEnabled(not enabled)
        self.auto_stretch_toggled.emit(enabled)

    def _on_min_pixel_changed(self, value: int):
        """Handle min pixel change."""
        self.min_pixel_changed.emit(value)
        self.update_histogram_markers()

    def _on_max_pixel_changed(self, value: int):
        """Handle max pixel change."""
        self.max_pixel_changed.emit(value)
        self.update_histogram_markers()

    def _on_brightness_slider_changed(self, value: int):
        """Handle brightness slider change."""
        brightness = value / 100.0
        self.brightness_label.setText(f"{value}%")
        self.brightness_changed.emit(brightness)

    def _on_contrast_slider_changed(self, value: int):
        """Handle contrast slider change."""
        contrast = value / 100.0
        self.contrast_label.setText(f"{value}%")
        self.contrast_changed.emit(contrast)

    def get_min_pixel(self) -> int:
        """Get minimum pixel value."""
        return self.min_pixel_spin.value()

    def get_max_pixel(self) -> int:
        """Get maximum pixel value."""
        return self.max_pixel_spin.value()

    def get_brightness(self) -> float:
        """Get brightness value (-1.0 to 1.0)."""
        return self.brightness_slider.value() / 100.0

    def get_contrast(self) -> float:
        """Get contrast value (0.0 to 2.0)."""
        return self.contrast_slider.value() / 100.0

    def is_auto_stretch(self) -> bool:
        """Check if auto-stretch is enabled."""
        return self.auto_stretch_checkbox.isChecked()

    def set_min_max_range(self, min_val: int, max_val: int):
        """Set the min/max pixel range based on image bit depth."""
        self.min_pixel_spin.setRange(min_val, max_val)
        self.max_pixel_spin.setRange(min_val, max_val)
        self.max_pixel_spin.setValue(max_val)

    def reset(self):
        """Reset all controls to default values."""
        self.auto_stretch_checkbox.setChecked(False)
        self.min_pixel_spin.setValue(0)
        self.max_pixel_spin.setValue(255)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(100)
        # Clear histogram
        self.hist_figure.clear()
        self.hist_canvas.draw()
        self.reset_requested.emit()

    def set_image_stats(self, min_val: int, max_val: int, actual_min: int, actual_max: int):
        """Set image statistics for auto-stretch calculation.

        Args:
            min_val: Minimum possible pixel value (e.g., 0)
            max_val: Maximum possible pixel value (e.g., 255, 65535)
            actual_min: Actual minimum pixel value in image
            actual_max: Actual maximum pixel value in image
        """
        self.set_min_max_range(min_val, max_val)

        if self.auto_stretch_checkbox.isChecked():
            self.min_pixel_spin.setValue(actual_min)
            self.max_pixel_spin.setValue(actual_max)

    def update_histogram(self, image_data: np.ndarray, num_bins: int = 256):
        """Update the histogram plot with image data.

        Args:
            image_data: Numpy array of image pixel values
            num_bins: Number of histogram bins (default 256)
        """
        self.hist_figure.clear()
        ax = self.hist_figure.add_subplot(111)

        # Handle multi-band images - use first band or convert to grayscale
        if len(image_data.shape) == 3:
            if image_data.shape[2] >= 3:
                # Use luminance for RGB
                data = 0.299 * image_data[:, :, 0] + 0.587 * image_data[:, :, 1] + 0.114 * image_data[:, :, 2]
            else:
                data = image_data[:, :, 0]
        else:
            data = image_data

        # Flatten and remove NaN values
        data = data.flatten()
        data = data[~np.isnan(data)]

        if len(data) > 0:
            # Calculate histogram
            counts, bins, patches = ax.hist(data, bins=num_bins, color='#3498db', alpha=0.7, edgecolor='none')

            # Add min/max vertical lines
            current_min = self.min_pixel_spin.value()
            current_max = self.max_pixel_spin.value()

            ax.axvline(x=current_min, color='#e74c3c', linestyle='--', linewidth=2, label=f'Min: {current_min}')
            ax.axvline(x=current_max, color='#2ecc71', linestyle='--', linewidth=2, label=f'Max: {current_max}')

            # Styling
            ax.set_xlabel('Pixel Value')
            ax.set_ylabel('Frequency')
            ax.set_title('Pixel Distribution')
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(True, alpha=0.3)

            # Set x-axis limits based on data range
            data_min, data_max = np.min(data), np.max(data)
            margin = (data_max - data_min) * 0.05
            ax.set_xlim(data_min - margin, data_max + margin)

        self.hist_figure.tight_layout()
        self.hist_canvas.draw()

    def update_histogram_markers(self):
        """Update the min/max markers on the histogram without recalculating."""
        # Get the current axis
        ax = self.hist_figure.axes[0] if self.hist_figure.axes else None
        if ax is None:
            return

        # Remove old vertical lines (they are axvline objects)
        for line in ax.lines[:]:
            line.remove()

        # Add new min/max lines
        current_min = self.min_pixel_spin.value()
        current_max = self.max_pixel_spin.value()

        ax.axvline(x=current_min, color='#e74c3c', linestyle='--', linewidth=2, label=f'Min: {current_min}')
        ax.axvline(x=current_max, color='#2ecc71', linestyle='--', linewidth=2, label=f'Max: {current_max}')

        # Update legend
        ax.legend(loc='upper right', fontsize=8)

        self.hist_canvas.draw()
