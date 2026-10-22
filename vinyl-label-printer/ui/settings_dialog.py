"""
Settings dialog — 4-tab panel for app configuration.

Tabs (left nav):
  0  Appearance   — theme + language
  1  Data source  — LOCAL vs DISCOGS mode + data folder location
  2  Discogs      — token management + account status
  3  About        — app info, license, author, version check, GitHub link

Signals emitted to MainWindow:
  mode_changed(str)    — 'local' | 'discogs'
  language_changed()   — emitted after language switch (no arg)

Theme changes go through ThemeManager, which restyles every open window.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from datetime import datetime

from __version__ import __version__, __status__
import modules.i18n as i18n
from modules.i18n import t
from modules.data_source import DataSourceMode
from modules.discogs_cache import DiscogsCache
from modules.credentials_manager import CredentialsManager
from modules.version_checker import (
    GITHUB_RELEASES_URL,
    get_latest_version,
    is_newer_than_latest,
    is_update_available,
)
from config.settings import (
    get_data_source_mode,
    set_data_source_mode,
    get_language_setting,
    set_language_setting,
    get_last_known_version,
    set_last_known_version,
    set_last_version_check,
    get_debug_logging,
    set_debug_logging,
    get_watermark_path,
    get_calibration_x,
    set_calibration_x,
    get_calibration_y,
    set_calibration_y,
)
from config.themes import ThemeColors
from modules.logger import set_debug_mode
from modules.paths import get_data_dir, get_log_file, get_output_dir
from ui.theme_manager import ThemedStyles, ThemeManager, current_colors


# ── Module-level helpers ───────────────────────────────────────────────────────

def _section_label_style(colors: ThemeColors, first: bool = False) -> str:
    """Section heading stylesheet — matches the sidebar section label style."""
    border_top = "" if first else f"border-top: 1px solid {colors.border};"
    return f"""
        QLabel {{
            color: {colors.text_muted};
            background: transparent;
            border: none;
            {border_top}
            padding: 16px 0px 4px 0px;
            letter-spacing: 1px;
        }}
    """


def _label_style(color: str) -> str:
    return f"color: {color}; background: transparent;"


def _card_style(colors: ThemeColors) -> str:
    """Rounded info card (status, watermark, app and version rows)."""
    return f"""
        QWidget {{
            background-color: {colors.bg_sidebar};
            border: 1px solid {colors.border};
            border-radius: 6px;
        }}
    """


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
        """(Re)apply the state style; SettingsDialog calls it on theme changes."""
        colors = current_colors()
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
        """(Re)apply the state style; SettingsDialog calls it on theme changes."""
        colors = current_colors()
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
        # Static per-widget stylesheets, re-applied by _apply_theme()
        self._styles = ThemedStyles()
        # Color role (ThemeColors field) of the version check status line
        self._update_status_role = ""
        # i18n key of the update hint, "" while it is hidden
        self._update_hint_key = ""
        self._discogs_connected = False

        self._build_ui()
        self._switch_tab(0)

        theme = ThemeManager.instance()
        theme.theme_changed.connect(self._apply_theme)
        theme.setting_changed.connect(self._update_theme_cards)

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
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

        self._styles.add(self, lambda c: f"""
            QDialog {{
                background-color: {c.bg_main};
            }}
        """)

    def _section_label(self, text: str, first: bool = False) -> QLabel:
        """Section heading in the settings tabs."""
        lbl = QLabel(text.upper())
        font = lbl.font()
        font.setPixelSize(10)
        font.setBold(True)
        lbl.setFont(font)
        self._styles.add(lbl, lambda c: _section_label_style(c, first))
        return lbl

    def _build_nav(self) -> QWidget:
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
        self._styles.add(self._nav_header, lambda c: _label_style(c.text_primary))
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

        self._styles.add(nav, lambda c: f"""
            QWidget {{
                background-color: {c.bg_sidebar};
                border-right: 1px solid {c.border};
            }}
        """)

        return nav

    def _scrollable(self, inner: QWidget) -> QWidget:
        """Wrap *inner* in a QScrollArea with matching background."""
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._styles.add(
            inner, lambda c: f"QWidget {{ background-color: {c.bg_main}; }}"
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        self._styles.add(scroll, lambda c: f"""
            QScrollArea {{ background-color: {c.bg_main}; border: none; }}
            QScrollArea > QWidget > QWidget {{ background-color: {c.bg_main}; }}
        """)
        return scroll

    # ── Tab 0: Appearance ──────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(8)

        self._lbl_sec_theme = self._section_label(t("settings_theme_label"), first=True)
        layout.addWidget(self._lbl_sec_theme)

        self._card_auto = _RadioCard(t("theme_auto"), self._theme_auto_desc())
        self._card_dark = _RadioCard(
            t("settings_theme_dark_name"),
            t("settings_theme_dark_desc"),
        )
        self._card_light = _RadioCard(
            t("settings_theme_light_name"),
            t("settings_theme_light_desc"),
        )
        self._theme_cards = {
            "auto": self._card_auto,
            "dark": self._card_dark,
            "light": self._card_light,
        }
        for setting, card in self._theme_cards.items():
            card.clicked.connect(lambda name=setting: self._on_theme_card(name))
            layout.addWidget(card)
        self._update_theme_cards(ThemeManager.instance().setting)

        self._lbl_sec_lang = self._section_label(t("menu_language"))
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
        self._styles.add(self._lbl_lang_info, lambda c: _label_style(c.text_muted))
        layout.addWidget(self._lbl_lang_info)

        # ── Watermark section ──────────────────────────────────────────────
        self._lbl_sec_watermark = self._section_label(t("watermark_section"))
        layout.addWidget(self._lbl_sec_watermark)

        # Status card
        wm_card = QWidget()
        wm_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        wm_card_layout = QHBoxLayout(wm_card)
        wm_card_layout.setContentsMargins(12, 8, 12, 8)
        self._lbl_watermark_status = QLabel("")
        wm_status_font = self._lbl_watermark_status.font()
        wm_status_font.setPixelSize(12)
        self._lbl_watermark_status.setFont(wm_status_font)
        self._lbl_watermark_status.setWordWrap(True)
        wm_card_layout.addWidget(self._lbl_watermark_status)
        self._styles.add(wm_card, _card_style)
        layout.addWidget(wm_card)

        # Buttons row
        wm_btn_row = QHBoxLayout()
        self._btn_watermark_select = QPushButton(t("watermark_select"))
        self._btn_watermark_select.setFixedHeight(30)
        self._btn_watermark_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_watermark_select.clicked.connect(self._on_select_watermark)
        self._btn_watermark_clear = QPushButton(t("watermark_clear"))
        self._btn_watermark_clear.setFixedHeight(30)
        self._btn_watermark_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_watermark_clear.clicked.connect(self._on_clear_watermark)
        wm_btn_row.addWidget(self._btn_watermark_select)
        wm_btn_row.addWidget(self._btn_watermark_clear)
        wm_btn_row.addStretch()
        layout.addLayout(wm_btn_row)

        # Populate initial status
        self._refresh_watermark_status()

        # ── Printer calibration section ────────────────────────────────────
        self._lbl_sec_calibration = self._section_label(t("print_calibration"))
        layout.addWidget(self._lbl_sec_calibration)

        self._lbl_calibration_info = QLabel(t("calibration_info"))
        self._lbl_calibration_info.setWordWrap(True)
        cal_info_font = self._lbl_calibration_info.font()
        cal_info_font.setPixelSize(11)
        self._lbl_calibration_info.setFont(cal_info_font)
        self._styles.add(
            self._lbl_calibration_info, lambda c: _label_style(c.text_muted)
        )
        layout.addWidget(self._lbl_calibration_info)

        def _make_spin(value: float) -> QDoubleSpinBox:
            spin = QDoubleSpinBox()
            spin.setRange(-5.0, 5.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setValue(value)
            spin.setSuffix(" mm")
            spin.setFixedWidth(100)
            self._styles.add(spin, lambda c: f"""
                QDoubleSpinBox {{
                    background-color: {c.bg_input};
                    color: {c.text_primary};
                    border: 1px solid {c.border};
                    border-radius: 6px;
                    padding: 4px 6px;
                }}
            """)
            return spin

        cal_x_row = QHBoxLayout()
        self._lbl_cal_x = QLabel(t("calibration_x"))
        cal_x_font = self._lbl_cal_x.font()
        cal_x_font.setPixelSize(12)
        self._lbl_cal_x.setFont(cal_x_font)
        self._spin_cal_x = _make_spin(get_calibration_x())
        cal_x_row.addWidget(self._lbl_cal_x)
        cal_x_row.addStretch()
        cal_x_row.addWidget(self._spin_cal_x)
        layout.addLayout(cal_x_row)

        cal_y_row = QHBoxLayout()
        self._lbl_cal_y = QLabel(t("calibration_y"))
        cal_y_font = self._lbl_cal_y.font()
        cal_y_font.setPixelSize(12)
        self._lbl_cal_y.setFont(cal_y_font)
        self._spin_cal_y = _make_spin(get_calibration_y())
        cal_y_row.addWidget(self._lbl_cal_y)
        cal_y_row.addStretch()
        cal_y_row.addWidget(self._spin_cal_y)
        layout.addLayout(cal_y_row)

        cal_btn_row = QHBoxLayout()
        self._btn_cal_reset = QPushButton(t("calibration_reset"))
        self._btn_cal_reset.setFixedHeight(30)
        self._btn_cal_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cal_reset.clicked.connect(self._on_calibration_reset)
        cal_btn_row.addWidget(self._btn_cal_reset)

        self._btn_cal_pdf = QPushButton(t("generate_calibration_pdf"))
        self._btn_cal_pdf.setFixedHeight(30)
        self._btn_cal_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cal_pdf.clicked.connect(self._on_generate_calibration_pdf)
        cal_btn_row.addWidget(self._btn_cal_pdf)
        cal_btn_row.addStretch()
        layout.addLayout(cal_btn_row)

        self._spin_cal_x.valueChanged.connect(self._on_calibration_x_changed)
        self._spin_cal_y.valueChanged.connect(self._on_calibration_y_changed)

        # ── Developer section ──────────────────────────────────────────────
        self._lbl_sec_debug = self._section_label(t("debug_section"))
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

        self._lbl_log_path = QLabel(f"Log: {get_log_file()}")
        log_path_font = self._lbl_log_path.font()
        log_path_font.setPixelSize(10)
        log_path_font.setFamily("Courier New")
        self._lbl_log_path.setFont(log_path_font)
        self._lbl_log_path.setVisible(get_debug_logging())
        layout.addWidget(self._lbl_log_path)

        self._styles.add(self._lbl_debug_subtitle, lambda c: _label_style(c.text_muted))
        self._styles.add(self._lbl_log_path, lambda c: _label_style(c.text_muted))

        self._chk_debug.toggled.connect(self._on_debug_toggle)

        layout.addStretch()

        return self._scrollable(inner)

    # ── Tab 1: Data source ─────────────────────────────────────────────────────

    def _build_datasource_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(8)

        self._lbl_sec_mode = self._section_label(t("settings_active_mode"), first=True)
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

        self._styles.add(warn_box, lambda c: f"""
            QWidget {{
                background-color: {c.bg_card};
                border-left: 3px solid {c.warning};
                border-radius: 0px;
            }}
        """)
        self._styles.add(self._lbl_mode_warn, lambda c: _label_style(c.text_muted))
        layout.addWidget(warn_box)

        # ── Data folder section ────────────────────────────────────────────
        self._lbl_sec_data_folder = self._section_label(t("settings_data_folder"))
        layout.addWidget(self._lbl_sec_data_folder)

        self._lbl_data_folder_info = QLabel(t("settings_data_folder_info"))
        self._lbl_data_folder_info.setWordWrap(True)
        data_info_font = self._lbl_data_folder_info.font()
        data_info_font.setPixelSize(11)
        self._lbl_data_folder_info.setFont(data_info_font)
        self._styles.add(
            self._lbl_data_folder_info, lambda c: _label_style(c.text_muted)
        )
        layout.addWidget(self._lbl_data_folder_info)

        data_folder_row = QHBoxLayout()
        # Read-only line edit: the path can be selected and copied
        self._edit_data_folder = QLineEdit(str(get_data_dir()))
        self._edit_data_folder.setReadOnly(True)
        self._edit_data_folder.setCursorPosition(0)
        self._edit_data_folder.setToolTip(str(get_data_dir()))
        self._edit_data_folder.setFixedHeight(30)
        self._btn_open_data_folder = QPushButton(t("settings_open_folder"))
        self._btn_open_data_folder.setFixedHeight(30)
        self._btn_open_data_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_open_data_folder.clicked.connect(self._on_open_data_folder)
        data_folder_row.addWidget(self._edit_data_folder, 1)
        data_folder_row.addWidget(self._btn_open_data_folder)
        layout.addLayout(data_folder_row)

        layout.addStretch()

        return self._scrollable(inner)

    # ── Tab 2: Discogs account ─────────────────────────────────────────────────

    def _build_discogs_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

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

        self._styles.add(status_card, _card_style)
        self._styles.add(self._lbl_discogs_status, lambda c: _label_style(c.text_primary))
        self._styles.add(self._lbl_discogs_username, lambda c: _label_style(c.text_muted))
        layout.addWidget(status_card)

        # Token section
        self._lbl_sec_token = self._section_label(t("discogs_lbl_token"))
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
        self._styles.add(self._token_edit, lambda c: f"""
            QLineEdit {{
                background-color: {c.bg_input};
                color: {c.text_primary};
                border: 1px solid {c.border};
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

        def btn_style(c: ThemeColors) -> str:
            return f"""
                QPushButton {{
                    background-color: {c.bg_card};
                    color: {c.text_primary};
                    border: 1px solid {c.border};
                    border-radius: 6px;
                    padding: 4px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c.accent_bg};
                    border-color: {c.accent};
                    color: {c.accent_light};
                }}
            """
        for btn in (self._btn_toggle_token, self._btn_change_token, self._btn_logout):
            self._styles.add(btn, btn_style)

        btn_row_layout.addWidget(self._btn_change_token)
        btn_row_layout.addWidget(self._btn_logout)
        btn_row_layout.addStretch()
        layout.addWidget(btn_row)

        layout.addStretch()

        self._refresh_discogs_status()

        return self._scrollable(inner)

    # ── Tab 3: About ───────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 8, 24, 24)
        layout.setSpacing(12)

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

        self._styles.add(app_card, _card_style)
        self._styles.add(lbl_app_name, lambda c: (
            f"color: {c.text_primary}; font-weight: bold; background: transparent;"
        ))
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

            self._styles.add(lbl_key, lambda c: _label_style(c.text_secondary))
            self._styles.add(lbl_val, lambda c: _label_style(c.text_primary))
            self._styles.add(row, lambda c: f"""
                QWidget {{
                    background-color: {c.bg_card};
                    border-bottom: 1px solid {c.border};
                    border-radius: 0px;
                }}
            """)

            row_layout.addWidget(lbl_key)
            row_layout.addStretch()
            row_layout.addWidget(lbl_val)
            layout.addWidget(row)

        # Version check section
        self._lbl_sec_version_check = self._section_label(t("version_check"))
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

            self._styles.add(lbl_key, lambda c: _label_style(c.text_secondary))
            self._styles.add(lbl_val, lambda c: _label_style(c.text_muted))
            self._styles.add(row, _card_style)

            row_layout.addWidget(lbl_key)
            row_layout.addStretch()
            row_layout.addWidget(lbl_val)
            layout.addWidget(row)

        # Check for updates button
        self._btn_about_check_updates = QPushButton(t("check_updates"))
        self._btn_about_check_updates.setFixedHeight(32)
        self._btn_about_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_about_check_updates.clicked.connect(self._check_for_updates)
        self._styles.add(self._btn_about_check_updates, lambda c: f"""
            QPushButton {{
                background-color: {c.bg_card};
                color: {c.text_primary};
                border: 1px solid {c.accent};
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {c.accent_bg};
            }}
            QPushButton:disabled {{
                color: {c.text_muted};
                border-color: {c.border};
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
        self._styles.add(
            self._lbl_about_release_notes, lambda c: _label_style(c.accent_light)
        )
        self._lbl_about_release_notes.mousePressEvent = (
            lambda _event: self._open_release_notes()
        )
        layout.addWidget(self._lbl_about_release_notes)

        # How to update: download hint + link to the releases page (shown only
        # when an update is available)
        self._lbl_about_update_hint = QLabel()
        self._lbl_about_update_hint.setVisible(False)
        self._lbl_about_update_hint.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_about_update_hint.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._lbl_about_update_hint.setOpenExternalLinks(True)
        self._lbl_about_update_hint.setWordWrap(True)
        self._styles.add(self._lbl_about_update_hint, lambda c: f"""
            QLabel {{
                background-color: {c.bg_sidebar};
                border: 1px solid {c.border};
                border-radius: 6px;
                padding: 10px 12px;
                color: {c.text_secondary};
            }}
        """)
        layout.addWidget(self._lbl_about_update_hint)

        # Pre-fill available version from cache (no network call on open)
        cached = get_last_known_version()
        if cached:
            self._lbl_about_available_val.setText(cached)

        # Divider before GitHub section
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setFixedHeight(1)
        self._styles.add(
            divider, lambda c: f"background-color: {c.border}; border: none;"
        )
        layout.addWidget(divider)

        # GitHub button
        self._btn_about_github = QPushButton(t("open_github"))
        self._btn_about_github.setFixedHeight(32)
        self._btn_about_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_about_github.clicked.connect(self._open_github)
        self._styles.add(self._btn_about_github, lambda c: f"""
            QPushButton {{
                color: {c.accent_light};
                background: transparent;
                border: none;
                font-size: 12px;
                text-align: left;
                padding: 4px 0px;
            }}
            QPushButton:hover {{
                color: {c.accent};
            }}
        """)
        layout.addWidget(self._btn_about_github)

        # Discogs attribution section — legal requirement per Discogs API ToU
        self._lbl_discogs_attribution_label = QLabel(t("discogs_attribution_label"))
        attr_lbl_font = self._lbl_discogs_attribution_label.font()
        attr_lbl_font.setPixelSize(10)
        attr_lbl_font.setBold(True)
        self._lbl_discogs_attribution_label.setFont(attr_lbl_font)
        self._styles.add(self._lbl_discogs_attribution_label, lambda c: (
            f"color: {c.text_secondary}; background: transparent;"
            " padding-top: 12px;"
        ))
        layout.addWidget(self._lbl_discogs_attribution_label)

        attr_box = QWidget()
        attr_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._styles.add(attr_box, lambda c: f"""
            QWidget {{
                background: {c.bg_sidebar};
                border: 1px solid {c.border};
                border-radius: 6px;
            }}
        """)
        attr_layout = QVBoxLayout(attr_box)
        attr_layout.setContentsMargins(14, 10, 14, 10)

        # This text must NOT be translated — it must appear verbatim per Discogs API ToU
        _lbl_attr_text = QLabel(
            "This application uses Discogs\u2019 API but is not affiliated "
            "with, sponsored or endorsed by Discogs."
        )
        _lbl_attr_text.setWordWrap(True)
        attr_text_font = _lbl_attr_text.font()
        attr_text_font.setPixelSize(11)
        _lbl_attr_text.setFont(attr_text_font)
        self._styles.add(_lbl_attr_text, lambda c: (
            f"color: {c.text_muted}; font-style: italic; background: transparent;"
        ))
        attr_layout.addWidget(_lbl_attr_text)

        # Cache policy notice — translatable
        self._lbl_discogs_cache_notice = QLabel(t("discogs_cache_notice"))
        self._lbl_discogs_cache_notice.setWordWrap(True)
        cache_notice_font = self._lbl_discogs_cache_notice.font()
        cache_notice_font.setPixelSize(11)
        self._lbl_discogs_cache_notice.setFont(cache_notice_font)
        self._styles.add(self._lbl_discogs_cache_notice, lambda c: (
            f"color: {c.text_muted}; font-style: italic;"
            " background: transparent; margin-top: 8px;"
        ))
        attr_layout.addWidget(self._lbl_discogs_cache_notice)

        layout.addWidget(attr_box)

        layout.addStretch()

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

    def _on_theme_card(self, setting: str) -> None:
        # Saves and applies the setting; _apply_theme / _update_theme_cards
        # follow via the ThemeManager signals.
        ThemeManager.instance().set_setting(setting)

    def _update_theme_cards(self, setting: str) -> None:
        """Mark the card of the saved theme setting as active."""
        for name, card in self._theme_cards.items():
            card.set_active(name == setting)

    def _theme_auto_desc(self) -> str:
        """Subtitle of the "auto" card, naming the theme the system resolves to."""
        resolved = ThemeManager.instance().resolved
        name_key = (
            "settings_theme_light_name" if resolved == "light"
            else "settings_theme_dark_name"
        )
        return t("settings_theme_auto_desc", theme=t(name_key))

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

    # ── Calibration handlers ───────────────────────────────────────────────────

    def _on_calibration_x_changed(self, value: float) -> None:
        from config.avery_formats import AVERY_FORMATS
        AVERY_FORMATS["4780"]["calibration_x_mm"] = value
        set_calibration_x(value)

    def _on_calibration_y_changed(self, value: float) -> None:
        from config.avery_formats import AVERY_FORMATS
        AVERY_FORMATS["4780"]["calibration_y_mm"] = value
        set_calibration_y(value)

    def _on_calibration_reset(self) -> None:
        self._spin_cal_x.setValue(0.0)
        self._spin_cal_y.setValue(0.0)

    def _on_generate_calibration_pdf(self) -> None:
        import os
        import sys
        import subprocess
        from config.avery_formats import get_format
        from modules.pdf_generator import generate_calibration_pdf

        out_path = get_output_dir() / "calibration_avery4780.pdf"
        fmt = get_format("4780")
        try:
            pdf = generate_calibration_pdf(out_path, fmt)
        except Exception as exc:
            QMessageBox.critical(self, t("err_print"), str(exc))
            return

        if sys.platform == "win32":
            os.startfile(str(pdf))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pdf)])
        else:
            subprocess.Popen(["xdg-open", str(pdf)])

    # ── Watermark handlers ─────────────────────────────────────────────────────

    def _on_select_watermark(self) -> None:
        main = self.parent()
        if hasattr(main, "_on_select_watermark"):
            main._on_select_watermark()
            self._refresh_watermark_status()

    def _on_clear_watermark(self) -> None:
        main = self.parent()
        if hasattr(main, "_on_clear_watermark"):
            main._on_clear_watermark()
            self._refresh_watermark_status()

    def _refresh_watermark_status(self) -> None:
        """Update the watermark status card to reflect current settings."""
        colors = current_colors()
        path   = get_watermark_path()
        active = bool(path and path.exists())
        if active:
            self._lbl_watermark_status.setText(
                t("watermark_active", filename=path.name)
            )
        else:
            self._lbl_watermark_status.setText(t("watermark_none"))
        if colors:
            self._lbl_watermark_status.setStyleSheet(
                _label_style(colors.success if active else colors.text_muted)
            )
        self._btn_watermark_clear.setEnabled(active)

    # ── Data source handlers ───────────────────────────────────────────────────

    def _on_open_data_folder(self) -> None:
        """Open the data folder (labels.db) in the system file manager."""
        import os
        import sys
        import subprocess

        folder = get_data_dir()
        try:
            if sys.platform == "win32":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            QMessageBox.warning(
                self, t("app_title"),
                t("err_open_folder", path=str(folder), detail=str(exc)),
            )

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
        dlg = DiscogsDialog(parent=self)
        dlg.exec()
        dlg.deleteLater()
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
        self._btn_about_check_updates.setEnabled(True)
        self._btn_about_check_updates.setText(t("check_updates"))

        if not result["success"]:
            self._lbl_about_available_val.setText("—")
            error = result["error"]
            if error == "no_releases":
                msg, role = t("no_releases_yet"), "text_muted"
            elif error == "network":
                msg, role = t("check_failed_network"), "danger"
            else:
                msg, role = t("check_failed_error"), "danger"
            self._set_update_status(msg, role)
            self._set_update_hint("")
            return

        self._lbl_about_available_val.setText(result["tag_name"])
        set_last_known_version(result["tag_name"])
        set_last_version_check(datetime.now().isoformat())

        if is_update_available(result["latest_version"]):
            self._set_update_status(
                t("update_available", version=result["tag_name"]), "accent"
            )
            self._release_url = result["release_url"]
            self._lbl_about_release_notes.setVisible(True)
            import sys
            hint_key = "update_hint_windows" if sys.platform == "win32" else "update_hint_linux"
            self._set_update_hint(hint_key)
        elif is_newer_than_latest(result["latest_version"]):
            self._set_update_status(
                t("newer_than_latest", version=result["tag_name"]), "success"
            )
            self._set_update_hint("")
        else:
            self._set_update_status(t("up_to_date"), "success")
            self._set_update_hint("")

    def _set_update_status(self, text: str, role: str) -> None:
        """Show the version check result in the color *role* (a ThemeColors field)."""
        self._update_status_role = role
        self._lbl_about_update_status.setText(text)
        self._apply_update_status_style()
        self._lbl_about_update_status.setVisible(True)

    def _apply_update_status_style(self) -> None:
        colors = current_colors()
        if colors and self._update_status_role:
            self._lbl_about_update_status.setStyleSheet(
                _label_style(getattr(colors, self._update_status_role))
            )

    def _set_update_hint(self, hint_key: str) -> None:
        """Show the download hint *hint_key* with the releases link ("" hides it)."""
        self._update_hint_key = hint_key
        self._lbl_about_update_hint.setVisible(bool(hint_key))
        if not hint_key:
            return
        colors = current_colors()
        # The link color is part of the rich text, so the text is rebuilt on
        # every theme change
        link_style = f' style="color: {colors.accent_light};"' if colors else ""
        self._lbl_about_update_hint.setText(
            f"{t(hint_key)}<br>"
            f'<a href="{GITHUB_RELEASES_URL}"{link_style}>{t("update_releases_link")}</a>'
        )

    def _open_release_notes(self) -> None:
        """Open the GitHub release page in the system browser."""
        url = getattr(self, "_release_url", GITHUB_RELEASES_URL)
        QDesktopServices.openUrl(QUrl(url))

    def _on_logout(self) -> None:
        CredentialsManager().clear()
        DiscogsCache().clear()
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

        self._discogs_connected = connected
        self._apply_discogs_dot_style()

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

    def _apply_discogs_dot_style(self) -> None:
        colors = current_colors()
        if colors:
            dot_color = colors.success if self._discogs_connected else colors.text_muted
            self._discogs_dot.setStyleSheet(
                f"background-color: {dot_color}; border-radius: 4px;"
            )

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _apply_theme(self, colors: ThemeColors | None = None) -> None:
        """Re-apply every color of the dialog; runs on ThemeManager.theme_changed."""
        colors = colors or current_colors()
        if not colors:
            return
        self._styles.apply(colors)

        # State-dependent styles
        for item in self._nav_items:
            item._update_style()
        for card in (
            *self._theme_cards.values(),
            self._card_de, self._card_en,
            self._card_local, self._card_discogs,
        ):
            card._update_style()
        self._card_auto.set_subtitle(self._theme_auto_desc())
        self._refresh_watermark_status()
        self._apply_discogs_dot_style()
        self._apply_update_status_style()
        self._set_update_hint(self._update_hint_key)

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
        self._card_auto.set_title(t("theme_auto"))
        self._card_auto.set_subtitle(self._theme_auto_desc())
        self._lbl_sec_lang.setText(t("menu_language").upper())
        self._lbl_lang_info.setText(t("settings_lang_change_info"))
        self._lbl_sec_watermark.setText(t("watermark_section").upper())
        self._btn_watermark_select.setText(t("watermark_select"))
        self._btn_watermark_clear.setText(t("watermark_clear"))
        self._refresh_watermark_status()
        self._lbl_sec_calibration.setText(t("print_calibration").upper())
        self._lbl_calibration_info.setText(t("calibration_info"))
        self._lbl_cal_x.setText(t("calibration_x"))
        self._lbl_cal_y.setText(t("calibration_y"))
        self._btn_cal_reset.setText(t("calibration_reset"))
        self._btn_cal_pdf.setText(t("generate_calibration_pdf"))
        self._lbl_sec_debug.setText(t("debug_section").upper())
        self._lbl_debug_title.setText(t("debug_logging_label"))
        self._lbl_debug_subtitle.setText(t("debug_logging_subtitle"))

        # Data source tab
        self._lbl_sec_mode.setText(t("settings_active_mode").upper())
        self._card_local.set_title(t("datasource_local"))
        self._card_local.set_subtitle(t("settings_mode_local_sub"))
        self._card_discogs.set_subtitle(t("settings_mode_discogs_sub"))
        self._lbl_mode_warn.setText(t("settings_mode_switch_warn"))
        self._lbl_sec_data_folder.setText(t("settings_data_folder").upper())
        self._lbl_data_folder_info.setText(t("settings_data_folder_info"))
        self._btn_open_data_folder.setText(t("settings_open_folder"))

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
        self._lbl_discogs_attribution_label.setText(t("discogs_attribution_label"))
        self._lbl_discogs_cache_notice.setText(t("discogs_cache_notice"))
        self._set_update_hint(self._update_hint_key)
