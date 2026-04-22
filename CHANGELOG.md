# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-04-21

### Added
* **Auto GCP Solver** - Standalone application (`pointy-auto-gcp`) for automatic GCP detection using feature matching and edge alignment
* **Auto Model Solver** - Standalone application (`pointy-auto-model`) for automatic geometric model fitting from GCP candidates
* New `Match_Pipeline` with feature extraction (AKAZE/ORB), matching, and outlier filtering (RANSAC/MAGSAC)
* Edge alignment optimization using genetic algorithm (`GA_Optimizer`) for refining image-to-image registration
* `GCP_Candidate_Set` and `Auto_Matcher` classes for managing match candidates

### Changed
* **Breaking**: Refactored GCP class API - renamed `test_pixel` to `pixel`, removed `projected` field
* **Breaking**: Serialization format updated - `test_pixel` key changed to `pixel` in JSON sidecar files
* Updated all Pointy code and tests to use new GCP `pixel` attribute
* Made ortho model sidecar loading errors fatal (removed try/except) for easier debugging

### Fixed
* `GCP_Residual` construction in `ortho_controller.py` now includes all required fields
* `to_gdal_format()` and `__str__` methods in Pointy GCP class use correct attribute names


## [1.1.0] - 2026-04-13

### Added
* Documentation site (Jupyter Book / MyST) with GitHub Actions deploy to GitHub Pages; user guide stubs for all major workflows
* Auto-Match background execution: `Auto_Match_Worker` QThread with progress bar and stage signals
* `Match_Results_Panel` showing summary stats and scrollable candidate table
* Candidate markers (cyan crosses) drawn on `Graphics_Image_View` for auto-match results
* `is_loading` state on `Test_Image_Viewer` to guard against operating on partially loaded images

### Fixed
* Auto-Match run button now blocked while image is loading; errors caught and shown in status bar instead of crashing


## [1.0.3] - 2026-04-12

### Added
* Auto Match panel UI shell with algorithm selection (AKAZE/ORB), extraction/matching/rejection settings, and results display
* Auto_Match_Controller skeleton with signal wiring
* `pointy/core/auto_match.py` with `Match_Algo`, `Matcher_Type`, `Rejection_Method` enums and `Auto_Match_Settings` dataclass
* `pointy/core/match/` package with backend pipeline classes: `Feature_Extractor` (AKAZE/ORB), `Feature_Matcher`, `Outlier_Filter` (RANSAC/MAGSAC), `GCP_Candidate_Set`, `Auto_Matcher`, `Match_Result`
* Tabbed Sidebar "Match" tab and Main Window controller wiring

### Changed
* Sidebar max width 400px → 450px; tab labels abbreviated and styling reduced for compact display
* Auto-GCP solver design document updated with UI wireframe, parameter tables, and Phase 0 completion

### Note
* Auto Match is **not yet operational** — UI and backend skeleton exist, but pipeline is not wired to controller and reference chip fetching is not implemented.

## [1.0.2] - 2026-04-12

### Added
* `GCP.source` field (`str`, default `'manual'`) and `GCP.metadata` field (`dict`) on the `GCP` dataclass
* `Collection_Nav_Panel` now displays the basename of the current image below the image counter.
* Auto-GCP solver design document updated with UI design, `Match_Algo` enum, manual GCP prior integration strategy, and revised phased implementation plan.

### Changed
* GCP persistence moved to per-image sidecar files (`image.png.gcps.json`); collection-level GCP file and `gcp_file` config removed.
* `Ortho_Controller` re-warps automatically when a new model is fitted while already in ortho mode.
* Log file path is now absolute (project root `pointy.log`).

### Fixed
* Model fitting errors now logged with `logging.error` matching the status bar message.

### Removed
* Removed two broken integration tests (`test_oblique_camera_scenario`, `test_affine_model_fitting`) — invalid test data; covered by `terminus_core_python` tests.

## [1.0.1] - 2026-04-11

### Added
- **CLI tool**: `pointy-model-tester` for batch model testing and image warping with TPS/Affine/RPC support
- **TPS optimization**: Sparse grid interpolation for TPS warping (reduced from 28s to 6s using LinearNDInterpolator)
- **Dependencies**: Added `scipy>=1.10.0` for interpolation functions
- **New modules**:
  - `src/pointy/core/transformation.py` - Image warping with TPS/Affine/RPC support
  - `src/pointy/apps/model_tester/` - Model testing CLI application
  - `src/pointy/controllers/` - Controller layer for GUI
  - `src/pointy/core/ortho_model_persistence.py` - Orthorectification model persistence
- **Workflows**: `.windsurf/workflows/update-changelog.md` for changelog updates

### Changed
- **Dependencies**: Updated terminus-core-python requirement from 0.1.0 to 0.1.1 for catalog lazy loading support
- **GUI components**: Various updates to GCP panel, tools panel, viewers for orthorectification support
- **Project structure**: Added `apps/` and `controllers/` directories for better organization

### Fixed
- **Circular import**: Fixed CRS/Transformer circular dependency using pyproj directly in CRS.compute_transform_bounds()
- **TPS warping**: Fixed sparse grid bounds to cover full output extent (reduced NaN values from 68M to 32M)
- **GeoTIFF output**: Fixed transform calculation for UTM output CRS via CRS.compute_transform_bounds()
- **NameError**: Fixed undefined variable in model_tester main.py

## [1.0.0] - 2026-03-29

### Added
- Initial release of GCP Picker application
- Test image viewer with mousewheel zoom and middle-click pan
- Reference viewer with Leaflet map integration
- Collection management with TOML configuration support
- Sidebar with navigation controls for image collections
- Image view control panel with brightness, contrast, min/max pixel adjustment
- Histogram visualization for image pixel distribution
- Auto-stretch (DRA) functionality for automatic contrast enhancement
- Metadata panel showing cursor position (lat/lon/alt for reference, pixel values for test)
- Ground control point (GCP) management and visualization
- Command-line interface with `-c` flag for loading collections on startup
- GDAL integration for GeoTIFF and raster format support
- WMS client for fetching reference imagery from web services

