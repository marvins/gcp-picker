# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

