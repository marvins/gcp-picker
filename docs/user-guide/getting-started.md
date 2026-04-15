# Getting Started

## Installation

```bash
git clone https://github.com/marvins/gcp-picker.git
cd pointy_mcpointface
pip install -e .
```

## Launching Pointy

```bash
python -m pointy
```

Or if you have a collection file:

```bash
python -m pointy --collection /path/to/collection.json
```

## Interface Overview

The main window is divided into three areas:

- **Left panel**: Reference viewer (Leaflet-based map)
- **Right panel**: Test image viewer
- **Right sidebar**: Tabbed panels for GCP management, orthorectification tools, and auto-match settings
