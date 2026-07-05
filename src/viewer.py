"""
PyQt6-based DICOM viewer — lightweight slice browser.

Replaces the original matplotlib GUI with a native Qt interface for
better performance and responsiveness.
"""

import sys
import json
import os

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QKeyEvent, QWheelEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QSizePolicy,
)

from .loader import find_series, load_series


SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'settings.json'
)


def _load_settings():
    default = {
        'bg_color': '#2b2b2b',
        'default_data_path': 'DATA',
    }
    path = os.path.abspath(SETTINGS_PATH)
    if os.path.exists(path):
        with open(path) as f:
            return {**default, **json.load(f)}
    return default


SETTINGS = _load_settings()


class ImageView(QGraphicsView):
    """QGraphicsView subclass that handles mouse-wheel slice scrolling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._viewer = None

    def set_viewer(self, viewer):
        self._viewer = viewer

    def wheelEvent(self, event: QWheelEvent):
        if self._viewer is not None:
            self._viewer._on_wheel(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._viewer is not None:
            self._viewer._fit_image()


class DicomViewer(QMainWindow):
    """
    PyQt6-based viewer for browsing DICOM series slice by slice.

    Usage:
        viewer = DicomViewer('/path/to/dicom/folder')
        viewer.show()

    Layout:
        ┌──────────────────────────┬──────────┐
        │                          │          │
        │       DICOM image        │  Slider  │
        │     (QGraphicsView)      │  (vert)  │
        │                          │          │
        ├──────────────────────────┴──────────┤
        │          Slice info label           │
        ├─────────────────────────────────────┤
        │   [Previous (Q)]    [Next (E)]      │
        └─────────────────────────────────────┘
    """

    def __init__(self, data_path):
        super().__init__()
        self.data_path = data_path

        # --- Load data -------------------------------------------------------
        self.series_list = find_series(data_path)
        if not self.series_list:
            print('No DICOM series found.')
            sys.exit(1)

        print('Series found:')
        for i, s in enumerate(self.series_list):
            print(f'  [{i}] {s["name"]} - {s["description"]} '
                  f'({len(s["files"])} slices)')

        self.current_series_idx = 0
        self._scroll_accumulator = 0
        self._load_current_series()

        # --- Build UI --------------------------------------------------------
        self._init_ui()

    def _load_current_series(self):
        series = self.series_list[self.current_series_idx]
        self._slices = load_series(series['files'])
        self.num_slices = len(self._slices)
        self._slice_idx = 0
        self._precompute_images()

    def _precompute_images(self):
        """Normalise every slice to uint8 using DICOM windowing."""
        self._images = []
        for ds in self._slices:
            arr = ds.pixel_array.astype(np.float64)

            wc = ds.get('WindowCenter', None)
            ww = ds.get('WindowWidth', None)

            if wc is not None and ww is not None:
                wc = float(wc[0]) if isinstance(wc, (list, tuple)) else float(wc)
                ww = float(ww[0]) if isinstance(ww, (list, tuple)) else float(ww)
                vmin = wc - ww / 2
                vmax = wc + ww / 2
            else:
                vmin = arr.min()
                vmax = arr.max()

            if vmax == vmin:
                vmax = vmin + 1

            arr = np.clip(arr, vmin, vmax)
            arr = ((arr - vmin) / (vmax - vmin) * 255).astype(np.uint8)
            self._images.append(arr)

    def _init_ui(self):
        name = self.series_list[0]['name']
        self.setWindowTitle(f'basic-dicomviewer-brick - {name}')
        self.setStyleSheet(f'background-color: {SETTINGS["bg_color"]};')

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # --- Image row (view + slider) --------------------------------------
        img_row = QHBoxLayout()
        img_row.setSpacing(6)

        self.scene = QGraphicsScene()
        self.view = ImageView()
        self.view.set_viewer(self)
        self.view.setScene(self.scene)
        self.view.setStyleSheet('border: none; background-color: black;')
        self.view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        img_row.addWidget(self.view, 1)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, self.num_slices - 1)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.valueChanged.connect(self._on_slider)
        self.slider.setFixedWidth(30)
        img_row.addWidget(self.slider)

        root.addLayout(img_row, 1)

        # --- Info label ------------------------------------------------------
        self.info_label = QLabel()
        self.info_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(
            'color: white; font-size: 12px; background: transparent;')
        root.addWidget(self.info_label)

        # --- Buttons ---------------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.prev_btn = QPushButton('Previous (Q)')
        self.next_btn = QPushButton('Next (E)')
        btn_style = (
            'QPushButton {'
            '  background-color: #4a4a4a; color: white;'
            '  border: none; padding: 6px 18px; font-size: 12px;'
            '}'
            'QPushButton:hover { background-color: #5a5a5a; }'
        )
        for btn in (self.prev_btn, self.next_btn):
            btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(self._prev_series)
        self.next_btn.clicked.connect(self._next_series)

        btn_row.addStretch()
        btn_row.addWidget(self.prev_btn)
        btn_row.addWidget(self.next_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # --- Show first slice ------------------------------------------------
        self._show_slice()

        # --- Window size -----------------------------------------------------
        self.resize(900, 900)

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------

    def _numpy_to_pixmap(self, arr):
        h, w = arr.shape
        qimg = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8)
        return QPixmap.fromImage(qimg)

    def _show_slice(self):
        arr = self._images[self._slice_idx]
        pixmap = self._numpy_to_pixmap(arr)
        self.pixmap_item.setPixmap(pixmap)
        self._fit_image()

        name = self.series_list[self.current_series_idx]['name']
        self.info_label.setText(
            f'Slice {self._slice_idx + 1}/{self.num_slices}  |  {name}'
        )

    def _fit_image(self):
        if self.pixmap_item.pixmap() is not None:
            self.view.fitInView(
                self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_slider(self, value):
        self._slice_idx = value
        self._show_slice()

    def _on_wheel(self, event: QWheelEvent):
        # angleDelta() returns eighths of a degree; 120 = 1 mouse notch.
        # On macOS trackpads angleDelta() is often 0 and pixelDelta() is
        # the actual scroll distance — we fall back to that and scale it.
        delta = event.angleDelta().y()
        if delta == 0:
            # Trackpad: scale pixel delta (~1 px ≈ 3°) so a normal
            # swipe accumulates ≈120 per "slice step".
            delta = event.pixelDelta().y() * 3

        self._scroll_accumulator += delta

        steps = self._scroll_accumulator // 120
        if steps != 0:
            self._scroll_accumulator -= steps * 120
            self._slice_idx = max(0, min(self.num_slices - 1,
                                         self._slice_idx - steps))
            self.slider.blockSignals(True)
            self.slider.setValue(self._slice_idx)
            self.slider.blockSignals(False)
            self._show_slice()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Q:
            self._prev_series()
        elif event.key() == Qt.Key.Key_E:
            self._next_series()
        super().keyPressEvent(event)

    def _prev_series(self):
        if self.current_series_idx > 0:
            self._switch_to_series(self.current_series_idx - 1)

    def _next_series(self):
        if self.current_series_idx < len(self.series_list) - 1:
            self._switch_to_series(self.current_series_idx + 1)

    def _switch_to_series(self, idx):
        self.current_series_idx = idx
        self._load_current_series()
        self.slider.blockSignals(True)
        self.slider.setRange(0, self.num_slices - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.setWindowTitle(
            f'basic-dicomviewer-brick - '
            f'{self.series_list[idx]["name"]}'
        )
        self._show_slice()
