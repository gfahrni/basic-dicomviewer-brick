# basic-dicomviewer-brick

A lightweight, matplotlib-based GUI to browse DICOM medical image series
slice by slice. Switch between multiple series, scroll through slices,
and view with proper DICOM windowing (brightness/contrast).

Designed as a basic building block for DICOM viewer projects in research
and development.

![Python](https://img.shields.io/badge/python-%3E%3D3.8-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Slice navigation** — mouse wheel, vertical slider, or keyboard
- **Multiple series** — auto-detect all series in a folder, switch with
  Previous / Next buttons or <kbd>Q</kbd> / <kbd>E</kbd> keys
- **DICOM windowing** — reads `WindowCenter` / `WindowWidth` tags for
  optimal grayscale display; falls back to min/max pixel values
- **Customisable** — colours and slider dimensions in `settings.json`
- **Flexible layout** — place DICOM files directly in the data folder or
  organise them in subdirectories (one per series)

---

## Project structure

```
basic-dicomviewer-brick/
├── run.py              # Entry point — handles CLI args, launches viewer
├── settings.json       # Configurable constants (colours, layout)
├── pyproject.toml      # Project metadata & dependencies
├── DATA/               # Place your DICOM data here (see "Data layout" below)
└── src/
    ├── __init__.py     # Makes src/ a Python package
    ├── loader.py       # find_series(), load_series() — data discovery & I/O
    └── viewer.py       # DicomViewer class — UI layout & interaction
```

---

## Installation

### 1. Clone or download the repository

```bash
git clone https://github.com/yourusername/basic-dicomviewer-brick.git
cd basic-dicomviewer-brick
```

### 2. Install dependencies

Using **pip** (recommended):

```bash
pip install .
```

Or install manually:

```bash
pip install numpy pydicom matplotlib
```

> **Note:** The GUI requires a working display (it uses `TkAgg` under the
> hood). On macOS, Tkinter usually comes with Python. On Linux,
> install `python3-tk` via your package manager.

---

## Usage

```bash
python run.py                    # opens DATA/ folder
python run.py /path/to/dicom     # opens a custom folder
```

### Data layout

Place your DICOM files inside `DATA/`. Two layouts are supported:

```
DATA/                          DATA/
├── scan1.dcm                  ├── series1/
├── scan2.dcm                  │   ├── 001.dcm
└── scan3.dcm                  │   ├── 002.dcm
 (flat, one series)            │   └── 003.dcm
                               └── series2/
                                   ├── 001.dcm
                                   └── 002.dcm
                              (nested, multiple series)
```

The viewer will auto-detect all series — one per subdirectory or, if files are flat, a single series.

### Controls

| Input | Action |
|---|---|
| Mouse wheel up/down | Previous / next slice |
| Vertical slider | Drag to jump to a slice |
| <kbd>Q</kbd> | Previous series |
| <kbd>E</kbd> | Next series |
| **Previous** / **Next** buttons | Same as keyboard |

---

## Configuration

Edit `settings.json` to adjust the look and feel:

| Key | Default | Description |
|---|---|---|
| `bg_color` | `"#2b2b2b"` | Background colour of the viewer window |
| `slider_x` | `0.94` | Horizontal position of the slice slider |
| `slider_w` | `0.02` | Width of the slider bar |
| `slider_scale` | `0.9` | Slider height relative to the image |
| `default_data_path` | `"DATA"` | Default folder to open (relative to project root) |

---

## Contributing

Contributions are welcome! Open an issue or submit a pull request.

---

## License

This project is open source and available under the
[MIT License](https://opensource.org/licenses/MIT).
