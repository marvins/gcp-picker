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
    lock_state_changed = Signal(bool)  # is_locked

    def __init__(self):
        super().__init__()
        self._is_locked = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the GCP panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header with title and lock button
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel("Ground Control Points")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Lock/Unlock button
        self.lock_button = QPushButton("🔓")
        self.lock_button.setToolTip("Lock GCP selection to prevent accidental clicks")
        self.lock_button.setCheckable(True)
        self.lock_button.setFixedSize(28, 28)
        self.lock_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #ffcccc;
                border: 1px solid #ff6666;
            }
        """)
        self.lock_button.clicked.connect(self._toggle_lock)
        header_layout.addWidget(self.lock_button)

        layout.addLayout(header_layout)

        # GCP Manager (reuse existing widget)
        self.gcp_manager = GCP_Manager()
        layout.addWidget(self.gcp_manager)

        # Connect signals
        self.gcp_manager.gcp_added.connect(self.gcp_added)
        self.gcp_manager.gcp_removed.connect(self.gcp_removed)
        self.gcp_manager.gcp_selected.connect(self._on_gcp_selected)
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

    def _toggle_lock(self, checked: bool):
        """Toggle the lock state."""
        self._is_locked = checked
        if checked:
            self.lock_button.setText("🔒")
            self.lock_button.setToolTip("GCP selection is locked. Click to unlock.")
        else:
            self.lock_button.setText("🔓")
            self.lock_button.setToolTip("Lock GCP selection to prevent accidental clicks")
        self.lock_state_changed.emit(self._is_locked)

    def _on_gcp_selected(self, gcp_id: int):
        """Handle GCP selection, respecting lock state."""
        if not self._is_locked:
            self.gcp_selected.emit(gcp_id)

    def is_locked(self) -> bool:
        """Return whether GCP selection is locked."""
        return self._is_locked

    def set_locked(self, locked: bool):
        """Set the lock state programmatically."""
        self.lock_button.setChecked(locked)
        self._toggle_lock(locked)

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
