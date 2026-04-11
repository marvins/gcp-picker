# Workflow Tests

This file outlines common failure modes and workflow tests to build to prevent regression.

## Common Failures Encountered

### 1. GCP Loading and Display
**Issue**: GCPs not appearing on test image viewer after auto-loading
**Root Cause**: Visual markers not being added to test viewer during auto-loading
**Test**: Verify GCPs appear on both test and reference viewers after loading from file
```python
def test_gcp_auto_load_display():
    # Load GCPs from file
    # Verify GCP count matches file
    # Verify GCPs appear on test viewer (visual check or count)
    # Verify GCPs appear on reference viewer (visual check or count)
```

### 2. Terrain Manager Initialization
**Issue**: `'Catalog' object has no attribute 'sources'` after lazy loading refactor
**Root Cause**: Code still referencing removed `sources` attribute instead of `source_cache`
**Test**: Verify terrain manager initializes successfully with lazy loading
```python
def test_terrain_manager_lazy_loading():
    # Initialize terrain manager
    # Verify catalog.source_paths is populated
    # Verify catalog.source_cache is empty initially (lazy loading)
    # Verify GeoTIFFs load on-demand when queried
```

### 3. Zoom Behavior
**Issue**: Zoom resets to image center instead of maintaining view position
**Root Cause**: `set_zoom()` method was resetting transform without preserving center
**Test**: Verify zoom maintains current view center
```python
def test_zoom_maintains_view_center():
    # Pan to specific location
    # Get center coordinates before zoom
    # Apply zoom
    # Verify center coordinates are preserved
```

### 4. Ctrl-C Graceful Shutdown
**Issue**: Qt event loop doesn't respond to Ctrl-C
**Root Cause**: No SIGINT signal handler installed
**Test**: Verify application shuts down gracefully on Ctrl-C
```python
def test_ctrl_c_shutdown():
    # Start application
    # Send SIGINT signal
    # Verify application exits cleanly (no hanging threads)
```

### 5. Import Errors After Refactoring
**Issue**: Import errors after moving terrain to terminus-core-python
**Root Cause**: Code still importing from old locations
**Test**: Verify all imports resolve correctly
```python
def test_import_resolution():
    # Import all main modules
    # Verify no ImportError or AttributeError
```

### 6. Catalog Lazy Loading
**Issue**: GeoTIFFs loading immediately instead of on-demand
**Root Cause**: Catalog was loading all GeoTIFFs at initialization
**Test**: Verify lazy loading behavior
```python
def test_catalog_lazy_loading():
    # Create catalog
    # Verify GeoTIFF count in source_paths
    # Verify GeoTIFF count in source_cache is 0 initially
    # Query elevation for coordinate
    # Verify only relevant GeoTIFFs are loaded into cache
```

### 7. GCP Auto-Loading Data Structure Errors
**Issue**: `'list' object has no attribute 'values'` during auto-loading
**Root Cause**: Code calling `.values()` on list returned by `get_gcps()`
**Test**: Verify GCP auto-loading handles correct data structures
```python
def test_gcp_auto_loading_data_structures():
    # Load GCPs from file
    # Verify get_gcps() returns list
    # Verify iteration over list works without calling .values()
```

## Priority Workflow Tests

### High Priority (Critical User Workflows)
1. **GCP Loading and Display** - Core functionality
2. **Terrain Manager Initialization** - Required for elevation data
3. **Zoom Behavior** - Basic navigation

### Medium Priority (Quality of Life)
4. **Ctrl-C Graceful Shutdown** - Development experience
5. **Catalog Lazy Loading** - Performance
6. **Import Errors** - Refactoring safety

### Low Priority (Edge Cases)
7. **GCP Auto-Loading Data Structures** - Already fixed, regression test

## Test Implementation Notes

- Use pytest-qt for GUI-related tests
- Mock external dependencies (elevation API, network calls)
- Test both happy paths and error conditions
- Verify no AttributeError when accessing attributes after refactoring
- Test data structure assumptions (list vs dict) explicitly
