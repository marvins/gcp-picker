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
#    File:    auto_model_solver_panel.py
#    Author:  Marvin Smith
#    Date:    04/19/2026
#
"""
Auto Model Solver Panel - Settings and results for edge-based model fitting.
"""

# Third-Party Libraries
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QCheckBox,
                             QDoubleSpinBox, QSpinBox, QFormLayout, QSizePolicy,
                             QScrollArea, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QProgressBar)

# Project Libraries
from pointy.core.auto_match import (Auto_Match_Settings, Edge_Alignment_Settings)


class Auto_Model_Solver_Results_Panel(QWidget):
    """Results display for the auto model solver.

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


class Auto_Model_Solver_Panel(QWidget):
    """Settings panel and results display for the auto model solver.

    Signals:
        run_requested: Emitted when the user clicks "Run Auto Model Solver",
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

        # Edge processing group
        layout.addWidget(self._build_edge_group())

        # Genetic algorithm group
        layout.addWidget(self._build_ga_group())

        # Results group
        layout.addWidget(self._build_results_group())

        layout.addStretch()

    def _build_edge_group(self) -> QGroupBox:
        """Build the edge processing settings group."""
        group = QGroupBox("Edge Processing")
        layout = QHBoxLayout(group)

        self._edge_dilation = QSpinBox()
        self._edge_dilation.setRange(0, 10)
        self._edge_dilation.setValue(3)

        layout.addWidget(QLabel("Edge Dilation:"))
        layout.addWidget(self._edge_dilation)
        layout.addWidget(QLabel("pixels"))
        layout.addStretch()

        return group

    def _build_ga_group(self) -> QGroupBox:
        """Build the genetic algorithm settings group."""
        group = QGroupBox("Genetic Algorithm")
        layout = QVBoxLayout(group)

        # Population and iterations
        pop_iter_layout = QHBoxLayout()
        self._ga_popsize = QSpinBox()
        self._ga_popsize.setRange(5, 50)
        self._ga_popsize.setValue(15)
        self._ga_maxiter = QSpinBox()
        self._ga_maxiter.setRange(50, 500)
        self._ga_maxiter.setValue(200)

        pop_iter_layout.addWidget(QLabel("Population:"))
        pop_iter_layout.addWidget(self._ga_popsize)
        pop_iter_layout.addWidget(QLabel("Max Iterations:"))
        pop_iter_layout.addWidget(self._ga_maxiter)
        pop_iter_layout.addStretch()

        # Recombination and mutation
        recomb_mut_layout = QHBoxLayout()
        self._ga_recombination = QDoubleSpinBox()
        self._ga_recombination.setRange(0.1, 1.0)
        self._ga_recombination.setValue(0.7)
        self._ga_recombination.setDecimals(2)
        self._ga_recombination.setSingleStep(0.1)

        self._ga_mutation = QDoubleSpinBox()
        self._ga_mutation.setRange(0.1, 1.0)
        self._ga_mutation.setValue(0.7)
        self._ga_mutation.setDecimals(2)
        self._ga_mutation.setSingleStep(0.1)

        recomb_mut_layout.addWidget(QLabel("Recombination:"))
        recomb_mut_layout.addWidget(self._ga_recombination)
        recomb_mut_layout.addWidget(QLabel("Mutation:"))
        recomb_mut_layout.addWidget(self._ga_mutation)
        recomb_mut_layout.addStretch()

        # Search bounds
        bounds_layout = QHBoxLayout()
        self._search_bounds = QDoubleSpinBox()
        self._search_bounds.setRange(10.0, 200.0)
        self._search_bounds.setValue(50.0)
        self._search_bounds.setDecimals(1)
        self._search_bounds.setSingleStep(5.0)

        bounds_layout.addWidget(QLabel("Search Bounds:"))
        bounds_layout.addWidget(self._search_bounds)
        bounds_layout.addWidget(QLabel("pixels"))
        bounds_layout.addStretch()

        layout.addLayout(pop_iter_layout)
        layout.addLayout(recomb_mut_layout)
        layout.addLayout(bounds_layout)

        return group

    def _build_results_group(self) -> QGroupBox:
        """Build the results display and control group."""
        group = QGroupBox("Results")
        layout = QVBoxLayout(group)

        self._results_panel = Auto_Model_Solver_Results_Panel()
        layout.addWidget(self._results_panel)

        # Run button
        self._run_btn = QPushButton("Run Model Fitter")
        self._run_btn.clicked.connect(self._on_run_clicked)
        layout.addWidget(self._run_btn)

        return group

    def _on_run_clicked(self):
        """Handle run button click."""
        settings = self.get_settings()
        self.run_requested.emit(settings)

    def get_settings(self) -> Auto_Match_Settings:
        """Get current settings as Auto_Match_Settings object."""
        # Edge settings (Edge-based alignment)
        edge_settings = Edge_Alignment_Settings(
            edge_dilation=self._edge_dilation.value(),
            ga_popsize=self._ga_popsize.value(),
            ga_maxiter=self._ga_maxiter.value(),
            ga_recombination=self._ga_recombination.value(),
            ga_mutation=self._ga_mutation.value(),
            search_bounds_px=self._search_bounds.value()
        )

        return Auto_Match_Settings(
            feature_settings=None,
            edge_settings=edge_settings,
            use_manual_prior=False
        )

    def update_results(self, candidates: int, inliers: int, coverage: float, rmse: float, rows: list[list]):
        """Update the results display."""
        self._results_panel.update_stats(candidates, inliers, coverage, rmse)
        self._results_panel.set_candidates(rows)

    def clear_results(self):
        """Clear the results display."""
        self._results_panel.clear()
