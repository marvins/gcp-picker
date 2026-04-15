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


def visualize_results(test_image: np.ndarray, ref_image: np.ndarray, candidate_rows: list[tuple[float, float, float, float]], output_dir: Path, manual_gcps: list[tuple[float, float, float, float]] | None = None, bounds: dict[str, float] | None = None) -> None:
    """Visualize GCPs on test and reference images using Plotly.

    Args:
        test_image: Test image array.
        ref_image: Reference image array.
        candidate_rows: List of (px_x, px_y, lon, lat) tuples for candidate GCPs.
        output_dir: Directory to save output images.
        manual_gcps: Optional list of (px_x, px_y, lon, lat) tuples for manual GCPs.
        bounds: Optional geographic bounds dict with sw_lat, sw_lon, ne_lat, ne_lon for geo-to-pixel transform.
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

    test_norm = normalize_image(test_image).astype(np.float32)
    # Convert reference image to uint8 [0,255] for Plotly
    ref_norm = ref_image

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
    manual_gcps_scaled = [(px_x / test_scale, px_y / test_scale, lon, lat) for px_x, px_y, lon, lat in manual_gcps] if manual_gcps else None
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

    # Add manual GCPs to test image (green markers)
    if manual_gcps_scaled:
        manual_x = [px_x for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_y = [px_y for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_text = [f'M{i+1}<br>({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled)]

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
                hovertemplate='<b>Manual GCP %{text}</b><extra></extra>'
            ),
            row=1, col=1
        )

    # Add auto GCPs to test image (red markers)
    auto_x = [px_x for px_x, px_y, lon, lat in candidate_rows_scaled]
    auto_y = [px_y for px_x, px_y, lon, lat in candidate_rows_scaled]
    auto_text = [f'A{i+1}<br>({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled)]

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
            hovertemplate='<b>Auto GCP %{text}</b><extra></extra>'
        ),
        row=1, col=1
    )

    # Add manual GCPs to reference image (green markers) using geo-to-pixel transform
    if manual_gcps_scaled and bounds:
        manual_ref_x = []
        manual_ref_y = []
        for px_x, px_y, lon, lat in manual_gcps_scaled:
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            manual_ref_x.append(ref_px)
            manual_ref_y.append(ref_py)
        manual_ref_text = [f'M{i+1}<br>({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(manual_gcps_scaled)]

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
                hovertemplate='<b>Manual GCP %{text}</b><extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )

    # Add auto GCPs to reference image (red markers) using geo-to-pixel transform
    if bounds:
        auto_ref_x = []
        auto_ref_y = []
        for px_x, px_y, lon, lat in candidate_rows_scaled:
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            auto_ref_x.append(ref_px)
            auto_ref_y.append(ref_py)
        auto_ref_text = [f'A{i+1}<br>({lon:.4f}, {lat:.4f})' for i, (px_x, px_y, lon, lat) in enumerate(candidate_rows_scaled)]

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
                hovertemplate='<b>Auto GCP %{text}</b><extra></extra>',
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

    if manual_gcps_scaled:
        manual_x = [px_x for px_x, px_y, lon, lat in manual_gcps_scaled]
        manual_y = [px_y for px_x, px_y, lon, lat in manual_gcps_scaled]
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
                hovertemplate='<b>Manual GCP %{text}</b><extra></extra>'
            )
        )

    auto_x = [px_x for px_x, px_y, lon, lat in candidate_rows_scaled]
    auto_y = [px_y for px_x, px_y, lon, lat in candidate_rows_scaled]
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
            hovertemplate='<b>Auto GCP %{text}</b><extra></extra>'
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

    # Add manual GCPs to reference image using geo-to-pixel transform
    if manual_gcps_scaled and bounds:
        manual_ref_x = []
        manual_ref_y = []
        for px_x, px_y, lon, lat in manual_gcps_scaled:
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            manual_ref_x.append(ref_px)
            manual_ref_y.append(ref_py)
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
                hovertemplate='<b>Manual GCP %{text}</b><extra></extra>'
            )
        )

    # Add auto GCPs to reference image using geo-to-pixel transform
    if bounds:
        auto_ref_x = []
        auto_ref_y = []
        for px_x, px_y, lon, lat in candidate_rows_scaled:
            ref_px, ref_py = geo_to_pixel_ref(lon, lat)
            auto_ref_x.append(ref_px)
            auto_ref_y.append(ref_py)
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
                hovertemplate='<b>Auto GCP %{text}</b><extra></extra>'
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
