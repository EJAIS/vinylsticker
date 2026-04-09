"""Central color configuration for application themes."""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    # Backgrounds
    bg_main:        str
    bg_sidebar:     str
    bg_card:        str
    bg_input:       str
    # Borders
    border:         str
    # Text
    text_primary:   str
    text_secondary: str
    text_muted:     str
    # Accent
    accent:         str
    accent_light:   str
    accent_bg:      str
    # Status
    success:        str
    warning:        str
    danger:         str
    # Label preview
    label_filled:   str
    label_empty:    str
    label_skipped:  str


THEMES = {
    "dark": ThemeColors(
        bg_main="#2a3042", bg_sidebar="#222737",
        bg_card="#313855", bg_input="#313855",
        border="#3d4663",
        text_primary="#f0f2f8", text_secondary="#c8cfe0", text_muted="#7b86a0",
        accent="#2e8b7a", accent_light="#7dd4c8", accent_bg="#1e4d45",
        success="#22c55e", warning="#f59e0b", danger="#ef4444",
        label_filled="#2e8b7a", label_empty="#2a3042", label_skipped="#313855",
    ),
    "light": ThemeColors(
        bg_main="#f4f6fa", bg_sidebar="#eaeff7",
        bg_card="#ffffff", bg_input="#ffffff",
        border="#d1d9e6",
        text_primary="#111827", text_secondary="#1f2d40", text_muted="#8896b3",
        accent="#2e8b7a", accent_light="#1e5c53", accent_bg="#c8e8e4",
        success="#16a34a", warning="#d97706", danger="#dc2626",
        label_filled="#2e8b7a", label_empty="#f4f6fa", label_skipped="#eaeff7",
    ),
}


def get_theme(name: str) -> ThemeColors:
    return THEMES.get(name, THEMES["dark"])
