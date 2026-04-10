"""
Settings dialog — 4-tab panel for app configuration.

Tabs (left nav):
  0  Appearance   — theme + language
  1  Data source  — LOCAL vs DISCOGS mode
  2  Discogs      — token management + account status
  3  About        — app info, license, author, version check, GitHub link

Signals emitted to MainWindow:
  theme_changed(str)   — 'dark' | 'light'
  mode_changed(str)    — 'local' | 'discogs'
  language_changed()   — emitted after language switch (no arg)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from datetime import datetime

from __version__ import __version__, __status__
import modules.i18n as i18n
from modules.i18n import t
from modules.data_source import DataSourceMode
from modules.credentials_manager import CredentialsManager
from modules.version_checker import get_latest_version, is_update_available
from config.settings import (
    get_theme,
    set_theme,
    get_data_source_mode,
    set_data_source_mode,
    get_language_setting,
    set_language_setting,
    get_last_known_version,
    set_last_known_version,
    set_last_version_check,
    get_debug_logging,
    set_debug_logging,
)
from modules.logger import set_debug_mode


# ── Module-level helpers ───────────────────────────────────────────────────────

def _get_colors():
    app = QApplication.instance()
    return app.property("theme_colors") if app else None


def _make_section_label(text: str, first: bool = False) -> QLabel:
    """Styled section heading — matches sidebar section label style."""
    lbl = QLabel(text.upper())
    font = lbl.font()
    font.setPixelSize(10)
    font.setBold(True)
    lbl.setFont(font)
    _apply_section_label_style(lbl, first)
    return lbl


def _apply_section_label_style(lbl: QLabel, first: bool = False) -> None:
    """Apply (or re-apply) the section label stylesheet from current theme colors."""
    colors = _get_colors()
    border_top = "" if first else f"border-top: 1px solid {colors.border};" if colors else ""
    color = colors.text_muted if colors else ""
    lbl.setStyleSheet(f"""
        QLabel {{
            color: {color};
            background: transparent;
            border: none;
            {border_top}
            padding: 16px 0px 4px 0px;
            letter-spacing: 1px;
        }}
    """)


# ── _NavItem ───────────────────────────────────────────────────────────────────

class _NavItem(QWidget):
    """Left navigation tab item."""

    clicked = pyqtSignal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._active = False
        self._hovered = False
        self._text = text

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self._lbl = QLabel(text)
        font = self._lbl.font()
        font.setPixelSize(13)
        self._lbl.setFont(font)
        layout.addWidget(self._lbl)

        self._update_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def set_text(self, text: str) -> None:
        self._text = text
        self._lbl.setText(text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self._update_style()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self._update_style()

    def _update_style(self) -> None:
        colors = _get_colors()
        if not colors:
            return

        if self._active:
            bg = colors.bg_card
            border = f"border: 1px solid {colors.accent};"
            text_color = colors.text_primary
            weight = "bold"
        elif self._hovered:
            bg = colors.accent_bg
            border = f"border: 1px solid {colors.accent};"
            text_color = colors.accent_light
            weight = "normal"
        else:
            bg = "transparent"
            border = "border: 1px solid transparent;"
            text_color = colors.text_secondary
            weight = "normal"

        self.setStyleSheet(f"""
            _NavItem {{
                background-color: {bg};
                border-radius: 6px;
                {border}
            }}
        """)
        self._lbl.setStyleSheet(
            f"color: {text_color}; font-weight: {weight}; background: transparent;"
        )


# ── _RadioCard ─────────────────────────────────────────────────────────────────

class _RadioCard(QWidget):
    """Selectable option card with title and optional subtitle."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
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

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def set_title(self, text: str) -> None:
        self._title_lbl.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle_lbl.setText(text)
        self._subtitle_lbl.setVisible(bool(text))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def _update_style(self) -> None:
        colors = _get_colors()
        if not colors:
            return

        if self._active:
            bg = colors.accent_bg
            border = f"border: 1px solid {colors.accent};"
            title_color = colors.accent_light
            subtitle_color = colors.accent_light
        else:
            bg = colors.bg_card
            border = f"border: 1px solid {colors.border};"
            title_color = colors.text_primary
            subtitle_color = colors.text_secondary

        self.setStyleSheet(f"""
            _RadioCard {{
                background-color: {bg};
                border-radius: 6px;
                {border}
            }}
        """)
        self._title_lbl.setStyleSheet(
            f"color: {title_color}; background: transparent;"
        )
        self._subtitle_lbl.setStyleSheet(
            f"color: {subtitle_color}; font-size: 11px; background: transparent;"
        )


# ── Background worker thread ───────────────────────────────────────────────────

class _VersionCheckThread(QThread):
    """Fetches the latest GitHub release in a background thread."""

    result_ready = pyqtSignal(dict)

    def run(self) -> None:
        result = get_latest_version()
        self.result_ready.emit(result)


# ── SettingsDialog ─────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Central settings dialog with left-nav + stacked content panels."""

    theme_changed    = pyqtSignal(str)   # 'dark' | 'light'
    mode_changed     = pyqtSignal(str)   # 'local' | 'discogs'
    language_changed = pyqtSignal()      # emitted after language switch
    debug_mode_changed = pyqtSignal(bool)  # emitted when debug toggle changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("menu_settings"))
        self.setMinimumSize(640, 480)
        self.resize(700, 520)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._nav_items: list[_NavItem] = []
        self._db_path = None  # set from MainWindow after construction if needed

        self._build_ui()
        self._switch_tab(0)

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        colors = _get_colors()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_nav())

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_appearance_tab())
        self._stack.addWidget(self._build_datasource_tab())
        self._stack.addWidget(self._build_discogs_tab())
        self._stack.addWidget(self._build_about_tab())
        outer.addWidget(self._stack, 1)

        if colors:
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {colors.bg_main};
                }}
            """)

    def _build_nav(self) -> QWidget:
        colors = _get_colors()

        nav = QWidget()
        nav.setFixedWidth(160)
        nav.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(nav)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        # Header
        self._nav_header = QLabel(t("menu_settings"))
        header_font = self._nav_header.font()
        header_font.setBold(True)
        header_font.setPixelSize(14)
        self._nav_header.setFont(header_font)
        self._nav_header.setContentsMargins(4, 0, 4, 8)
        if colors:
            self._nav_header.setStyleSheet(
                f"color: {colors.text_primary}; background: transparent;"
            )
        layout.addWidget(self._nav_header)

        # Nav items
        tab_keys = [
            t("menu_appearance"),
            t("settings_tab_datasource"),
            t("settings_tab_discogs"),
            t("settings_tab_about"),
        ]
        for i, label in enumerate(tab_keys):
            item = _NavItem(label, nav)
            item.clicked.connect(lambda idx=i: self._switch_tab(idx))
            self._nav_items.append(item)
            layout.addWidget(item)

        layout.addStretch()

        if colors:
            nav.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors.bg_sidebar};
                    border-right: 1px solid {colors.border};
                }}
            """)

        return nav

    def _scrollable(self, inner: QWidget) -> QWidget:
        """Wrap *inner* in a QScrollArea with matching background."""
        colors = _get_colors()
        if colors:
            inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            inner.setStyleSheet(f"QWidget {{ background-color: {colors.bg_main}; }}")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        if colors:
            scroll.setStyleSheet(f"""
                QScrollArea {{ background-color: {colors.bg_main}; border: none; }}
                QScrollArea > QWidget > QWidget {{ background-color: {colors.bg_main}; }}
            """)
        return scroll

    # ── Tab 0: Appearance ──────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(8)

        self._lbl_sec_theme = _make_section_label(t("settings_theme_label"), first=True)
        layout.addWidget(self._lbl_sec_theme)

        self._card_dark = _RadioCard(
            t("settings_theme_dark_name"),
            t("settings_theme_dark_desc"),
        )
        self._card_light = _RadioCard(
            t("settings_theme_light_name"),
            t("settings_theme_light_desc"),
        )
        current_theme = get_theme()
        self._card_dark.set_active(current_theme == "dark")
        self._card_light.set_active(current_theme == "light")
        self._card_dark.clicked.connect(lambda: self._on_theme_card("dark"))
        self._card_light.clicked.connect(lambda: self._on_theme_card("light"))
        layout.addWidget(self._card_dark)
        layout.addWidget(self._card_light)

        # Restart notice (hidden until theme is changed)
        self._restart_notice = QWidget()
        self._restart_notice.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        notice_layout = QHBoxLayout(self._restart_notice)
        notice_layout.setContentsMargins(12, 8, 12, 8)
        self._restart_notice_lbl = QLabel(t("restart_required"))
        self._restart_notice_lbl.setWordWrap(True)
        notice_layout.addWidget(self._restart_notice_lbl)
        self._restart_notice.setVisible(False)
        self._apply_restart_notice_style()
        layout.addWidget(self._restart_notice)

        self._lbl_sec_lang = _make_section_label(t("menu_language"))
        layout.addWidget(self._lbl_sec_lang)

        self._card_de = _RadioCard("Deutsch")
        self._card_en = _RadioCard("English")
        current_lang = get_language_setting()
        self._card_de.set_active(current_lang == "DE")
        self._card_en.set_active(current_lang == "EN")
        self._card_de.clicked.connect(lambda: self._on_lang_card("DE"))
        self._card_en.clicked.connect(lambda: self._on_lang_card("EN"))
        layout.addWidget(self._card_de)
        layout.addWidget(self._card_en)

        self._lbl_lang_info = QLabel(t("settings_lang_change_info"))
        lang_info_font = self._lbl_lang_info.font()
        lang_info_font.setPixelSize(11)
        self._lbl_lang_info.setFont(lang_info_font)
        colors = _get_colors()
        if colors:
            self._lbl_lang_info.setStyleSheet(
                f"color: {colors.text_muted}; background: transparent;"
            )
        layout.addWidget(self._lbl_lang_info)

        # ── Developer section ──────────────────────────────────────────────
        self._lbl_sec_debug = _make_section_label(t("debug_section"))
        layout.addWidget(self._lbl_sec_debug)

        # Toggle row: [title + subtitle on left] | [checkbox on right]
        debug_row = QWidget()
        debug_row_layout = QHBoxLayout(debug_row)
        debug_row_layout.setContentsMargins(0, 4, 0, 4)
        debug_row_layout.setSpacing(8)

        debug_labels = QVBoxLayout()
        debug_labels.setSpacing(2)
        self._lbl_debug_title = QLabel(t("debug_logging_label"))
        title_font = self._lbl_debug_title.font()
        title_font.setPixelSize(13)
        self._lbl_debug_title.setFont(title_font)
        self._lbl_debug_subtitle = QLabel(t("debug_logging_subtitle"))
        sub_font = self._lbl_debug_subtitle.font()
        sub_font.setPixelSize(11)
        self._lbl_debug_subtitle.setFont(sub_font)
        debug_labels.addWidget(self._lbl_debug_title)
        debug_labels.addWidget(self._lbl_debug_subtitle)

        self._chk_debug = QCheckBox()
        self._chk_debug.setChecked(get_debug_logging())

        debug_row_layout.addLayout(debug_labels)
        debug_row_layout.addStretch()
        debug_row_layout.addWidget(self._chk_debug)
        layout.addWidget(debug_row)

        self._lbl_log_path = QLabel("Log: logs/app.log")
        log_path_font = self._lbl_log_path.font()
        log_path_font.setPixelSize(10)
        log_path_font.setFamily("Courier New")
        self._lbl_log_path.setFont(log_path_font)
        self._lbl_log_path.setVisible(get_debug_logging())
        layout.addWidget(self._lbl_log_path)

        if colors:
            self._lbl_debug_subtitle.setStyleSheet(
                f"color: {colors.text_muted}; background: transparent;"
            )
            self._lbl_log_path.setStyleSheet(
                f"color: {colors.text_muted}; background: transparent;"
            )

        self._chk_debug.toggled.connect(self._on_debug_toggle)

        layout.addStretch()

        self._inner_appearance = inner
        return self._scrollable(inner)

    # ── Tab 1: Data source ─────────────────────────────────────────────────────

    def _build_datasource_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(8)

        self._lbl_sec_mode = _make_section_label(t("settings_active_mode"), first=True)
        layout.addWidget(self._lbl_sec_mode)

        self._card_local = _RadioCard(
            t("datasource_local"),
            t("settings_mode_local_sub"),
        )
        self._card_discogs = _RadioCard(
            "Discogs",
            t("settings_mode_discogs_sub"),
        )
        current_mode = get_data_source_mode()
        self._card_local.set_active(current_mode == DataSourceMode.LOCAL)
        self._card_discogs.set_active(current_mode == DataSourceMode.DISCOGS)
        self._card_local.clicked.connect(lambda: self._on_mode_card(DataSourceMode.LOCAL))
        self._card_discogs.clicked.connect(lambda: self._on_mode_card(DataSourceMode.DISCOGS))
        layout.addWidget(self._card_local)
        layout.addWidget(self._card_discogs)

        # Warning box
        warn_box = QWidget()
        warn_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        warn_layout = QHBoxLayout(warn_box)
        warn_layout.setContentsMargins(12, 10, 12, 10)
        self._lbl_mode_warn = QLabel(t("settings_mode_switch_warn"))
        self._lbl_mode_warn.setWordWrap(True)
        warn_layout.addWidget(self._lbl_mode_warn)

        colors = _get_colors()
        if colors:
            warn_box.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors.bg_card};
                    border-left: 3px solid {colors.warning};
                    border-radius: 0px;
                }}
            """)
            self._lbl_mode_warn.setStyleSheet(
                f"color: {colors.text_muted}; background: transparent;"
            )
        layout.addWidget(warn_box)
        layout.addStretch()

        self._inner_datasource = inner
        return self._scrollable(inner)

    # ── Tab 2: Discogs account ─────────────────────────────────────────────────

    def _build_discogs_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

        colors = _get_colors()

        # Status card
        status_card = QWidget()
        status_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(8)

        self._discogs_dot = QLabel()
        self._discogs_dot.setFixedSize(8, 8)
        self._lbl_discogs_status = QLabel()
        status_font = self._lbl_discogs_status.font()
        status_font.setPixelSize(13)
        self._lbl_discogs_status.setFont(status_font)
        self._lbl_discogs_username = QLabel()
        user_font = self._lbl_discogs_username.font()
        user_font.setPixelSize(12)
        self._lbl_discogs_username.setFont(user_font)

        status_layout.addWidget(self._discogs_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        status_layout.addWidget(self._lbl_discogs_status, 0, Qt.AlignmentFlag.AlignVCenter)
        status_layout.addStretch()
        status_layout.addWidget(self._lbl_discogs_username, 0, Qt.AlignmentFlag.AlignVCenter)

        if colors:
            status_card.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors.bg_sidebar};
                    border: 1px solid {colors.border};
                    border-radius: 6px;
                }}
            """)
        layout.addWidget(status_card)

        # Token section
        self._lbl_sec_token = _make_section_label(t("discogs_lbl_token"))
        layout.addWidget(self._lbl_sec_token)

        token_row = QWidget()
        token_layout = QHBoxLayout(token_row)
        token_layout.setContentsMargins(0, 0, 0, 0)
        token_layout.setSpacing(8)

        self._token_edit = QLineEdit()
        self._token_edit.setReadOnly(True)
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_edit.setPlaceholderText("••••••••••••••••••••")
        mono_font = self._token_edit.font()
        mono_font.setFamily("monospace")
        self._token_edit.setFont(mono_font)
        if colors:
            self._token_edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {colors.bg_input};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border};
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }}
            """)

        self._btn_toggle_token = QPushButton(t("settings_discogs_show_token"))
        self._btn_toggle_token.setFixedHeight(32)
        self._btn_toggle_token.clicked.connect(self._on_toggle_token)
        self._btn_toggle_token.setCursor(Qt.CursorShape.PointingHandCursor)

        token_layout.addWidget(self._token_edit, 1)
        token_layout.addWidget(self._btn_toggle_token)
        layout.addWidget(token_row)

        # Action buttons
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(8)

        self._btn_change_token = QPushButton(t("settings_discogs_change_token"))
        self._btn_change_token.setFixedHeight(32)
        self._btn_change_token.clicked.connect(self._on_change_token)
        self._btn_change_token.setCursor(Qt.CursorShape.PointingHandCursor)

        self._btn_logout = QPushButton(t("discogs_btn_logout"))
        self._btn_logout.setFixedHeight(32)
        self._btn_logout.clicked.connect(self._on_logout)
        self._btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)

        if colors:
            btn_style = f"""
                QPushButton {{
                    background-color: {colors.bg_card};
                    color: {colors.text_primary};
                    border: 1px solid {colors.border};
                    border-radius: 6px;
                    padding: 4px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {colors.accent_bg};
                    border-color: {colors.accent};
                    color: {colors.accent_light};
                }}
            """
            self._btn_toggle_token.setStyleSheet(btn_style)
            self._btn_change_token.setStyleSheet(btn_style)
            self._btn_logout.setStyleSheet(btn_style)

        btn_row_layout.addWidget(self._btn_change_token)
        btn_row_layout.addWidget(self._btn_logout)
        btn_row_layout.addStretch()
        layout.addWidget(btn_row)

        layout.addStretch()

        self._refresh_discogs_status()

        self._inner_discogs = inner
        return self._scrollable(inner)

    # ── Tab 3: About ───────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

        colors = _get_colors()

        # App card
        app_card = QWidget()
        app_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        app_layout = QVBoxLayout(app_card)
        app_layout.setContentsMargins(12, 10, 12, 10)
        app_layout.setSpacing(2)

        lbl_app_name = QLabel("Vinyl Label Printer")
        name_font = lbl_app_name.font()
        name_font.setBold(True)
        name_font.setPixelSize(15)
        lbl_app_name.setFont(name_font)

        app_layout.addWidget(lbl_app_name)

        if colors:
            app_card.setStyleSheet(f"""
                QWidget {{
                    background-color: {colors.bg_sidebar};
                    border: 1px solid {colors.border};
                    border-radius: 6px;
                }}
            """)
            lbl_app_name.setStyleSheet(
                f"color: {colors.text_primary}; font-weight: bold; background: transparent;"
            )
        layout.addWidget(app_card)

        # Info rows (License + Author only) — store key labels for retranslation
        self._lbl_about_license_key = QLabel(t("settings_license"))
        self._lbl_about_author_key  = QLabel(t("settings_author"))

        info_rows = [
            (self._lbl_about_license_key, "GNU GPL v3.0"),
            (self._lbl_about_author_key,  "EJAIS"),
        ]
        for lbl_key, value_text in info_rows:
            row = QWidget()
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            key_font = lbl_key.font()
            key_font.setPixelSize(12)
            lbl_key.setFont(key_font)

            lbl_val = QLabel(value_text)
            val_font = lbl_val.font()
            val_font.setPixelSize(12)
            lbl_val.setFont(val_font)

            if colors:
                lbl_key.setStyleSheet(
                    f"color: {colors.text_secondary}; background: transparent;"
                )
                lbl_val.setStyleSheet(
                    f"color: {colors.text_primary}; background: transparent;"
                )
                row.setStyleSheet(f"""
                    QWidget {{
                        background-color: {colors.bg_card};
                        border-bottom: 1px solid {colors.border};
                        border-radius: 0px;
                    }}
                """)

            row_layout.addWidget(lbl_key)
            row_layout.addStretch()
            row_layout.addWidget(lbl_val)
            layout.addWidget(row)

        # Version check section
        self._lbl_sec_version_check = _make_section_label(t("version_check"))
        layout.addWidget(self._lbl_sec_version_check)

        # Version rows: installed + available
        self._lbl_about_installed_key  = QLabel(t("installed_version"))
        self._lbl_about_available_key  = QLabel(t("available_version"))
        self._lbl_about_available_val  = QLabel(t("not_yet_checked"))

        ver_rows = [
            (self._lbl_about_installed_key,  f"v{__version__} {__status__}",  False),
            (self._lbl_about_available_key,  self._lbl_about_available_val,    True),
        ]
        for lbl_key, val_or_widget, is_widget in ver_rows:
            row = QWidget()
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            key_font = lbl_key.font()
            key_font.setPixelSize(12)
            lbl_key.setFont(key_font)

            if is_widget:
                lbl_val = val_or_widget
            else:
                lbl_val = QLabel(val_or_widget)
            val_font = lbl_val.font()
            val_font.setPixelSize(12)
            lbl_val.setFont(val_font)

            if colors:
                lbl_key.setStyleSheet(
                    f"color: {colors.text_secondary}; background: transparent;"
                )
                lbl_val.setStyleSheet(
                    f"color: {colors.text_muted}; background: transparent;"
                )
                row.setStyleSheet(f"""
                    QWidget {{
                        background-color: {colors.bg_sidebar};
                        border: 1px solid {colors.border};
                        border-radius: 6px;
                    }}
                """)

            row_layout.addWidget(lbl_key)
            row_layout.addStretch()
            row_layout.addWidget(lbl_val)
            layout.addWidget(row)

        # Check for updates button
        self._btn_about_check_updates = QPushButton(t("check_updates"))
        self._btn_about_check_updates.setFixedHeight(32)
        self._btn_about_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_about_check_updates.clicked.connect(self._check_for_updates)
        if colors:
            self._btn_about_check_updates.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.bg_card};
                    color: {colors.text_primary};
                    border: 1px solid {colors.accent};
                    border-radius: 6px;
                    padding: 4px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {colors.accent_bg};
                }}
                QPushButton:disabled {{
                    color: {colors.text_muted};
                    border-color: {colors.border};
                }}
            """)
        layout.addWidget(self._btn_about_check_updates)

        # Status label (shown after check completes)
        self._lbl_about_update_status = QLabel("")
        status_font = self._lbl_about_update_status.font()
        status_font.setPixelSize(12)
        self._lbl_about_update_status.setFont(status_font)
        self._lbl_about_update_status.setVisible(False)
        self._lbl_about_update_status.setStyleSheet("background: transparent;")
        layout.addWidget(self._lbl_about_update_status)

        # "Release Notes" link (shown only when an update is available)
        self._lbl_about_release_notes = QLabel(t("release_notes"))
        rn_font = self._lbl_about_release_notes.font()
        rn_font.setPixelSize(12)
        self._lbl_about_release_notes.setFont(rn_font)
        self._lbl_about_release_notes.setVisible(False)
        self._lbl_about_release_notes.setCursor(Qt.CursorShape.PointingHandCursor)
        if colors:
            self._lbl_about_release_notes.setStyleSheet(
                f"color: {colors.accent_light}; background: transparent;"
            )
        self._lbl_about_release_notes.mousePressEvent = (
            lambda _event: self._open_release_notes()
        )
        layout.addWidget(self._lbl_about_release_notes)

        # Pre-fill available version from cache (no network call on open)
        cached = get_last_known_version()
        if cached:
            self._lbl_about_available_val.setText(cached)

        # Divider before GitHub section
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setFixedHeight(1)
        if colors:
            divider.setStyleSheet(f"background-color: {colors.border}; border: none;")
        layout.addWidget(divider)

        # GitHub button
        self._btn_about_github = QPushButton(t("open_github"))
        self._btn_about_github.setFixedHeight(32)
        self._btn_about_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_about_github.clicked.connect(self._open_github)
        if colors:
            self._btn_about_github.setStyleSheet(f"""
                QPushButton {{
                    color: {colors.accent_light};
                    background: transparent;
                    border: none;
                    font-size: 12px;
                    text-align: left;
                    padding: 4px 0px;
                }}
                QPushButton:hover {{
                    color: {colors.accent};
                }}
            """)
        layout.addWidget(self._btn_about_github)

        layout.addStretch()

        self._inner_about = inner
        return self._scrollable(inner)

    # ── Tab switching ──────────────────────────────────────────────────────────

    def _switch_tab(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, item in enumerate(self._nav_items):
            item.set_active(i == index)
        if index == 2:
            self._refresh_discogs_status()

    def switch_to_tab(self, index: int) -> None:
        """Navigate to *index* (0 = Appearance, 1 = Data source, …)."""
        self._switch_tab(index)

    # ── Appearance handlers ────────────────────────────────────────────────────

    def _on_theme_card(self, theme: str) -> None:
        from config.themes import get_theme as _gc
        from config.stylesheet import build_stylesheet

        set_theme(theme)
        colors = _gc(theme)
        app = QApplication.instance()
        app.setStyleSheet(build_stylesheet(colors))
        app.setProperty("theme_colors", colors)

        self._card_dark.set_active(theme == "dark")
        self._card_light.set_active(theme == "light")

        self._refresh_nav_style()
        self._restart_notice.setVisible(True)
        self.theme_changed.emit(theme)

    def _on_lang_card(self, lang: str) -> None:
        i18n.set_language(lang)
        set_language_setting(lang)
        self._card_de.set_active(lang == "DE")
        self._card_en.set_active(lang == "EN")
        self.language_changed.emit()
        self.retranslate()

    def _on_debug_toggle(self, enabled: bool) -> None:
        set_debug_logging(enabled)
        set_debug_mode(enabled)
        self._lbl_log_path.setVisible(enabled)
        self.debug_mode_changed.emit(enabled)

    # ── Data source handlers ───────────────────────────────────────────────────

    def _on_mode_card(self, mode: DataSourceMode) -> None:
        if mode == get_data_source_mode():
            return
        if mode == DataSourceMode.DISCOGS and not CredentialsManager().are_valid():
            QMessageBox.information(
                self,
                t("settings_tab_discogs"),
                t("datasource_no_creds_msg"),
            )
            self._switch_tab(2)
            return
        set_data_source_mode(mode)
        self._card_local.set_active(mode == DataSourceMode.LOCAL)
        self._card_discogs.set_active(mode == DataSourceMode.DISCOGS)
        self.mode_changed.emit(mode.value)

    # ── Discogs handlers ───────────────────────────────────────────────────────

    def _on_toggle_token(self) -> None:
        if self._token_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._btn_toggle_token.setText(t("settings_discogs_hide_token"))
        else:
            self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._btn_toggle_token.setText(t("settings_discogs_show_token"))

    def _on_change_token(self) -> None:
        from ui.discogs_dialog import DiscogsDialog
        db_path = self._db_path
        if db_path is None:
            from pathlib import Path
            db_path = Path(__file__).parent.parent / "data" / "database.xlsx"
        dlg = DiscogsDialog(db_path, parent=self)
        dlg.exec()
        self._refresh_discogs_status()

    def _open_github(self) -> None:
        url = QUrl("https://github.com/EJAIS/vinylsticker")
        QDesktopServices.openUrl(url)

    # ── Version check ──────────────────────────────────────────────────────────

    def _check_for_updates(self) -> None:
        """Start a background version check; update UI on completion."""
        self._btn_about_check_updates.setEnabled(False)
        self._btn_about_check_updates.setText(t("checking_version"))
        self._lbl_about_available_val.setText("…")
        self._lbl_about_update_status.setText("")
        self._lbl_about_update_status.setVisible(False)
        self._lbl_about_release_notes.setVisible(False)

        self._version_thread = _VersionCheckThread(self)
        self._version_thread.result_ready.connect(self._on_version_check_complete)
        self._version_thread.start()

    def _on_version_check_complete(self, result: dict) -> None:
        """Handle version check result from the background thread."""
        colors = _get_colors()
        self._btn_about_check_updates.setEnabled(True)
        self._btn_about_check_updates.setText(t("check_updates"))

        if not result["success"]:
            self._lbl_about_available_val.setText("—")
            error = result["error"]
            if error == "no_releases":
                msg = t("no_releases_yet")
                style_color = colors.text_muted if colors else ""
            elif error == "network":
                msg = t("check_failed_network")
                style_color = colors.danger if colors else ""
            else:
                msg = t("check_failed_error")
                style_color = colors.danger if colors else ""
            self._lbl_about_update_status.setText(msg)
            if colors:
                self._lbl_about_update_status.setStyleSheet(
                    f"color: {style_color}; background: transparent;"
                )
            self._lbl_about_update_status.setVisible(True)
            return

        self._lbl_about_available_val.setText(result["tag_name"])
        set_last_known_version(result["tag_name"])
        set_last_version_check(datetime.now().isoformat())

        self._lbl_about_update_status.setVisible(True)
        if is_update_available(result["latest_version"]):
            msg = t("update_available", version=result["tag_name"])
            self._lbl_about_update_status.setText(msg)
            if colors:
                self._lbl_about_update_status.setStyleSheet(
                    f"color: {colors.accent}; background: transparent;"
                )
            self._release_url = result["release_url"]
            self._lbl_about_release_notes.setVisible(True)
        else:
            self._lbl_about_update_status.setText(t("up_to_date"))
            if colors:
                self._lbl_about_update_status.setStyleSheet(
                    f"color: {colors.success}; background: transparent;"
                )

    def _open_release_notes(self) -> None:
        """Open the GitHub release page in the system browser."""
        url = getattr(self, "_release_url", "https://github.com/EJAIS/vinylsticker/releases")
        QDesktopServices.openUrl(QUrl(url))

    def _on_logout(self) -> None:
        CredentialsManager().clear()
        self._refresh_discogs_status()
        if get_data_source_mode() == DataSourceMode.DISCOGS:
            set_data_source_mode(DataSourceMode.LOCAL)
            self._card_local.set_active(True)
            self._card_discogs.set_active(False)
            self.mode_changed.emit(DataSourceMode.LOCAL.value)

    def _refresh_discogs_status(self) -> None:
        creds = CredentialsManager().load()
        connected = CredentialsManager().are_valid()
        username = creds.get("discogs_username", "")
        token = creds.get("discogs_token", "")
        colors = _get_colors()

        if colors:
            dot_color = colors.success if connected else colors.text_muted
            self._discogs_dot.setStyleSheet(
                f"background-color: {dot_color}; border-radius: 4px;"
            )
            self._lbl_discogs_status.setStyleSheet(
                f"color: {colors.text_primary}; background: transparent;"
            )
            self._lbl_discogs_username.setStyleSheet(
                f"color: {colors.text_muted}; background: transparent;"
            )

        if connected:
            self._lbl_discogs_status.setText(t("settings_discogs_connected"))
            self._lbl_discogs_username.setText(
                f"{t('settings_discogs_logged_in_as')} {username}"
            )
            self._lbl_discogs_username.setVisible(True)
        else:
            self._lbl_discogs_status.setText(t("sidebar_not_connected"))
            self._lbl_discogs_username.setVisible(False)

        self._token_edit.setText(token)
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._btn_toggle_token.setText(t("settings_discogs_show_token"))

    # ── Style refresh (called after theme change) ──────────────────────────────

    def _apply_restart_notice_style(self) -> None:
        colors = _get_colors()
        if not colors:
            return
        self._restart_notice.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.accent_bg};
                border: 1px solid {colors.accent};
                border-radius: 6px;
            }}
        """)
        self._restart_notice_lbl.setStyleSheet(
            f"color: {colors.accent_light}; background: transparent;"
        )

    def _refresh_nav_style(self) -> None:
        """Re-apply nav panel and dialog background after a theme change."""
        colors = _get_colors()
        if not colors:
            return

        # Dialog background
        self.setStyleSheet(f"QDialog {{ background-color: {colors.bg_main}; }}")

        # Re-style all stored section labels
        _apply_section_label_style(self._lbl_sec_theme, first=True)
        _apply_section_label_style(self._lbl_sec_lang)
        _apply_section_label_style(self._lbl_sec_mode, first=True)
        _apply_section_label_style(self._lbl_sec_token)
        _apply_section_label_style(self._lbl_sec_version_check)

        # Re-apply inner tab widget backgrounds
        bg_qss = f"QWidget {{ background-color: {colors.bg_main}; }}"
        for inner in (
            self._inner_appearance, self._inner_datasource,
            self._inner_discogs, self._inner_about,
        ):
            inner.setStyleSheet(bg_qss)

        # Re-style info label
        self._lbl_lang_info.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )

        # Re-style restart notice
        self._apply_restart_notice_style()

        # Refresh nav items
        for item in self._nav_items:
            item._update_style()

        # Refresh radio cards
        for card in (
            self._card_dark, self._card_light,
            self._card_de, self._card_en,
            self._card_local, self._card_discogs,
        ):
            card._update_style()

        # Refresh Discogs status labels
        self._refresh_discogs_status()

    # ── Qt event overrides ─────────────────────────────────────────────────────

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._restart_notice.setVisible(False)

    # ── Retranslate ────────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        """Update all translatable strings after a language switch."""
        self.setWindowTitle(t("menu_settings"))
        self._nav_header.setText(t("menu_settings"))

        # Nav items
        tab_keys = [
            t("menu_appearance"),
            t("settings_tab_datasource"),
            t("settings_tab_discogs"),
            t("settings_tab_about"),
        ]
        for item, label in zip(self._nav_items, tab_keys):
            item.set_text(label)

        # Appearance tab
        self._lbl_sec_theme.setText(t("settings_theme_label").upper())
        self._card_dark.set_title(t("settings_theme_dark_name"))
        self._card_dark.set_subtitle(t("settings_theme_dark_desc"))
        self._card_light.set_title(t("settings_theme_light_name"))
        self._card_light.set_subtitle(t("settings_theme_light_desc"))
        self._restart_notice_lbl.setText(t("restart_required"))
        self._lbl_sec_lang.setText(t("menu_language").upper())
        self._lbl_lang_info.setText(t("settings_lang_change_info"))
        self._lbl_sec_debug.setText(t("debug_section").upper())
        self._lbl_debug_title.setText(t("debug_logging_label"))
        self._lbl_debug_subtitle.setText(t("debug_logging_subtitle"))

        # Data source tab
        self._lbl_sec_mode.setText(t("settings_active_mode").upper())
        self._card_local.set_title(t("datasource_local"))
        self._card_local.set_subtitle(t("settings_mode_local_sub"))
        self._card_discogs.set_subtitle(t("settings_mode_discogs_sub"))
        self._lbl_mode_warn.setText(t("settings_mode_switch_warn"))

        # Discogs tab
        self._lbl_sec_token.setText(t("discogs_lbl_token").upper())
        self._btn_toggle_token.setText(t("settings_discogs_show_token"))
        self._btn_change_token.setText(t("settings_discogs_change_token"))
        self._btn_logout.setText(t("discogs_btn_logout"))
        self._refresh_discogs_status()

        # About tab
        self._lbl_about_license_key.setText(t("settings_license"))
        self._lbl_about_author_key.setText(t("settings_author"))
        self._lbl_sec_version_check.setText(t("version_check").upper())
        self._lbl_about_installed_key.setText(t("installed_version"))
        self._lbl_about_available_key.setText(t("available_version"))
        self._btn_about_check_updates.setText(t("check_updates"))
        self._lbl_about_release_notes.setText(t("release_notes"))
        self._btn_about_github.setText(t("open_github"))
