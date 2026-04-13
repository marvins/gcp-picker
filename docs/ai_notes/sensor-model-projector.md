# Sensor Model Projector Design

## Overview

This document outlines the design for a sensor-based projector that models camera geometry using intrinsic and extrinsic parameters. This enables precise georeferencing for aerial and satellite imagery by modeling the physical camera platform rather than using empirical transformations (Affine, TPS, RPC).

## Motivation

Current transformation models:
- **Affine**: Linear only, cannot model sensor distortions
- **TPS**: Empirical, requires many GCPs, no physical basis
- **RPC**: Empirical polynomial approximation, requires 9+ GCPs

A sensor model projector would:
- Provide physically-grounded transformations
- Enable calibration from sparse GCPs
- Support platform-specific parameters (pitch, roll, yaw, lever arm)
- Integrate with auto-GCP solver for automated calibration
- Allow cross-platform model sharing (same camera, different flights)

---

## Mathematical Model

### Coordinate Frames

1. **Image Frame (u, v)**: Pixel coordinates (origin at top-left)
2. **Camera Frame (X_c, Y_c, Z_c)**: 3D coordinates with origin at camera perspective center
3. **Body Frame (X_b, Y_b, Z_b)**: Platform body coordinates (aircraft/satellite)
4. **World Frame (X_w, Y_w, Z_w)**: ECEF or geographic coordinates

### Intrinsic Model (Pinhole Camera)

Standard pinhole camera model with radial and tangential distortion:

**Projection equation (normalized coordinates):**
$$x_n = \frac{u - c_x}{f_x}$$
$$y_n = \frac{v - c_y}{f_y}$$

**Radial distortion:**
$$r^2 = x_n^2 + y_n^2$$
$$x_d = x_n (1 + k_1 r^2 + k_2 r^4 + k_3 r^6)$$
$$y_d = y_n (1 + k_1 r^2 + k_2 r^4 + k_3 r^6)$$

**Tangential distortion:**
$$x_d = x_d + 2p_1 x_n y_n + p_2 (r^2 + 2x_n^2)$$
$$y_d = y_d + p_1 (r^2 + 2y_n^2) + 2p_2 x_n y_n$$

**Intrinsic parameters:**
- `f_x`, `f_y`: Focal length in pixels (can be derived from mm focal length and sensor size)
- `c_x`, `c_y`: Principal point (optical center) in pixels
- `k₁`, `k₂`, `k₃`: Radial distortion coefficients
- `p₁`, `p₂`: Tangential distortion coefficients

### Extrinsic Model (Tait-Bryan Angles)

Transformation from body frame to camera frame using pitch (φ), roll (θ), yaw (ψ):

**Rotation matrix (XYZ convention):**
$$R = R_z(\psi) R_y(\theta) R_x(\phi)$$

Where:
$$R_x(\phi) = \begin{bmatrix} 1 & 0 & 0 \\ 0 & \cos(\phi) & -\sin(\phi) \\ 0 & \sin(\phi) & \cos(\phi) \end{bmatrix}$$

$$R_y(\theta) = \begin{bmatrix} \cos(\theta) & 0 & \sin(\theta) \\ 0 & 1 & 0 \\ -\sin(\theta) & 0 & \cos(\theta) \end{bmatrix}$$

$$R_z(\psi) = \begin{bmatrix} \cos(\psi) & -\sin(\psi) & 0 \\ \sin(\psi) & \cos(\psi) & 0 \\ 0 & 0 & 1 \end{bmatrix}$$

**Extrinsic parameters:**
- `φ` (phi): Pitch angle (rotation about X-axis)
- `θ` (theta): Roll angle (rotation about Y-axis)
- `ψ` (psi): Yaw angle (rotation about Z-axis)

### Calibration Parameters

**Lever Arm Offset:**
Translation from platform GPS/IMU reference point to camera perspective center:
$$T_{\text{lever}} = [\Delta X, \Delta Y, \Delta Z] \quad \text{(in body frame)}$$

**Boresight Matrix:**
Fine-tuning adjustment for camera mounting:
$$R_{\text{boresight}} = R_z(\Delta \psi) R_y(\Delta \theta) R_x(\Delta \phi)$$

Where $\Delta \phi, \Delta \theta, \Delta \psi$ are small correction angles (typically < 1°).

### Complete Transformation

**Body to World:**
$$P_{\text{world}} = R_{\text{body to world}} P_{\text{body}} + T_{\text{body to world}}$$

**Camera to Body:**
$$P_{\text{body}} = R_{\text{camera to body}} P_{\text{camera}} + T_{\text{lever}}$$

**Combined:**
$$P_{\text{world}} = R_{\text{body to world}} (R_{\text{camera to body}} P_{\text{camera}} + T_{\text{lever}}) + T_{\text{body to world}}$$

**Forward (pixel → geographic):**
1. Pixel → Normalized image coordinates (intrinsic)
2. Normalized → Camera frame (inverse intrinsic)
3. Camera → Body frame (extrinsic + boresight)
4. Body → World frame (platform pose from EXIF/GPS)
5. World → Geographic (ECEF → lat/lon)

**Inverse (geographic → pixel):**
1. Geographic → World frame (lat/lon → ECEF)
2. World → Body frame (inverse platform pose)
3. Body → Camera frame (inverse extrinsic - boresight)
4. Camera → Normalized image coordinates (intrinsic)
5. Normalized → Pixel (intrinsic with distortion)

---

## Class Design

### Sensor_Projector (Base Class)

```python
from dataclasses import dataclass
from tmns.geo.proj.base import Projector
from tmns.geo.coord import Geographic, Pixel

@dataclass
class Intrinsic_Params:
    """Pinhole camera intrinsic parameters."""
    f_x: float  # Focal length x (pixels)
    f_y: float  # Focal length y (pixels)
    c_x: float  # Principal point x (pixels)
    c_y: float  # Principal point y (pixels)
    k1: float = 0.0  # Radial distortion k1
    k2: float = 0.0  # Radial distortion k2
    k3: float = 0.0  # Radial distortion k3
    p1: float = 0.0  # Tangential distortion p1
    p2: float = 0.0  # Tangential distortion p2

@dataclass
class Extrinsic_Params:
    """Camera extrinsic parameters (Tait-Bryan angles)."""
    pitch: float  # Rotation about X-axis (radians)
    roll: float   # Rotation about Y-axis (radians)
    yaw: float    # Rotation about Z-axis (radians)

@dataclass
class Calibration_Params:
    """Calibration corrections."""
    lever_arm: tuple[float, float, float]  # [ΔX, ΔY, ΔZ] in body frame (meters)
    boresight_pitch: float = 0.0  # Correction to pitch (radians)
    boresight_roll: float = 0.0   # Correction to roll (radians)
    boresight_yaw: float = 0.0    # Correction to yaw (radians)

class Sensor_Projector(Projector):
    """Base class for sensor-based projectors.

    Implements the Projector interface using intrinsic and extrinsic
    camera parameters to perform physically-grounded transformations.
    """

    def __init__(
        self,
        intrinsic: Intrinsic_Params,
        extrinsic: Extrinsic_Params,
        calibration: Calibration_Params | None = None
    ):
        self._intrinsic = intrinsic
        self._extrinsic = extrinsic
        self._calibration = calibration or Calibration_Params((0.0, 0.0, 0.0))
        self._platform_pose: tuple[Geographic, Extrinsic_Params] | None = None

    @property
    def transformation_type(self) -> Transformation_Type:
        return Transformation_Type.SENSOR

    def update_model(
        self,
        intrinsic: Intrinsic_Params | None = None,
        extrinsic: Extrinsic_Params | None = None,
        calibration: Calibration_Params | None = None
    ) -> None:
        """Update sensor model parameters."""
        if intrinsic is not None:
            self._intrinsic = intrinsic
        if extrinsic is not None:
            self._extrinsic = extrinsic
        if calibration is not None:
            self._calibration = calibration

    def set_platform_pose(self, position: Geographic, orientation: Extrinsic_Params) -> None:
        """Set platform position and orientation from EXIF/GPS/IMU."""
        self._platform_pose = (position, orientation)

    def source_to_geographic(self, pixel: Pixel) -> Geographic:
        """Transform pixel to geographic using sensor model."""
        # Implementation: pixel → normalized → camera → body → world → geographic
        pass

    def geographic_to_source(self, geo: Geographic) -> Pixel:
        """Transform geographic to pixel using sensor model."""
        # Implementation: geographic → world → body → camera → normalized → pixel
        pass

    def solve_from_gcps(self, gcps: list[tuple[Pixel, Geographic]]) -> None:
        """Calibrate sensor parameters from GCPs."""
        # Implementation: bundle adjustment or least-squares solver
        pass
```

### Derived Classes

**Pinhole_Projector**: Standard pinhole model (base implementation)

**Fisheye_Projector**: For wide-angle fisheye lenses

**RPC_Sensor_Projector**: Hybrid model using RPC as intrinsic + extrinsic

---

## Solver Design

### Calibration from GCPs

**Objective**: Minimize reprojection error by optimizing intrinsic, extrinsic, and calibration parameters.

**Cost function:**
$$E(\theta) = \sum_i \| \text{project}(P_{\text{world},i}, \theta) - P_{\text{pixel},i} \|^2$$

Where θ includes:
- Intrinsic parameters (f_x, f_y, c_x, c_y, k₁, k₂, k₃, p₁, p₂)
- Extrinsic parameters (φ, θ, ψ) per image
- Calibration parameters (lever arm, boresight)

**Solver approaches:**

1. **Bundle Adjustment** (recommended):
   - Simultaneous optimization of all parameters
   - Uses Levenberg-Marquardt or Gauss-Newton
   - Libraries: `scipy.optimize.least_squares`, `ceres-solver`
   - Handles multiple images with shared calibration parameters

2. **Two-step approach** (simpler):
   - Step 1: Solve extrinsics per image (assuming fixed intrinsics)
   - Step 2: Solve intrinsics and calibration from all images
   - Iterate until convergence

3. **Auto-GCP integration**:
   - Use auto-GCP solver to generate initial GCP matches
   - Refine sensor parameters using solver
   - Iterate: better parameters → better GCP matches → better parameters

**Minimum GCP requirements:**
- Intrinsic only: 5+ GCPs (f_x, f_y, c_x, c_y, distortion)
- Extrinsic per image: 3+ GCPs (pitch, roll, yaw)
- Full calibration: 10+ GCPs across multiple images

---

## Integration with Auto-GCP Solver

### Workflow

```
1. Load image with EXIF/GPS data
   → Extract platform position (lat/lon, altitude)
   → Extract initial orientation (if available from IMU)

2. Create initial Sensor_Projector
   → Use manufacturer specs for intrinsics (focal length, sensor size)
   → Use EXIF orientation for initial extrinsics
   → Set calibration to identity (zero corrections)

3. Run auto-GCP solver
   → Match image features to reference map
   → Generate initial GCP correspondences

4. Calibrate sensor model
   → Solve for calibration parameters using GCPs
   → Refine intrinsics if needed
   → Update projector with optimized parameters

5. Re-run auto-GCP with calibrated model
   → Better model → more accurate matches
   → Iterate until convergence

6. Final orthorectification
   → Use calibrated Sensor_Projector for warping
```

### Benefits

- **Fewer GCPs needed**: Physical model constrains solution space
- **Cross-flight consistency**: Same camera = same intrinsics across flights
- **Automated calibration**: Auto-GCP + solver enables hands-off calibration
- **Quality metrics**: Reprojection error provides quality assessment
- **Model reuse**: Calibrated model can be applied to new images from same platform

---

## Implementation Plan

### Phase 1 — Core Sensor Model
- [ ] Implement `Intrinsic_Params`, `Extrinsic_Params`, `Calibration_Params` dataclasses
- [ ] Implement `Sensor_Projector` base class
- [ ] Implement pinhole projection functions (forward/inverse with distortion)
- [ ] Implement coordinate frame transformations (camera ↔ body ↔ world)
- [ ] Add sensor model to `Transformation_Type` enum
- [ ] Implement `compute_remap_coordinates` for sensor projector

### Phase 2 — Solver
- [ ] Implement cost function for reprojection error
- [ ] Implement bundle adjustment solver using `scipy.optimize.least_squares`
- [ ] Implement two-step solver as fallback
- [ ] Add parameter bounds and constraints
- [ ] Add solver diagnostics (covariance, residuals)

### Phase 3 — Auto-GCP Integration
- [ ] Define interface between auto-GCP solver and sensor projector
- [ ] Implement iterative calibration workflow
- [ ] Add convergence detection
- [ ] Add quality metrics (RMSE, parameter uncertainty)

### Phase 4 — Advanced Features
- [ ] Support for multiple camera models (fisheye, RPC)
- [ ] Support for multi-camera rigs (stereo, arrays)
- [ ] Temporal calibration (camera drift over time)
- [ ] Export/import calibrated models (JSON, sidecar files)

---

## References

- Hartley, R. & Zisserman, A. (2004). *Multiple View Geometry in Computer Vision*
- OpenCV Camera Calibration: https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
- Ceres Solver: http://ceres-solver.org/
- Brown, D.C. (1971). "Close-range camera calibration"
- Photogrammetry: Standard aerial triangulation methods

---

## Open Questions

1. **Initial parameter estimation**: How to get good starting values for optimization?
   - Use EXIF data where available
   - Use manufacturer specifications
   - Use Affine/RPC fit as initial guess

2. **Parameter coupling**: Should we fix some parameters during solving?
   - Often fix focal length if known from specs
   - Fix principal point to image center if sensor not characterized
   - Allow all parameters to float for full calibration

3. **Multiple images**: How to handle multi-image calibration?
   - Bundle adjustment with shared intrinsics
   - Separate extrinsics per image
   - Shared calibration parameters (lever arm, boresight)

4. **Quality control**: How to detect and reject outlier GCPs?
   - RANSAC during solver
   - Post-solver residual filtering
   - Iterative re-weighting

5. **Performance**: Solver speed for large GCP sets?
   - Sparse Jacobian for bundle adjustment
   - GPU acceleration for projection
   - Hierarchical solving (coarse to fine)
