"""
Data-loading utilities for basic-dicomviewer-brick.

Responsibilities:
    - Scan a directory for DICOM series (groups of .dcm files).
    - Read the DICOM files and return them sorted by slice order.

Separated from viewer.py so that the I/O logic can be tested or reused
independently of the GUI.
"""

import os
import pydicom
from pydicom.misc import is_dicom


def _list_dicom_files(dir_path):
    """
    Return all files in *dir_path* that are valid DICOM files,
    regardless of file extension. Uses pydicom's preamble check
    (128 zero bytes + "DICM") which is fast and doesn't read the
    entire file.
    """
    files = []
    for entry in os.listdir(dir_path):
        full = os.path.join(dir_path, entry)
        if os.path.isfile(full) and is_dicom(full):
            files.append(full)
    return sorted(files)


def find_series(data_path):
    """
    Scan *data_path* and return a list of found DICOM series.

    A "series" is a group of .dcm files that belong together (e.g. one MRI
    scan sequence). This function handles two layouts:

        1. Flat layout  – .dcm files are directly inside *data_path*.
        2. Nested layout – *data_path* contains subdirectories, each holding
           one series' worth of .dcm files.

    Each series is returned as a dict:
        {
            'name':        str  – folder name (or leaf of data_path),
            'description': str  – DICOM SeriesDescription tag, if present,
            'files':       list – sorted absolute paths to .dcm files,
        }

    Args:
        data_path: Path to a directory containing DICOM data.

    Returns:
        A list of series dicts, or an empty list if nothing was found.
    """
    series = []

    # --- Try flat layout first ------------------------------------------------
    # Look for .dcm files straight in data_path (no subfolders).
    dcm_files = _list_dicom_files(data_path)
    if dcm_files:
        # Read just the metadata of the first file (stop_before_pixels=True
        # skips the large pixel array, making this fast).
        ds = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)

        # Get the SeriesDescription tag, falling back to the folder name.
        desc = ds.get('SeriesDescription', os.path.basename(data_path))

        series.append({
            'name': os.path.basename(data_path),
            'description': desc,
            'files': dcm_files,
        })
        # Flat layout found files → we're done, no need to check subfolders.
        return series

    # --- Try nested layout ----------------------------------------------------
    # No .dcm files at the top level → look inside each subdirectory.
    for entry in sorted(os.listdir(data_path)):
        subdir = os.path.join(data_path, entry)

        # Skip files, only descend into directories.
        if not os.path.isdir(subdir):
            continue

        # Gather .dcm files inside this subdirectory.
        dcm_files = _list_dicom_files(subdir)
        if not dcm_files:
            # This subdir has no DICOM files → skip it.
            continue

        # Read metadata from the first file to get a human-readable name.
        ds = pydicom.dcmread(dcm_files[0], stop_before_pixels=True)
        desc = ds.get('SeriesDescription', entry)

        series.append({
            'name': entry,
            'description': desc,
            'files': dcm_files,
        })

    return series


def load_series(files):
    """
    Fully read a list of DICOM files and return them sorted by slice order.

    DICOM slices are typically ordered by the (0020,0013) InstanceNumber tag.
    Sorting is important because the file system order may not match the
    anatomical order (e.g. files might be named IM-0001-0001.dcm, etc.).

    Args:
        files: List of paths to .dcm files belonging to one series.

    Returns:
        A list of pydicom Dataset objects, sorted by InstanceNumber.
    """
    slices = []

    # Read every file completely (pixel data included this time).
    for f in files:
        ds = pydicom.dcmread(f)
        slices.append(ds)

    # Sort by InstanceNumber (default to 0 if the tag is missing).
    # The lambda extracts the value from each Dataset.
    slices.sort(key=lambda x: x.get('InstanceNumber', 0))

    return slices
