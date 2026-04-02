#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2025 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    about_dialog.py
#    Author:  Marvin Smith
#    Date:    4/1/2026
#
"""
About Dialog - Display version and dependency information
"""

import sys

from qtpy.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTextEdit, QFrame, QGridLayout
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont


class AboutDialog(QDialog):
    """About dialog displaying version and dependency information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Pointy-McPointface")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.load_version_info()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header section
        header_layout = QHBoxLayout()

        # Logo/Icon placeholder
        logo_label = QLabel("Pointy-McPointface")
        logo_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        # Version info in header
        self.version_label = QLabel("Version: --")
        self.version_label.setFont(QFont("Arial", 12))
        header_layout.addWidget(self.version_label)

        layout.addLayout(header_layout)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator)

        # Tab widget for different info sections
        self.tab_widget = QTabWidget()

        # About tab
        self.about_tab = self._create_about_tab()
        self.tab_widget.addTab(self.about_tab, "About")

        # Dependencies tab
        self.dependencies_tab = self._create_dependencies_tab()
        self.tab_widget.addTab(self.dependencies_tab, "Dependencies")

        # System Info tab
        self.system_tab = self._create_system_tab()
        self.tab_widget.addTab(self.system_tab, "System")

        layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_about_tab(self) -> QWidget:
        """Create the About tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # App description
        desc_label = QLabel(
            "Pointy-McPointface is an application for selecting "
            "ground control points between test imagery and reference sources "
            "with progressive orthorectification."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        # Build info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(10)

        row = 0
        self.build_date_label = self._add_info_row(info_grid, row, "Build Date:", "--")
        row += 1
        self.git_hash_label = self._add_info_row(info_grid, row, "Git Commit:", "--")
        row += 1
        self.python_version_label = self._add_info_row(info_grid, row, "Python:", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        row += 1

        layout.addLayout(info_grid)
        layout.addStretch()

        # License info
        license_label = QLabel("Licensed under MIT License")
        license_label.setStyleSheet("color: gray;")
        layout.addWidget(license_label)

        return widget

    def _add_info_row(self, grid: QGridLayout, row: int, label: str, value: str) -> QLabel:
        """Add a label-value row to the grid."""
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 10, QFont.Bold))
        grid.addWidget(label_widget, row, 0)

        value_widget = QLabel(value)
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        grid.addWidget(value_widget, row, 1)

        return value_widget

    def _create_dependencies_tab(self) -> QWidget:
        """Create the Dependencies tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.deps_text = QTextEdit()
        self.deps_text.setReadOnly(True)
        self.deps_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.deps_text)

        return widget

    def _create_system_tab(self) -> QWidget:
        """Create the System Info tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.system_text = QTextEdit()
        self.system_text.setReadOnly(True)
        self.system_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.system_text)

        return widget

    def load_version_info(self):
        """Load version and dependency information."""
        # Try to get version info from the package
        try:
            from pointy import get_version_info
            version_info = get_version_info()

            self.version_label.setText(f"Version: {version_info.get('version', '--')}")
            self.build_date_label.setText(version_info.get('build_date', '--'))
            self.git_hash_label.setText(version_info.get('git_hash', '--'))
        except ImportError:
            # Fallback if package not installed
            self.version_label.setText("Version: 1.0.0-dev")
            self.build_date_label.setText("unknown")
            self.git_hash_label.setText("unknown")

        # Load dependencies
        self._load_dependencies()

        # Load system info
        self._load_system_info()

    def _load_dependencies(self):
        """Load dependency information."""
        from importlib.metadata import version as get_pkg_version

        deps = []

        # Core dependencies to check
        core_packages = [
            'PyQt6', 'PyQt6-WebEngine', 'QtPy', 'gdal', 'rasterio',
            'numpy', 'opencv-python', 'Pillow', 'pyproj',
            'requests', 'matplotlib', 'scikit-image'
        ]

        for package in core_packages:
            try:
                ver = get_pkg_version(package)
                deps.append(f"{package:20s} {ver}")
            except Exception:
                deps.append(f"{package:20s} [not installed]")

        self.deps_text.setPlainText("\n".join(deps))

    def _load_system_info(self):
        """Load system information."""
        info_lines = [
            f"Platform: {sys.platform}",
            f"Python Version: {sys.version}",
            f"Python Executable: {sys.executable}",
            "Python Path:",
        ]

        for path in sys.path[:5]:  # Show first 5 paths
            info_lines.append(f"  - {path}")

        # Qt info
        try:
            from qtpy import API_NAME, QT_VERSION
            info_lines.extend([
                "",
                f"Qt Binding: {API_NAME}",
                f"Qt Version: {QT_VERSION}",
            ])
        except ImportError:
            pass

        self.system_text.setPlainText("\n".join(info_lines))


def show_about_dialog(parent=None) -> None:
    """Show the About dialog."""
    dialog = AboutDialog(parent)
    dialog.exec_()
