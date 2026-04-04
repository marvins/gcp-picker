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

## TODO List

### High Priority
- [ ] Check and fix unsorted imports across codebase
- [ ] Implement RPC_Projection class for Rational Polynomial Camera models
- [ ] Implement TPS_Projection class for Thin Plate Spline transformations
- [ ] Create integration tests for RPC and TPS projection types

### Medium Priority
- [ ] Add comprehensive error handling throughout Projector API
- [ ] Implement model caching and persistence strategies
- [ ] Add coordinate validation and boundary condition testing
- [ ] Create GUI integration for Projector API selection
- [ ] Add real-world data tests with actual imagery

### Low Priority
- [ ] Optimize performance for large GCP datasets
- [ ] Add support for additional coordinate reference systems
- [ ] Implement advanced interpolation methods
- [ ] Create comprehensive documentation and examples

## Installation

### Prerequisites

- Python 3.14+ (for modern union syntax `|` and other features)
- GDAL library (for geospatial raster support)

### Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install GDAL (system-specific)
# macOS:
brew install gdal

# Ubuntu/Debian:
sudo apt-get install gdal-bin libgdal-dev

# Windows: Use OSGeo4W or conda
```

## Configuration

### API Keys and External Services

The application supports several external elevation data sources that require API keys. Configuration follows this precedence order:

1. **Command Line Arguments** (highest priority)
2. **Application Configuration File**
3. **Environment Variables** (lowest priority)

#### Supported Elevation Sources

##### Google Elevation API
- **Purpose**: Primary elevation data source with global coverage
- **Rate Limits**: Free tier: 2,500 requests per day, $0.005 per additional request
- **Required**: API key from Google Cloud Platform

##### OpenTopography API
- **Purpose**: SRTM and other scientific DEM datasets
- **Rate Limits**: Free tier: 200 requests/day (academics), 50/day (non-academics)
- **Required**: API key from OpenTopography portal
- **Register**: https://portal.opentopography.org/requestService?service=api

#### Configuration Methods

##### 1. Environment Variables (Recommended for Development)

```bash
# Google Elevation API
export GOOGLE_ELEVATION_API_KEY="your_google_api_key_here"

# OpenTopography API
export OPENTOPOGRAPHY_API_KEY="your_opentopography_api_key_here"

# Add to shell profile for persistence
echo 'export GOOGLE_ELEVATION_API_KEY="your_key"' >> ~/.bashrc
echo 'export OPENTOPOGRAPHY_API_KEY="your_key"' >> ~/.bashrc
```

##### 2. Application Configuration File

Create `~/.pointy/config.yaml`:

```yaml
# Elevation API Configuration
elevation:
  google:
    api_key: "your_google_api_key_here"
  opentopography:
    api_key: "your_opentopography_api_key_here"

# Cache settings
cache:
  enabled: true
  max_size_mb: 100
  directory: "~/.pointy/cache"

# Source preferences
sources:
  preferred_order: ["google", "opentopography", "aws"]
  fallback_enabled: true
```

##### 3. Command Line Arguments

```bash
# When running the application
python main.py --google-api-key "your_key" --opentopography-api-key "your_key"

# When running tests
pytest --google-api-key "your_key" --opentopography-api-key "your_key"
```

#### API Key Setup Instructions

##### Google Elevation API

1. **Create Google Cloud Project**
   - Visit https://console.cloud.google.com/
   - Create new project or select existing one

2. **Enable Elevation API**
   - Go to "APIs & Services" → "Library"
   - Search for "Elevation API"
   - Click "Enable"

3. **Create API Key**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the generated key

4. **Restrict API Key (Recommended)**
   - Edit the API key
   - Under "API restrictions", select "Restrict key"
   - Choose "Elevation API" only
   - Add IP or application restrictions as needed

##### OpenTopography API

1. **Register Account**
   - Visit https://portal.opentopography.org/
   - Click "Sign Up" to create account

2. **Request API Key**
   - Go to "My Account" → "Request Service"
   - Select "API" service
   - Fill out the form with your intended use
   - Academic users get higher rate limits

3. **Receive API Key**
   - Key will be emailed to you
   - Also available in "My Account" section

#### Fallback Behavior

The elevation system uses intelligent fallback:

1. **Primary Source**: Google Elevation API (if key available)
2. **Secondary Source**: OpenTopography (if key available)
3. **Tertiary Source**: AWS Terrain Tiles (no key required, limited coverage)

If no API keys are configured, the system will:
- Use AWS Terrain Tiles as primary source
- Log warnings about missing keys
- Still provide elevation data for supported regions

#### Testing Configuration

Test your API key configuration:

```python
from pointy.core.terrain import Manager

# Test configuration
manager = Manager.create_default()
coord = Geographic(40.7, -74.0)  # New York

elevation = manager.elevation(coord)
print(f"Elevation: {elevation}m")

# Check which sources are working
stats = manager.get_cache_stats()
print(f"Available sources: {stats['sources']}")
```

#### Troubleshooting API Keys

##### Google Elevation API Issues
- **Error**: "REQUEST_DENIED" → Check API key restrictions
- **Error**: "INVALID_ARGUMENT" → Verify coordinate format
- **Error**: "OVER_QUERY_LIMIT" → Wait and retry, or upgrade quota

##### OpenTopography API Issues
- **Error**: 401 Unauthorized → Check API key validity
- **Error**: 403 Forbidden → Rate limit exceeded
- **Error**: 404 Not Found → Check API endpoint URL

##### General Issues
- **Missing Elevation Data**: Use SKIP_ELEVATION_LOOKUP=true for testing
- **Import Errors**: Ensure GDAL is properly installed and configured
- **Network Issues**: Check internet connectivity for WMS/WMTS services

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
- **TestImageViewer**: Left panel for test imagery with async loading
- **ReferenceViewer**: Right panel for reference sources
- **GCPManager**: GCP table and management interface
- **Projector API**: Modern coordinate transformation interface
  - **Identity_Projection**: Pass-through transformations
  - **Affine_Projection**: Matrix-based transformations
  - **RPC_Projection**: Rational Polynomial Camera models (planned)
  - **TPS_Projection**: Thin Plate Spline transformations (planned)
- **Orthorectifier**: Legacy RPC-based orthorectification (being refactored)

### Data Flow

1. User selects points in both viewers
2. GCPProcessor creates GCP objects with coordinate validation
3. GCPManager displays and manages GCPs
4. Projector API performs coordinate transformations:
   - source ↔ geographic ↔ destination mappings
   - Roundtrip validation and precision checking
   - Model fitting and optimization
5. Results displayed back in TestImageViewer with async loading

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
├── pyproject.toml          # Project configuration and dependencies
├── src/
│   └── pointy/            # Main package directory
│       ├── __init__.py
│       ├── main_window.py     # Main application window
│       ├── viewers/           # Image viewer components
│       │   ├── test_image_viewer.py      # Async loading support
│       │   └── reference_viewer.py
│       ├── sidebar/           # Sidebar components
│       │   ├── tabbed_sidebar.py          # Main sidebar container
│       │   ├── components/
│       │   │   ├── gcp_panel.py            # GCP management
│       │   │   ├── status_panel.py         # Status display
│       │   │   ├── metadata_panel.py       # Cursor metadata
│       │   │   └── collection_nav_panel.py # Image navigation
│       │   └── tools/
│       ├── core/              # Core functionality
│       │   ├── coordinate.py   # Coordinate system definitions
│       │   ├── gcp.py          # Ground Control Point data structure
│       │   ├── projector.py    # Modern Projector API
│       │   ├── terrain.py      # Elevation data management
│       │   ├── orthorectifier.py # Legacy orthorectification
│       │   └── qt_async_image_loader.py # Async image loading
│       └── data/              # Configuration and data files
│           └── config/
│               └── imagery_services.json
├── test/                   # Test suite
│   ├── unit/              # Unit tests
│   │   ├── test_projector.py      # Projector API tests
│   │   └── test_*.py
│   └── integration/       # Integration tests
│       └── test_camera_integration.py # Camera scenario tests
├── ortho-logic.md         # Projector API design document
├── refactoring_recommendations.md # Architecture improvements
└── README.md
```

### Extending the Application

- **New Projection Types**: Implement RPC_Projection and TPS_Projection classes in `projector.py`
- **Reference Sources**: Add new WMS/WMTS providers in `ReferenceViewer`
- **Coordinate Systems**: Extend coordinate types in `coordinate.py`
- **GCP Validation**: Add custom validation rules in `gcp.py`
- **File Formats**: Extend I/O support in GCP management components
- **UI Components**: Add new sidebar panels in `tabbed_sidebar.py`

### Testing

Run the test suite:
```bash
# Unit tests
python -m pytest test/unit/

# Integration tests
python -m pytest test/integration/

# All tests with coverage
python -m pytest --cov=pointy

# Skip elevation lookup for testing
SKIP_ELEVATION_LOOKUP=true python -m pytest
```
