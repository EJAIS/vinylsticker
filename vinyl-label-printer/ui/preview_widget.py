"""
PDF preview widget.

Renders each page of a generated PDF as a QPixmap using pdf2image (which
requires poppler to be installed system-wide) and displays it in a QLabel
with page navigation controls.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from modules.i18n import t


class PreviewWidget(QWidget):
    """Displays pages of a PDF as rendered images with navigation buttons."""

    _PREVIEW_DPI = 150   # render resolution — balances quality and RAM usage

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pages: list  = []   # list[PIL.Image.Image]
        self._current_page: int = 0
        self._init_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_pdf(self, pdf_path: Path) -> None:
        """Render all pages of *pdf_path* and display the first one.

        Catches ImportError / missing-poppler errors and shows a German error
        dialog so the app never crashes on a missing system dependency.
        """
        try:
            from pdf2image import convert_from_path  # imported lazily
            self._pages = convert_from_path(str(pdf_path), dpi=self._PREVIEW_DPI)
        except Exception as exc:
            if "poppler" in str(exc).lower() or isinstance(exc, ImportError):
                QMessageBox.critical(self, t("app_title"), t("err_poppler"))
            else:
                QMessageBox.critical(
                    self, t("app_title"),
                    f"{exc.__class__.__name__}: {exc}",
                )
            self._pages = []
            self._update_nav()
            self._placeholder.setVisible(True)
            self._image_label.setVisible(False)
            return

        self._current_page = 0
        self._show_current_page()

    def retranslate(self) -> None:
        """Update all translatable texts after a language switch."""
        self._btn_prev.setText(t("btn_prev"))
        self._btn_next.setText(t("btn_next"))
        self._update_nav()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Image area ────────────────────────────────────────────────────────
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._image_label.setMinimumSize(300, 420)
        self._image_label.setVisible(False)

        # Placeholder shown before any PDF is loaded
        self._placeholder = QLabel(t("no_preview"))
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._placeholder.setStyleSheet("color: grey; font-style: italic;")

        layout.addWidget(self._image_label)
        layout.addWidget(self._placeholder)

        # ── Navigation bar ────────────────────────────────────────────────────
        nav_layout = QHBoxLayout()

        self._btn_prev = QPushButton(t("btn_prev"))
        self._btn_prev.setEnabled(False)
        self._btn_prev.clicked.connect(self._on_prev)

        self._page_label = QLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_next = QPushButton(t("btn_next"))
        self._btn_next.setEnabled(False)
        self._btn_next.clicked.connect(self._on_next)

        self._update_nav()

        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._page_label)
        nav_layout.addWidget(self._btn_next)

        layout.addLayout(nav_layout)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _show_current_page(self) -> None:
        if not self._pages:
            self._placeholder.setVisible(True)
            self._image_label.setVisible(False)
            self._update_nav()
            return

        pil_img = self._pages[self._current_page]

        # Convert PIL image → QImage → QPixmap
        data   = pil_img.tobytes("raw", "RGB")
        qimage = QImage(
            data,
            pil_img.width,
            pil_img.height,
            pil_img.width * 3,          # bytes per line
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(qimage)

        # Scale to fit the label while keeping aspect ratio
        self._image_label.setPixmap(
            pixmap.scaled(
                self._image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        self._image_label.setVisible(True)
        self._placeholder.setVisible(False)
        self._update_nav()

    def _update_nav(self) -> None:
        total = len(self._pages)
        if total == 0:
            self._page_label.setText(t("no_preview"))
        else:
            self._page_label.setText(
                t("page_indicator", current=self._current_page + 1, total=total)
            )
        self._btn_prev.setEnabled(self._current_page > 0)
        self._btn_next.setEnabled(self._current_page < total - 1)

    # ── Navigation slots ──────────────────────────────────────────────────────

    def _on_prev(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._show_current_page()

    def _on_next(self) -> None:
        if self._current_page < len(self._pages) - 1:
            self._current_page += 1
            self._show_current_page()

    # ── Qt overrides ──────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Re-scale the displayed pixmap when the widget is resized."""
        super().resizeEvent(event)
        if self._pages:
            self._show_current_page()
