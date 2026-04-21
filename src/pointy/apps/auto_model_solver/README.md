# Auto Model Solver

Standalone CLI tool for fitting transformation models using Sobel edge alignment with genetic algorithms. Optimizes affine transform parameters through differential evolution to align test and reference imagery.

## Installation

The auto-model-solver is installed as part of the pointy-mcpointface package:

```bash
pip install -e .
```

## Usage

### Generate a sample configuration file

```bash
pointy-auto-model-solver -g
```

This creates `options.toml` in the current directory with default values and comments. Edit this file to configure your test.

### Use a custom configuration file

```bash
pointy-auto-model-solver -c my_config.toml
```

### Enable verbose logging

```bash
pointy-auto-model-solver -c my_config.toml -v
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
- `file`: Path to manual GCP JSON file for warm-starting the optimization

### `[auto_match.edge_settings]`
- `edge_dilation`: Edge dilation factor for robustness
- `ga_popsize`: Population size for genetic algorithm
- `ga_maxiter`: Maximum iterations for genetic algorithm
- `ga_mutation`: Mutation factor (0-1)
- `ga_recombination`: Recombination factor (0-1)

### `[auto_match.debug]` (optional)
- `save_sobel_images`: Save Sobel edge images to disk for debugging (true/false)
- `output_directory`: Directory path for debug output files (default: "temp/debug")
- `save_intermediate_steps`: Save additional intermediate processing steps (true/false)

## Algorithm Pipeline

1. **Sobel Edge Detection**: Convert both images to edge maps using gradient magnitude
2. **Differential Evolution**: Optimize 6-DOF affine transform parameters
3. **Synthetic GCP Extraction**: Generate grid-pattern GCPs from optimized transform
4. **Model Fitting**: Fit Affine or RPC model based on GCP count
5. **GeoTiff Generation**: Optional georectified output

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

[auto_match.edge_settings]
edge_dilation = 2
ga_popsize = 30
ga_maxiter = 100
ga_mutation = 0.7
ga_recombination = 0.9

[auto_match.debug]
save_sobel_images = true
output_directory = "temp/debug"
save_intermediate_steps = false
```

## Output

The tool outputs:
- Optimization runtime
- Number of synthetic GCPs generated
- Final optimization score
- Fitted model parameters
- Georectified GeoTiff (optional)

## Features

- **Warm-starting**: Use existing models to initialize optimization
- **Manual GCP Integration**: Combine manual GCPs with synthetic ones
- **Multiple Reference Sources**: File-based or Leaflet map tiles
- **Robust Edge Detection**: Configurable edge dilation and thresholding
