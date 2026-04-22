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
#    File:    model_solver_result.py
#    Author:  Marvin Smith
#    Date:    04/19/2026
#
"""
Model Solver Result - Results from the auto model solver.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Model_Solver_Result:
    """Results from the auto model solver.

    Contains the refined model, alignment statistics, and solver metrics.
    """

    # Model results
    refined_model: Any  # The refined projector model (RPC, TPS, etc.)
    original_model: Any  # The original model for comparison

    # Alignment statistics
    success: bool
    n_candidates: int
    n_inliers: int
    coverage_percent: float
    rmse: float

    # Solver metrics
    solver_iterations: int
    solver_converged: bool
    solver_fitness: float

    # Timing
    elapsed_seconds: float

    # Error information
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization."""
        return {
            'success': self.success,
            'n_candidates': self.n_candidates,
            'n_inliers': self.n_inliers,
            'coverage_percent': self.coverage_percent,
            'rmse': self.rmse,
            'solver_iterations': self.solver_iterations,
            'solver_converged': self.solver_converged,
            'solver_fitness': self.solver_fitness,
            'elapsed_seconds': self.elapsed_seconds,
            'error_message': self.error_message
        }

    def to_log_string(self) -> str:
        """Generate formatted log string of solver results.

        Returns:
            Multi-line string with key solver metrics formatted for logging.
        """
        lines = [
            f"  Candidates: {self.n_candidates}",
            f"  Inliers: {self.n_inliers}",
            f"  Coverage: {self.coverage_percent:.1f}%",
            f"  RMSE: {self.rmse:.2f} pixels",
            f"  Solver iterations: {self.solver_iterations}",
            f"  Solver converged: {self.solver_converged}",
            f"  Solver fitness: {self.solver_fitness:.6f}",
            f"  Elapsed time: {self.elapsed_seconds:.2f}s"
        ]
        return "\n".join(lines)
