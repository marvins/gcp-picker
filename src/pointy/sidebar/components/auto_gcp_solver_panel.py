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
#    File:    auto_gcp_solver_panel.py
#    Author:  Marvin Smith
#    Date:    04/19/2026
#
"""
Auto GCP Solver Panel - Settings and results for feature-based GCP matching.
"""

# Third-Party Libraries
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGroupBox, QCheckBox,
                             QDoubleSpinBox, QSpinBox, QFormLayout, QSizePolicy,
                             QScrollArea, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QProgressBar)

# Project Libraries
from pointy.core.auto_match import (Auto_Match_Settings, Feature_Extraction_Settings,
                                    Matching_Settings, Outlier_Settings,
                                    AKAZE_Params, ORB_Params,
                                    Match_Algo, Matcher_Type, Rejection_Method)


class Auto_GCP_Solver_Results_Panel(QWidget):
    """Results display for the auto GCP solver.

    Shows a summary stats row (Candidates / Inliers / Coverage / RMSE) and a
    scrollable table listing every candidate GCP with its pixel and geographic
    coordinates.

    Public API:
        update_stats(candidates, inliers, coverage, rmse)  — refresh stat chips
        set_candidates(rows)                                — populate table
        clear()                                             — reset everything
    """

    _HEADERS = ["#", "Px X", "Px Y", "Lon", "Lat"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Summary stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        self._candidates_lbl = self._make_stat_chip("Candidates", "#4CAF50")
        self._inliers_lbl = self._make_stat_chip("Inliers", "#2196F3")
        self._coverage_lbl = self._make_stat_chip("Coverage", "#FF9800")
        self._rmse_lbl = self._make_stat_chip("RMSE", "#9C27B0")

        stats_layout.addWidget(self._candidates_lbl)
        stats_layout.addWidget(self._inliers_lbl)
        stats_layout.addWidget(self._coverage_lbl)
        stats_layout.addWidget(self._rmse_lbl)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Results table
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._HEADERS))
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setMaximumHeight(200)

        layout.addWidget(self._table)

    def _make_stat_chip(self, label: str, color: str) -> QLabel:
        """Create a small stat chip with colored background."""
        chip = QLabel(f"{label}: —")
        chip.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)
        chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return chip

    def update_stats(self, candidates: int, inliers: int, coverage: float, rmse: float):
        """Update the summary statistics."""
        self._candidates_lbl.setText(f"Candidates: {candidates}")
        self._inliers_lbl.setText(f"Inliers: {inliers}")
        self._coverage_lbl.setText(f"Coverage: {coverage:.1f}%")
        self._rmse_lbl.setText(f"RMSE: {rmse:.2f}")

    def set_candidates(self, rows: list[list]):
        """Populate the results table with candidate GCP data."""
        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(i, j, item)

    def clear(self):
        """Reset all statistics and table contents."""
        self._candidates_lbl.setText("Candidates: —")
        self._inliers_lbl.setText("Inliers: —")
        self._coverage_lbl.setText("Coverage: —")
        self._rmse_lbl.setText("RMSE: —")
        self._table.setRowCount(0)


class Auto_GCP_Solver_Panel(QWidget):
    """Settings panel and results display for the auto GCP solver.

    Signals:
        run_requested: Emitted when the user clicks "Run Auto GCP Solver",
            carrying the current ``Auto_Match_Settings``.
    """

    run_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Algorithm selection group
        layout.addWidget(self._build_algo_group())

        # Remaining groups go into a scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        scroll_layout.addWidget(self._build_extraction_group())
        scroll_layout.addWidget(self._build_akaze_params_group())
        scroll_layout.addWidget(self._build_orb_params_group())
        scroll_layout.addWidget(self._build_matching_group())
        scroll_layout.addWidget(self._build_rejection_group())
        scroll_layout.addWidget(self._build_results_group())

        self._on_algo_changed(0)

        scroll = QScrollArea()
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)

        layout.addWidget(scroll, stretch=1)

    def _build_algo_group(self) -> QGroupBox:
        """Build the algorithm selection group."""
        group = QGroupBox("Feature Algorithm")
        layout = QHBoxLayout(group)

        self._algo_combo = QComboBox()
        self._algo_combo.addItems(["AKAZE", "ORB"])
        self._algo_combo.currentIndexChanged.connect(self._on_algo_changed)

        layout.addWidget(QLabel("Algorithm:"))
        layout.addWidget(self._algo_combo)
        layout.addStretch()

        return group

    def _build_extraction_group(self) -> QGroupBox:
        """Build the feature extraction settings group."""
        group = QGroupBox("Feature Extraction")
        layout = QVBoxLayout(group)

        # Test image settings
        test_layout = QHBoxLayout()
        self._test_max_features = QSpinBox()
        self._test_max_features.setRange(100, 10000)
        self._test_max_features.setValue(2000)
        self._test_pyramid = QSpinBox()
        self._test_pyramid.setRange(0, 4)
        self._test_pyramid.setValue(0)
        self._test_clahe = QCheckBox("CLAHE")
        self._test_clahe.setChecked(True)

        test_layout.addWidget(QLabel("Test:"))
        test_layout.addWidget(QLabel("Max Features:"))
        test_layout.addWidget(self._test_max_features)
        test_layout.addWidget(QLabel("Pyramid:"))
        test_layout.addWidget(self._test_pyramid)
        test_layout.addWidget(self._test_clahe)
        test_layout.addStretch()

        # Reference image settings
        ref_layout = QHBoxLayout()
        self._ref_max_features = QSpinBox()
        self._ref_max_features.setRange(100, 10000)
        self._ref_max_features.setValue(2000)
        self._ref_pyramid = QSpinBox()
        self._ref_pyramid.setRange(0, 4)
        self._ref_pyramid.setValue(0)
        self._ref_clahe = QCheckBox("CLAHE")

        ref_layout.addWidget(QLabel("Ref:"))
        ref_layout.addWidget(QLabel("Max Features:"))
        ref_layout.addWidget(self._ref_max_features)
        ref_layout.addWidget(QLabel("Pyramid:"))
        ref_layout.addWidget(self._ref_pyramid)
        ref_layout.addWidget(self._ref_clahe)
        ref_layout.addStretch()

        layout.addLayout(test_layout)
        layout.addLayout(ref_layout)

        return group

    def _build_akaze_params_group(self) -> QGroupBox:
        """Build the AKAZE-specific parameters group."""
        self._akaze_group = QGroupBox("AKAZE Parameters")
        layout = QFormLayout(self._akaze_group)

        self._akaze_threshold = QDoubleSpinBox()
        self._akaze_threshold.setRange(0.0001, 0.01)
        self._akaze_threshold.setValue(0.001)
        self._akaze_threshold.setDecimals(4)
        self._akaze_threshold.setSingleStep(0.0001)

        self._akaze_octaves = QSpinBox()
        self._akaze_octaves.setRange(1, 8)
        self._akaze_octaves.setValue(4)

        self._akaze_layers = QSpinBox()
        self._akaze_layers.setRange(1, 8)
        self._akaze_layers.setValue(4)

        layout.addRow("Threshold:", self._akaze_threshold)
        layout.addRow("Octaves:", self._akaze_octaves)
        layout.addRow("Layers:", self._akaze_layers)

        return self._akaze_group

    def _build_orb_params_group(self) -> QGroupBox:
        """Build the ORB-specific parameters group."""
        self._orb_group = QGroupBox("ORB Parameters")
        layout = QFormLayout(self._orb_group)

        self._orb_scale = QDoubleSpinBox()
        self._orb_scale.setRange(1.0, 2.0)
        self._orb_scale.setValue(1.2)
        self._orb_scale.setDecimals(2)
        self._orb_scale.setSingleStep(0.1)

        self._orb_levels = QSpinBox()
        self._orb_levels.setRange(1, 16)
        self._orb_levels.setValue(8)

        self._orb_edge = QSpinBox()
        self._orb_edge.setRange(1, 64)
        self._orb_edge.setValue(31)

        self._orb_patch = QSpinBox()
        self._orb_patch.setRange(1, 64)
        self._orb_patch.setValue(31)

        layout.addRow("Scale Factor:", self._orb_scale)
        layout.addRow("Levels:", self._orb_levels)
        layout.addRow("Edge Threshold:", self._orb_edge)
        layout.addRow("Patch Size:", self._orb_patch)

        return self._orb_group

    def _build_matching_group(self) -> QGroupBox:
        """Build the descriptor matching settings group."""
        group = QGroupBox("Descriptor Matching")
        layout = QHBoxLayout(group)

        self._matcher_combo = QComboBox()
        self._matcher_combo.addItems(["FLANN", "Brute Force"])

        self._ratio_test = QDoubleSpinBox()
        self._ratio_test.setRange(0.5, 1.0)
        self._ratio_test.setValue(0.75)
        self._ratio_test.setDecimals(2)
        self._ratio_test.setSingleStep(0.05)

        layout.addWidget(QLabel("Matcher:"))
        layout.addWidget(self._matcher_combo)
        layout.addWidget(QLabel("Ratio Test:"))
        layout.addWidget(self._ratio_test)
        layout.addStretch()

        return group

    def _build_rejection_group(self) -> QGroupBox:
        """Build the outlier rejection settings group."""
        group = QGroupBox("Outlier Rejection")
        layout = QHBoxLayout(group)

        self._rejection_combo = QComboBox()
        self._rejection_combo.addItems(["RANSAC", "MAGSAC"])

        self._inlier_threshold = QDoubleSpinBox()
        self._inlier_threshold.setRange(0.5, 10.0)
        self._inlier_threshold.setValue(3.0)
        self._inlier_threshold.setDecimals(1)
        self._inlier_threshold.setSingleStep(0.5)

        layout.addWidget(QLabel("Method:"))
        layout.addWidget(self._rejection_combo)
        layout.addWidget(QLabel("Threshold:"))
        layout.addWidget(self._inlier_threshold)
        layout.addStretch()

        return group

    def _build_results_group(self) -> QGroupBox:
        """Build the results display and control group."""
        group = QGroupBox("Results")
        layout = QVBoxLayout(group)

        self._results_panel = Auto_GCP_Solver_Results_Panel()
        layout.addWidget(self._results_panel)

        # Run button
        self._run_btn = QPushButton("Run GCP Solver")
        self._run_btn.clicked.connect(self._on_run_clicked)
        layout.addWidget(self._run_btn)

        return group

    def _on_algo_changed(self, index: int):
        """Handle algorithm selection change."""
        is_akaze = (index == 0)
        self._akaze_group.setVisible(is_akaze)
        self._orb_group.setVisible(not is_akaze)

    def _on_run_clicked(self):
        """Handle run button click."""
        settings = self.get_settings()
        self.run_requested.emit(settings)

    def get_settings(self) -> Auto_Match_Settings:
        """Get current settings as Auto_Match_Settings object."""
        # Algorithm selection
        keypoint_algo = Match_Algo.AKAZE if self._algo_combo.currentIndex() == 0 else Match_Algo.ORB

        # AKAZE parameters
        akaze_params = AKAZE_Params(
            threshold=self._akaze_threshold.value(),
            n_octaves=self._akaze_octaves.value(),
            n_octave_layers=self._akaze_layers.value()
        )

        # ORB parameters
        orb_params = ORB_Params(
            scale_factor=self._orb_scale.value(),
            n_levels=self._orb_levels.value(),
            edge_threshold=self._orb_edge.value(),
            patch_size=self._orb_patch.value()
        )

        # Test extraction settings
        test_extraction = Feature_Extraction_Settings(
            max_features=self._test_max_features.value(),
            pyramid_level=self._test_pyramid.value(),
            clahe=self._test_clahe.isChecked(),
            akaze=akaze_params,
            orb=orb_params
        )

        # Reference extraction settings
        ref_extraction = Feature_Extraction_Settings(
            max_features=self._ref_max_features.value(),
            pyramid_level=self._ref_pyramid.value(),
            clahe=self._ref_clahe.isChecked(),
            akaze=akaze_params,
            orb=orb_params
        )

        # Matching settings
        matching = Matching_Settings(
            ratio_test=self._ratio_test.value(),
            matcher=Matcher_Type.FLANN if self._matcher_combo.currentIndex() == 0 else Matcher_Type.BRUTE_FORCE
        )

        # Outlier rejection settings
        outlier = Outlier_Settings(
            rejection_method=Rejection_Method.RANSAC if self._rejection_combo.currentIndex() == 0 else Rejection_Method.MAGSAC,
            inlier_threshold=self._inlier_threshold.value()
        )

        # Feature settings (ALGO1)
        from pointy.core.auto_match import Algo1_Settings
        feature_settings = Algo1_Settings(
            keypoint_algo=keypoint_algo,
            test_extraction=test_extraction,
            ref_extraction=ref_extraction,
            matching=matching,
            outlier=outlier
        )

        return Auto_Match_Settings(
            feature_settings=feature_settings,
            edge_settings=None,
            use_manual_prior=False
        )

    def update_results(self, candidates: int, inliers: int, coverage: float, rmse: float, rows: list[list]):
        """Update the results display."""
        self._results_panel.update_stats(candidates, inliers, coverage, rmse)
        self._results_panel.set_candidates(rows)

    def clear_results(self):
        """Clear the results display."""
        self._results_panel.clear()
