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
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup

import qdarktheme

import modules.i18n as i18n
from modules.i18n import t
from modules.excel_reader import LabelRecord, load_print_queue
from modules.pdf_generator import generate_pdf
from modules.printer import print_pdf
from modules.data_source import DataSourceMode
from modules.credentials_manager import CredentialsManager
from config.settings import (
    get_watermark_path, set_watermark_path,
    get_data_source_mode, set_data_source_mode,
    get_theme, set_theme,
)
from ui.grid_widget import GridWidget
from ui.preview_widget import PreviewWidget
from ui.discogs_dialog import DiscogsDialog

_RADIO_STYLE = """
QRadioButton         { color: #757575; }
QRadioButton:checked { color: #1976D2; font-weight: bold; }
"""

# Paths are resolved relative to this file's location (vinyl-label-printer/)
_BASE_DIR  = Path(__file__).parent.parent
_DB_PATH   = _BASE_DIR / "data" / "database.xlsx"
_OUT_DIR   = _BASE_DIR / "output"
_PDF_NAME  = "labels.pdf"


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._records:          list[LabelRecord] = []
        self._pdf_path:         Path | None = None
        self._db_path:          Path = _DB_PATH
        self._watermark_path:   Path | None = get_watermark_path()
        self._mode:             DataSourceMode = get_data_source_mode()
        self._switching_source: bool = False

        self._init_ui()
        self._init_menu()
        self._load_queue()
        self._update_watermark_label()
        self._apply_mode_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(900, 620)

        # ── Left panel ────────────────────────────────────────────────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(10)

        # Data source toggle
        self._grp_source = QGroupBox(t("datasource_group"))
        grp_source_layout = QVBoxLayout(self._grp_source)
        grp_source_layout.setSpacing(4)
        grp_source_layout.setContentsMargins(6, 4, 6, 4)
        radio_row = QHBoxLayout()
        self._radio_local   = QRadioButton(t("datasource_local"))
        self._radio_discogs = QRadioButton(t("datasource_discogs"))
        self._radio_local.setStyleSheet(_RADIO_STYLE)
        self._radio_discogs.setStyleSheet(_RADIO_STYLE)
        self._source_group = QButtonGroup(self)
        self._source_group.addButton(self._radio_local,   0)
        self._source_group.addButton(self._radio_discogs, 1)
        radio_row.addWidget(self._radio_local)
        radio_row.addWidget(self._radio_discogs)
        radio_row.addStretch()
        grp_source_layout.addLayout(radio_row)
        left_layout.addWidget(self._grp_source)

        self._radio_local.toggled.connect(self._on_source_changed)
        self._radio_discogs.toggled.connect(self._on_source_changed)

        # File picker + reload row
        file_row = QHBoxLayout()
        self._btn_open_db = QPushButton(t("btn_open_db"))
        self._btn_open_db.setToolTip(t("tooltip_open_db"))
        self._btn_open_db.clicked.connect(self._on_open_db)
        self._btn_reload = QPushButton(t("btn_reload"))
        self._btn_reload.setToolTip(t("tooltip_reload"))
        self._btn_reload.clicked.connect(self._on_reload)
        self._btn_discogs = QPushButton(t("btn_discogs"))
        self._btn_discogs.setToolTip(t("tooltip_discogs"))
        self._btn_discogs.clicked.connect(self._on_load_discogs)
        file_row.addWidget(self._btn_open_db)
        file_row.addWidget(self._btn_reload)
        file_row.addWidget(self._btn_discogs)
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

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _init_menu(self) -> None:
        settings_menu = self.menuBar().addMenu("Einstellungen")
        appearance_menu = settings_menu.addMenu("Erscheinungsbild")

        group = QActionGroup(self)
        group.setExclusive(True)

        current = get_theme()
        for label, value in [
            ("Automatisch (Systemeinstellung)", "auto"),
            ("Hell", "light"),
            ("Dunkel", "dark"),
        ]:
            action = QAction(label, self, checkable=True)
            action.setChecked(current == value)
            action.setData(value)
            group.addAction(action)
            appearance_menu.addAction(action)

        group.triggered.connect(self._on_theme_changed)

    def _on_theme_changed(self, action: QAction) -> None:
        from PyQt6.QtWidgets import QApplication
        new_theme = action.data()
        if new_theme == get_theme():
            return
        set_theme(new_theme)
        app = QApplication.instance()
        resolved = new_theme
        if new_theme == "auto":
            resolved = "dark" if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
        app.setStyleSheet(qdarktheme.load_stylesheet(resolved))
        app.setPalette(qdarktheme.load_palette(resolved))
        QMessageBox.information(
            self,
            "Design geändert",
            "Bitte App neu starten, um das Theme vollständig anzuwenden.",
        )

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
        else:
            self._lbl_queue_count.setText(t("status_no_records"))
        self._update_status_bar()

    # ── Data source mode ──────────────────────────────────────────────────────

    def _on_source_changed(self, _checked: bool) -> None:
        if self._switching_source:
            return
        new_mode = (
            DataSourceMode.DISCOGS
            if self._radio_discogs.isChecked()
            else DataSourceMode.LOCAL
        )
        if new_mode == self._mode:
            return

        if new_mode == DataSourceMode.DISCOGS:
            cred_mgr = CredentialsManager()
            if not cred_mgr.are_valid():
                box = QMessageBox(self)
                box.setWindowTitle(t("datasource_no_creds_title"))
                box.setText(t("datasource_no_creds_msg"))
                btn_setup = box.addButton(
                    t("datasource_no_creds_btn"),
                    QMessageBox.ButtonRole.AcceptRole,
                )
                box.addButton(
                    t("btn_cancel_generic"),
                    QMessageBox.ButtonRole.RejectRole,
                )
                box.exec()
                if box.clickedButton() == btn_setup:
                    dlg = DiscogsDialog(self._db_path, parent=self)
                    dlg.exec()
                if not cred_mgr.are_valid():
                    self._revert_source()
                    return

            if self._records:
                box = QMessageBox(self)
                box.setWindowTitle(t("datasource_overwrite_title"))
                box.setText(t("datasource_overwrite_msg", n=len(self._records)))
                btn_cont = box.addButton(
                    t("datasource_overwrite_continue"),
                    QMessageBox.ButtonRole.AcceptRole,
                )
                box.addButton(
                    t("btn_cancel_generic"),
                    QMessageBox.ButtonRole.RejectRole,
                )
                box.exec()
                if box.clickedButton() != btn_cont:
                    self._revert_source()
                    return

        else:  # LOCAL
            QMessageBox.information(
                self,
                t("datasource_switch_local_title"),
                t("datasource_switch_local_msg"),
            )

        self._mode = new_mode
        set_data_source_mode(new_mode)
        self._apply_mode_ui()
        self._update_status_bar()

    def _revert_source(self) -> None:
        """Restore radio buttons to match the current mode without triggering the slot."""
        self._switching_source = True
        self._radio_local.setChecked(self._mode == DataSourceMode.LOCAL)
        self._radio_discogs.setChecked(self._mode == DataSourceMode.DISCOGS)
        self._switching_source = False

    def _apply_mode_ui(self) -> None:
        """Sync all mode-dependent widget states to self._mode."""
        is_discogs = self._mode == DataSourceMode.DISCOGS
        self._btn_discogs.setEnabled(is_discogs)
        self._btn_discogs.setToolTip(
            t("tooltip_discogs") if is_discogs else t("tooltip_discogs_disabled")
        )
        self._grp_source.setToolTip(
            t("datasource_discogs_hint") if is_discogs else ""
        )
        self._switching_source = True
        self._radio_local.setChecked(not is_discogs)
        self._radio_discogs.setChecked(is_discogs)
        self._switching_source = False

    def _update_status_bar(self) -> None:
        """Show a mode-aware status message in the status bar."""
        n = len(self._records)
        if self._mode == DataSourceMode.DISCOGS:
            creds = CredentialsManager().load()
            username = creds.get("discogs_username", "")
            if n:
                self._status.showMessage(
                    t("status_mode_discogs", username=username, n=n)
                )
            else:
                self._status.showMessage(
                    t("status_mode_discogs_empty", username=username)
                )
        else:
            if n:
                self._status.showMessage(t("status_mode_local", n=n))
            else:
                self._status.showMessage(t("status_mode_local_empty"))

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

    def _on_load_discogs(self) -> None:
        """Open the Discogs import dialog; reload the print queue on success."""
        if self._mode != DataSourceMode.DISCOGS:
            return
        dlg = DiscogsDialog(self._db_path, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_queue()

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
        self._grp_source.setTitle(t("datasource_group"))
        self._radio_local.setText(t("datasource_local"))
        self._radio_discogs.setText(t("datasource_discogs"))
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
        self._btn_discogs.setText(t("btn_discogs"))
        self._apply_mode_ui()  # re-applies tooltip based on mode
        self._btn_generate.setText(t("btn_generate"))
        self._btn_print.setText(t("btn_print"))

        # Update queue count label text
        if self._records:
            self._lbl_queue_count.setText(t("status_loaded", n=len(self._records)))
        else:
            self._lbl_queue_count.setText(t("status_no_records"))
        self._update_status_bar()

        # Retranslate preview navigation buttons/label
        self._preview.retranslate()
