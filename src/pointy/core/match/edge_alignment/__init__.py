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
#    File:    __init__.py
#    Author:  Marvin Smith
#    Date:    04/17/2026
#
"""
pointy.core.match.edge_alignment — Edge-based GA automatic GCP matching.

This module implements the edge-based alignment approach using Sobel gradient
magnitudes and genetic algorithm optimization to find the best homography/affine
transformation between test and reference images.

Algorithm Overview
------------------
1. Compute 2D Sobel gradient magnitude (edge images) for both test and reference
2. Optionally dilate edges for robustness
3. Use manual GCPs to establish a rough initial transform (optional prior)
4. Run genetic algorithm to optimize transform parameters by maximizing
   edge alignment (via NCC or mutual information)
5. Extract synthetic GCPs from the converged transform

Public API (TBD)
----------------
Edge_Aligner        — Main orchestrator for edge alignment
Sobel_Edges         — Edge detection with optional dilation
GA_Optimizer        — Genetic algorithm for transform parameter search
"""

# Edge-based genetic algorithm alignment
from pointy.core.match.edge_alignment.edge_aligner import Edge_Aligner
from pointy.core.match.edge_alignment.ga_optimizer import GA_Optimizer, GA_Result, GA_Settings
from pointy.core.match.edge_alignment.sobel_edges import Sobel_Edges, Sobel_Edge_Settings

__all__ = [
    'Edge_Aligner',
    'GA_Optimizer',
    'GA_Result',
    'GA_Settings',
    'Sobel_Edges',
    'Sobel_Edge_Settings',
]
