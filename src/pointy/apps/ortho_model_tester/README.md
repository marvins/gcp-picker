# Ortho Model Tester

Standalone CLI tool for testing and validating orthorectification models. Loads fitted projector models (RPC, Affine) and applies them to test imagery to generate georectified outputs.

## Installation

The ortho-model-tester is installed as part of the pointy-mcpointface package:

```bash
pip install -e .
```

## Usage

### Basic usage with a fitted model

```bash
pointy-ortho-model-tester -i test_image.tif -m fitted_model.json -o rectified.tif
```

### Specify output CRS and GSD

```bash
pointy-ortho-model-tester \
    -i test_image.tif \
    -m fitted_model.json \
    -o rectified.tif \
    --crs EPSG:32611 \
    --gsd 1.0
```

### Load model from GeoTIFF sidecar

```bash
pointy-ortho-model-tester \
    -i test_image.tif \
    --use-sidecar \
    -o rectified.tif
```

## Command Line Options

- `-i, --input`: Input test image path (required)
- `-m, --model`: Path to fitted model JSON file (optional, can use sidecar)
- `-o, --output`: Output GeoTIFF path (required)
- `--crs`: Output CRS (default: EPSG:4326)
- `--gsd`: Ground sample distance in meters (optional)
- `--use-sidecar`: Load model from GeoTIFF sidecar file
- `-v, --verbose`: Enable verbose logging

## Model Formats

### JSON Model File
The model file should contain a serialized Projector object:
```json
{
  "type": "Affine",
  "transform_matrix": [[sx, sxy, tx], [syx, sy, ty], [0, 0, 1]],
  "crs": "EPSG:4326"
}
```

### GeoTIFF Sidecar
If the input image has an associated `.ortho.json` sidecar file, it will be automatically loaded unless `--model` is specified.

## Output

The tool generates:
- Georectified GeoTIFF with proper CRS and transform
- Log output with transformation details
- Performance metrics (warping time, output dimensions)

## Features

- **Multiple Model Types**: Supports Affine and RPC projectors
- **Flexible CRS**: Output to any coordinate reference system
- **GSD Control**: Specify output ground sample distance
- **Sidecar Support**: Automatic model loading from GeoTIFF sidecars
- **Performance Monitoring**: Detailed timing and size metrics
