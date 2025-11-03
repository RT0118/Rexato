"""
Path-related utilities
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development mode - use the script's directory
        base_path = Path(__file__).parent.parent.absolute()
    
    # Join path and normalize for Qt's url() function
    full_path = os.path.join(base_path, relative_path)
    # Convert to forward slashes (Qt accepts this on Windows too)
    normalized_path = str(full_path).replace('\\', '/')
    return normalized_path

