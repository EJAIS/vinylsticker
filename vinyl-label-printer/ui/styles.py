"""Shared Qt StyleSheet constants and helper functions."""

TABLE_STYLESHEET = """
QTableWidget {
    border: 1px solid #CCCCCC;
    gridline-color: #E0E0E0;
    background-color: white;
    color: black;
}
QTableWidget::item {
    color: black;
    padding: 4px;
}
QTableWidget::item:hover {
    background-color: #EEF4FF;
}
QTableWidget::item:selected {
    background-color: #BBDEFB;
    color: black;
}
QHeaderView::section {
    background-color: #F5F5F5;
    color: black;
    border: 1px solid #CCCCCC;
    padding: 4px;
    font-weight: bold;
}
"""

SEARCH_FIELD_STYLESHEET = """
QLineEdit {
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    padding: 4px 8px;
    background: white;
    color: black;
}
QLineEdit:focus {
    border: 1px solid #2196F3;
}
"""


def apply_table_style(table) -> None:
    """Apply the shared table stylesheet to *table*."""
    table.setStyleSheet(TABLE_STYLESHEET)


def apply_search_style(widget) -> None:
    """Apply the shared search-field stylesheet to *widget*."""
    widget.setStyleSheet(SEARCH_FIELD_STYLESHEET)
