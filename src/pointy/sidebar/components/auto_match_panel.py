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
#    File:    auto_match_panel.py
#    Author:  Marvin Smith
#    Date:    04/12/2026
#
"""
Auto Match Panel - Settings and results for automatic GCP matching.
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


class Match_Results_Panel(QWidget):
    """Results display for the automatic GCP matcher.

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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_stats_row())
        layout.addWidget(self._build_table(), stretch=1)

    def _build_header(self) -> QLabel:
        lbl = QLabel("Results")
        lbl.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 10pt;
                color: #333;
                padding: 4px 2px 2px 2px;
            }
        """)
        return lbl

    def _build_stats_row(self) -> QWidget:
        row = QWidget()
        h   = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        def chip(label: str) -> tuple[QLabel, QLabel]:
            cell = QWidget()
            cell.setStyleSheet("""
                QWidget {
                    background: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
            """)
            v = QVBoxLayout(cell)
            v.setContentsMargins(4, 3, 4, 3)
            v.setSpacing(1)
            title = QLabel(label)
            title.setStyleSheet("font-size: 7pt; color: #666; font-weight: bold; border: none;")
            title.setAlignment(Qt.AlignCenter)
            value = QLabel("—")
            value.setStyleSheet("font-size: 9pt; color: #111; border: none;")
            value.setAlignment(Qt.AlignCenter)
            v.addWidget(title)
            v.addWidget(value)
            return cell, value

        cand_cell,  self._candidates_lbl = chip("Candidates")
        inlr_cell,  self._inliers_lbl   = chip("Inliers")
        cov_cell,   self._coverage_lbl  = chip("Coverage")
        rmse_cell,  self._rmse_lbl      = chip("RMSE")

        for cell in (cand_cell, inlr_cell, cov_cell, rmse_cell):
            h.addWidget(cell, stretch=1)

        return row

    def _build_table(self) -> QTableWidget:
        self._table = QTableWidget(0, len(self._HEADERS))
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget {
                font-size: 8pt;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #e8e8e8;
                font-weight: bold;
                font-size: 7pt;
                padding: 2px;
                border: 1px solid #ccc;
            }
            QTableWidget::item:alternate {
                background-color: #f9f9f9;
            }
        """)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, len(self._HEADERS)):
            hdr.setSectionResizeMode(col, QHeaderView.Stretch)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return self._table

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_stats(self, candidates: int, inliers: int,
                     coverage: float | None, rmse: float | None):
        """Refresh the four summary stat chips.

        Args:
            candidates: Total keypoints / ratio-test survivors.
            inliers:    Matches surviving outlier rejection.
            coverage:   Spatial coverage 0–1, or None.
            rmse:       RMSE in pixels after fitting, or None.
        """
        self._candidates_lbl.setText(str(candidates))
        self._inliers_lbl.setText(str(inliers))
        self._coverage_lbl.setText(f"{coverage * 100:.0f}%" if coverage is not None else "—")
        self._rmse_lbl.setText(f"{rmse:.2f} px" if rmse is not None else "—")

    def set_candidates(self, rows: list[tuple[float, float, float, float]]):
        """Populate the candidate table.

        Args:
            rows: Sequence of (px_x, px_y, lon, lat) for each candidate GCP.
        """
        self._table.setRowCount(0)
        for i, (px_x, px_y, lon, lat) in enumerate(rows):
            self._table.insertRow(i)
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setForeground(QColor(80, 80, 80))
            self._table.setItem(i, 0, idx_item)
            self._table.setItem(i, 1, QTableWidgetItem(f"{px_x:.1f}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"{px_y:.1f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"{lon:.6f}"))
            self._table.setItem(i, 4, QTableWidgetItem(f"{lat:.6f}"))
        self._table.scrollToTop()

    def clear(self):
        """Reset stats and clear the candidate table."""
        self._candidates_lbl.setText("—")
        self._inliers_lbl.setText("—")
        self._coverage_lbl.setText("—")
        self._rmse_lbl.setText("—")
        self._table.setRowCount(0)


class Auto_Match_Panel(QWidget):
    """Settings panel and results display for the automatic GCP matcher.

    Signals:
        run_requested: Emitted when the user clicks "Run Auto-Match",
            carrying the current ``Auto_Match_Settings``.
    """

    run_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Algo group sits above the scroll area, always visible
        layout.addWidget(self._build_algo_group())

        # Remaining groups go into a scroll area so they can expand freely
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
        # No stretch - groups should expand to fill available vertical space

        self._on_algo_changed(0)

        scroll = QScrollArea()
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        layout.addWidget(scroll, stretch=1)

        # Progress bar (hidden by default, shown during execution)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.run_btn = QPushButton("Run Auto-Match")
        self.run_btn.setToolTip("Run all stages and populate the GCP table with candidates")
        self.run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.run_btn.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.run_btn)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _style_group(group: QGroupBox):
        """Apply bold title and generous vertical padding to a QGroupBox."""
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
            }
        """)

    def _build_algo_group(self) -> QGroupBox:
        """Algorithm selector and manual GCP prior option."""
        group = QGroupBox("Algorithm")
        form = QFormLayout(group)
        form.setSpacing(6)

        self.algo_combo = QComboBox()
        self.algo_combo.setMinimumWidth(120)
        self.algo_combo.setStyleSheet("color: black; background-color: white;")
        for algo in Match_Algo:
            self.algo_combo.addItem(algo.value.upper(), userData=algo)
        self.algo_combo.setCurrentIndex(0)
        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        form.addRow("Method", self.algo_combo)

        self.manual_prior_cb = QCheckBox("Use Manual GCPs as Prior")
        self.manual_prior_cb.setChecked(True)
        self.manual_prior_cb.setToolTip(
            "Seed the reference footprint and spatial filter from existing manual GCPs"
        )
        form.addRow(self.manual_prior_cb)

        self._style_group(group)
        return group

    def _build_akaze_params_group(self) -> QGroupBox:
        """AKAZE-specific tunable parameters."""
        self._akaze_group = QGroupBox("AKAZE Parameters")
        form = QFormLayout(self._akaze_group)
        form.setSpacing(6)

        self.akaze_threshold_spin = QDoubleSpinBox()
        self.akaze_threshold_spin.setRange(0.0001, 0.05)
        self.akaze_threshold_spin.setSingleStep(0.0005)
        self.akaze_threshold_spin.setDecimals(4)
        self.akaze_threshold_spin.setValue(0.001)
        self.akaze_threshold_spin.setToolTip(
            "Detector response threshold — lower detects more keypoints"
        )
        form.addRow("Threshold", self.akaze_threshold_spin)

        self.akaze_octaves_spin = QSpinBox()
        self.akaze_octaves_spin.setRange(1, 8)
        self.akaze_octaves_spin.setValue(4)
        self.akaze_octaves_spin.setToolTip("Maximum octave evolution of the image")
        form.addRow("Octaves", self.akaze_octaves_spin)

        self.akaze_octave_layers_spin = QSpinBox()
        self.akaze_octave_layers_spin.setRange(1, 8)
        self.akaze_octave_layers_spin.setValue(4)
        self.akaze_octave_layers_spin.setToolTip("Sub-levels per scale octave")
        form.addRow("Octave Layers", self.akaze_octave_layers_spin)

        self._style_group(self._akaze_group)
        return self._akaze_group

    def _build_orb_params_group(self) -> QGroupBox:
        """ORB-specific tunable parameters."""
        self._orb_group = QGroupBox("ORB Parameters")
        form = QFormLayout(self._orb_group)
        form.setSpacing(6)

        self.orb_scale_factor_spin = QDoubleSpinBox()
        self.orb_scale_factor_spin.setRange(1.05, 2.0)
        self.orb_scale_factor_spin.setSingleStep(0.05)
        self.orb_scale_factor_spin.setDecimals(2)
        self.orb_scale_factor_spin.setValue(1.2)
        self.orb_scale_factor_spin.setToolTip(
            "Pyramid decimation ratio — smaller = finer scale steps"
        )
        form.addRow("Scale Factor", self.orb_scale_factor_spin)

        self.orb_n_levels_spin = QSpinBox()
        self.orb_n_levels_spin.setRange(1, 16)
        self.orb_n_levels_spin.setValue(8)
        self.orb_n_levels_spin.setToolTip("Number of pyramid levels")
        form.addRow("Levels", self.orb_n_levels_spin)

        self.orb_edge_threshold_spin = QSpinBox()
        self.orb_edge_threshold_spin.setRange(1, 64)
        self.orb_edge_threshold_spin.setValue(31)
        self.orb_edge_threshold_spin.setToolTip(
            "Border size (px) where features are not detected; should match Patch Size"
        )
        form.addRow("Edge Threshold", self.orb_edge_threshold_spin)

        self.orb_patch_size_spin = QSpinBox()
        self.orb_patch_size_spin.setRange(1, 64)
        self.orb_patch_size_spin.setValue(31)
        self.orb_patch_size_spin.setToolTip(
            "Patch size for the oriented BRIEF descriptor"
        )
        form.addRow("Patch Size", self.orb_patch_size_spin)

        self._style_group(self._orb_group)
        return self._orb_group

    def _build_extraction_group(self) -> QGroupBox:
        """Feature extraction settings."""
        group = QGroupBox("Feature Extraction")
        form = QFormLayout(group)
        form.setSpacing(6)

        self.max_features_spin = QSpinBox()
        self.max_features_spin.setRange(100, 20000)
        self.max_features_spin.setSingleStep(500)
        self.max_features_spin.setValue(2000)
        form.addRow("Max Features", self.max_features_spin)

        self.pyramid_combo = QComboBox()
        self.pyramid_combo.setMinimumWidth(120)
        self.pyramid_combo.setStyleSheet("color: black; background-color: white;")
        pyramid_labels = ["0 — full res", "1 — 1/2 res", "2 — 1/4 res", "3 — 1/8 res"]
        for i, label in enumerate(pyramid_labels):
            self.pyramid_combo.addItem(label, userData=i)
        self.pyramid_combo.setCurrentIndex(2)
        form.addRow("Pyramid Level", self.pyramid_combo)

        self.clahe_cb = QCheckBox()
        self.clahe_cb.setChecked(True)
        self.clahe_cb.setToolTip("Apply CLAHE contrast enhancement before extraction (recommended for IR imagery)")
        form.addRow("CLAHE Pre-proc", self.clahe_cb)

        self._style_group(group)
        return group

    def _build_matching_group(self) -> QGroupBox:
        """Descriptor matching settings."""
        group = QGroupBox("Matching")
        form = QFormLayout(group)
        form.setSpacing(6)

        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.5, 1.0)
        self.ratio_spin.setSingleStep(0.05)
        self.ratio_spin.setDecimals(2)
        self.ratio_spin.setValue(0.75)
        self.ratio_spin.setToolTip("Lowe ratio test threshold — lower is stricter")
        form.addRow("Ratio Test", self.ratio_spin)

        self.matcher_combo = QComboBox()
        self.matcher_combo.setMinimumWidth(120)
        self.matcher_combo.setStyleSheet("color: black; background-color: white;")
        for m in Matcher_Type:
            self.matcher_combo.addItem(m.value.upper(), userData=m)
        self.matcher_combo.setCurrentIndex(1)
        form.addRow("Matcher", self.matcher_combo)

        self._style_group(group)
        return group

    def _build_rejection_group(self) -> QGroupBox:
        """Outlier rejection settings."""
        group = QGroupBox("Outlier Rejection")
        form = QFormLayout(group)
        form.setSpacing(6)

        self.rejection_combo = QComboBox()
        self.rejection_combo.setMinimumWidth(120)
        self.rejection_combo.setStyleSheet("color: black; background-color: white;")
        for r in Rejection_Method:
            self.rejection_combo.addItem(r.value.upper(), userData=r)
        self.rejection_combo.setCurrentIndex(0)
        form.addRow("Method", self.rejection_combo)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.5, 20.0)
        self.threshold_spin.setSingleStep(0.5)
        self.threshold_spin.setDecimals(1)
        self.threshold_spin.setValue(3.0)
        self.threshold_spin.setSuffix(" px")
        form.addRow("Inlier Threshold", self.threshold_spin)

        self._style_group(group)
        return group

    def _build_results_group(self) -> QWidget:
        """Rich results panel: summary stats + scrollable candidate table."""
        self._results_panel = Match_Results_Panel()
        return self._results_panel

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_akaze_params(self) -> AKAZE_Params:
        """Return AKAZE parameters from the panel controls."""
        return AKAZE_Params(
            threshold       = self.akaze_threshold_spin.value(),
            n_octaves       = self.akaze_octaves_spin.value(),
            n_octave_layers = self.akaze_octave_layers_spin.value(),
        )

    def get_orb_params(self) -> ORB_Params:
        """Return ORB parameters from the panel controls."""
        return ORB_Params(
            scale_factor   = self.orb_scale_factor_spin.value(),
            n_levels       = self.orb_n_levels_spin.value(),
            edge_threshold = self.orb_edge_threshold_spin.value(),
            patch_size     = self.orb_patch_size_spin.value(),
        )

    def get_test_extraction(self) -> Feature_Extraction_Settings:
        """Return test-image extraction settings from the panel controls."""
        return Feature_Extraction_Settings(
            max_features  = self.max_features_spin.value(),
            pyramid_level = self.pyramid_combo.currentData(),
            clahe         = self.clahe_cb.isChecked(),
            akaze         = self.get_akaze_params(),
            orb           = self.get_orb_params(),
        )

    def get_ref_extraction(self) -> Feature_Extraction_Settings:
        """Return reference-chip extraction settings (fixed: full-res, no CLAHE)."""
        return Feature_Extraction_Settings(
            max_features  = self.max_features_spin.value(),
            pyramid_level = 0,
            clahe         = False,
            akaze         = self.get_akaze_params(),
            orb           = self.get_orb_params(),
        )

    def get_matching(self) -> Matching_Settings:
        """Return matching settings from the panel controls."""
        return Matching_Settings(
            ratio_test = self.ratio_spin.value(),
            matcher    = self.matcher_combo.currentData(),
        )

    def get_outlier(self) -> Outlier_Settings:
        """Return outlier rejection settings from the panel controls."""
        return Outlier_Settings(
            rejection_method = self.rejection_combo.currentData(),
            inlier_threshold = self.threshold_spin.value(),
        )

    def get_settings(self) -> Auto_Match_Settings:
        """Return the current panel state as an ``Auto_Match_Settings``."""
        return Auto_Match_Settings(
            algo             = self.algo_combo.currentData(),
            use_manual_prior = self.manual_prior_cb.isChecked(),
            test_extraction  = self.get_test_extraction(),
            ref_extraction   = self.get_ref_extraction(),
            matching         = self.get_matching(),
            outlier          = self.get_outlier(),
        )

    def update_results(self, candidates: int, inliers: int,
                       coverage: float | None, rmse: float | None,
                       candidate_rows: list[tuple[float, float, float, float]] | None = None):
        """Populate the results panel after a run.

        Args:
            candidates:     Total keypoints detected in the test image.
            inliers:        Matches surviving outlier rejection.
            coverage:       Spatial coverage fraction 0–1, or None.
            rmse:           Residual RMSE in pixels after fitting, or None.
            candidate_rows: Optional list of (px_x, px_y, lon, lat) for each
                            candidate GCP, populates the candidate table.
        """
        self._results_panel.update_stats(candidates, inliers, coverage, rmse)
        if candidate_rows is not None:
            self._results_panel.set_candidates(candidate_rows)

    def clear_results(self):
        """Reset all result labels and clear the candidate table."""
        self._results_panel.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

    def set_progress(self, value: int, text: str | None = None):
        """Update progress bar value and optional text.

        Args:
            value: Progress percentage 0-100.
            text: Optional override for progress text (e.g., stage name).
        """
        self.progress_bar.setValue(value)
        if text is not None:
            self.progress_bar.setFormat(text)

    def set_progress_visible(self, visible: bool):
        """Show or hide the progress bar."""
        self.progress_bar.setVisible(visible)
        if not visible:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p%")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_run_clicked(self):
        self.run_requested.emit(self.get_settings())

    def set_run_button_enabled(self, enabled: bool):
        """Enable or disable the Run Auto-Match button.

        Called by controller during background execution.
        """
        self.run_btn.setEnabled(enabled)
        if enabled:
            self.run_btn.setText("Run Auto-Match")
        else:
            self.run_btn.setText("Running...")

    def _on_algo_changed(self, _index: int):
        """Show only the param group relevant to the selected algorithm."""
        algo = self.algo_combo.currentData()
        self._akaze_group.setVisible(algo == Match_Algo.AKAZE)
        self._orb_group.setVisible(algo == Match_Algo.ORB)
