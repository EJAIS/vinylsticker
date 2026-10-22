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
    # Review table cells
    cell_error_bg:  str   # empty required field
    row_warn_bg:    str   # row that contains an empty required field
    blink_bg:       str   # short flash after a cell was edited
    # Info banners, links and status lines
    info_border:    str
    info_text:      str
    link:           str
    status_ok:      str
    status_warn:    str


THEMES = {
    "dark": ThemeColors(
        bg_main="#2a3042", bg_sidebar="#222737",
        bg_card="#313855", bg_input="#313855",
        border="#3d4663",
        text_primary="#f0f2f8", text_secondary="#c8cfe0", text_muted="#7b86a0",
        accent="#2e8b7a", accent_light="#7dd4c8", accent_bg="#1e4d45",
        success="#22c55e", warning="#f59e0b", danger="#ef4444",
        label_filled="#2e8b7a", label_empty="#2a3042", label_skipped="#313855",
        cell_error_bg="#6b2d3a", row_warn_bg="#47303f", blink_bg="#5c5428",
        info_border="#7dd4c8", info_text="#c8cfe0", link="#7dd4c8",
        status_ok="#22c55e", status_warn="#f59e0b",
    ),
    "light": ThemeColors(
        bg_main="#f4f6fa", bg_sidebar="#eaeff7",
        bg_card="#ffffff", bg_input="#ffffff",
        border="#d1d9e6",
        text_primary="#111827", text_secondary="#1f2d40", text_muted="#8896b3",
        accent="#2e8b7a", accent_light="#1e5c53", accent_bg="#c8e8e4",
        success="#16a34a", warning="#d97706", danger="#dc2626",
        label_filled="#2e8b7a", label_empty="#f4f6fa", label_skipped="#eaeff7",
        cell_error_bg="#ffebee", row_warn_bg="#fff5f5", blink_bg="#fff9c4",
        info_border="#2196f3", info_text="#555555", link="#2196f3",
        status_ok="#2e7d32", status_warn="#e65100",
    ),
}


def get_theme(name: str) -> ThemeColors:
    return THEMES.get(name, THEMES["dark"])
