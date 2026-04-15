# Auto-GCP Tester

Standalone CLI tool for testing the auto-match feature extraction and matching pipeline without the GUI. Useful for debugging and parameter tuning.

## Installation

The auto-gcp-tester is installed as part of the pointy-mcpointface package:

```bash
pip install -e .
```

## Usage

### Generate a sample configuration file

```bash
pointy-auto-gcp-tester -g
```

This creates `options.toml` in the current directory with default values and comments. Edit this file to configure your test.

### Use a custom configuration file

```bash
pointy-auto-gcp-tester -c my_config.toml
```

### Enable verbose logging

```bash
pointy-auto-gcp-tester -c my_config.toml -v
```

## Configuration File Format

The configuration file uses TOML format with the following sections:

### `[test_image]`
- `path`: Path to the test image file

### `[reference]`
- `type`: Either `"file"` (local image) or `"leaflet"` (map tiles)
- `file_path`: Path to reference image (if type="file")
- `sw_lat`, `sw_lon`, `ne_lat`, `ne_lon`: Geographic bounds of the reference image

### `[gcps]` (optional)
- `file`: Path to manual GCP JSON file for use as a prior in matching

### `[auto_match.test_extraction]`
- `algo`: Feature detection algorithm (`"AKAZE"` or `"ORB"`)
- `max_features`: Maximum number of features to detect
- `pyramid_level`: Image pyramid level for downsampling (higher = faster, fewer features)
- `clahe`: Enable CLAHE histogram equalization
- `akaze_threshold`, `akaze_n_octaves`, `akaze_n_octave_layers`: AKAZE-specific parameters
- `orb_scale_factor`, `orb_n_levels`, `orb_edge_threshold`, `orb_patch_size`: ORB-specific parameters

### `[auto_match.ref_extraction]`
- `max_features`: Maximum features for reference image
- `pyramid_level`: Pyramid level for reference (typically 0 for full resolution)
- `clahe`: Enable CLAHE for reference

### `[auto_match.matching]`
- `matcher`: Matcher type (`"FLANN"` or `"BF"`)
- `ratio_test`: Lowe ratio test threshold

### `[auto_match.outlier]`
- `rejection_method`: Outlier rejection method (`"RANSAC"` or `"MAGSAC"`)
- `inlier_threshold`: Inlier threshold in pixels

## Example Configuration

```toml
[test_image]
path = "/path/to/test_image.png"

[reference]
type = "file"
file_path = "/path/to/reference_image.png"
sw_lat = 35.3
sw_lon = -119.1
ne_lat = 35.5
ne_lon = -118.9

[gcps]
file = "/path/to/manual_gcps.json"

[auto_match.test_extraction]
algo = "AKAZE"
max_features = 2000
pyramid_level = 2
clahe = true
akaze_threshold = 0.001
akaze_n_octaves = 4
akaze_n_octave_layers = 4

[auto_match.ref_extraction]
max_features = 2000
pyramid_level = 0
clahe = false

[auto_match.matching]
matcher = "FLANN"
ratio_test = 0.75

[auto_match.outlier]
rejection_method = "RANSAC"
inlier_threshold = 3.0
```

## Output

The tool outputs:
- Pipeline runtime
- Number of candidate GCPs generated
- Number of inliers after outlier rejection
- Coverage percentage
- RMSE (root mean square error) in pixels
- List of candidate GCPs with pixel and geographic coordinates

## Limitations

- Currently only supports `type="file"` reference imagery (local images)
- Leaflet reference type requires headless browser support and is not yet implemented in CLI mode
