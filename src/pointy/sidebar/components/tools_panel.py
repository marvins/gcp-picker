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
Tools Panel - Model fitting controls and results for the Ortho tab
"""

# Python Standard Libraries
from enum import Enum
from typing import List

# Third-Party Libraries
from qtpy.QtCore import Signal
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QComboBox, QGroupBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QSizePolicy)

# Project Libraries
from tmns.geo.proj import Transformation_Type
from pointy.core.transformation import GCP_Residual


class Output_Projection(Enum):
    """Output coordinate reference system for orthorectified view."""
    WGS84   = 'WGS84 (Lat/Lon)'
    UTM     = 'UTM (auto-zone)'


AVAILABLE_MODELS = [
    t.value.capitalize()
    for t in Transformation_Type
    if t != Transformation_Type.IDENTITY
]


class Tools_Panel(QWidget):
    """Model fitting controls and results panel."""

    # Signals
    fit_requested = Signal(str)              # model_name
    output_projection_changed = Signal(str)  # Output_Projection.value
    sidecar_delete_requested = Signal()     # delete sidecar file

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the tools panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Title
        title_label = QLabel("Model Settings")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)

        # Model Settings Group
        model_group = QGroupBox("Model Settings")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(6)

        # Model selector row
        model_row = QHBoxLayout()
        model_label = QLabel("Model:")
        model_label.setFixedWidth(80)
        model_row.addWidget(model_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(AVAILABLE_MODELS)
        self.model_combo.setToolTip("Select the projection model to fit")
        model_row.addWidget(self.model_combo, 1)
        model_layout.addLayout(model_row)

        # Output projection row
        proj_row = QHBoxLayout()
        proj_label = QLabel("Output CRS:")
        proj_label.setFixedWidth(80)
        proj_row.addWidget(proj_label)
        self.proj_combo = QComboBox()
        for p in Output_Projection:
            self.proj_combo.addItem(p.value)
        self.proj_combo.setToolTip("Coordinate system for the orthorectified output")
        self.proj_combo.currentTextChanged.connect(self._on_proj_changed)
        proj_row.addWidget(self.proj_combo, 1)
        model_layout.addLayout(proj_row)

        # Fit button
        fit_row = QHBoxLayout()
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setToolTip("Fit the selected model to the current GCPs")
        self.fit_btn.clicked.connect(self._on_fit_clicked)
        fit_row.addWidget(self.fit_btn)
        fit_row.addStretch()
        model_layout.addLayout(fit_row)

        # Sidecar status row
        sidecar_row = QHBoxLayout()
        self.sidecar_status_label = QLabel("No Sidecar")
        self.sidecar_status_label.setStyleSheet("QLabel { color: #666; font-size: 8pt; font-style: italic; }")
        sidecar_row.addWidget(self.sidecar_status_label)
        self.delete_sidecar_btn = QPushButton("Del")
        self.delete_sidecar_btn.setToolTip("Delete ortho model sidecar file")
        self.delete_sidecar_btn.hide()
        self.delete_sidecar_btn.clicked.connect(self._on_delete_sidecar)
        sidecar_row.addWidget(self.delete_sidecar_btn)
        sidecar_row.addStretch()
        model_layout.addLayout(sidecar_row)

        layout.addWidget(model_group)

        # Fit Results Group
        results_group = QGroupBox("Fit Results")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(4)

        # Overall RMSE
        rmse_row = QHBoxLayout()
        rmse_row.addWidget(QLabel("Overall RMSE:"))
        self.rmse_label = QLabel("N/A")
        self.rmse_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.rmse_label.setStyleSheet("QLabel { color: #666; }")
        rmse_row.addWidget(self.rmse_label)
        rmse_row.addStretch()
        results_layout.addLayout(rmse_row)

        # GCP residuals table
        self.residuals_table = QTableWidget(0, 6)
        self.residuals_table.setHorizontalHeaderLabels(["ID", "Lat", "Lon", "dX (px)", "dY (px)", "RMS (px)"])
        self.residuals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.residuals_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.residuals_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.residuals_table.setAlternatingRowColors(True)
        self.residuals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.residuals_table.setMinimumHeight(250)
        results_layout.addWidget(self.residuals_table)

        layout.addWidget(results_group)
        layout.addStretch()

        self._apply_styling()

    def _on_fit_clicked(self):
        """Emit fit_requested with the currently selected model name."""
        self.fit_requested.emit(self.model_combo.currentText())

    def _on_proj_changed(self, value: str):
        """Emit output_projection_changed when the CRS selector changes."""
        self.output_projection_changed.emit(value)

    def _on_delete_sidecar(self):
        """Handle delete sidecar button click."""
        self.sidecar_delete_requested.emit()

    def set_sidecar_status(self, has_sidecar: bool, model_type: str | None = None, replaced: bool = False):
        """Update the sidecar status label.

        Args:
            has_sidecar: True if a sidecar exists for the current image.
            model_type: Model type string if sidecar exists, None otherwise.
            replaced: True if the sidecar was just replaced (vs loaded from disk).
        """
        if has_sidecar and model_type:
            if replaced:
                self.sidecar_status_label.setText(f"✓ {model_type.capitalize()} model saved (replaced sidecar)")
            else:
                self.sidecar_status_label.setText(f"✓ {model_type.capitalize()} model loaded from sidecar")
            self.sidecar_status_label.setStyleSheet("QLabel { color: green; font-size: 8pt; font-style: italic; }")
            self.delete_sidecar_btn.show()
        else:
            self.sidecar_status_label.setText("No Sidecar")
            self.sidecar_status_label.setStyleSheet("QLabel { color: #666; font-size: 8pt; font-style: italic; }")
            self.delete_sidecar_btn.hide()

    def get_selected_model(self) -> str:
        """Return the currently selected model name."""
        return self.model_combo.currentText()

    def get_output_projection(self) -> Output_Projection:
        """Return the currently selected output projection."""
        return Output_Projection(self.proj_combo.currentText())

    def update_fit_results(self, rmse: float | None, residuals: list[GCP_Residual]):
        """Populate the results panel after a fit.

        Args:
            rmse: Overall root-mean-square error in pixels, or None if unavailable.
            residuals: List of GCP_Residual objects with residual information.
        """
        if rmse is None:
            self.rmse_label.setText("N/A")
            self.rmse_label.setStyleSheet("QLabel { color: #666; }")
        else:
            self.rmse_label.setText(f"{rmse:.3f} px")
            if rmse < 1.0:
                self.rmse_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            elif rmse < 2.0:
                self.rmse_label.setStyleSheet("QLabel { color: orange; font-weight: bold; }")
            else:
                self.rmse_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")

        self.residuals_table.setRowCount(0)
        for residual in residuals:
            row = self.residuals_table.rowCount()
            self.residuals_table.insertRow(row)
            self.residuals_table.setItem(row, 0, QTableWidgetItem(str(residual.gcp_id)))
            self.residuals_table.setItem(row, 1, QTableWidgetItem(f"{residual.lat_deg:.6f}"))
            self.residuals_table.setItem(row, 2, QTableWidgetItem(f"{residual.lon_deg:.6f}"))
            self.residuals_table.setItem(row, 3, QTableWidgetItem(f"{residual.dx_px:+.2f}"))
            self.residuals_table.setItem(row, 4, QTableWidgetItem(f"{residual.dy_px:+.2f}"))
            self.residuals_table.setItem(row, 5, QTableWidgetItem(f"{residual.rms_px:.2f}"))

    def clear_fit_results(self):
        """Reset results to the unfitted state."""
        self.rmse_label.setText("N/A")
        self.rmse_label.setStyleSheet("QLabel { color: #666; }")
        self.residuals_table.setRowCount(0)

    def _apply_styling(self):
        """Apply widget stylesheet."""
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
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 3px 5px;
                background-color: white;
                color: black;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #1976d2;
                selection-color: white;
                border: 1px solid #ccc;
            }
            QTableWidget {
                border: 1px solid #ddd;
                font-size: 8pt;
            }
            QHeaderView::section {
                background-color: #e8eaf6;
                padding: 3px;
                border: none;
                font-size: 8pt;
                font-weight: bold;
            }
        """)
