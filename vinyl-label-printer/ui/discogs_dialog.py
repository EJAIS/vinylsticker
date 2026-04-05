"""
Discogs import dialog.

Flow:
  1. On open: load credentials via CredentialsManager.
  2. No valid credentials → show Setup panel.
  3. Valid credentials → show Collection panel directly.
  4. User selects releases → "In Druckwarteschlange übernehmen"
     → _TracklistWorker fetches A/B tracks for each release
     → ReviewDialog opens for editing / confirmation
     → on ReviewDialog.accept(): write to Print sheet, close dialog

Setup panel
───────────
  • Username + Token fields
  • "Token prüfen und speichern" → verify via API, then switch to Collection panel

Collection panel
────────────────
  • "Angemeldet als: {username}" + "Abmelden" button
  • "7\" Singles laden" → background fetch with progress label
  • Live search bar (filters in-memory list)
  • QTableWidget: ☐ | Titel | Interpret | Label | Jahr
  • "Alle auswählen" / "Auswahl aufheben"
  • "In Druckwarteschlange übernehmen" → fetch tracklists → open ReviewDialog
  • "Abbrechen"
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import requests as _requests
from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.credentials_manager import CredentialsManager
from modules.discogs_client import DiscogsClient
from modules.i18n import t
from ui.review_widget import ReviewDialog


# ── Background workers ────────────────────────────────────────────────────────

class _VerifyWorker(QThread):
    """Verify a token without blocking the UI."""

    success = pyqtSignal()
    failure = pyqtSignal(str)

    def __init__(self, username: str, token: str, parent=None) -> None:
        super().__init__(parent)
        self._username = username
        self._token    = token

    def run(self) -> None:
        try:
            valid = DiscogsClient(self._username, self._token).verify_token()
        except ConnectionError:
            self.failure.emit(t("discogs_err_network"))
            return
        except Exception as exc:
            self.failure.emit(str(exc))
            return
        if valid:
            self.success.emit()
        else:
            self.failure.emit(t("discogs_err_token"))


class _FetchWorker(QThread):
    """Fetch the collection in the background."""

    progress = pyqtSignal(int, int)   # current_page, total_pages
    finished = pyqtSignal(list)       # list[dict] raw releases
    error    = pyqtSignal(int, str)   # http_status_code (0=network), message

    def __init__(self, username: str, token: str, parent=None) -> None:
        super().__init__(parent)
        self._username = username
        self._token    = token

    def run(self) -> None:
        try:
            client   = DiscogsClient(self._username, self._token)
            releases = client.fetch_collection(
                progress_callback=lambda cur, tot: self.progress.emit(cur, tot)
            )
            self.finished.emit(releases)
        except _requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            self.error.emit(code, str(exc))
        except ConnectionError:
            self.error.emit(0, t("discogs_err_network"))
        except Exception as exc:
            self.error.emit(0, str(exc))


class _TracklistWorker(QThread):
    """Fetch tracklists for selected releases and expand into per-side rows."""

    progress = pyqtSignal(int, int)   # n, total
    finished = pyqtSignal(list, list) # (records_data: list[dict], warnings: list[str])

    def __init__(
        self,
        selected: list[dict],
        username: str,
        token: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._selected = selected
        self._username = username
        self._token    = token

    def run(self) -> None:
        client: DiscogsClient = DiscogsClient(self._username, self._token)
        total         = len(self._selected)
        records_data: list[dict] = []
        warnings:     list[str]  = []

        for n, release in enumerate(self._selected, 1):
            self.progress.emit(n, total)
            base = {
                "artist": release["artist"],
                "label":  release["label"],
                "year":   release["year"],
                # country is populated from the release endpoint below;
                # fall back to the collection value if the fetch fails
                "country": release["country"],
            }
            try:
                result = client.fetch_tracklist(release["discogs_id"])
            except Exception:
                warnings.append(release["title"])
                records_data.append({**base, "title": release["title"], "side": ""})
                continue

            # Overwrite country with the authoritative value from the release endpoint
            base["country"] = result["country"] or release["country"]
            tracks = result["tracks"]

            a_sides = [trk for trk in tracks if trk["position"] == "A"]
            b_sides = [trk for trk in tracks if trk["position"] == "B"]

            if len(a_sides) == 1 and len(b_sides) == 1:
                # Simple single: two rows with individual track titles
                records_data.append({**base, "title": a_sides[0]["title"], "side": "A"})
                records_data.append({**base, "title": b_sides[0]["title"], "side": "B"})
            elif tracks:
                # EP / Maxi / ambiguous: one row per track, full position as side
                for trk in tracks:
                    records_data.append(
                        {**base, "title": trk["title"], "side": trk["position"]}
                    )
            else:
                # No AB tracks returned: one fallback row
                records_data.append({**base, "title": release["title"], "side": ""})

        self.finished.emit(records_data, warnings)


# ── Main dialog ───────────────────────────────────────────────────────────────

_SETUP_IDX      = 0
_COLLECTION_IDX = 1

_COL_CHECK  = 0
_COL_TITLE  = 1
_COL_ARTIST = 2
_COL_LABEL  = 3
_COL_YEAR   = 4


class DiscogsDialog(QDialog):
    """Import 7\" singles from Discogs into the print queue.

    The filtered 7" release list is cached at class level so that reopening
    the dialog within the same session skips the API call.  The cache is
    keyed by Discogs username and cleared on logout.
    """

    # Class-level session cache — persists across dialog instances
    _cached_releases: list[dict] = []
    _cache_username:  str        = ""

    def __init__(self, db_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._db_path   = db_path
        self._cred_mgr  = CredentialsManager()
        self._releases: list[dict] = []
        self._displayed: list[dict] = []
        self._rate_timer: Optional[QTimer] = None
        self._rate_countdown = 0
        self._fetch_worker:     Optional[_FetchWorker]     = None
        self._verify_worker:    Optional[_VerifyWorker]    = None
        self._tracklist_worker: Optional[_TracklistWorker] = None

        self.setWindowTitle(t("dlg_discogs_title"))
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setMinimumSize(480, 380)
        self.resize(760, 600)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._init_state()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_setup_panel())
        self._stack.addWidget(self._build_collection_panel())
        root.addWidget(self._stack)

    # Setup panel ─────────────────────────────────────────────────────────────

    def _build_setup_panel(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        title = QLabel(f"<b>{t('discogs_setup_heading')}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(t("discogs_setup_info"))
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        layout.addWidget(info)

        form_grp    = QGroupBox(t("discogs_group_creds"))
        form_layout = QVBoxLayout(form_grp)

        user_row = QHBoxLayout()
        user_row.addWidget(QLabel(t("discogs_lbl_username")))
        self._setup_username = QLineEdit()
        self._setup_username.setPlaceholderText(t("discogs_ph_username"))
        user_row.addWidget(self._setup_username)
        form_layout.addLayout(user_row)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel(t("discogs_lbl_token")))
        self._setup_token = QLineEdit()
        self._setup_token.setPlaceholderText(t("discogs_ph_token"))
        self._setup_token.setEchoMode(QLineEdit.EchoMode.Password)
        token_row.addWidget(self._setup_token)
        form_layout.addLayout(token_row)

        layout.addWidget(form_grp)

        self._setup_status = QLabel("")
        self._setup_status.setWordWrap(True)
        layout.addWidget(self._setup_status)

        self._btn_verify = QPushButton(t("discogs_btn_verify"))
        self._btn_verify.clicked.connect(self._on_verify_token)
        layout.addWidget(self._btn_verify)

        btn_cancel_setup = QPushButton(t("discogs_btn_cancel"))
        btn_cancel_setup.clicked.connect(self.reject)
        layout.addWidget(btn_cancel_setup)

        layout.addStretch()
        return w

    # Collection panel ────────────────────────────────────────────────────────

    def _build_collection_panel(self) -> QWidget:
        w      = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # Auth status row
        auth_row = QHBoxLayout()
        self._lbl_auth_status = QLabel("")
        auth_row.addWidget(self._lbl_auth_status)
        auth_row.addStretch()
        self._btn_logout = QPushButton(t("discogs_btn_logout"))
        self._btn_logout.setFlat(True)
        self._btn_logout.clicked.connect(self._on_logout)
        auth_row.addWidget(self._btn_logout)
        layout.addLayout(auth_row)

        # Fetch button + progress label
        fetch_row = QHBoxLayout()
        self._btn_fetch = QPushButton(t("discogs_btn_fetch"))
        self._btn_fetch.clicked.connect(self._on_fetch)
        fetch_row.addWidget(self._btn_fetch)
        self._lbl_progress = QLabel("")
        fetch_row.addWidget(self._lbl_progress)
        fetch_row.addStretch()
        layout.addLayout(fetch_row)

        # Search bar
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(t("discogs_search_lbl")))
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText(t("discogs_search_ph"))
        self._search_bar.textChanged.connect(self._on_search)
        search_row.addWidget(self._search_bar)
        layout.addLayout(search_row)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "☐",
            t("discogs_col_title"),
            t("discogs_col_artist"),
            t("discogs_col_label"),
            t("discogs_col_year"),
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_CHECK, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_TITLE, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_ARTIST, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_LABEL, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_YEAR, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Select all / deselect all
        select_row = QHBoxLayout()
        btn_all = QPushButton(t("discogs_btn_all"))
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none = QPushButton(t("discogs_btn_none"))
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        select_row.addWidget(btn_all)
        select_row.addWidget(btn_none)
        select_row.addStretch()
        layout.addLayout(select_row)

        # Accept / cancel
        btn_row = QHBoxLayout()
        self._btn_import = QPushButton(t("discogs_btn_import"))
        self._btn_import.setEnabled(False)
        self._btn_import.clicked.connect(self._on_import)
        btn_cancel = QPushButton(t("discogs_btn_cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_import)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        return w

    # ── State initialisation ──────────────────────────────────────────────────

    def _init_state(self) -> None:
        creds    = self._cred_mgr.load()
        username = creds.get("discogs_username", "")
        token    = creds.get("discogs_token", "")
        if username and token:
            self._show_collection_panel(username)
        else:
            self._stack.setCurrentIndex(_SETUP_IDX)

    # ── Slot: verify token ────────────────────────────────────────────────────

    def _on_verify_token(self) -> None:
        username = self._setup_username.text().strip()
        token    = self._setup_token.text().strip()

        if not username or not token:
            self._setup_status.setText(t("discogs_enter_fields"))
            return

        self._btn_verify.setEnabled(False)
        self._setup_status.setText(t("discogs_verifying"))

        self._verify_worker = _VerifyWorker(username, token, parent=self)
        self._verify_worker.success.connect(
            lambda: self._on_verify_success(username, token)
        )
        self._verify_worker.failure.connect(self._on_verify_failure)
        self._verify_worker.finished.connect(
            lambda: self._btn_verify.setEnabled(True)
        )
        self._verify_worker.start()

    def _on_verify_success(self, username: str, token: str) -> None:
        self._cred_mgr.save(username, token)
        self._setup_status.setText("")
        self._show_collection_panel(username)

    def _on_verify_failure(self, message: str) -> None:
        self._setup_status.setText(f"<span style='color:red'>{message}</span>")

    # ── Slot: logout ──────────────────────────────────────────────────────────

    def _on_logout(self) -> None:
        self._cred_mgr.clear()
        self._releases  = []
        self._displayed = []
        DiscogsDialog._cached_releases = []
        DiscogsDialog._cache_username  = ""
        self._table.setRowCount(0)
        self._lbl_progress.setText("")
        self._btn_import.setEnabled(False)
        self._stack.setCurrentIndex(_SETUP_IDX)

    # ── Slot: fetch collection ────────────────────────────────────────────────

    def _on_fetch(self) -> None:
        creds    = self._cred_mgr.load()
        username = creds.get("discogs_username", "")
        token    = creds.get("discogs_token", "")

        self._btn_fetch.setEnabled(False)
        self._btn_import.setEnabled(False)
        self._table.setRowCount(0)
        self._lbl_progress.setText(t("discogs_connecting"))

        self._fetch_worker = _FetchWorker(username, token, parent=self)
        self._fetch_worker.progress.connect(self._on_fetch_progress)
        self._fetch_worker.finished.connect(self._on_fetch_finished)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.finished.connect(
            lambda _: self._btn_fetch.setEnabled(True)
        )
        self._fetch_worker.error.connect(
            lambda *_: self._btn_fetch.setEnabled(True)
        )
        self._fetch_worker.start()

    def _on_fetch_progress(self, current: int, total: int) -> None:
        self._lbl_progress.setText(
            t("discogs_progress", current=current, total=total)
        )

    def _on_fetch_finished(self, raw_releases: list) -> None:
        creds  = self._cred_mgr.load()
        username = creds.get("discogs_username", "")
        client = DiscogsClient(
            username,
            creds.get("discogs_token", ""),
        )
        filtered = client.filter_7inch(raw_releases)

        # Save to class-level session cache
        DiscogsDialog._cached_releases = filtered
        DiscogsDialog._cache_username  = username

        self._apply_releases(filtered, from_cache=False)

    def _apply_releases(self, releases: list[dict], from_cache: bool = False) -> None:
        """Populate the table from a (possibly cached) release list."""
        self._releases  = releases
        self._displayed = list(releases)

        if from_cache:
            self._lbl_progress.setText(t("discogs_cached", n=len(releases)))
        else:
            self._lbl_progress.setText(t("discogs_found", n=len(releases)))

        if not releases:
            QMessageBox.information(
                self,
                t("discogs_no_results_title"),
                t("discogs_no_results_msg"),
            )
            return

        self._populate_table(self._displayed)
        self._btn_import.setEnabled(True)

    def _on_fetch_error(self, code: int, message: str) -> None:
        self._lbl_progress.setText("")
        if code == 401:
            self._cred_mgr.clear()
            QMessageBox.warning(
                self,
                t("discogs_token_expired_title"),
                t("discogs_token_expired_msg"),
            )
            self._on_logout()
        elif code == 429:
            self._start_rate_limit_countdown()
        else:
            QMessageBox.critical(self, t("discogs_err_title"), message)

    # ── Rate-limit countdown ──────────────────────────────────────────────────

    def _start_rate_limit_countdown(self) -> None:
        self._rate_countdown = 60
        self._btn_fetch.setEnabled(False)
        self._tick_rate_limit()
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(1000)
        self._rate_timer.timeout.connect(self._tick_rate_limit)
        self._rate_timer.start()

    def _tick_rate_limit(self) -> None:
        if self._rate_countdown <= 0:
            if self._rate_timer:
                self._rate_timer.stop()
            self._lbl_progress.setText("")
            self._btn_fetch.setEnabled(True)
            self._on_fetch()
            return
        self._lbl_progress.setText(
            t("discogs_rate_limit", n=self._rate_countdown)
        )
        self._rate_countdown -= 1

    # ── Slot: live search ─────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        q = text.strip().lower()
        if not q:
            self._displayed = list(self._releases)
        else:
            self._displayed = [
                r for r in self._releases
                if q in r["artist"].lower() or q in r["title"].lower()
            ]
        self._populate_table(self._displayed)

    # ── Table helpers ─────────────────────────────────────────────────────────

    def _populate_table(self, releases: list[dict]) -> None:
        self._table.setRowCount(0)
        for rec in releases:
            row = self._table.rowCount()
            self._table.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            chk.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(row, _COL_CHECK, chk)

            self._table.setItem(row, _COL_TITLE,  QTableWidgetItem(rec["title"]))
            self._table.setItem(row, _COL_ARTIST, QTableWidgetItem(rec["artist"]))
            self._table.setItem(row, _COL_LABEL,  QTableWidgetItem(rec["label"]))
            year_str = str(rec["year"]) if rec["year"] else ""
            self._table.setItem(row, _COL_YEAR,   QTableWidgetItem(year_str))

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_CHECK)
            if item:
                item.setCheckState(state)

    # ── Slot: import → fetch tracklists ──────────────────────────────────────

    def _on_import(self) -> None:
        selected_releases: list[dict] = []
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, _COL_CHECK)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                selected_releases.append(self._displayed[row])

        if not selected_releases:
            QMessageBox.information(
                self, t("discogs_no_sel_title"), t("discogs_no_sel_msg")
            )
            return

        creds    = self._cred_mgr.load()
        username = creds.get("discogs_username", "")
        token    = creds.get("discogs_token", "")

        self._btn_import.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._btn_logout.setEnabled(False)

        self._tracklist_worker = _TracklistWorker(
            selected_releases, username, token, parent=self
        )
        self._tracklist_worker.progress.connect(self._on_tracklist_progress)
        self._tracklist_worker.finished.connect(self._on_tracklist_done)
        self._tracklist_worker.start()

    def _on_tracklist_progress(self, n: int, total: int) -> None:
        self._lbl_progress.setText(
            t("discogs_tracklist_progress", n=n, total=total)
        )

    def _on_tracklist_done(self, records_data: list, warnings: list) -> None:
        self._lbl_progress.setText("")
        self._btn_import.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        self._btn_logout.setEnabled(True)

        if warnings:
            QMessageBox.warning(
                self,
                t("discogs_tracklist_warn_title"),
                t("discogs_tracklist_warn_msg", n=len(warnings))
                + "\n" + "\n".join(f"• {w}" for w in warnings),
            )

        dlg = ReviewDialog(records_data, self._db_path, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.accept()

    # ── Panel switching ───────────────────────────────────────────────────────

    def _show_collection_panel(self, username: str) -> None:
        self._lbl_auth_status.setText(
            t("discogs_logged_in", username=username)
        )
        self._stack.setCurrentIndex(_COLLECTION_IDX)

        # Auto-populate from session cache if available for this user
        if (
            DiscogsDialog._cache_username == username
            and DiscogsDialog._cached_releases
        ):
            self._apply_releases(DiscogsDialog._cached_releases, from_cache=True)
