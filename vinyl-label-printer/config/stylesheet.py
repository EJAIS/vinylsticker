"""QSS stylesheet generator — builds a complete Qt stylesheet from a ThemeColors instance."""

from config.themes import ThemeColors


def build_stylesheet(colors: ThemeColors) -> str:
    """Generate a complete QSS string using the given ThemeColors."""
    return f"""
/* ── Base ─────────────────────────────────────────────────────────────────── */

QMainWindow, QDialog {{
    background-color: {colors.bg_main};
    color: {colors.text_primary};
}}

QWidget {{
    background-color: {colors.bg_main};
    color: {colors.text_primary};
    font-size: 13px;
}}

/* ── Labels ───────────────────────────────────────────────────────────────── */

QLabel {{
    background-color: transparent;
    color: {colors.text_primary};
}}

/* ── Group boxes ──────────────────────────────────────────────────────────── */

QGroupBox {{
    background-color: {colors.bg_card};
    border: 1px solid {colors.border};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 6px;
    color: {colors.text_secondary};
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    top: 0px;
    color: {colors.text_secondary};
}}

/* ── Buttons ──────────────────────────────────────────────────────────────── */

QPushButton {{
    background-color: {colors.bg_card};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {colors.accent_bg};
    border-color: {colors.accent};
    color: {colors.accent_light};
}}

QPushButton:pressed {{
    background-color: {colors.accent};
    color: {colors.text_primary};
}}

QPushButton:disabled {{
    background-color: {colors.bg_sidebar};
    color: {colors.text_muted};
    border-color: {colors.border};
}}

QPushButton[primary="true"] {{
    background-color: {colors.accent};
    color: {colors.text_primary};
    border: none;
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
}}

QPushButton[primary="true"]:hover {{
    background-color: {colors.accent_light};
    color: {colors.bg_main};
}}

QPushButton[primary="true"]:pressed {{
    background-color: {colors.accent_bg};
    color: {colors.text_primary};
}}

QPushButton[primary="true"]:disabled {{
    background-color: {colors.accent_bg};
    color: {colors.text_muted};
}}

/* ── Line edits ───────────────────────────────────────────────────────────── */

QLineEdit {{
    background-color: {colors.bg_input};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {colors.accent};
    selection-color: {colors.text_primary};
}}

QLineEdit:focus {{
    border-color: {colors.accent};
}}

QLineEdit:disabled {{
    background-color: {colors.bg_sidebar};
    color: {colors.text_muted};
}}

/* ── Combo boxes ──────────────────────────────────────────────────────────── */

QComboBox {{
    background-color: {colors.bg_input};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {colors.accent};
}}

QComboBox:focus {{
    border-color: {colors.accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors.bg_card};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    selection-background-color: {colors.accent};
    selection-color: {colors.text_primary};
}}

/* ── Tables ───────────────────────────────────────────────────────────────── */

QTableWidget {{
    background-color: {colors.bg_card};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    gridline-color: {colors.border};
    selection-background-color: {colors.accent_bg};
    selection-color: {colors.text_primary};
    alternate-background-color: {colors.bg_sidebar};
}}

QTableWidget::item {{
    padding: 4px;
    border: none;
}}

QTableWidget::item:hover {{
    background-color: {colors.accent_bg};
    color: {colors.text_primary};
}}

QTableWidget::item:selected {{
    background-color: {colors.accent};
    color: {colors.text_primary};
}}

QHeaderView::section {{
    background-color: {colors.bg_sidebar};
    color: {colors.text_secondary};
    border: 1px solid {colors.border};
    padding: 4px;
    font-weight: bold;
}}

QHeaderView::section:checked {{
    background-color: {colors.accent_bg};
}}

/* ── Scroll bars ──────────────────────────────────────────────────────────── */

QScrollBar:vertical {{
    background-color: {colors.bg_sidebar};
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors.border};
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors.accent};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {colors.bg_sidebar};
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors.border};
    min-width: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors.accent};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Radio buttons ────────────────────────────────────────────────────────── */

QRadioButton {{
    color: {colors.text_muted};
    spacing: 6px;
}}

QRadioButton:checked {{
    color: {colors.accent_light};
    font-weight: bold;
}}

QRadioButton::indicator {{
    width: 14px;
    height: 14px;
}}

QRadioButton::indicator:unchecked {{
    border: 2px solid {colors.border};
    border-radius: 7px;
    background-color: {colors.bg_input};
}}

QRadioButton::indicator:checked {{
    border: 2px solid {colors.accent};
    border-radius: 7px;
    background-color: {colors.accent};
}}

/* ── Check boxes ──────────────────────────────────────────────────────────── */

QCheckBox {{
    color: {colors.text_primary};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 2px solid {colors.border};
    border-radius: 3px;
    background-color: {colors.bg_input};
}}

QCheckBox::indicator:checked {{
    background-color: {colors.accent};
    border-color: {colors.accent};
}}

QCheckBox::indicator:hover {{
    border-color: {colors.accent};
}}

/* ── Menu bar & menus ─────────────────────────────────────────────────────── */

QMenuBar {{
    background-color: {colors.bg_sidebar};
    color: {colors.text_primary};
    border-bottom: 1px solid {colors.border};
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 10px;
}}

QMenuBar::item:selected {{
    background-color: {colors.accent_bg};
    color: {colors.accent_light};
}}

QMenu {{
    background-color: {colors.bg_card};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
}}

QMenu::item {{
    padding: 5px 20px;
}}

QMenu::item:selected {{
    background-color: {colors.accent_bg};
    color: {colors.accent_light};
}}

QMenu::separator {{
    height: 1px;
    background-color: {colors.border};
    margin: 4px 0px;
}}

/* ── Status bar ───────────────────────────────────────────────────────────── */

QStatusBar {{
    background-color: {colors.bg_sidebar};
    color: {colors.text_muted};
    border-top: 1px solid {colors.border};
}}

/* ── Splitter ─────────────────────────────────────────────────────────────── */

QSplitter::handle {{
    background-color: {colors.border};
}}

/* ── Message boxes ────────────────────────────────────────────────────────── */

QMessageBox {{
    background-color: {colors.bg_card};
    color: {colors.text_primary};
}}

QMessageBox QLabel {{
    color: {colors.text_primary};
    background-color: transparent;
}}
"""
