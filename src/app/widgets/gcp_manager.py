"""
GCP Manager Widget - Manage ground control points
"""

from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QSpinBox, QDoubleSpinBox, QCheckBox)
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QFont, QColor

from app.core.gcp import GCP

class GCP_Manager(QWidget):
    """Widget for managing ground control points."""

    # Signals
    gcp_added = Signal(object)  # GCP object
    gcp_removed = Signal(int)  # gcp_id
    gcp_selected = Signal(int)  # gcp_id
    gcp_updated = Signal(object)  # GCP object

    def __init__(self):
        super().__init__()
        self.next_gcp_id = 1
        self.gcps = {}  # gcp_id -> GCP

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Ground Control Points")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # GCP count label
        self.count_label = QLabel("0 GCPs")
        self.count_label.setStyleSheet("QLabel { color: gray; font-size: 9pt; }")
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # GCP table
        self.gcp_table = QTableWidget()
        self.gcp_table.setColumnCount(7)
        self.gcp_table.setHorizontalHeaderLabels([
            "ID", "Test X", "Test Y", "Ref X", "Ref Y", "Lon", "Lat"
        ])

        # Setup table properties
        self.gcp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.gcp_table.setSelectionMode(QTableWidget.SingleSelection)
        self.gcp_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.gcp_table.itemChanged.connect(self.on_item_changed)

        # Resize columns
        header = self.gcp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Test X
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Test Y
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Ref X
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Ref Y
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Lon
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Lat

        layout.addWidget(self.gcp_table)

        # Control buttons
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add GCP")
        self.add_btn.clicked.connect(self.add_gcp_from_pending)
        button_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_selected_gcp)
        self.remove_btn.setEnabled(False)
        button_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all_gcps)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        # Auto-add checkbox
        self.auto_add_checkbox = QCheckBox("Auto-add from pending points")
        self.auto_add_checkbox.setChecked(True)
        button_layout.addWidget(self.auto_add_checkbox)

        layout.addLayout(button_layout)

        # Accuracy info
        self.accuracy_label = QLabel("RMSE: N/A")
        self.accuracy_label.setStyleSheet("QLabel { color: blue; font-size: 9pt; }")
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
        test_x_item = QTableWidgetItem(f"{gcp.test_x:.2f}")
        test_y_item = QTableWidgetItem(f"{gcp.test_y:.2f}")
        self.gcp_table.setItem(row, 1, test_x_item)
        self.gcp_table.setItem(row, 2, test_y_item)

        # Reference coordinates
        ref_x_item = QTableWidgetItem(f"{gcp.ref_x:.2f}")
        ref_y_item = QTableWidgetItem(f"{gcp.ref_y:.2f}")
        self.gcp_table.setItem(row, 3, ref_x_item)
        self.gcp_table.setItem(row, 4, ref_y_item)

        # Geographic coordinates
        lon_item = QTableWidgetItem(f"{gcp.longitude:.6f}")
        lat_item = QTableWidgetItem(f"{gcp.latitude:.6f}")
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
            if gcp_id_item:
                return int(gcp_id_item.text())
        return None

    def on_selection_changed(self):
        """Handle table selection change."""
        gcp_id = self.get_selected_gcp_id()
        self.remove_btn.setEnabled(gcp_id is not None)

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

        gcp_id = int(gcp_id_item.text())
        if gcp_id not in self.gcps:
            return

        gcp = self.gcps[gcp_id]

        try:
            # Update GCP based on column
            if item.column() == 1:  # Test X
                gcp.test_x = float(item.text())
            elif item.column() == 2:  # Test Y
                gcp.test_y = float(item.text())
            elif item.column() == 3:  # Ref X
                gcp.ref_x = float(item.text())
            elif item.column() == 4:  # Ref Y
                gcp.ref_y = float(item.text())
            elif item.column() == 5:  # Lon
                gcp.longitude = float(item.text())
            elif item.column() == 6:  # Lat
                gcp.latitude = float(item.text())

            # Emit update signal
            self.gcp_updated.emit(gcp)

        except ValueError:
            # Revert to original value if invalid
            self.set_table_row(row, gcp)

    def add_gcp_from_pending(self):
        """Add GCP from pending points (placeholder for future implementation)."""
        # This would be connected to pending points from the main window
        pass

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
