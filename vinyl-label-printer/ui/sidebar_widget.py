"""
Sidebar widget — vertical navigation panel on the left of the main window.

Contains two SidebarButton groups (Data / Print) plus an app header.
Emits signals that MainWindow connects to its action handlers.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from __version__ import __version__, __status__
from modules.data_source import DataSourceMode
from modules.i18n import t


class SidebarButton(QWidget):
    """Clickable navigation item with a title and an optional subtitle line."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        primary: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._primary = primary
        self._hovered = False
        self._active = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._title_lbl = QLabel(title)
        title_font = self._title_lbl.font()
        title_font.setPixelSize(13)
        self._title_lbl.setFont(title_font)

        self._subtitle_lbl = QLabel(subtitle)
        sub_font = self._subtitle_lbl.font()
        sub_font.setPixelSize(11)
        self._subtitle_lbl.setFont(sub_font)
        self._subtitle_lbl.setVisible(bool(subtitle))

        layout.addWidget(self._title_lbl)
        layout.addWidget(self._subtitle_lbl)

        self._update_style()

    # ── State setters ─────────────────────────────────────────────────────────

    def set_title(self, text: str) -> None:
        self._title_lbl.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle_lbl.setText(text)
        self._subtitle_lbl.setVisible(bool(text))

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    # ── Qt event overrides ────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self._update_style()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self._update_style()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        # Only re-style on enabled/disabled transitions.
        # Responding to StyleChange would recurse: setStyleSheet() fires
        # StyleChange → changeEvent → setStyleSheet() → …
        if event.type() == QEvent.Type.EnabledChange:
            self._update_style()

    # ── Style ─────────────────────────────────────────────────────────────────

    def _update_style(self) -> None:
        app = QApplication.instance()
        colors = app.property("theme_colors") if app else None
        if not colors:
            return

        enabled = self.isEnabled()

        if self._primary:
            if enabled:
                bg = colors.accent
                border = f"border: 1px solid {colors.accent};"
                title_color = colors.accent_light
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                bg = colors.bg_card
                border = f"border: 1px dashed {colors.border};"
                title_color = colors.text_muted
                self.setCursor(Qt.CursorShape.ForbiddenCursor)
        elif self._active or (self._hovered and enabled):
            bg = colors.accent_bg
            border = f"border: 1px solid {colors.accent};"
            title_color = colors.accent_light
        else:
            # Default: always-visible card background + border so button is
            # recognisable without requiring a hover.
            bg = colors.bg_card
            border = f"border: 1px solid {colors.border};"
            title_color = colors.text_secondary if enabled else colors.text_muted

        self.setStyleSheet(f"""
            SidebarButton {{
                background-color: {bg};
                border-radius: 6px;
                {border}
            }}
        """)

        weight = "bold" if (self._active or self._primary) else "normal"
        self._title_lbl.setStyleSheet(
            f"color: {title_color}; font-weight: {weight}; background: transparent;"
        )
        subtitle_color = (
            colors.accent_light if (self._active or self._primary and self.isEnabled())
            else colors.text_secondary
        )
        self._subtitle_lbl.setStyleSheet(
            f"color: {subtitle_color}; font-size: 11px; background: transparent;"
        )


class SidebarWidget(QWidget):
    """Left-side navigation panel (fixed 200 px wide)."""

    load_data_clicked       = pyqtSignal()
    queue_clicked           = pyqtSignal()
    start_position_clicked  = pyqtSignal()
    create_pdf_clicked      = pyqtSignal()
    print_clicked           = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._mode = DataSourceMode.LOCAL
        self._pdf_status = "ready"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)

        # ── App header ────────────────────────────────────────────────────────
        self._lbl_app_name = QLabel("Vinyl Label Printer")
        name_font = self._lbl_app_name.font()
        name_font.setBold(True)
        name_font.setPixelSize(14)
        self._lbl_app_name.setFont(name_font)
        self._lbl_app_name.setContentsMargins(12, 0, 12, 0)

        self._lbl_version = QLabel(f"v{__version__} {__status__}")
        ver_font = self._lbl_version.font()
        ver_font.setPixelSize(11)
        self._lbl_version.setFont(ver_font)
        self._lbl_version.setContentsMargins(12, 0, 12, 4)

        layout.addWidget(self._lbl_app_name)
        layout.addWidget(self._lbl_version)

        # ── Section: Data ─────────────────────────────────────────────────────
        # First section: no top border (sits right below the header divider)
        self._lbl_section_data = self._make_section_label(
            t("sidebar_section_data"), top_border=False
        )
        layout.addWidget(self._lbl_section_data)

        self._btn_load_data = SidebarButton(
            t("sidebar_load_data"), t("sidebar_local"), parent=self
        )
        self._btn_queue = SidebarButton(
            t("sidebar_queue"), t("sidebar_empty"), parent=self
        )
        self._btn_load_data.clicked.connect(self.load_data_clicked)
        self._btn_queue.clicked.connect(self.queue_clicked)
        layout.addWidget(self._btn_load_data)
        layout.addWidget(self._btn_queue)

        # ── Section: Print ────────────────────────────────────────────────────
        # Second section: top border acts as the visual divider
        self._lbl_section_print = self._make_section_label(
            t("sidebar_section_print"), top_border=True
        )
        layout.addWidget(self._lbl_section_print)

        self._btn_start_pos = SidebarButton(
            t("sidebar_start_pos"), "Label 1 (R1 C1)", parent=self
        )
        self._btn_create_pdf = SidebarButton(
            t("sidebar_create_pdf"), t("sidebar_status_ready"), parent=self
        )
        self._btn_print = SidebarButton(
            t("btn_print"), primary=True, parent=self
        )
        self._btn_print.setEnabled(False)

        self._btn_start_pos.clicked.connect(self.start_position_clicked)
        self._btn_create_pdf.clicked.connect(self.create_pdf_clicked)
        self._btn_print.clicked.connect(self.print_clicked)
        layout.addWidget(self._btn_start_pos)
        layout.addWidget(self._btn_create_pdf)
        layout.addWidget(self._btn_print)

        layout.addStretch()

        self._apply_sidebar_style()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_section_label(self, text: str, top_border: bool = True) -> QLabel:
        lbl = QLabel(text.upper())
        font = lbl.font()
        font.setPixelSize(10)
        font.setBold(True)
        lbl.setFont(font)
        # Store whether this label should have a top divider line
        lbl.setProperty("top_border", top_border)
        return lbl

    def _apply_sidebar_style(self) -> None:
        app = QApplication.instance()
        colors = app.property("theme_colors") if app else None
        if not colors:
            return

        self.setStyleSheet(f"""
            SidebarWidget {{
                background-color: {colors.bg_sidebar};
                border-right: 1px solid {colors.border};
            }}
            QLabel {{
                color: {colors.text_muted};
                background: transparent;
            }}
        """)

        # Header labels
        self._lbl_app_name.setStyleSheet(
            f"color: {colors.text_primary}; font-weight: bold; background: transparent;"
        )
        self._lbl_version.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )

        # Section labels: structural dividers — no background, no border-radius,
        # generous top spacing; second label adds a top separator line.
        self._lbl_section_data.setStyleSheet(f"""
            QLabel {{
                color: {colors.text_muted};
                background: transparent;
                border: none;
                padding: 16px 12px 4px 12px;
                letter-spacing: 1px;
            }}
        """)
        self._lbl_section_print.setStyleSheet(f"""
            QLabel {{
                color: {colors.text_muted};
                background: transparent;
                border: none;
                border-top: 1px solid {colors.border};
                padding: 16px 12px 4px 12px;
                letter-spacing: 1px;
            }}
        """)

        # Trigger SidebarButton style refresh
        for btn in (
            self._btn_load_data, self._btn_queue,
            self._btn_start_pos, self._btn_create_pdf, self._btn_print,
        ):
            btn._update_style()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_queue_count(self, n: int) -> None:
        if n > 0:
            self._btn_queue.set_subtitle(f"{n} {t('sidebar_labels_ready')}")
        else:
            self._btn_queue.set_subtitle(t("sidebar_empty"))

    def set_start_position(self, pos: int, row: int, col: int) -> None:
        self._btn_start_pos.set_subtitle(f"Label {pos} (R{row} C{col})")

    def set_pdf_status(self, status: str) -> None:
        self._pdf_status = status
        _key_map = {
            "ready":      "sidebar_status_ready",
            "generating": "sidebar_status_generating",
            "done":       "sidebar_status_created",
        }
        self._btn_create_pdf.set_subtitle(t(_key_map.get(status, "sidebar_status_ready")))

    def set_print_enabled(self, enabled: bool) -> None:
        self._btn_print.setEnabled(enabled)

    def set_active_mode(self, mode: DataSourceMode) -> None:
        self._mode = mode
        if mode == DataSourceMode.DISCOGS:
            self._btn_load_data.set_subtitle(t("sidebar_discogs_mode"))
        else:
            self._btn_load_data.set_subtitle(t("sidebar_local"))

    def retranslate(self) -> None:
        self._lbl_section_data.setText(t("sidebar_section_data").upper())
        self._lbl_section_print.setText(t("sidebar_section_print").upper())
        self._btn_load_data.set_title(t("sidebar_load_data"))
        self._btn_queue.set_title(t("sidebar_queue"))
        self._btn_start_pos.set_title(t("sidebar_start_pos"))
        self._btn_create_pdf.set_title(t("sidebar_create_pdf"))
        self._btn_print.set_title(t("btn_print"))
        self.set_active_mode(self._mode)
        self.set_pdf_status(self._pdf_status)
