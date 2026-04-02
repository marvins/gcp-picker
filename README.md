# Pointy-McPointface - Ground-Control-Point Generator

A PyQt6-based GUI application for selecting ground control points between test imagery and reference sources with progressive orthorectification capabilities.

## Features

- **Pointy Dual Viewer Interface**: Side-by-side display of test image and reference source
- **Multiple Reference Sources**: Support for WMS, WMTS, and GDAL virtual rasters
- **Interactive Point Selection**: Click to select corresponding points in both viewers
- **GCP Management**: Add, edit, delete, and manage ground control points
- **Progressive Orthorectification**: RPC-based orthorectification that updates as you add GCPs
- **File I/O**: Save and load GCPs in multiple formats (JSON, CSV, text)
- **Real-time Updates**: Automatic orthorectification when sufficient GCPs are available

## Installation

### Prerequisites

- Python 3.12+
- GDAL library (for geospatial raster support)

### Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install GDAL (system-specific)
# macOS:
brew install gdal

# Ubuntu/Debian:
sudo apt-get install gdal-bin libgdal-dev

# Windows: Use OSGeo4W or conda
```

## Usage

### Basic Workflow

1. **Load Test Image**: Click "Load Image" in the left panel or use File → Open Test Image
2. **Select Reference Source**: Choose between WMS/WMTS or GDAL virtual raster in the right panel
3. **Select Corresponding Points**:
   - Click a point in the test image (left viewer)
   - Click the corresponding point in the reference source (right viewer)
   - GCP is automatically created from the pair
4. **Enable Orthorectification**: Toggle View → Enable Orthorectification (requires 3+ GCPs)
5. **Save GCPs**: Use File → Save GCPs to persist your work

### Reference Sources

#### WMS/WMTS
1. Enter service URL (e.g., `https://maps.wien.gv.at/wms`)
2. Click "Get Layers" to retrieve available layers
3. Select layer and coordinate system
4. Set bounding box and image size
5. Click "Load WMS"

#### GDAL Virtual Raster
1. Click "Browse" to select a .vrt file or any raster
2. Click "Load GDAL Source"

### GCP Management

- **View GCPs**: Bottom panel shows all GCPs in a table
- **Edit GCPs**: Click table cells to modify coordinates
- **Delete GCPs**: Select row and click "Remove"
- **Clear All**: Remove all GCPs with "Clear All" button

### Orthorectification

- Requires minimum 3 GCPs
- Uses RPC data if available in GeoTIFF
- Updates progressively as more GCPs are added
- Output saved as `_ortho.tif` file

## File Formats

### GCP Files
- **JSON**: Complete project data with metadata
- **CSV**: Tabular format for spreadsheet use
- **Text**: Simple space-delimited format

### Supported Image Formats
- GeoTIFF (.tif, .tiff)
- JPEG (.jpg, .jpeg)
- PNG (.png)
- Various GDAL-supported formats

## Keyboard Shortcuts

- `Ctrl+O`: Open test image
- `Ctrl+S`: Save GCPs
- `Ctrl+L`: Load GCPs
- `Ctrl+Q`: Exit application

## Architecture

### Core Components

- **MainWindow**: Main application window and layout
- **TestImageViewer**: Left panel for test imagery
- **ReferenceViewer**: Right panel for reference sources
- **GCPManager**: GCP table and management interface
- **Orthorectifier**: RPC-based orthorectification engine

### Data Flow

1. User selects points in both viewers
2. GCPProcessor creates GCP objects
3. GCPManager displays and manages GCPs
4. Orthorectifier processes images when enabled
5. Results displayed back in TestImageViewer

## Dependencies

### Core Libraries
- **PyQt6**: GUI framework
- **GDAL**: Geospatial raster processing
- **NumPy**: Array operations
- **OpenCV**: Image processing
- **Requests**: HTTP client for WMS

### Optional Dependencies
- **SciPy**: Advanced resampling (falls back to nearest neighbor)
- **Pillow**: Image format support

## Troubleshooting

### Common Issues

1. **GDAL Import Error**: Install GDAL system package and set GDAL_DATA environment variable
2. **WMS Connection Failed**: Check service URL and network connectivity
3. **Orthorectification Fails**: Ensure 3+ GCPs and valid RPC data
4. **Image Loading Issues**: Verify file format and permissions

### Performance Tips

- Use smaller image sizes for WMS requests
- Limit GCP count to essential points
- Enable orthorectification only when needed
- Use appropriate zoom levels

## Development

### Project Structure
```
pointy_mcpointface/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── src/
│   └── pointy/            # Main package directory
│       ├── __init__.py
│       ├── main_window.py     # Main application window
│       ├── viewers/           # Image viewer components
│       │   ├── test_image_viewer.py
│       │   └── reference_viewer.py
│       ├── widgets/           # UI widgets
│       │   ├── image_canvas.py
│       │   ├── zoom_controls.py
│       │   ├── gcp_manager.py
│       │   └── status_panel.py
│       └── core/              # Core functionality
│           ├── gcp.py
│           ├── gcp_processor.py
│           ├── orthorectifier.py
│           ├── wms_client.py
│           └── gdal_reader.py
└── README.md
```

### Extending the Application

- Add new reference source types in `ReferenceViewer`
- Implement additional orthorectification methods in `Orthorectifier`
- Add custom GCP validation in `GCP_Processor`
- Extend file format support in `GCP_Processor`
