"""
Main application window.

Wires together:
  - GridWidget      — start-position picker
  - PreviewWidget   — PDF preview
  - excel_reader    — Print-queue loader
  - pdf_generator   — PDF generation
  - printer         — OS print trigger
  - i18n            — language switching
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

import modules.i18n as i18n
from modules.i18n import t
from modules.excel_reader import LabelRecord, load_print_queue
from modules.pdf_generator import generate_pdf
from modules.printer import print_pdf
from config.settings import get_watermark_path, set_watermark_path
from ui.grid_widget import GridWidget
from ui.preview_widget import PreviewWidget

# Paths are resolved relative to this file's location (vinyl-label-printer/)
_BASE_DIR  = Path(__file__).parent.parent
_DB_PATH   = _BASE_DIR / "data" / "database.xlsx"
_OUT_DIR   = _BASE_DIR / "output"
_PDF_NAME  = "labels.pdf"


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._records:       list[LabelRecord] = []
        self._pdf_path:      Path | None = None
        self._db_path:       Path = _DB_PATH
        self._watermark_path: Path | None = get_watermark_path()

        self._init_ui()
        self._load_queue()
        self._update_watermark_label()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(900, 620)

        # ── Left panel ────────────────────────────────────────────────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(10)

        # File picker + reload row
        file_row = QHBoxLayout()
        self._btn_open_db = QPushButton(t("btn_open_db"))
        self._btn_open_db.setToolTip(t("tooltip_open_db"))
        self._btn_open_db.clicked.connect(self._on_open_db)
        self._btn_reload = QPushButton(t("btn_reload"))
        self._btn_reload.setToolTip(t("tooltip_reload"))
        self._btn_reload.clicked.connect(self._on_reload)
        file_row.addWidget(self._btn_open_db)
        file_row.addWidget(self._btn_reload)
        left_layout.addLayout(file_row)

        # Queue info group
        self._grp_queue = QGroupBox(t("group_queue"))
        grp_queue_layout = QVBoxLayout(self._grp_queue)
        self._lbl_queue_count = QLabel()
        grp_queue_layout.addWidget(self._lbl_queue_count)
        left_layout.addWidget(self._grp_queue)

        # Start-position group
        self._grp_start = QGroupBox(t("group_start"))
        grp_start_layout = QVBoxLayout(self._grp_start)

        self._grid = GridWidget()
        self._grid.setToolTip(t("tooltip_grid"))
        self._grid.startPositionChanged.connect(self._on_start_position_changed)
        grp_start_layout.addWidget(self._grid, alignment=Qt.AlignmentFlag.AlignHCenter)

        left_layout.addWidget(self._grp_start)

        # Watermark group
        self._grp_watermark = QGroupBox(t("group_watermark"))
        grp_wm_layout = QVBoxLayout(self._grp_watermark)
        self._lbl_watermark = QLabel(t("lbl_watermark_none"))
        self._lbl_watermark.setWordWrap(True)
        grp_wm_layout.addWidget(self._lbl_watermark)
        wm_btn_row = QHBoxLayout()
        self._btn_watermark = QPushButton(t("btn_watermark"))
        self._btn_watermark.setToolTip(t("tooltip_watermark"))
        self._btn_watermark.clicked.connect(self._on_select_watermark)
        self._btn_watermark_clear = QPushButton(t("btn_watermark_clear"))
        self._btn_watermark_clear.setToolTip(t("tooltip_watermark_clear"))
        self._btn_watermark_clear.clicked.connect(self._on_clear_watermark)
        wm_btn_row.addWidget(self._btn_watermark)
        wm_btn_row.addWidget(self._btn_watermark_clear)
        grp_wm_layout.addLayout(wm_btn_row)
        left_layout.addWidget(self._grp_watermark)

        # Language selector
        lang_row = QHBoxLayout()
        self._lbl_lang = QLabel(t("language_label"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(i18n.AVAILABLE_LANGUAGES)
        self._lang_combo.setCurrentText(i18n.get_language())
        self._lang_combo.currentTextChanged.connect(self._on_language_changed)
        lang_row.addWidget(self._lbl_lang)
        lang_row.addWidget(self._lang_combo)
        lang_row.addStretch()
        left_layout.addLayout(lang_row)

        # Action buttons
        self._btn_generate = QPushButton(t("btn_generate"))
        self._btn_generate.clicked.connect(self._on_generate_pdf)
        left_layout.addWidget(self._btn_generate)

        self._btn_print = QPushButton(t("btn_print"))
        self._btn_print.setEnabled(False)
        self._btn_print.clicked.connect(self._on_print)
        left_layout.addWidget(self._btn_print)

        left_layout.addStretch()

        # ── Right panel (preview) ─────────────────────────────────────────────
        self._preview = PreviewWidget()
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # ── Splitter ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 640])

        self.setCentralWidget(splitter)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_queue(self) -> None:
        """Load the Print sheet from disk and update the grid."""
        try:
            self._records = load_print_queue(self._db_path)
        except Exception as exc:
            QMessageBox.critical(
                self, t("app_title"), t("err_excel", detail=str(exc))
            )
            self._records = []

        self._grid.set_total_records(len(self._records))

        if self._records:
            self._lbl_queue_count.setText(t("status_loaded", n=len(self._records)))
            self._status.showMessage(t("status_loaded", n=len(self._records)))
        else:
            self._lbl_queue_count.setText(t("status_no_records"))
            self._status.showMessage(t("status_no_records"))

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_open_db(self) -> None:
        """Open a system file dialog so the user can pick a database.xlsx."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("dlg_open_db_title"),
            str(self._db_path.parent),
            t("dlg_open_db_filter"),
        )
        if not path:
            return  # user cancelled
        self._db_path = Path(path)
        self._pdf_path = None
        self._btn_print.setEnabled(False)
        self._load_queue()
        self._status.showMessage(
            t("status_db_loaded", path=self._db_path.name)
        )

    def _update_watermark_label(self) -> None:
        if self._watermark_path:
            self._lbl_watermark.setText(self._watermark_path.name)
        else:
            self._lbl_watermark.setText(t("lbl_watermark_none"))

    def _on_select_watermark(self) -> None:
        """Open a file dialog to pick a PNG/JPG watermark image."""
        start_dir = (
            str(self._watermark_path.parent)
            if self._watermark_path else str(Path.home())
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("dlg_watermark_title"),
            start_dir,
            t("dlg_watermark_filter"),
        )
        if not path:
            return
        self._watermark_path = Path(path)
        set_watermark_path(self._watermark_path)
        self._lbl_watermark.setText(self._watermark_path.name)
        self._status.showMessage(t("status_watermark_set",
                                   name=self._watermark_path.name))

    def _on_clear_watermark(self) -> None:
        """Remove the watermark selection."""
        self._watermark_path = None
        set_watermark_path(None)
        self._lbl_watermark.setText(t("lbl_watermark_none"))
        self._status.showMessage(t("status_watermark_cleared"))

    def _on_reload(self) -> None:
        """Re-read the print queue from the current database file."""
        self._load_queue()
        self._status.showMessage(
            t("status_reloaded", n=len(self._records))
        )

    def _on_start_position_changed(self, index: int) -> None:
        """Regenerate PDF immediately when the user picks a new start cell."""
        if self._pdf_path is not None:
            self._on_generate_pdf()

    def _on_generate_pdf(self) -> None:
        if not self._records:
            self._status.showMessage(t("status_no_records"))
            return

        # Validate watermark file before generating
        if self._watermark_path is not None and not self._watermark_path.exists():
            QMessageBox.warning(
                self, t("app_title"),
                t("err_watermark_missing", path=str(self._watermark_path)),
            )
            return

        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._pdf_path = _OUT_DIR / _PDF_NAME

        generate_pdf(
            records=self._records,
            output_path=self._pdf_path,
            format_name="4780",
            start_position=self._grid.start_index,
            watermark_path=self._watermark_path,
        )

        self._preview.load_pdf(self._pdf_path)
        self._btn_print.setEnabled(True)
        self._status.showMessage(t("status_pdf_ready"))

    def _on_print(self) -> None:
        if self._pdf_path is None or not self._pdf_path.exists():
            QMessageBox.warning(self, t("app_title"), t("err_no_pdf"))
            return
        try:
            print_pdf(self._pdf_path)
            self._status.showMessage(t("status_printing"))
        except Exception as exc:
            QMessageBox.critical(
                self, t("app_title"), t("err_print", detail=str(exc))
            )

    def _on_language_changed(self, code: str) -> None:
        """Switch the active language and retranslate all widgets."""
        try:
            i18n.set_language(code)
        except KeyError:
            return
        self._retranslate_ui()

    # ── Retranslation ─────────────────────────────────────────────────────────

    def _retranslate_ui(self) -> None:
        """Update every translatable string after a language switch."""
        self.setWindowTitle(t("app_title"))
        self._grp_queue.setTitle(t("group_queue"))
        self._grp_start.setTitle(t("group_start"))
        self._grid.setToolTip(t("tooltip_grid"))
        self._lbl_lang.setText(t("language_label"))
        self._btn_open_db.setText(t("btn_open_db"))
        self._btn_open_db.setToolTip(t("tooltip_open_db"))
        self._btn_reload.setText(t("btn_reload"))
        self._btn_reload.setToolTip(t("tooltip_reload"))
        self._grp_watermark.setTitle(t("group_watermark"))
        self._btn_watermark.setText(t("btn_watermark"))
        self._btn_watermark.setToolTip(t("tooltip_watermark"))
        self._btn_watermark_clear.setText(t("btn_watermark_clear"))
        self._btn_watermark_clear.setToolTip(t("tooltip_watermark_clear"))
        self._update_watermark_label()
        self._btn_generate.setText(t("btn_generate"))
        self._btn_print.setText(t("btn_print"))

        # Update queue count label text
        if self._records:
            self._lbl_queue_count.setText(t("status_loaded", n=len(self._records)))
            self._status.showMessage(t("status_loaded", n=len(self._records)))
        else:
            self._lbl_queue_count.setText(t("status_no_records"))
            self._status.showMessage(t("status_no_records"))

        # Retranslate preview navigation buttons/label
        self._preview.retranslate()
