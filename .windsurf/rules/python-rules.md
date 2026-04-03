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
- **Use full imports, not local imports**: Always use full module paths in imports, not relative imports
- Import modules in this sequence:

```python
# Python Standard Libraries
import os
import sys

# Third-Party Libraries
import numpy as np
from qtpy.QtWidgets import QApplication, QMainWindow

# Project Libraries
from pointy.core.coordinate import Geographic, Pixel, UTM
from pointy.core.terrain import elevation
```

- **No exceptions**: Even if an import is only used in one method, it must be at the top of the file
- **Rationale**: Improves readability, makes dependencies clear, and follows Python best practices
- **CRITICAL REMINDER**: NEVER use inline imports inside functions/methods. All imports MUST be at the top of the file in the proper section.

#  Typing Hints

- Use `|` for union types (Python 3.10+):
```python
def setup_logging(log_file: str | None = None):
    value: int | str | None
```

#  File IP Header

All Python files must include the standard IP header at the top:

```python
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#*                                                                                    *#
#*                           Copyright (c) 2026 Terminus LLC                          *#
#*                                                                                    *#
#*                                All Rights Reserved.                                *#
#*                                                                                    *#
#*          Use of this source code is governed by LICENSE in the repo root.          *#
#*                                                                                    *#
#**************************** INTELLECTUAL PROPERTY RIGHTS ****************************#
#
#    File:    filename.py
#    Author:  Author Name
#    Date:    MM/DD/YYYY
#
```

- **Format**: Use the exact IP header format shown above
- **File**: Update filename to match actual file name
- **Author**: Use "Marvin Smith" for project files
- **Date**: Use current date in MM/DD/YYYY format
- **Rationale**: Standardizes intellectual property notices across the project