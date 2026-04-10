"""
Footer widget — fixed-height status bar at the bottom of the main window.

Left side:  Settings button.
Right side: Discogs connection dot + username, vertical divider, mode badge pill.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from modules.data_source import DataSourceMode
from modules.i18n import t


class FooterWidget(QWidget):
    """48 px tall footer with settings button and connection/mode status."""

    settings_clicked = pyqtSignal()
    debug_badge_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._connected = False
        self._username = ""
        self._mode = DataSourceMode.LOCAL

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)

        # Settings button (left)
        self._btn_settings = QPushButton(f"⚙  {t('menu_settings')}")
        self._btn_settings.setFixedHeight(30)
        self._btn_settings.clicked.connect(self.settings_clicked)
        layout.addWidget(self._btn_settings)

        # Debug badge (hidden by default, shown when debug logging is active)
        self._debug_badge = QPushButton(t("debug_mode_active"))
        self._debug_badge.setFixedHeight(30)
        self._debug_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self._debug_badge.clicked.connect(self.debug_badge_clicked)
        self._debug_badge.setVisible(False)
        layout.addWidget(self._debug_badge)

        layout.addStretch()

        # Status dot (8 px circle, drawn via border-radius)
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)

        # Username / connection label
        self._lbl_username = QLabel(t("sidebar_not_connected"))
        username_font = self._lbl_username.font()
        username_font.setPixelSize(12)
        self._lbl_username.setFont(username_font)

        # Vertical divider (1 px, 12 px tall)
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.VLine)
        self._divider.setFixedSize(1, 12)

        # Mode badge pill
        self._lbl_mode = QLabel(t("sidebar_local_mode"))
        mode_font = self._lbl_mode.font()
        mode_font.setPixelSize(12)
        self._lbl_mode.setFont(mode_font)

        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._lbl_username, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._divider, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._lbl_mode, 0, Qt.AlignmentFlag.AlignVCenter)

        self._apply_style()

    # ── Style ─────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        app = QApplication.instance()
        colors = app.property("theme_colors") if app else None
        if not colors:
            return

        self.setStyleSheet(f"""
            FooterWidget {{
                background-color: {colors.bg_sidebar};
                border-top: 1px solid {colors.border};
            }}
        """)

        self._btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.bg_card};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {colors.accent_bg};
                border-color: {colors.accent};
                color: {colors.accent_light};
            }}
        """)
        self._btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)

        dot_color = colors.success if self._connected else colors.text_muted
        self._dot.setStyleSheet(
            f"background-color: {dot_color}; border-radius: 4px;"
        )

        self._lbl_username.setStyleSheet(
            f"color: {colors.text_primary}; background: transparent;"
        )

        self._divider.setStyleSheet(
            f"background-color: {colors.border}; border: none;"
        )

        self._lbl_mode.setStyleSheet(f"""
            QLabel {{
                background-color: {colors.accent_bg};
                color: {colors.accent_light};
                border-radius: 20px;
                padding: 4px 12px;
                font-weight: bold;
            }}
        """)

        self._debug_badge.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.danger};
                color: #ffffff;
                border: none;
                border-radius: 20px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.danger};
                opacity: 0.85;
            }}
        """)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_discogs_status(self, connected: bool, username: str) -> None:
        self._connected = connected
        self._username = username

        app = QApplication.instance()
        colors = app.property("theme_colors") if app else None

        if connected and username:
            self._lbl_username.setText(username)
        else:
            self._lbl_username.setText(t("sidebar_not_connected"))

        if colors:
            dot_color = colors.success if connected else colors.text_muted
            self._dot.setStyleSheet(
                f"background-color: {dot_color}; border-radius: 4px;"
            )

    def update_mode(self, mode: DataSourceMode) -> None:
        self._mode = mode
        if mode == DataSourceMode.DISCOGS:
            self._lbl_mode.setText(t("sidebar_discogs_mode"))
        else:
            self._lbl_mode.setText(t("sidebar_local_mode"))

    def update_debug_mode(self, active: bool) -> None:
        self._debug_badge.setVisible(active)

    def retranslate(self) -> None:
        self._btn_settings.setText(f"⚙  {t('menu_settings')}")
        self._debug_badge.setText(t("debug_mode_active"))
        self.update_mode(self._mode)
        if not self._connected:
            self._lbl_username.setText(t("sidebar_not_connected"))
