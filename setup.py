"""
Setup script - generates version file before building

This wraps setuptools to generate _version.py before the build process.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from setuptools import setup


def generate_version_file():
    """Generate the _version.py file."""
    src_dir = Path(__file__).parent / "src" / "gcp_picker"
    src_dir.mkdir(parents=True, exist_ok=True)

    version_file = src_dir / "_version.py"

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    version = "1.0.0"

    if pyproject_path.exists():
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                version = data.get("project", {}).get("version", version)
        except Exception:
            pass

    # Get git hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent,
        )
        git_hash = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_hash = "unknown"

    build_date = datetime.now(timezone.utc).isoformat()

    version_content = f'''"""Version information - auto-generated during build"""

__version__ = "{version}"
__build_date__ = "{build_date}"
__git_hash__ = "{git_hash}"


def get_version_info() -> dict:
    return {{
        "version": __version__,
        "build_date": __build_date__,
        "git_hash": __git_hash__,
    }}
'''

    with open(version_file, "w") as f:
        f.write(version_content)

    print(f"Generated version file: {version_file}")


# Generate version file before running setup
generate_version_file()

# Now proceed with standard setuptools
setup()
