---
trigger: glob
globs: *.py
---
# Naming Conventions Rules

This directory contains naming convention rules for the GCP Picker project.

## Python Naming Conventions

The project follows Rust-style naming conventions adapted for Python:

### Classes
- **Style**: PascalCase with underscores
- **Examples**: `Image_Canvas`, `GCP_Manager`, `Coordinate_Transformer`
- **Rationale**: Improves readability, follows Rust convention

### Methods and Functions
- **Style**: snake_case
- **Examples**: `set_pixmap`, `add_gcp_point`, `pixel_to_image_coords`
- **Rationale**: Standard Python convention

### Variables
- **Style**: snake_case
- **Examples**: `zoom_factor`, `gcp_points`, `current_reference`
- **Rationale**: Standard Python convention

### Constants
- **Style**: SCREAMING_SNAKE_CASE
- **Examples**: `DEFAULT_ZOOM`, `MAX_GCP_POINTS`, `CACHE_SIZE`
- **Rationale**: Standard Python convention

### Modules
- **Style**: snake_case
- **Examples**: `coordinate.py`, `terrain.py`, `gcp_processor.py`
- **Rationale**: Standard Python convention

# Module Rules

- **ALL imports must be at the top of the file** - No inline imports inside functions or methods
- Import modules in this sequence:

```python
# Standard library imports
import os
import sys

# Third-party imports
import numpy as np
from qtpy.QtWidgets import QApplication, QMainWindow

# Project imports
from app.core.coordinate import Geographic, Pixel, UTM
from app.core.terrain import elevation
```

- **No exceptions**: Even if an import is only used in one method, it must be at the top of the file
- **Rationale**: Improves readability, makes dependencies clear, and follows Python best practices

#  Typing Hints

- Use `|` for union types (Python 3.10+):
```python
def setup_logging(log_file: str | None = None):
    value: int | str | None
```

