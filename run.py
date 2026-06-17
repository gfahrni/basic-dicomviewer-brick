"""
Entry point for the basic-dicomviewer-brick application.

This is the thin launch script. It handles command-line arguments,
resolves the data directory, and hands control to the DicomViewer class.

Usage:
    python run.py                  # opens DATA/ folder
    python run.py /path/to/dcm     # opens a custom folder
"""

import sys
import os
import json

# Import the main viewer class from our src package
from src.viewer import DicomViewer


def _default_data_path():
    """
    Resolve the default data directory from settings.json.

    The value in settings.json is treated as relative to the project root
    (one level above src/). This lets users change the default folder
    without touching any Python code.
    """
    # settings.json lives next to run.py (the project root).
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    try:
        with open(settings_path) as f:
            settings = json.load(f)
        rel = settings.get('default_data_path', 'DATA')
    except (FileNotFoundError, json.JSONDecodeError):
        rel = 'DATA'

    return os.path.join(os.path.dirname(__file__), rel)


def main():
    """
    Parse arguments and start the viewer.

    Behaviour:
        - If a directory path is passed as the first CLI argument, use it.
        - Otherwise fall back to the default path from settings.json.
        - Exit with an error if the chosen path doesn't exist.
    """
    # sys.argv[0] is the script name, sys.argv[1] is the first real argument
    data_path = sys.argv[1] if len(sys.argv) > 1 else _default_data_path()

    # Validate that the path is an actual directory before proceeding
    if not os.path.isdir(data_path):
        print(f'Error: {data_path} is not a valid directory.')
        sys.exit(1)

    # Create the viewer – it loads data and opens the matplotlib window
    DicomViewer(data_path)


# This guard ensures main() only runs when this file is executed directly,
# not when it's imported as a module by another script.
if __name__ == '__main__':
    main()
