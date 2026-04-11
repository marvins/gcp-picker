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
#    File:    gcp_manager.py
#    Author:  Marvin Smith
#    Date:    4/3/2026
#
"""
GCP Manager Widget - Manage ground control points
"""

#  Python Standard Libraries

#  Third-Party Libraries
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QFont, QColor
from qtpy.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QPushButton,
                           QHeaderView, QTableWidget, QTableWidgetItem,
                           QVBoxLayout, QWidget)


class GCP_Manager(QWidget):
    """Widget for managing ground control points."""

    # Signals
    gcp_added = Signal(object)  # GCP object
    gcp_removed = Signal(int)  # gcp_id
    gcp_selected = Signal(int)  # gcp_id
    gcp_updated = Signal(object)  # GCP object
    gcp_navigate = Signal(int)  # gcp_id — double-click to navigate

    def __init__(self):
        super().__init__()
        self.next_gcp_id = 1
        self.gcps = {}  # gcp_id -> GCP

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Ground Control Points")
        title_label.setFont(QFont("Arial", 8, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # GCP count label
        self.count_label = QLabel("0 GCPs")
        self.count_label.setStyleSheet("QLabel { color: gray; font-size: 8pt; }")
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # GCP table
        self.gcp_table = QTableWidget()
        self.gcp_table.setColumnCount(7)
        self.gcp_table.setHorizontalHeaderLabels([
            "ID", "Test X", "Test Y", "Ref X", "Ref Y", "Lon", "Lat"
        ])

        # Compact font and row height
        table_font = QFont("Arial", 8)
        self.gcp_table.setFont(table_font)
        self.gcp_table.horizontalHeader().setFont(QFont("Arial", 8, QFont.Bold))
        self.gcp_table.verticalHeader().setDefaultSectionSize(20)
        self.gcp_table.verticalHeader().setVisible(False)
        self.gcp_table.setShowGrid(False)
        self.gcp_table.setAlternatingRowColors(True)
        self.gcp_table.setStyleSheet("""
            QTableWidget { border: none; }
            QHeaderView::section { padding: 2px 4px; border: none; border-bottom: 1px solid #ccc; background: #f0f0f0; }
        """)

        # Setup table properties
        self.gcp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.gcp_table.setSelectionMode(QTableWidget.SingleSelection)
        self.gcp_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.gcp_table.itemChanged.connect(self.on_item_changed)
        self.gcp_table.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Resize columns — Lon/Lat get interactive stretch, others fixed
        header = self.gcp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Test X
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Test Y
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Ref X
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Ref Y
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # Lon
        header.setSectionResizeMode(6, QHeaderView.Stretch)           # Lat

        layout.addWidget(self.gcp_table)

        # Control buttons
        button_layout = QHBoxLayout()

        btn_style = "QPushButton { font-size: 8pt; padding: 2px 6px; }"

        self.add_btn = QPushButton("Add GCP")
        self.add_btn.setStyleSheet(btn_style)
        self.add_btn.clicked.connect(self.manual_add_gcp)
        button_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet(btn_style)
        self.remove_btn.clicked.connect(self.remove_selected_gcp)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setStyleSheet(btn_style)
        self.clear_btn.clicked.connect(self.clear_all_gcps)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        # Auto-add checkbox
        self.auto_add_checkbox = QCheckBox("Auto")
        self.auto_add_checkbox.setToolTip("Auto-add GCP from pending points")
        self.auto_add_checkbox.setChecked(True)
        self.auto_add_checkbox.setStyleSheet("QCheckBox { font-size: 8pt; }")
        button_layout.addWidget(self.auto_add_checkbox)

        layout.addLayout(button_layout)

        # Accuracy info
        self.accuracy_label = QLabel("RMSE: N/A")
        self.accuracy_label.setStyleSheet("QLabel { color: #0055cc; font-size: 8pt; padding: 1px 2px; }")
        layout.addWidget(self.accuracy_label)

    def add_gcp(self, gcp):
        """Add a GCP to the manager."""
        self.gcps[gcp.id] = gcp

        # Add to table
        row = self.gcp_table.rowCount()
        self.gcp_table.insertRow(row)

        # Add items
        self.set_table_row(row, gcp)

        # Update count
        self.update_count()

        # Emit signal
        self.gcp_added.emit(gcp)

    def set_table_row(self, row, gcp):
        """Set table row data for a GCP."""
        # Make items non-editable for ID column
        id_item = QTableWidgetItem(str(gcp.id))
        id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
        self.gcp_table.setItem(row, 0, id_item)

        # Test coordinates
        test_x_item = QTableWidgetItem(f"{gcp.test_pixel.x_px:.2f}")
        test_y_item = QTableWidgetItem(f"{gcp.test_pixel.y_px:.2f}")
        self.gcp_table.setItem(row, 1, test_x_item)
        self.gcp_table.setItem(row, 2, test_y_item)

        # Reference coordinates
        ref_x_item = QTableWidgetItem(f"{gcp.reference_pixel.x_px:.2f}")
        ref_y_item = QTableWidgetItem(f"{gcp.reference_pixel.y_px:.2f}")
        self.gcp_table.setItem(row, 3, ref_x_item)
        self.gcp_table.setItem(row, 4, ref_y_item)

        # Geographic coordinates
        lon_item = QTableWidgetItem(f"{gcp.geographic.longitude_deg:.6f}")
        lat_item = QTableWidgetItem(f"{gcp.geographic.latitude_deg:.6f}")
        self.gcp_table.setItem(row, 5, lon_item)
        self.gcp_table.setItem(row, 6, lat_item)

        # Color code based on accuracy if available
        if hasattr(gcp, 'error') and gcp.error is not None:
            color = QColor(255, 0, 0) if gcp.error > 10 else QColor(0, 128, 0)
            for col in range(7):
                item = self.gcp_table.item(row, col)
                if item:
                    item.setBackground(color)

    def remove_selected_gcp(self):
        """Remove the selected GCP."""
        current_row = self.gcp_table.currentRow()
        if current_row >= 0:
            gcp_id_item = self.gcp_table.item(current_row, 0)
            if gcp_id_item:
                # Check if this is a pending point
                if gcp_id_item.text() == "PENDING":
                    # Remove the pending point row directly
                    self.gcp_table.removeRow(current_row)
                    # Update count to remove pending indicator
                    self.update_count()
                else:
                    # Remove a regular GCP
                    gcp_id = int(gcp_id_item.text())
                    self.remove_gcp(gcp_id)

    def remove_gcp(self, gcp_id):
        """Remove a GCP by ID."""
        if gcp_id in self.gcps:
            del self.gcps[gcp_id]

            # Remove from table
            for row in range(self.gcp_table.rowCount()):
                gcp_id_item = self.gcp_table.item(row, 0)
                if gcp_id_item and int(gcp_id_item.text()) == gcp_id:
                    self.gcp_table.removeRow(row)
                    break

            # Update count
            self.update_count()

            # Emit signal
            self.gcp_removed.emit(gcp_id)

    def clear_all_gcps(self):
        """Clear all GCPs."""
        self.gcps.clear()
        self.gcp_table.setRowCount(0)
        self.update_count()

    def update_gcp_list(self, gcps):
        """Update the GCP list with new GCPs."""
        self.clear_all_gcps()
        for gcp in gcps:
            self.add_gcp(gcp)

    def get_selected_gcp_id(self):
        """Get the currently selected GCP ID."""
        current_row = self.gcp_table.currentRow()
        if current_row >= 0:
            gcp_id_item = self.gcp_table.item(current_row, 0)
            if gcp_id_item and gcp_id_item.text() != "PENDING":
                return int(gcp_id_item.text())
        return None

    def select_gcp_by_id(self, gcp_id: int):
        """Select the table row corresponding to gcp_id."""
        for row in range(self.gcp_table.rowCount()):
            item = self.gcp_table.item(row, 0)
            if item and item.text() == str(gcp_id):
                self.gcp_table.setCurrentCell(row, 0)
                return

    def on_item_double_clicked(self, item):
        """Emit gcp_navigate when the user double-clicks a GCP row."""
        gcp_id = self.get_selected_gcp_id()
        if gcp_id is not None:
            self.gcp_navigate.emit(gcp_id)

    def on_selection_changed(self):
        """Handle table selection change."""
        gcp_id = self.get_selected_gcp_id()
        current_row = self.gcp_table.currentRow()

        # Enable remove button if we have a real GCP or a pending point
        has_selection = (gcp_id is not None) or (current_row >= 0 and
                        self.gcp_table.item(current_row, 0) and
                        self.gcp_table.item(current_row, 0).text() == "PENDING")
        self.remove_btn.setEnabled(has_selection)

        if gcp_id is not None:
            self.gcp_selected.emit(gcp_id)

    def on_item_changed(self, item):
        """Handle item edit."""
        if item.column() == 0:  # ID column - don't allow editing
            return

        row = item.row()
        gcp_id_item = self.gcp_table.item(row, 0)
        if not gcp_id_item:
            return

        # Skip pending point rows
        if gcp_id_item.text() == "PENDING":
            return

        gcp_id = int(gcp_id_item.text())
        if gcp_id not in self.gcps:
            return

        gcp = self.gcps[gcp_id]

        try:
            # Update GCP based on column
            if item.column() == 1:  # Test X
                gcp.test_pixel.x_px = float(item.text())
            elif item.column() == 2:  # Test Y
                gcp.test_pixel.y_px = float(item.text())
            elif item.column() == 3:  # Ref X
                gcp.reference_pixel.x_px = float(item.text())
            elif item.column() == 4:  # Ref Y
                gcp.reference_pixel.y_px = float(item.text())
            elif item.column() == 5:  # Lon
                gcp.geographic.longitude_deg = float(item.text())
            elif item.column() == 6:  # Lat
                gcp.geographic.latitude_deg = float(item.text())

            # Emit update signal
            self.gcp_updated.emit(gcp)

        except ValueError:
            # Revert to original value if invalid
            self.set_table_row(row, gcp)

    def manual_add_gcp(self):
        """Manually add a GCP (placeholder for manual entry)."""
        # This could open a dialog for manual GCP entry
        # For now, just emit a signal that could be connected to main window
        pass

    def show_pending_test_point(self, x: float, y: float):
        """Show a pending test point in the GCP table."""
        # Remove any existing pending point row
        self.clear_pending_point()

        # Add a special row for the pending point
        row_position = self.gcp_table.rowCount()
        self.gcp_table.insertRow(row_position)

        # Set the pending point data - we have test coordinates
        self.gcp_table.setItem(row_position, 0, QTableWidgetItem("PENDING"))
        self.gcp_table.setItem(row_position, 1, QTableWidgetItem(f"{x:.1f}"))
        self.gcp_table.setItem(row_position, 2, QTableWidgetItem(f"{y:.1f}"))
        self.gcp_table.setItem(row_position, 3, QTableWidgetItem("--"))  # Ref X unknown
        self.gcp_table.setItem(row_position, 4, QTableWidgetItem("--"))  # Ref Y unknown
        self.gcp_table.setItem(row_position, 5, QTableWidgetItem("--"))  # Lon unknown
        self.gcp_table.setItem(row_position, 6, QTableWidgetItem("--"))  # Lat unknown

        # Style the pending row
        for col in range(7):  # Updated to 7 columns
            item = self.gcp_table.item(row_position, col)
            if item:
                item.setBackground(QColor(255, 200, 200))  # Light red background
                item.setForeground(QColor(150, 0, 0))  # Dark red text

        # Update count to include pending
        count = len(self.gcps)
        self.count_label.setText(f"{count} GCP{'s' if count != 1 else ''} + 1 pending")

    def show_pending_reference_point(self, x: float, y: float, lon: float, lat: float):
        """Show a pending reference point in the GCP table."""
        # Remove any existing pending point row
        self.clear_pending_point()

        # Add a special row for the pending point
        row_position = self.gcp_table.rowCount()
        self.gcp_table.insertRow(row_position)

        # Set the pending point data - we have reference coordinates
        self.gcp_table.setItem(row_position, 0, QTableWidgetItem("PENDING"))
        self.gcp_table.setItem(row_position, 1, QTableWidgetItem("--"))  # Test X unknown
        self.gcp_table.setItem(row_position, 2, QTableWidgetItem("--"))  # Test Y unknown
        self.gcp_table.setItem(row_position, 3, QTableWidgetItem(f"{x:.1f}"))
        self.gcp_table.setItem(row_position, 4, QTableWidgetItem(f"{y:.1f}"))
        self.gcp_table.setItem(row_position, 5, QTableWidgetItem(f"{lon:.6f}"))
        self.gcp_table.setItem(row_position, 6, QTableWidgetItem(f"{lat:.6f}"))

        # Style the pending row
        for col in range(7):  # Updated to 7 columns
            item = self.gcp_table.item(row_position, col)
            if item:
                item.setBackground(QColor(255, 200, 200))  # Light red background
                item.setForeground(QColor(150, 0, 0))  # Dark red text

        # Update count to include pending
        count = len(self.gcps)
        self.count_label.setText(f"{count} GCP{'s' if count != 1 else ''} + 1 pending")

    def clear_pending_point(self):
        """Clear any pending point from the table."""
        # Find and remove the pending row
        for row in range(self.gcp_table.rowCount()):
            item = self.gcp_table.item(row, 0)
            if item and item.text() == "PENDING":
                self.gcp_table.removeRow(row)
                break

        # Update count
        count = len(self.gcps)
        self.count_label.setText(f"{count} GCP{'s' if count != 1 else ''}")

    def update_count(self):
        """Update the GCP count label."""
        count = len(self.gcps)
        self.count_label.setText(f"{count} GCP{'s' if count != 1 else ''}")

        # Update accuracy if we have enough points
        if count >= 3:
            self.calculate_accuracy()
        else:
            self.accuracy_label.setText("RMSE: N/A")

    def calculate_accuracy(self):
        """Calculate and display accuracy metrics."""
        if len(self.gcps) < 3:
            return

        try:
            # Simple RMSE calculation (placeholder)
            # In a real implementation, this would use the transformation
            total_error = 0
            for gcp in self.gcps.values():
                # For now, just use a placeholder error calculation
                error = 0.1  # Placeholder
                total_error += error ** 2

            rmse = (total_error / len(self.gcps)) ** 0.5
            self.accuracy_label.setText(f"RMSE: {rmse:.3f} pixels")

        except Exception:
            self.accuracy_label.setText("RMSE: Error")
