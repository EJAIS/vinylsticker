"""
Main application window.

Wires together:
  - SidebarWidget   — navigation / action panel
  - PreviewWidget   — PDF preview
  - FooterWidget    — settings button + connection / mode status
  - label_store     — print queue (labels.db)
  - pdf_generator   — PDF generation
  - printer         — OS print trigger
  - i18n            — language switching

Printed marking (LOCAL mode): after a successful "Print" or "Create PDF" the
user is asked once whether the labels of the PDF that are linked to the
collection (record_id) should be marked as printed. The question is not
repeated for the same unchanged queue in this session (e.g. "Create PDF"
followed by "Print"), and not asked when the step was aborted or failed.
The OS print dialog itself is outside the app: whether the user printed or
cancelled there is not visible, hence the question.

PDF and queue stay in step: once a PDF was created in this session, every
reload of the queue whose content differs from the PDF's regenerates it, and
so does a watermark or calibration change in the settings. These automatic
regenerations never ask the printed question. An empty queue clears the
preview; a failed generation disables "Print", so an outdated PDF can never
be printed.
"""

from __future__ import annotations

import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
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
from __version__ import __version__
from modules.i18n import t
from modules.logger import get_logger

logger = get_logger()
from modules import label_store
from modules.records import SIDES, LabelRecord
from modules.pdf_generator import generate_pdf
from modules.printer import print_pdf
from modules.data_source import DataSourceMode
from modules.credentials_manager import CredentialsManager
from modules.paths import get_output_dir
from config.settings import (
    get_watermark_path, set_watermark_path,
    get_data_source_mode,
    get_debug_logging,
    get_calibration_x,
    get_calibration_y,
)
from ui.grid_widget import GridWidget
from ui.preview_widget import PreviewWidget
from ui.sidebar_widget import SidebarWidget
from ui.footer_widget import FooterWidget
from ui.collection_dialog import CollectionDialog
from ui.discogs_dialog import DiscogsDialog
from ui.review_widget import ReviewDialog
from ui.shortcuts import StandardKey, add_shortcut, keys, shortcut_text, with_shortcut
from ui.window_state import restore_geometry, save_geometry

_PDF_NAME = "labels.pdf"
# "Print" hands a copy of the PDF to the OS (see _print_copy); the newest
# copies are kept because a viewer may still have them open
_PRINT_COPY_PREFIX = "labels-print-"
_PRINT_COPIES_KEPT = 5
# A calibration spin box emits a change per step: regenerate once it settles
_LAYOUT_REFRESH_MS = 400
_GEOMETRY_KEY = "main_window"


def _window_title() -> str:
    """Main window title incl. version — rebuilt on every language switch."""
    return f"{t('app_title')} v{__version__}"


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self._records:        list[LabelRecord] = []
        # The current, printable PDF; None while there is none or it failed
        self._pdf_path:       Path | None = None
        # A PDF was created in this session: keep it in step with the queue.
        # None is created on app start.
        self._pdf_in_session: bool = False
        # Queue state of the last PDF generation attempt (successful or not)
        self._pdf_target:     tuple | None = None
        # Queue rows in the current PDF, and the queue state the printed
        # question was last asked for (asked once per unchanged queue)
        self._pdf_records:    list[LabelRecord] = []
        self._printed_asked:  tuple | None = None
        self._watermark_path: Path | None = get_watermark_path()
        self._mode:           DataSourceMode = get_data_source_mode()
        # The start position is deliberately not persisted: it is label 1 on
        # app start and is reset to label 1 after every successful "Print",
        # because the next print usually goes onto a fresh sheet.
        self._start_index:    int = 0

        # Apply persisted calibration to the active format dict
        from config.avery_formats import AVERY_FORMATS
        AVERY_FORMATS["4780"]["calibration_x_mm"] = get_calibration_x()
        AVERY_FORMATS["4780"]["calibration_y_mm"] = get_calibration_y()

        # Debounces PDF regenerations after watermark / calibration changes
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(_LAYOUT_REFRESH_MS)
        self._layout_timer.timeout.connect(self._refresh_pdf_layout)

        self._init_ui()
        self._init_shortcuts()
        self._load_queue()
        self._update_footer_status()
        self._footer.update_debug_mode(get_debug_logging())
        restore_geometry(self, _GEOMETRY_KEY)
        logger.info("Main window started")

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle(_window_title())
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
        self._footer.mode_badge_clicked.connect(self._on_mode_badge_clicked)

    def _init_shortcuts(self) -> None:
        """Window shortcuts; they do not fire while a modal dialog is open."""
        self._shortcut_keys = {
            "load_data":  keys(None, "Ctrl+L"),
            "queue":      keys(None, "Ctrl+E"),
            "create_pdf": keys(None, "Ctrl+Shift+P"),
            "print":      keys(StandardKey.Print, "Ctrl+P"),
            "settings":   keys(None, "Ctrl+,"),
        }
        slots = {
            "load_data":  self.on_load_data,
            "queue":      self.on_open_queue,
            "create_pdf": self.on_create_pdf,
            "print":      self._on_print_shortcut,
            "settings":   self.on_open_settings,
        }
        self._shortcuts = {
            name: add_shortcut(self, self._shortcut_keys[name], slot)
            for name, slot in slots.items()
        }
        self._update_shortcut_tooltips()

    def _update_shortcut_tooltips(self) -> None:
        self._sidebar.set_shortcut_hints({
            name: shortcut_text(seqs[:1]) for name, seqs in self._shortcut_keys.items()
        })
        self._footer.set_settings_tooltip(
            with_shortcut(t("menu_settings"), self._shortcut_keys["settings"])
        )

    def _on_print_shortcut(self) -> None:
        if self._sidebar.print_enabled():
            self.on_print()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_queue(self) -> None:
        """Load the print queue from labels.db; bring PDF, preview and footer in step."""
        try:
            self._records = label_store.load_queue()
        except Exception as exc:
            logger.error(f"Could not load the print queue: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self, t("app_title"), t("err_queue_load", detail=str(exc))
            )
            self._records = []
        self._sidebar.set_queue_count(len(self._records))
        self._sync_pdf_with_queue()
        self._update_placeholder()
        self._update_collection_status()

    def _sync_pdf_with_queue(self) -> None:
        """Regenerate the PDF if the queue content differs from it (no printed question)."""
        if not self._records:
            self._clear_pdf()
            return
        if not self._pdf_in_session:
            return
        if self._queue_state(self._records) == self._pdf_target:
            return
        logger.debug("Print queue changed — regenerating the PDF")
        self._create_pdf()

    def _clear_pdf(self) -> None:
        """No printable PDF: placeholder in the preview, "Print" off, PDF status reset."""
        self._pdf_path = None
        self._pdf_records = []
        self._preview.clear()
        self._sidebar.set_print_enabled(False)
        self._sidebar.set_pdf_status("ready")

    # ── Main action handlers ──────────────────────────────────────────────────

    def on_load_data(self) -> None:
        """Load data button: open the collection (LOCAL) or the Discogs dialog (DISCOGS)."""
        if self._mode == DataSourceMode.DISCOGS:
            dlg = DiscogsDialog(parent=self)
            accepted = dlg.exec() == QDialog.DialogCode.Accepted
            dlg.deleteLater()
            if accepted:
                self._load_queue()
                self._update_footer_status()
        else:
            dlg = CollectionDialog(parent=self)
            # Record edits can update linked queue rows
            dlg.queue_changed.connect(self._load_queue)
            dlg.collection_changed.connect(self._update_collection_status)
            accepted = dlg.exec() == QDialog.DialogCode.Accepted
            dlg.deleteLater()
            if accepted:
                self._load_queue()
            else:
                self._update_collection_status()

    def on_open_queue(self) -> None:
        """Queue button: open the queue editor (ReviewDialog), also when the queue is empty.

        In LOCAL mode it offers "Also save to collection" for new entries.
        """
        dlg = ReviewDialog(
            [asdict(r) for r in self._records],
            parent=self,
            collection=self._mode == DataSourceMode.LOCAL,
        )
        accepted = dlg.exec() == QDialog.DialogCode.Accepted
        dlg.deleteLater()
        if accepted:
            self._load_queue()

    def on_pick_start_pos(self) -> None:
        """Start position button: open the GridWidget in a small dialog."""
        dlg = self._create_start_pos_dialog()
        dlg.exec()
        dlg.deleteLater()
        self._update_start_position_text()

    def _update_start_position_text(self) -> None:
        row = self._start_index // GridWidget.COLS + 1
        col = self._start_index % GridWidget.COLS + 1
        self._sidebar.set_start_position(self._start_index + 1, row, col)

    def _create_start_pos_dialog(self) -> QDialog:
        """Build the modal start position picker (GridWidget + OK button)."""
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
            if self._pdf_in_session and self._records:
                # A new start position re-renders the same labels: no question
                self._create_pdf()

        grid.startPositionChanged.connect(_on_pos)

        btn_ok = QPushButton("OK")
        btn_ok.setProperty("primary", True)
        btn_ok.clicked.connect(dlg.accept)
        layout.addWidget(btn_ok, 0, Qt.AlignmentFlag.AlignRight)
        return dlg

    def on_create_pdf(self) -> None:
        """Create PDF button: generate PDF, load it into the preview, offer the printed mark."""
        if self._create_pdf():
            self._offer_mark_printed()

    def _create_pdf(self) -> bool:
        """Generate the PDF and load it into the preview; True on success.

        Never asks the printed question (only on_create_pdf / on_print do). On
        failure "Print" is disabled, so the previous PDF cannot be printed.
        """
        if not self._records:
            return False
        self._pdf_target = self._queue_state(self._records)

        if self._watermark_path is not None and not self._watermark_path.exists():
            self._clear_pdf()
            QMessageBox.warning(
                self, t("app_title"),
                t("err_watermark_missing", path=str(self._watermark_path)),
            )
            return False

        self._sidebar.set_pdf_status("generating")
        QApplication.processEvents()

        pdf_path = get_output_dir() / _PDF_NAME

        try:
            generate_pdf(
                records=self._records,
                output_path=pdf_path,
                format_name="4780",
                start_position=self._start_index,
                watermark_path=self._watermark_path,
            )
        except Exception as exc:
            logger.error(f"PDF generation failed: {type(exc).__name__}: {exc}")
            self._clear_pdf()
            QMessageBox.critical(
                self, t("app_title"), t("err_pdf", detail=str(exc))
            )
            return False

        self._pdf_path = pdf_path
        self._pdf_in_session = True
        self._pdf_records = list(self._records)
        self._preview.load_pdf(self._pdf_path)
        self._sidebar.set_pdf_status("done")
        self._sidebar.set_print_enabled(True)
        return True

    def _on_print_layout_changed(self) -> None:
        """Watermark or calibration changed: regenerate an existing PDF (debounced)."""
        if self._pdf_in_session and self._records:
            self._layout_timer.start()

    def _refresh_pdf_layout(self) -> None:
        if self._pdf_in_session and self._records:
            logger.debug("Watermark / calibration changed — regenerating the PDF")
            self._create_pdf()

    def on_print(self) -> None:
        """Print button: send the generated PDF to the OS print dialog."""
        if self._pdf_path is None or not self._pdf_path.exists():
            QMessageBox.warning(self, t("app_title"), t("err_no_pdf"))
            return
        try:
            print_pdf(self._print_copy())
        except Exception as exc:
            QMessageBox.critical(
                self, t("app_title"), t("err_print", detail=str(exc))
            )
            return
        self._offer_mark_printed()
        self._reset_start_position()

    def _print_copy(self) -> Path:
        """Copy the PDF for the OS print dialog and return the copy.

        The viewer opened by print_pdf() reads the file asynchronously, and
        the PDF is regenerated right after printing (start position reset):
        a copy of its own keeps the viewer on the labels that were printed.
        Older copies beyond the newest few are removed (files still open in
        a viewer on Windows cannot be, and are tried again next time).
        """
        assert self._pdf_path is not None
        folder = self._pdf_path.parent
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        copy = folder / f"{_PRINT_COPY_PREFIX}{stamp}.pdf"
        shutil.copyfile(self._pdf_path, copy)
        old = sorted(folder.glob(f"{_PRINT_COPY_PREFIX}*.pdf"), reverse=True)
        for path in old[_PRINT_COPIES_KEPT:]:
            try:
                path.unlink()
            except OSError as exc:
                logger.debug(f"Could not remove old print copy {path.name}: {exc}")
        return copy

    def _reset_start_position(self) -> None:
        """After a successful "Print": start position back to label 1, PDF to match."""
        if self._start_index == 0:
            return
        self._start_index = 0
        self._update_start_position_text()
        if self._records:
            self._create_pdf()

    # ── Printed marking (LOCAL mode) ──────────────────────────────────────────

    @staticmethod
    def _queue_state(records: list[LabelRecord]) -> tuple:
        """Everything that identifies the printed labels (rows, data, links)."""
        return tuple(
            (r.id, r.title, r.artist, r.label, r.country, r.year, r.side, r.catno,
             r.record_id, r.record_side)
            for r in records
        )

    def _offer_mark_printed(self) -> None:
        """Ask once per unchanged queue whether to mark the linked labels of the PDF as printed.

        Only rows linked to a collection record side count; DISCOGS mode never asks.
        """
        if self._mode != DataSourceMode.LOCAL:
            return
        linked = [
            r for r in self._pdf_records if r.record_id is not None and r.record_side in SIDES
        ]
        if not linked:
            return
        state = self._queue_state(self._pdf_records)
        if state == self._printed_asked:
            return
        self._printed_asked = state
        if not self._ask_mark_printed(len(linked)):
            return
        try:
            label_store.mark_sides_printed([(r.record_id, r.record_side) for r in linked])
        except Exception as exc:
            logger.error(f"Could not mark labels as printed: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self, t("app_title"), t("printed_mark_err", detail=str(exc))
            )
        self._update_collection_status()

    def _ask_mark_printed(self, n_labels: int) -> bool:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(t("printed_ask_title"))
        msg.setText(t("printed_ask_msg", n=n_labels))
        btn_yes = msg.addButton(t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(t("btn_no"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(btn_yes)
        msg.setEscapeButton(btn_no)
        msg.exec()
        return msg.clickedButton() == btn_yes

    def on_open_settings(self) -> None:
        """Settings button: open SettingsDialog (singleton — reuse across calls)."""
        from ui.settings_dialog import SettingsDialog
        if not hasattr(self, "_settings_dialog"):
            self._settings_dialog = SettingsDialog(self)
            self._settings_dialog.mode_changed.connect(self.on_mode_changed)
            self._settings_dialog.language_changed.connect(self._retranslate_ui)
            self._settings_dialog.debug_mode_changed.connect(
                self._footer.update_debug_mode
            )
            self._settings_dialog.print_layout_changed.connect(
                self._on_print_layout_changed
            )
        self._settings_dialog.show()
        self._settings_dialog.raise_()

    def _on_debug_badge_clicked(self) -> None:
        """Open Settings dialog and navigate to the Appearance tab."""
        self.on_open_settings()
        self._settings_dialog.switch_to_tab(0)

    def _on_mode_badge_clicked(self) -> None:
        """Open Settings dialog and navigate to the Data source tab."""
        self.on_open_settings()
        self._settings_dialog.switch_to_tab(1)

    def on_mode_changed(self, mode_str: str) -> None:
        """React to data-source mode change from the settings dialog."""
        self._mode = DataSourceMode(mode_str)
        logger.debug(f"Mode changed: {mode_str}")
        self._footer.update_mode(self._mode)
        self._sidebar.set_active_mode(self._mode)
        self._update_footer_status()
        self._update_placeholder()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _update_footer_status(self) -> None:
        """Sync footer status (Discogs connection / collection) and mode badge."""
        if self._mode == DataSourceMode.DISCOGS:
            creds = CredentialsManager().load()
            username = creds.get("discogs_username", "")
            self._footer.update_discogs_status(bool(username), username)
        else:
            self._footer.update_discogs_status(False, "")
            self._update_collection_status()
        self._footer.update_mode(self._mode)

    def _update_collection_status(self) -> None:
        """Collection counts in the footer (LOCAL mode only)."""
        if self._mode != DataSourceMode.LOCAL:
            return
        try:
            n_records, n_unprinted = label_store.collection_counts()
        except Exception as exc:
            logger.warning(f"Could not count the collection: {type(exc).__name__}: {exc}")
            return
        self._footer.update_collection_status(n_records, n_unprinted)

    def _update_placeholder(self) -> None:
        """Preview hint for the current queue and mode (shown while there is no PDF)."""
        if self._records:
            text = t("preview_hint_no_pdf", n=len(self._records))
        elif self._mode == DataSourceMode.DISCOGS:
            text = t("preview_hint_empty_discogs")
        else:
            text = t("preview_hint_empty_local")
        self._preview.set_placeholder_text(text)

    # ── Window geometry ───────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        save_geometry(self, _GEOMETRY_KEY)
        settings_dialog = getattr(self, "_settings_dialog", None)
        if settings_dialog is not None and settings_dialog.isVisible():
            # Closed together with the main window, without its own done()
            settings_dialog.reject()
        super().closeEvent(event)

    # ── Watermark (preserved for SettingsDialog integration) ──────────────────

    def _on_select_watermark(self) -> bool:
        """Choose a watermark file; True if one was chosen."""
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
            return False
        self._watermark_path = Path(path)
        set_watermark_path(self._watermark_path)
        return True

    def _on_clear_watermark(self) -> bool:
        """Remove the watermark; True if there was one."""
        had_watermark = self._watermark_path is not None
        self._watermark_path = None
        set_watermark_path(None)
        return had_watermark

    # ── Theme / language ──────────────────────────────────────────────────────

    def _on_language_changed(self, code: str) -> None:
        try:
            i18n.set_language(code)
        except KeyError:
            return
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        """Update all translatable strings after a language switch."""
        self.setWindowTitle(_window_title())
        self._sidebar.retranslate()
        self._footer.retranslate()
        self._preview.retranslate()
        self._sidebar.set_queue_count(len(self._records))
        self._update_shortcut_tooltips()
        self._update_placeholder()
