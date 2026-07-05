# basic-dicomviewer-brick

A lightweight, PyQt6-based GUI to browse DICOM medical image series
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
- **Flat or nested folders** — works whether `.dcm` files are directly
  in the data directory or organised in subdirectories

---

## Project structure

```
basic-dicomviewer-brick/
├── run.py              # Entry point — handles CLI args, launches viewer
├── settings.json       # Configurable constants (colours, layout)
├── pyproject.toml      # Project metadata & dependencies
├── DATA/               # Example DICOM datasets (MRI_abdo1, MRI_abdo2)
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
pip install numpy pydicom PyQt6
```

---

## Usage

```bash
python run.py                    # opens DATA/ folder
python run.py /path/to/dicom     # opens a custom folder
```

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
