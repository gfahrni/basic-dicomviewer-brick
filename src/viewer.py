"""
basic-dicomviewer-brick — graphical window to browse slices of a medical image series.

This module contains the DicomViewer class, which builds a matplotlib GUI
to let a user:
    - Scroll through slices (mouse wheel, slider, keyboard).
    - Switch between multiple series found in the data folder.
    - View images with proper DICOM windowing (brightness / contrast).

It imports data-loading helpers from .loader (same package).
"""

import sys
import json
import os

import numpy as np
import matplotlib

# Force matplotlib to use the TkAgg backend *before* pyplot is imported.
# TkAgg is a cross-platform, interactive backend that works well for GUIs.
# If we didn't set this, matplotlib might pick a non-interactive backend
# (e.g. 'Agg') on headless systems, and the window wouldn't appear.
matplotlib.use('TkAgg')

# Remove 'q' / 'Q' from the quit keymap — we use those keys for
# "previous series". Without this, pressing 'q' both closes the window
# AND triggers our handler, causing a crash when the figure is half-destroyed.
matplotlib.rcParams['keymap.quit'] = [
    k for k in matplotlib.rcParams.get('keymap.quit', [])
    if k.lower() != 'q'
]
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Relative import: get find_series / load_series from the sibling loader.py
from .loader import find_series, load_series


# ---------------------------------------------------------------------------
# Settings loader
# ---------------------------------------------------------------------------

def _load_settings():
    """
    Load user-facing settings from a JSON file next to the src/ folder.

    Falls back to sensible defaults if the file is missing. This approach
    lets anyone tweak colours or layout without editing Python code.
    """
    default = {
        'bg_color': '#2b2b2b',       # dark background for the figure
        'slider_x': 0.94,            # horizontal position of the slice slider
        'slider_w': 0.02,            # width of the slider bar
        'slider_scale': 0.9,         # slider height relative to the image
    }

    # settings.json lives in the project root (one level above src/).
    path = os.path.join(os.path.dirname(__file__), '..', 'settings.json')
    path = os.path.abspath(path)

    if os.path.exists(path):
        with open(path) as f:
            # Merge: user values override defaults, but missing keys keep defaults.
            return {**default, **json.load(f)}

    return default


# Load settings once at module import time (they rarely change at runtime).
SETTINGS = _load_settings()


# ---------------------------------------------------------------------------
# Main viewer class
# ---------------------------------------------------------------------------

class DicomViewer:
    """
    A matplotlib-based GUI for browsing DICOM series slice by slice.

    Usage:
        viewer = DicomViewer('/path/to/dicom/folder')
        # The constructor builds the window and calls plt.show() —
        # execution blocks here until the user closes the window.

    Layout (bottom → top):
        [ Previous ] [ Next ]      ← series-switching buttons
        [     image      ]         ← the DICOM slice
        [   slider (right) ]       ← vertical slice scroller
    """

    def __init__(self, data_path):
        """
        Initialize the viewer: discover series, load data, build UI.

        Args:
            data_path: Directory containing DICOM files or series subfolders.
        """
        self.data_path = data_path

        # ------------------------------------------------------------------
        # Step 1 — Discover and load data
        # ------------------------------------------------------------------

        self.series_list = find_series(data_path)
        if not self.series_list:
            print('No DICOM series found.')
            sys.exit(1)

        # Print available series to the terminal so the user knows what's loaded.
        print('Series found:')
        for i, s in enumerate(self.series_list):
            print(f'  [{i}] {s["name"]} - {s["description"]} ({len(s["files"])} slices)')

        # Start with the first series.
        self.current_series_idx = 0
        self._slices = load_series(self.series_list[0]['files'])
        self.num_slices = len(self._slices)
        self._slice_idx = 0  # 0-based index of the currently displayed slice

        # Pre-compute brightness/contrast values for every slice.
        self._precompute_windowing()

        # ------------------------------------------------------------------
        # Step 2 — Build the matplotlib figure
        # ------------------------------------------------------------------

        self.fig = plt.figure(figsize=(10, 10))
        self.fig.set_facecolor(SETTINGS['bg_color'])
        self.fig.canvas.manager.set_window_title(
            f'basic-dicomviewer-brick - {self.series_list[0]["name"]}'
        )

        # Layout constants (all in figure-relative coordinates, 0..1).
        margin = 0.02
        button_h = 0.04     # height of the Previous / Next buttons
        btn_gap = 0.02      # gap between the two buttons
        btn_w = (0.90 - btn_gap) / 2   # each button is half the available width

        # ---- Previous / Next series buttons (bottom) ---------------------
        prev_ax = self.fig.add_axes([margin, margin, btn_w, button_h])
        next_ax = self.fig.add_axes([margin + btn_w + btn_gap, margin, btn_w, button_h])
        for ax in (prev_ax, next_ax):
            ax.set_facecolor('#3c3c3c')

        self._prev_btn = Button(
            prev_ax, 'Previous (Q)', color='#4a4a4a', hovercolor='#5a5a5a'
        )
        self._next_btn = Button(
            next_ax, 'Next (E)', color='#4a4a4a', hovercolor='#5a5a5a'
        )
        self._prev_btn.label.set_color('white')
        self._next_btn.label.set_color('white')
        self._prev_btn.on_clicked(self._prev_series)
        self._next_btn.on_clicked(self._next_series)

        # ---- Image axes (above the buttons) ------------------------------
        # Leave room for the buttons at the bottom and a margin on all sides.
        img_y = margin + button_h + 0.02
        img_h = 1.0 - img_y - margin
        self.ax = self.fig.add_axes([margin, img_y, 0.90, img_h])
        self.ax.set_facecolor(SETTINGS['bg_color'])

        # Display the first slice.
        first_arr = self._slices[0].pixel_array
        vmin, vmax = self._vmin_max[0]
        self._im = self.ax.imshow(first_arr, cmap='gray', vmin=vmin, vmax=vmax)
        info = (
            f'Slice 1/{self.num_slices}  |  '
            f'{self.series_list[self.current_series_idx]["name"]}'
        )
        self.ax.set_title(info, fontsize=12, color='white')
        self.ax.axis('off')   # hide tick marks / axes

        # ---- Vertical slice slider (right edge of the image) -------------
        slider_w = SETTINGS['slider_w'] * SETTINGS['slider_scale']
        slider_x = SETTINGS['slider_x'] + (SETTINGS['slider_w'] - slider_w) / 2
        init_h = img_h * SETTINGS['slider_scale']
        init_y = img_y + img_h * (1 - SETTINGS['slider_scale']) / 2

        slider_ax = self.fig.add_axes([slider_x, init_y, slider_w, init_h])
        slider_ax.set_facecolor('#3c3c3c')

        self._slider = Slider(
            ax=slider_ax,
            label='',
            valmin=0,
            valmax=self.num_slices - 1,
            valinit=0,
            valstep=1,              # snap to integer slice indices
            orientation='vertical',
            track_color='#555555',
            handle_style={'facecolor': '#aaaaaa', 'size': 10},
        )
        self._slider.on_changed(self._on_slider)
        self._slider_active = False  # prevents feedback loops

        # ---- Wire up events ----------------------------------------------
        self.fig.canvas.draw()
        self._reposition_slider_to_image()
        self.fig.canvas.mpl_connect('resize_event', self._on_resize)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)
        self.fig.canvas.mpl_connect('key_press_event', self._on_key)

        # Show the window and start the GUI event loop.
        # This call blocks until the user closes the window.
        self.fig.canvas.manager.show()
        plt.show()

    # ------------------------------------------------------------------
    # Windowing (brightness / contrast)
    # ------------------------------------------------------------------

    def _precompute_windowing(self):
        """
        Calculate a (vmin, vmax) display range for every slice.

        DICOM images often store a "WindowCenter" and "WindowWidth" tag
        that define the optimal grayscale mapping for diagnosis.
        If those tags are missing, fall back to the min / max pixel value.

        Stores the list in ``self._vmin_max``, parallel to ``self._slices``.
        """
        self._vmin_max = []
        for ds in self._slices:
            arr = ds.pixel_array

            window_center = ds.get('WindowCenter', None)
            window_width = ds.get('WindowWidth', None)

            if window_center is not None and window_width is not None:
                # DICOM may store these as a list (e.g. for multi-frame);
                # if so, take the first element by converting to float.
                wc = (
                    float(window_center)
                    if hasattr(window_center, '__iter__')
                    else float(window_center)
                )
                ww = (
                    float(window_width)
                    if hasattr(window_width, '__iter__')
                    else float(window_width)
                )
                # Window formula: centre ± half-width
                vmin = wc - ww / 2
                vmax = wc + ww / 2
            else:
                # No windowing info → use the raw data range.
                vmin = arr.min()
                vmax = arr.max()

            self._vmin_max.append((vmin, vmax))

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _show_slice(self):
        """
        Update the image axes to show the current slice (self._slice_idx).

        Refreshes the pixel data, the colour-map limits, the title,
        and the slider position (unless the slider itself triggered this).
        """
        ds = self._slices[self._slice_idx]
        arr = ds.pixel_array
        vmin, vmax = self._vmin_max[self._slice_idx]

        self._im.set_data(arr)
        self._im.set_clim(vmin, vmax)

        info = (
            f'Slice {self._slice_idx + 1}/{self.num_slices}  |  '
            f'{self.series_list[self.current_series_idx]["name"]}'
        )
        self.ax.set_title(info, fontsize=12, color='white')

        # Sync the slider without triggering _on_slider (which would loop).
        if hasattr(self, '_slider') and not self._slider_active:
            self._slider_active = True
            self._slider.set_val(self._slice_idx)
            self._slider_active = False

        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Slider callbacks
    # ------------------------------------------------------------------

    def _on_slider(self, val):
        """Called when the user drags the slider."""
        self._slice_idx = int(val)
        self._show_slice()

    def _reposition_slider_to_image(self):
        """
        Keep the vertical slider aligned with the displayed image area.

        After a window resize the image dimensions in figure-coordinates
        change, so we recompute the slider position to stay lined up.
        """
        im = self.ax.get_images()[0]
        extent = im.get_extent()

        # Convert image corners from data → display → figure coordinates.
        bl = self.ax.transData.transform((extent[0], extent[2]))
        tr = self.ax.transData.transform((extent[1], extent[3]))
        inv = self.fig.transFigure.inverted()
        bl_fig = inv.transform(bl)
        tr_fig = inv.transform(tr)

        h = tr_fig[1] - bl_fig[1]

        slider_w = SETTINGS['slider_w'] * SETTINGS['slider_scale']
        slider_x = SETTINGS['slider_x'] + (SETTINGS['slider_w'] - slider_w) / 2
        new_h = h * SETTINGS['slider_scale']
        new_y = bl_fig[1] + h * (1 - SETTINGS['slider_scale']) / 2

        self._slider.ax.set_position([slider_x, new_y, slider_w, new_h])

    # ------------------------------------------------------------------
    # Window event callbacks
    # ------------------------------------------------------------------

    def _on_resize(self, event):
        """Re-align the slider when the window is resized."""
        self._reposition_slider_to_image()

    def _on_scroll(self, event):
        """Mouse wheel: scroll up/down to move through slices."""
        if event.button == 'up':
            self._slice_idx = max(0, self._slice_idx - 1)
        elif event.button == 'down':
            self._slice_idx = min(self.num_slices - 1, self._slice_idx + 1)
        self._show_slice()

    # ------------------------------------------------------------------
    # Series switching
    # ------------------------------------------------------------------

    def _load_series_by_index(self, idx):
        """
        Replace the currently displayed series with another one.

        This reloads all slice data, recomputes windowing, resets the
        slider range, and updates the window title.
        """
        series = self.series_list[idx]
        self.current_series_idx = idx
        self._slices = load_series(series['files'])
        self.num_slices = len(self._slices)
        self._slice_idx = 0
        self._precompute_windowing()
        self.fig.canvas.manager.set_window_title(f'basic-dicomviewer-brick - {series["name"]}')

        # Reset slider range for the new series.
        self._slider_active = True
        self._slider.valmax = self.num_slices - 1
        self._slider.ax.set_ylim(self.num_slices - 1, 0)
        self._slider.set_val(0)
        self._slider_active = False

        # Show the first slice.
        first_arr = self._slices[0].pixel_array
        vmin, vmax = self._vmin_max[0]
        self._im.set_data(first_arr)
        self._im.set_clim(vmin, vmax)
        info = (
            f'Slice 1/{self.num_slices}  |  '
            f'{self.series_list[self.current_series_idx]["name"]}'
        )
        self.ax.set_title(info, fontsize=12, color='white')
        self.fig.canvas.draw_idle()

    def _on_key(self, event):
        """Keyboard shortcut handler: Q = previous series, E = next series."""
        if event.key == 'q':
            self._prev_series(event)
        elif event.key == 'e':
            self._next_series(event)

    def _next_series(self, event):
        """Switch to the next series (if available)."""
        if self.current_series_idx < len(self.series_list) - 1:
            self._load_series_by_index(self.current_series_idx + 1)

    def _prev_series(self, event):
        """Switch to the previous series (if available)."""
        if self.current_series_idx > 0:
            self._load_series_by_index(self.current_series_idx - 1)
