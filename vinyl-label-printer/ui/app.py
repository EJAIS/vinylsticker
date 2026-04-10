"""
Main application window.

Wires together:
  - SidebarWidget   — navigation / action panel
  - PreviewWidget   — PDF preview
  - FooterWidget    — settings button + connection / mode status
  - excel_reader    — print-queue loader
  - pdf_generator   — PDF generation
  - printer         — OS print trigger
  - i18n            — language switching
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import modules.i18n as i18n
from modules.i18n import t
from modules.logger import get_logger

logger = get_logger()
from modules.excel_reader import LabelRecord, load_print_queue
from modules.pdf_generator import generate_pdf
from modules.printer import print_pdf
from modules.data_source import DataSourceMode
from modules.credentials_manager import CredentialsManager
from config.settings import (
    get_watermark_path, set_watermark_path,
    get_data_source_mode, set_data_source_mode,
    get_theme,
    get_debug_logging,
)
from ui.grid_widget import GridWidget
from ui.preview_widget import PreviewWidget
from ui.sidebar_widget import SidebarWidget
from ui.footer_widget import FooterWidget
from ui.discogs_dialog import DiscogsDialog
from ui.review_widget import ReviewDialog

# Paths resolved relative to vinyl-label-printer/
_BASE_DIR = Path(__file__).parent.parent
_DB_PATH  = _BASE_DIR / "data" / "database.xlsx"
_OUT_DIR  = _BASE_DIR / "output"
_PDF_NAME = "labels.pdf"


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._records:        list[LabelRecord] = []
        self._pdf_path:       Path | None = None
        self._db_path:        Path = _DB_PATH
        self._watermark_path: Path | None = get_watermark_path()
        self._mode:           DataSourceMode = get_data_source_mode()
        self._start_index:    int = 0

        self._init_ui()
        self._load_queue()
        self._update_footer_status()
        self._footer.update_debug_mode(get_debug_logging())
        logger.info("Main window started")

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(900, 620)
        self.menuBar().setVisible(False)

        # Sidebar
        self._sidebar = SidebarWidget()
        self._sidebar.set_active_mode(self._mode)
        self._sidebar.set_start_position(1, 1, 1)

        # Preview
        self._preview = PreviewWidget()
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # Footer
        self._footer = FooterWidget()
        self._footer.update_mode(self._mode)

        # Main content (sidebar + preview side by side)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._sidebar)
        content_layout.addWidget(self._preview, 1)

        # Root layout (content + footer stacked vertically)
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(content, 1)
        root_layout.addWidget(self._footer)

        self.setCentralWidget(root)

        # Wire sidebar signals
        self._sidebar.load_data_clicked.connect(self.on_load_data)
        self._sidebar.queue_clicked.connect(self.on_open_queue)
        self._sidebar.start_position_clicked.connect(self.on_pick_start_pos)
        self._sidebar.create_pdf_clicked.connect(self.on_create_pdf)
        self._sidebar.print_clicked.connect(self.on_print)

        # Wire footer signals
        self._footer.settings_clicked.connect(self.on_open_settings)
        self._footer.debug_badge_clicked.connect(self._on_debug_badge_clicked)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_queue(self) -> None:
        """Load the Print sheet from disk and update the sidebar queue count."""
        try:
            self._records = load_print_queue(self._db_path)
        except Exception as exc:
            QMessageBox.critical(
                self, t("app_title"), t("err_excel", detail=str(exc))
            )
            self._records = []
        self._sidebar.set_queue_count(len(self._records))

    # ── Main action handlers ──────────────────────────────────────────────────

    def on_load_data(self) -> None:
        """Load data button: reload Excel (LOCAL) or open Discogs dialog (DISCOGS)."""
        if self._mode == DataSourceMode.DISCOGS:
            dlg = DiscogsDialog(self._db_path, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._load_queue()
                self._update_footer_status()
        else:
            self._load_queue()

    def on_open_queue(self) -> None:
        """Queue button: open the ReviewDialog so the user can inspect / edit records."""
        if not self._records:
            QMessageBox.information(
                self, t("app_title"), t("status_no_records")
            )
            return
        dlg = ReviewDialog(
            [asdict(r) for r in self._records],
            self._db_path,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_queue()

    def on_pick_start_pos(self) -> None:
        """Start position button: open the GridWidget in a small dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle(t("sidebar_start_pos"))
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grid = GridWidget()
        grid.set_total_records(len(self._records))
        grid.set_start_index(self._start_index)
        layout.addWidget(grid, 0, Qt.AlignmentFlag.AlignHCenter)

        def _on_pos(index: int) -> None:
            self._start_index = index
            if self._pdf_path is not None:
                self.on_create_pdf()

        grid.startPositionChanged.connect(_on_pos)

        btn_ok = QPushButton("OK")
        btn_ok.setProperty("primary", True)
        btn_ok.clicked.connect(dlg.accept)
        layout.addWidget(btn_ok, 0, Qt.AlignmentFlag.AlignRight)

        dlg.exec()

        row = self._start_index // GridWidget.COLS + 1
        col = self._start_index % GridWidget.COLS + 1
        self._sidebar.set_start_position(self._start_index + 1, row, col)

    def on_create_pdf(self) -> None:
        """Create PDF button: generate PDF and load it into the preview."""
        if not self._records:
            return

        if self._watermark_path is not None and not self._watermark_path.exists():
            QMessageBox.warning(
                self, t("app_title"),
                t("err_watermark_missing", path=str(self._watermark_path)),
            )
            return

        self._sidebar.set_pdf_status("generating")
        QApplication.processEvents()

        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        self._pdf_path = _OUT_DIR / _PDF_NAME

        generate_pdf(
            records=self._records,
            output_path=self._pdf_path,
            format_name="4780",
            start_position=self._start_index,
            watermark_path=self._watermark_path,
        )

        self._preview.load_pdf(self._pdf_path)
        self._sidebar.set_pdf_status("done")
        self._sidebar.set_print_enabled(True)

    def on_print(self) -> None:
        """Print button: send the generated PDF to the OS print dialog."""
        if self._pdf_path is None or not self._pdf_path.exists():
            QMessageBox.warning(self, t("app_title"), t("err_no_pdf"))
            return
        try:
            print_pdf(self._pdf_path)
        except Exception as exc:
            QMessageBox.critical(
                self, t("app_title"), t("err_print", detail=str(exc))
            )

    def on_open_settings(self) -> None:
        """Settings button: open SettingsDialog (singleton — reuse across calls)."""
        from ui.settings_dialog import SettingsDialog
        if not hasattr(self, "_settings_dialog"):
            self._settings_dialog = SettingsDialog(self)
            self._settings_dialog._db_path = self._db_path
            self._settings_dialog.theme_changed.connect(self.on_theme_changed)
            self._settings_dialog.mode_changed.connect(self.on_mode_changed)
            self._settings_dialog.language_changed.connect(self._retranslate_ui)
            self._settings_dialog.debug_mode_changed.connect(
                self._footer.update_debug_mode
            )
            app_inst = QApplication.instance()
            if app_inst:
                self._settings_dialog.setStyleSheet(app_inst.styleSheet())
        self._settings_dialog.show()
        self._settings_dialog.raise_()

    def _on_debug_badge_clicked(self) -> None:
        """Open Settings dialog and navigate to the Appearance tab."""
        self.on_open_settings()
        self._settings_dialog.switch_to_tab(0)

    def on_theme_changed(self, theme_name: str) -> None:
        """Apply a new theme to the whole application."""
        from config.themes import get_theme as _gc
        from config.stylesheet import build_stylesheet
        colors = _gc(theme_name)
        app = QApplication.instance()
        app.setStyleSheet(build_stylesheet(colors))
        app.setProperty("theme_colors", colors)
        self._sidebar._apply_sidebar_style()
        self._footer._apply_style()
        for w in app.allWidgets():
            w.update()

    def on_mode_changed(self, mode_str: str) -> None:
        """React to data-source mode change from the settings dialog."""
        self._mode = DataSourceMode(mode_str)
        logger.debug(f"Mode changed: {mode_str}")
        self._footer.update_mode(self._mode)
        self._sidebar.set_active_mode(self._mode)
        self._update_footer_status()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _update_footer_status(self) -> None:
        """Sync footer connection dot and mode badge with current state."""
        if self._mode == DataSourceMode.DISCOGS:
            creds = CredentialsManager().load()
            username = creds.get("discogs_username", "")
            self._footer.update_discogs_status(bool(username), username)
        else:
            self._footer.update_discogs_status(False, "")
        self._footer.update_mode(self._mode)

    # ── Watermark (preserved for SettingsDialog integration) ──────────────────

    def _on_select_watermark(self) -> None:
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

    def _on_clear_watermark(self) -> None:
        self._watermark_path = None
        set_watermark_path(None)

    # ── Theme / language ──────────────────────────────────────────────────────

    def _on_language_changed(self, code: str) -> None:
        try:
            i18n.set_language(code)
        except KeyError:
            return
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        """Update all translatable strings after a language switch."""
        self.setWindowTitle(t("app_title"))
        self._sidebar.retranslate()
        self._footer.retranslate()
        self._preview.retranslate()
        self._sidebar.set_queue_count(len(self._records))
