"""
Central theme handling.

ThemeManager is the only place that resolves the theme setting, applies the
global stylesheet and publishes the active ThemeColors:

  setting   "auto" | "dark" | "light" (persisted in settings.json)
  resolved  "dark" | "light" — "auto" follows the OS color scheme live

Widgets that set colors themselves read current_colors() when they are built
and connect a bound method to ThemeManager.instance().theme_changed to re-apply
them. PyQt drops a connection to a bound method of a QObject when that object
is destroyed, so closed and deleted dialogs never receive the signal.
"""

from __future__ import annotations

from typing import Callable

from PyQt6 import sip
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget

from config.settings import set_theme as save_theme_setting
from config.stylesheet import build_stylesheet
from config.themes import ThemeColors, get_theme as get_theme_colors
from modules.logger import get_logger

THEME_SETTINGS = ("auto", "dark", "light")

logger = get_logger()


def resolve_auto_theme(
    scheme: Qt.ColorScheme, window_color: QColor
) -> tuple[str, str]:
    """Map the OS color scheme to "dark" or "light"; return (theme, reason).

    The color scheme is Unknown on desktops Qt cannot query (e.g. Linux without
    a working xdg-desktop-portal); then the lightness of the platform palette's
    window color decides.
    """
    if scheme == Qt.ColorScheme.Dark:
        return "dark", "OS color scheme is dark"
    if scheme == Qt.ColorScheme.Light:
        return "light", "OS color scheme is light"
    lightness = window_color.lightness()
    theme = "dark" if lightness < 128 else "light"
    return theme, (
        f"OS color scheme unknown, platform window color {window_color.name()} "
        f"has lightness {lightness}"
    )


class ThemeManager(QObject):
    """Owns the theme setting and the active ThemeColors (one per QApplication)."""

    # Emitted after the global stylesheet was replaced
    theme_changed = pyqtSignal(object)    # ThemeColors
    # Emitted whenever the setting changes, even if the resolved theme does not
    setting_changed = pyqtSignal(str)     # "auto" | "dark" | "light"

    _instance: ThemeManager | None = None

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._setting = "auto"
        self._resolved = ""
        self._colors: ThemeColors | None = None

        # Follow OS theme switches while the setting is "auto". colorSchemeChanged
        # needs Qt 6.5; paletteChanged covers platforms whose color scheme is
        # Unknown but whose palette still follows the desktop theme.
        hints = app.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        if hasattr(app, "paletteChanged"):
            app.paletteChanged.connect(self._on_system_theme_changed)

    @classmethod
    def instance(cls) -> ThemeManager:
        """Return the manager of the running QApplication, creating it once."""
        if cls._instance is None or sip.isdeleted(cls._instance):
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("ThemeManager needs a QApplication")
            cls._instance = cls(app)
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def setting(self) -> str:
        return self._setting

    @property
    def resolved(self) -> str:
        """The applied theme: "dark" or "light" ("" before the first apply)."""
        return self._resolved

    @property
    def colors(self) -> ThemeColors | None:
        return self._colors

    def set_setting(self, setting: str, persist: bool = True) -> None:
        """Switch to *setting* ("auto" | "dark" | "light") and apply it now."""
        if setting not in THEME_SETTINGS:
            logger.warning(f"Unknown theme setting {setting!r} — using 'auto'")
            setting = "auto"
        changed = setting != self._setting
        self._setting = setting
        if persist:
            save_theme_setting(setting)
        self._apply(force=self._colors is None)
        if changed:
            self.setting_changed.emit(setting)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _resolve(self) -> tuple[str, str]:
        if self._setting != "auto":
            return self._setting, "set in the settings"
        hints = self._app.styleHints()
        scheme = (
            hints.colorScheme() if hasattr(hints, "colorScheme")
            else Qt.ColorScheme.Unknown
        )
        window_color = self._app.palette().color(QPalette.ColorRole.Window)
        return resolve_auto_theme(scheme, window_color)

    def _apply(self, force: bool = False) -> None:
        """Resolve the setting; replace the stylesheet if the theme changed."""
        resolved, reason = self._resolve()
        if resolved == self._resolved and not force:
            return
        logger.info(f"Theme: {resolved} (setting: {self._setting}; {reason})")
        self._resolved = resolved
        self._colors = get_theme_colors(resolved)
        self._app.setStyleSheet(build_stylesheet(self._colors))
        # Kept for code that reads the colors from the application object
        self._app.setProperty("theme_colors", self._colors)
        self.theme_changed.emit(self._colors)
        # Custom-painted widgets (e.g. GridWidget) read the colors in paintEvent
        for widget in self._app.allWidgets():
            widget.update()

    def _on_system_theme_changed(self, *_args) -> None:
        if self._setting == "auto" and self._colors is not None:
            self._apply()


def current_colors() -> ThemeColors | None:
    """Return the active ThemeColors, or None before a theme was applied."""
    if QApplication.instance() is None:
        return None
    return ThemeManager.instance().colors


StyleBuilder = Callable[[ThemeColors], str]


class ThemedStyles:
    """Per-widget stylesheets built from ThemeColors, re-applied on demand.

    A dialog registers each widget with a function that builds its stylesheet
    from the colors; apply() re-applies all of them after a theme change. The
    widgets must live as long as the owner of this registry (their parent).
    """

    def __init__(self) -> None:
        self._entries: list[tuple[QWidget, StyleBuilder]] = []

    def add(self, widget: QWidget, build: StyleBuilder) -> QWidget:
        """Register *widget*, style it with the current colors, return it."""
        self._entries.append((widget, build))
        colors = current_colors()
        if colors is not None:
            widget.setStyleSheet(build(colors))
        return widget

    def apply(self, colors: ThemeColors) -> None:
        for widget, build in self._entries:
            widget.setStyleSheet(build(colors))
