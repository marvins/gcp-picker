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
#    File:    plot.py
#    Author:  Marvin Smith
#    Date:    04/14/2026
#
"""
Visualization utilities for auto-gcp-tester.
"""

# Python Standard Libraries
import logging
from pathlib import Path

# Third-Party Libraries
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def visualize_results(test_image: np.ndarray, ref_image: np.ndarray, candidate_rows: list[tuple[float, float, float, float]], output_dir: Path, manual_gcps: list | None = None, bounds: dict[str, float] | None = None, inlier_mask: np.ndarray | None = None, raw_match_pixels: np.ndarray | None = None, raw_match_ref_pixels: np.ndarray | None = None) -> None:
    """Visualize GCPs on test and reference images using Plotly.

    Args:
        test_image: Test image array.
        ref_image: Reference image array.
        candidate_rows: List of (px_x, px_y, lon, lat) tuples for candidate GCPs.
        output_dir: Directory to save output images.
        manual_gcps: Optional list of GCP objects for manual GCPs.
        bounds: Optional geographic bounds dict with sw_lat, sw_lon, ne_lat, ne_lon for geo-to-pixel transform.
        inlier_mask: Optional boolean array marking which candidates are RANSAC inliers.
        raw_match_pixels: Optional Nx2 array of test image pixel coords for raw kNN matches (before ratio test).
        raw_match_ref_pixels: Optional Nx2 array of reference image pixel coords for raw kNN matches.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Saving visualization results to {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalize images for display
    def normalize_image(img: np.ndarray) -> np.ndarray:
        if img.dtype == np.uint16:
            # Use percentile-based normalization for better contrast
            p2, p98 = np.percentile(img, (2, 98))
            img = img.astype(np.float32)
            img = np.clip((img - p2) / (p98 - p2), 0, 1)
        elif img.dtype == np.uint8:
            img = img.astype(np.float32) / 255.0
        elif img.dtype != np.float32 and img.dtype != np.float64:
            img = img.astype(np.float32) / 255.0
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        if img.shape[2] == 1:
            img = np.repeat(img, 3, axis=2)
        return np.clip(img, 0, 1)

    test_norm = normalize_image(test_image)
    # Convert reference image to uint8 [0,255] for Plotly
    ref_norm = ref_image
    # Convert both to uint8 [0,255] for Plotly compatibility
    test_norm = (test_norm * 255).astype(np.uint8)
    if ref_norm.dtype != np.uint8:
        if ref_norm.dtype == np.float32 or ref_norm.dtype == np.float64:
            ref_norm = (ref_norm * 255).astype(np.uint8)
        else:
            ref_norm = ref_norm.astype(np.uint8)

    # Debug logging
    logger.info(f"Test norm dtype: {test_norm.dtype}, shape: {test_norm.shape}, min: {test_norm.min():.4f}, max: {test_norm.max():.4f}")
    logger.info(f"Ref norm dtype: {ref_norm.dtype}, shape: {ref_norm.shape}, min: {ref_norm.min()}, max: {ref_norm.max()}")

    # Adaptive downsampling: downsample images larger than 4k x 4k
    def downsample_to_max(img: np.ndarray, max_size: int = 4096) -> tuple[np.ndarray, float]:
        """Downsample image until it's smaller than max_size in both dimensions.

        Returns:
            tuple of (downsampled_image, total_scale_factor)
        """
        h, w = img.shape[:2]
        scale_factor = 1.0
        while h > max_size or w > max_size:
            img = img[::2, ::2]
            h, w = img.shape[:2]
            scale_factor *= 2
        return img, scale_factor

    test_norm, test_scale = downsample_to_max(test_norm, max_size=4096)
    ref_norm, ref_scale = downsample_to_max(ref_norm, max_size=4096)

    logger.info(f"Downsampled test image by {test_scale}x to {test_norm.shape}")
    logger.info(f"Downsampled reference image by {ref_scale}x to {ref_norm.shape}")

    # Scale GCP coordinates accordingly
    # Convert GCP objects to tuples if needed
    if manual_gcps and len(manual_gcps) > 0:
        if hasattr(manual_gcps[0], 'pixel'):
            # GCP objects
            manual_gcps_scaled = [(gcp.pixel.x_px / test_scale, gcp.pixel.y_px / test_scale, gcp.geographic.longitude_deg, gcp.geographic.latitude_deg) for gcp in manual_gcps]
        else:
            # Already tuples
            manual_gcps_scaled = [(px_x / test_scale, px_y / test_scale, lon, lat) for px_x, px_y, lon, lat in manual_gcps]
    else:
        manual_gcps_scaled = None
    candidate_rows_scaled = [(px_x / test_scale, px_y / test_scale, lon, lat) for px_x, px_y, lon, lat in candidate_rows]

    # Geo-to-pixel transformation for reference image (uses downsampled resolution)
    def geo_to_pixel_ref(lon: float, lat: float) -> tuple[float, float]:
        """Convert geo coordinates to pixel coordinates on reference image."""
        if bounds is None:
            return 0, 0
        px_x = ((lon - bounds['sw_lon']) / (bounds['ne_lon'] - bounds['sw_lon'])) * ref_norm.shape[1]
        px_y = ((bounds['ne_lat'] - lat) / (bounds['ne_lat'] - bounds['sw_lat'])) * ref_norm.shape[0]
        return px_x, px_y

    # Create side-by-side visualization
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Test Image with GCPs', 'Reference Image with GCPs'),
        horizontal_spacing=0.02
    )

    # Add test image
    fig.add_trace(
        go.Image(z=test_norm),
        row=1, col=1
    )

    # Add reference image
    fig.add_trace(
        go.Image(z=ref_norm),
        row=1, col=2
    )

    # Add raw kNN matches (before ratio test) to test image (blue dots)
    if raw_match_pixels is not None and len(raw_match_pixels) > 0:
        raw_x = raw_match_pixels[:, 0] / test_scale
        raw_y = raw_match_pixels[:, 1] / test_scale
        fig.add_trace(
            go.Scattergl(
                x=raw_x,
                y=raw_y,
                mode='markers',
                marker=dict(color='blue', size=4, symbol='circle', opacity=0.3),
                name='Ratio Test Candidates',
                legendgroup='raw',
                hovertemplate='Ratio Test Candidate<extra></extra>'
            ),
            row=1, col=1
        )

    # Add manual GCPs to test image (green markers)
    if manual_gcps_scaled:
        manual_x = [px_x for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_y = [px_y for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_text = [f'M{i+1}' for i in range(len(manual_gcps_scaled))]
        manual_hover = [f'M{i+1}: ({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled)]

        fig.add_trace(
            go.Scattergl(
                x=manual_x,
                y=manual_y,
                mode='markers+text',
                marker=dict(color='green', size=10, symbol='cross'),
                text=manual_text,
                textposition='top right',
                textfont=dict(size=8, color='green'),
                name='Manual GCPs',
                legendgroup='manual',
                hovertext=manual_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            ),
            row=1, col=1
        )

    # Add auto GCPs to test image (separate inliers and candidates)
    if inlier_mask is not None and len(candidate_rows_scaled) == len(inlier_mask):
        # Separate inliers and candidates
        inlier_indices = np.where(inlier_mask)[0]
        candidate_indices = np.where(~inlier_mask)[0]

        # Add candidates (orange markers)
        if len(candidate_indices) > 0:
            cand_x = [candidate_rows_scaled[i][0] for i in candidate_indices]
            cand_y = [candidate_rows_scaled[i][1] for i in candidate_indices]
            cand_hover = [f'C{i+1}: ({candidate_rows_scaled[i][2]:.4f}, {candidate_rows_scaled[i][3]:.4f})' for i in candidate_indices]
            fig.add_trace(
                go.Scattergl(
                    x=cand_x,
                    y=cand_y,
                    mode='markers',
                    marker=dict(color='orange', size=8, symbol='circle', opacity=0.6),
                    name='Candidates (Ratio Test)',
                    legendgroup='candidates',
                    hovertext=cand_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                ),
                row=1, col=1
            )

        # Add inliers (red markers)
        if len(inlier_indices) > 0:
            inlier_x = [candidate_rows_scaled[i][0] for i in inlier_indices]
            inlier_y = [candidate_rows_scaled[i][1] for i in inlier_indices]
            inlier_text = [f'A{i+1}' for i in inlier_indices]
            inlier_hover = [f'A{i+1}: ({candidate_rows_scaled[i][2]:.4f}, {candidate_rows_scaled[i][3]:.4f})' for i in inlier_indices]
            fig.add_trace(
                go.Scattergl(
                    x=inlier_x,
                    y=inlier_y,
                    mode='markers+text',
                    marker=dict(color='red', size=10, symbol='cross'),
                    text=inlier_text,
                    textposition='top right',
                    textfont=dict(size=8, color='red'),
                    name='Inliers (RANSAC)',
                    legendgroup='inliers',
                    hovertext=inlier_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                ),
                row=1, col=1
            )
    else:
        # Fallback: show all as auto GCPs if no inlier_mask
        auto_x = [px_x for px_x, px_y, lon, lat in candidate_rows_scaled]
        auto_y = [px_y for px_x, px_y, lon, lat in candidate_rows_scaled]
        auto_text = [f'A{i+1}' for i in range(len(candidate_rows_scaled))]
        auto_hover = [f'A{i+1}: ({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled)]

        fig.add_trace(
            go.Scattergl(
                x=auto_x,
                y=auto_y,
                mode='markers+text',
                marker=dict(color='red', size=10, symbol='cross'),
                text=auto_text,
                textposition='top right',
                textfont=dict(size=8, color='red'),
                name='Auto GCPs',
                legendgroup='auto',
                hovertext=auto_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            ),
            row=1, col=1
        )

    # Add raw kNN matches (before ratio test) to reference image (blue dots)
    if raw_match_ref_pixels is not None and bounds and len(raw_match_ref_pixels) > 0:
        raw_ref_x = raw_match_ref_pixels[:, 0] / ref_scale
        raw_ref_y = raw_match_ref_pixels[:, 1] / ref_scale
        fig.add_trace(
            go.Scattergl(
                x=raw_ref_x,
                y=raw_ref_y,
                mode='markers',
                marker=dict(color='blue', size=4, symbol='circle', opacity=0.3),
                name='Raw kNN Matches (Before Ratio Test)',
                legendgroup='raw',
                hovertemplate='Raw Match<extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )

    # Add manual GCPs to reference image (green markers) using geo-to-pixel transform
    if manual_gcps_scaled and bounds:
        manual_ref_x = []
        manual_ref_y = []
        manual_ref_hover = []
        for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled):
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            manual_ref_x.append(ref_px)
            manual_ref_y.append(ref_py)
            manual_ref_hover.append(f'M{i+1}: ({lon:.4f}, {lat:.4f})')
        manual_ref_text = [f'M{i+1}' for i in range(len(manual_gcps_scaled))]

        fig.add_trace(
            go.Scattergl(
                x=manual_ref_x,
                y=manual_ref_y,
                mode='markers+text',
                marker=dict(color='green', size=10, symbol='cross'),
                text=manual_ref_text,
                textposition='top right',
                textfont=dict(size=8, color='green'),
                name='Manual GCPs',
                legendgroup='manual',
                hovertext=manual_ref_hover,
                hovertemplate='%{hovertext}<extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )

    # Add auto GCPs to reference image (separate inliers and candidates)
    if bounds and inlier_mask is not None and len(candidate_rows_scaled) == len(inlier_mask):
        # Separate inliers and candidates
        inlier_indices = np.where(inlier_mask)[0]
        candidate_indices = np.where(~inlier_mask)[0]

        # Add candidates (orange markers)
        if len(candidate_indices) > 0:
            cand_ref_x = []
            cand_ref_y = []
            cand_ref_hover = []
            for i in candidate_indices:
                px_x, px_y, lon, lat = candidate_rows_scaled[i]
                ref_px, ref_py = geo_to_pixel_ref(lon, lat)
                cand_ref_x.append(ref_px)
                cand_ref_y.append(ref_py)
                cand_ref_hover.append(f'C{i+1}: ({lon:.4f}, {lat:.4f})')
            fig.add_trace(
                go.Scattergl(
                    x=cand_ref_x,
                    y=cand_ref_y,
                    mode='markers',
                    marker=dict(color='orange', size=8, symbol='circle', opacity=0.6),
                    name='Candidates (Ratio Test)',
                    legendgroup='candidates',
                    hovertext=cand_ref_hover,
                    hovertemplate='%{hovertext}<extra></extra>',
                    showlegend=False
                ),
                row=1, col=2
            )

        # Add inliers (red markers)
        if len(inlier_indices) > 0:
            inlier_ref_x = []
            inlier_ref_y = []
            inlier_ref_hover = []
            for i in inlier_indices:
                px_x, px_y, lon, lat = candidate_rows_scaled[i]
                ref_px, ref_py = geo_to_pixel_ref(lon, lat)
                inlier_ref_x.append(ref_px)
                inlier_ref_y.append(ref_py)
                inlier_ref_hover.append(f'A{i+1}: ({lon:.4f}, {lat:.4f})')
            inlier_ref_text = [f'A{i+1}' for i in inlier_indices]
            fig.add_trace(
                go.Scattergl(
                    x=inlier_ref_x,
                    y=inlier_ref_y,
                    mode='markers+text',
                    marker=dict(color='red', size=10, symbol='cross'),
                    text=inlier_ref_text,
                    textposition='top right',
                    textfont=dict(size=8, color='red'),
                    name='Inliers (RANSAC)',
                    legendgroup='inliers',
                    hovertext=inlier_ref_hover,
                    hovertemplate='%{hovertext}<extra></extra>',
                    showlegend=False
                ),
                row=1, col=2
            )
    elif bounds:
        # Fallback: show all as auto GCPs if no inlier_mask
        auto_ref_x = []
        auto_ref_y = []
        auto_ref_hover = []
        for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled):
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            auto_ref_x.append(ref_px)
            auto_ref_y.append(ref_py)
            auto_ref_hover.append(f'A{i+1}: ({lon:.4f}, {lat:.4f})')
        auto_ref_text = [f'A{i+1}' for i in range(len(candidate_rows_scaled))]

        fig.add_trace(
            go.Scattergl(
                x=auto_ref_x,
                y=auto_ref_y,
                mode='markers+text',
                marker=dict(color='red', size=10, symbol='cross'),
                text=auto_ref_text,
                textposition='top right',
                textfont=dict(size=8, color='red'),
                name='Auto GCPs',
                legendgroup='auto',
                hovertext=auto_ref_hover,
                hovertemplate='%{hovertext}<extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )

    # Update layout
    fig.update_xaxes(showgrid=False, showticklabels=False, row=1, col=1)
    fig.update_yaxes(showgrid=False, showticklabels=False, row=1, col=1)
    fig.update_xaxes(showgrid=False, showticklabels=False, row=1, col=2)
    fig.update_yaxes(showgrid=False, showticklabels=False, row=1, col=2)
    fig.update_layout(
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Save as HTML
    side_by_side_path = output_dir / 'gcp_matches_side_by_side.html'
    fig.write_html(str(side_by_side_path))
    logger.info(f"Saved side-by-side visualization: {side_by_side_path}")

    # Create individual test image visualization
    fig_test = go.Figure()
    fig_test.add_trace(go.Image(z=test_norm))

    # Add raw kNN matches (before ratio test) to test image (blue dots)
    if raw_match_pixels is not None and len(raw_match_pixels) > 0:
        raw_x = raw_match_pixels[:, 0] / test_scale
        raw_y = raw_match_pixels[:, 1] / test_scale
        fig_test.add_trace(
            go.Scattergl(
                x=raw_x,
                y=raw_y,
                mode='markers',
                marker=dict(color='blue', size=4, symbol='circle', opacity=0.3),
                name='Raw kNN Matches (Before Ratio Test)',
                legendgroup='raw',
                hovertemplate='Raw Match<extra></extra>'
            )
        )

    if manual_gcps_scaled:
        manual_x = [px_x for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_y = [px_y for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_hover = [f'M{i+1}: ({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled)]
        fig_test.add_trace(
            go.Scattergl(
                x=manual_x,
                y=manual_y,
                mode='markers+text',
                marker=dict(color='green', size=10, symbol='cross'),
                text=[f'M{i+1}' for i in range(len(manual_gcps_scaled))],
                textposition='top right',
                textfont=dict(size=8, color='green'),
                name='Manual GCPs',
                legendgroup='manual',
                hovertext=manual_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            )
        )

    # Add auto GCPs to test image (separate inliers and candidates)
    if inlier_mask is not None and len(candidate_rows_scaled) == len(inlier_mask):
        # Separate inliers and candidates
        inlier_indices = np.where(inlier_mask)[0]
        candidate_indices = np.where(~inlier_mask)[0]

        # Add candidates (orange markers)
        if len(candidate_indices) > 0:
            cand_x = [candidate_rows_scaled[i][0] for i in candidate_indices]
            cand_y = [candidate_rows_scaled[i][1] for i in candidate_indices]
            cand_hover = [f'C{i+1}: ({candidate_rows_scaled[i][2]:.4f}, {candidate_rows_scaled[i][3]:.4f})' for i in candidate_indices]
            fig_test.add_trace(
                go.Scattergl(
                    x=cand_x,
                    y=cand_y,
                    mode='markers',
                    marker=dict(color='orange', size=8, symbol='circle', opacity=0.6),
                    name='Candidates (Ratio Test)',
                    legendgroup='candidates',
                    hovertext=cand_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                )
            )

        # Add inliers (red markers)
        if len(inlier_indices) > 0:
            inlier_x = [candidate_rows_scaled[i][0] for i in inlier_indices]
            inlier_y = [candidate_rows_scaled[i][1] for i in inlier_indices]
            inlier_text = [f'A{i+1}' for i in inlier_indices]
            inlier_hover = [f'A{i+1}: ({candidate_rows_scaled[i][2]:.4f}, {candidate_rows_scaled[i][3]:.4f})' for i in inlier_indices]
            fig_test.add_trace(
                go.Scattergl(
                    x=inlier_x,
                    y=inlier_y,
                    mode='markers+text',
                    marker=dict(color='red', size=10, symbol='cross'),
                    text=inlier_text,
                    textposition='top right',
                    textfont=dict(size=8, color='red'),
                    name='Inliers (RANSAC)',
                    legendgroup='inliers',
                    hovertext=inlier_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                )
            )
    else:
        # Fallback: show all as auto GCPs if no inlier_mask
        auto_x = [px_x for px_x, px_y, lon, lat in candidate_rows_scaled]
        auto_y = [px_y for px_x, px_y, lon, lat in candidate_rows_scaled]
        auto_hover = [f'A{i+1}: ({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled)]
        fig_test.add_trace(
            go.Scattergl(
                x=auto_x,
                y=auto_y,
                mode='markers+text',
                marker=dict(color='red', size=10, symbol='cross'),
                text=[f'A{i+1}' for i in range(len(candidate_rows_scaled))],
                textposition='top right',
                textfont=dict(size=8, color='red'),
                name='Auto GCPs',
                legendgroup='auto',
                hovertext=auto_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            )
        )

    fig_test.update_xaxes(showgrid=False, showticklabels=False)
    fig_test.update_yaxes(showgrid=False, showticklabels=False)
    fig_test.update_layout(
        height=800,
        showlegend=True,
        title='Test Image with GCPs'
    )

    test_labeled_path = output_dir / 'test_image_labeled.html'
    fig_test.write_html(str(test_labeled_path))
    logger.info(f"Saved test image with GCPs: {test_labeled_path}")

    # Create reference image visualization with GCPs
    fig_ref = go.Figure()
    fig_ref.add_trace(go.Image(z=ref_norm))

    # Add raw kNN matches (before ratio test) to reference image (blue dots)
    if raw_match_ref_pixels is not None and bounds and len(raw_match_ref_pixels) > 0:
        raw_ref_x = raw_match_ref_pixels[:, 0] / ref_scale
        raw_ref_y = raw_match_ref_pixels[:, 1] / ref_scale
        fig_ref.add_trace(
            go.Scattergl(
                x=raw_ref_x,
                y=raw_ref_y,
                mode='markers',
                marker=dict(color='blue', size=4, symbol='circle', opacity=0.3),
                name='Raw kNN Matches (Before Ratio Test)',
                legendgroup='raw',
                hovertemplate='Raw Match<extra></extra>'
            )
        )

    # Add manual GCPs to reference image using geo-to-pixel transform
    if manual_gcps_scaled and bounds:
        manual_ref_x = []
        manual_ref_y = []
        manual_ref_hover = []
        for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled):
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            manual_ref_x.append(ref_px)
            manual_ref_y.append(ref_py)
            manual_ref_hover.append(f'M{i+1}: ({lon:.4f}, {lat:.4f})')
        fig_ref.add_trace(
            go.Scattergl(
                x=manual_ref_x,
                y=manual_ref_y,
                mode='markers+text',
                marker=dict(color='green', size=10, symbol='cross'),
                text=[f'M{i+1}' for i in range(len(manual_gcps_scaled))],
                textposition='top right',
                textfont=dict(size=8, color='green'),
                name='Manual GCPs',
                legendgroup='manual',
                hovertext=manual_ref_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            )
        )

    # Add auto GCPs to reference image (separate inliers and candidates)
    if bounds and inlier_mask is not None and len(candidate_rows_scaled) == len(inlier_mask):
        # Separate inliers and candidates
        inlier_indices = np.where(inlier_mask)[0]
        candidate_indices = np.where(~inlier_mask)[0]

        # Add candidates (orange markers)
        if len(candidate_indices) > 0:
            cand_ref_x = []
            cand_ref_y = []
            cand_ref_hover = []
            for i in candidate_indices:
                px_x, px_y, lon, lat = candidate_rows_scaled[i]
                ref_px, ref_py = geo_to_pixel_ref(lon, lat)
                cand_ref_x.append(ref_px)
                cand_ref_y.append(ref_py)
                cand_ref_hover.append(f'C{i+1}: ({lon:.4f}, {lat:.4f})')
            fig_ref.add_trace(
                go.Scattergl(
                    x=cand_ref_x,
                    y=cand_ref_y,
                    mode='markers',
                    marker=dict(color='orange', size=8, symbol='circle', opacity=0.6),
                    name='Candidates (Ratio Test)',
                    legendgroup='candidates',
                    hovertext=cand_ref_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                )
            )

        # Add inliers (red markers)
        if len(inlier_indices) > 0:
            inlier_ref_x = []
            inlier_ref_y = []
            inlier_ref_hover = []
            for i in inlier_indices:
                px_x, px_y, lon, lat = candidate_rows_scaled[i]
                ref_px, ref_py = geo_to_pixel_ref(lon, lat)
                inlier_ref_x.append(ref_px)
                inlier_ref_y.append(ref_py)
                inlier_ref_hover.append(f'A{i+1}: ({lon:.4f}, {lat:.4f})')
            inlier_ref_text = [f'A{i+1}' for i in inlier_indices]
            fig_ref.add_trace(
                go.Scattergl(
                    x=inlier_ref_x,
                    y=inlier_ref_y,
                    mode='markers+text',
                    marker=dict(color='red', size=10, symbol='cross'),
                    text=inlier_ref_text,
                    textposition='top right',
                    textfont=dict(size=8, color='red'),
                    name='Inliers (RANSAC)',
                    legendgroup='inliers',
                    hovertext=inlier_ref_hover,
                    hovertemplate='%{hovertext}<extra></extra>'
                )
            )
    elif bounds:
        # Fallback: show all as auto GCPs if no inlier_mask
        auto_ref_x = []
        auto_ref_y = []
        auto_ref_hover = []
        for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled):
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            auto_ref_x.append(ref_px)
            auto_ref_y.append(ref_py)
            auto_ref_hover.append(f'A{i+1}: ({lon:.4f}, {lat:.4f})')
        fig_ref.add_trace(
            go.Scattergl(
                x=auto_ref_x,
                y=auto_ref_y,
                mode='markers+text',
                marker=dict(color='red', size=10, symbol='cross'),
                text=[f'A{i+1}' for i in range(len(candidate_rows_scaled))],
                textposition='top right',
                textfont=dict(size=8, color='red'),
                name='Auto GCPs',
                legendgroup='auto',
                hovertext=auto_ref_hover,
                hovertemplate='%{hovertext}<extra></extra>'
            )
        )

    fig_ref.update_xaxes(showgrid=False, showticklabels=False)
    fig_ref.update_yaxes(showgrid=False, showticklabels=False)
    fig_ref.update_layout(
        height=800,
        showlegend=True,
        title='Reference Image with GCP Locations'
    )

    ref_labeled_path = output_dir / 'reference_image_labeled.html'
    fig_ref.write_html(str(ref_labeled_path))
    logger.info(f"Saved reference image with GCPs: {ref_labeled_path}")
