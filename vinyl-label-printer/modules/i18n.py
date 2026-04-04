"""
Internationalisation (i18n) module.

All user-visible strings are defined here, keyed first by language code (e.g.
"DE", "EN") and then by a semantic key.  No string literals should appear in
any other module or UI file — always call t("key") or t("key", **kwargs).

Adding a new language
---------------------
1. Add a new top-level entry to _STRINGS with the ISO 639-1 code as the key.
2. Translate all keys from the "DE" block.
3. The new code will automatically appear in the language selector.
"""

_STRINGS: dict[str, dict[str, str]] = {
    "DE": {
        # Window / application
        "app_title":         "Vinyl-Label-Drucker",

        # Group boxes
        "group_queue":       "Druckwarteschlange",
        "group_start":       "Startposition",

        # Buttons
        "btn_open_db":       "Datei öffnen …",
        "btn_reload":        "Neu laden",
        "btn_watermark":     "Wasserzeichen …",
        "btn_watermark_clear": "Entfernen",
        "btn_generate":      "PDF erstellen",
        "btn_print":         "Drucken",
        "btn_prev":          "← Zurück",
        "btn_next":          "Weiter →",

        # Language selector
        "language_label":    "Sprache:",

        # Preview
        "page_indicator":    "Seite {current} von {total}",
        "no_preview":        "Kein PDF geladen.",

        # Status bar messages
        "status_loaded":     "{n} Etiketten in der Warteschlange",
        "status_no_records": "Keine Datensätze in der Warteschlange.",
        "status_pdf_ready":  "PDF erstellt – bereit zum Drucken.",
        "status_printing":   "Druckauftrag gesendet.",

        # Error messages
        "err_no_pdf":        "Kein PDF vorhanden. Bitte zuerst PDF erstellen.",
        "err_poppler":       (
            "Poppler wurde nicht gefunden.\n"
            "Bitte installieren:\n"
            "  Linux:   sudo apt install poppler-utils\n"
            "  Windows: poppler-DLLs in PATH eintragen"
        ),
        "err_excel":         "Excel-Datei konnte nicht geladen werden:\n{detail}",
        "err_print":         "Druckfehler:\n{detail}",

        # Tooltips
        "tooltip_grid":      (
            "Klicken Sie auf eine Zelle,\num die Startposition zu wählen."
        ),
        "tooltip_open_db":   "Excel-Datei (database.xlsx) auswählen",
        "tooltip_reload":    "Druckwarteschlange aus der Excel-Datei neu einlesen",
        "tooltip_watermark": "PNG- oder JPG-Bild als Wasserzeichen auswählen",
        "tooltip_watermark_clear": "Wasserzeichen entfernen",

        # File dialog
        "dlg_open_db_title": "Datenbankdatei öffnen",
        "dlg_open_db_filter":"Excel-Dateien (*.xlsx *.xls);;Alle Dateien (*)",
        "status_db_loaded":  "Datei geladen: {path}",
        "status_reloaded":   "Neu geladen: {n} Etiketten in der Warteschlange.",
        "status_watermark_set": "Wasserzeichen: {name}",
        "status_watermark_cleared": "Wasserzeichen entfernt.",

        # Watermark group
        "group_watermark":   "Wasserzeichen",
        "lbl_watermark_none":"(kein Wasserzeichen)",
        "dlg_watermark_title":"Wasserzeichen-Bild auswählen",
        "dlg_watermark_filter":"Bilder (*.png *.jpg *.jpeg);;Alle Dateien (*)",
        "err_watermark_missing":
            "Wasserzeichen-Datei nicht gefunden:\n{path}\n\n"
            "Bitte eine neue Datei auswählen oder das Wasserzeichen entfernen.",
    },

    "EN": {
        # Window / application
        "app_title":         "Vinyl Label Printer",

        # Group boxes
        "group_queue":       "Print Queue",
        "group_start":       "Start Position",

        # Buttons
        "btn_open_db":       "Open file …",
        "btn_reload":        "Reload",
        "btn_watermark":     "Watermark …",
        "btn_watermark_clear": "Remove",
        "btn_generate":      "Generate PDF",
        "btn_print":         "Print",
        "btn_prev":          "← Back",
        "btn_next":          "Next →",

        # Language selector
        "language_label":    "Language:",

        # Preview
        "page_indicator":    "Page {current} of {total}",
        "no_preview":        "No PDF loaded.",

        # Status bar messages
        "status_loaded":     "{n} labels in queue",
        "status_no_records": "No records in print queue.",
        "status_pdf_ready":  "PDF generated – ready to print.",
        "status_printing":   "Print job sent.",

        # Error messages
        "err_no_pdf":        "No PDF available. Please generate PDF first.",
        "err_poppler":       (
            "Poppler was not found.\n"
            "Please install it:\n"
            "  Linux:   sudo apt install poppler-utils\n"
            "  Windows: add poppler DLLs folder to PATH"
        ),
        "err_excel":         "Could not load Excel file:\n{detail}",
        "err_print":         "Print error:\n{detail}",

        # Tooltips
        "tooltip_grid":      "Click a cell to set the start position.",
        "tooltip_open_db":   "Select the Excel database file (database.xlsx)",
        "tooltip_reload":    "Re-read the print queue from the Excel file",
        "tooltip_watermark": "Select a PNG or JPG image to use as watermark",
        "tooltip_watermark_clear": "Remove the watermark",

        # File dialog
        "dlg_open_db_title": "Open database file",
        "dlg_open_db_filter":"Excel files (*.xlsx *.xls);;All files (*)",
        "status_db_loaded":  "File loaded: {path}",
        "status_reloaded":   "Reloaded: {n} labels in queue.",
        "status_watermark_set": "Watermark: {name}",
        "status_watermark_cleared": "Watermark removed.",

        # Watermark group
        "group_watermark":   "Watermark",
        "lbl_watermark_none":"(no watermark)",
        "dlg_watermark_title":"Select watermark image",
        "dlg_watermark_filter":"Images (*.png *.jpg *.jpeg);;All files (*)",
        "err_watermark_missing":
            "Watermark file not found:\n{path}\n\n"
            "Please select a new file or remove the watermark.",
    },
}

# ── Public API ────────────────────────────────────────────────────────────────

AVAILABLE_LANGUAGES: list[str] = list(_STRINGS.keys())

_current_lang: str = "DE"


def set_language(code: str) -> None:
    """Switch the active language.

    Args:
        code: One of the keys in AVAILABLE_LANGUAGES (e.g. "DE", "EN").

    Raises:
        KeyError: If *code* is not a known language.
    """
    global _current_lang
    if code not in _STRINGS:
        raise KeyError(f"Unknown language code: {code!r}. "
                       f"Available: {AVAILABLE_LANGUAGES}")
    _current_lang = code


def get_language() -> str:
    """Return the currently active language code."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Look up *key* in the active language and format with *kwargs*.

    Falls back to the "DE" translation if the key is missing in the current
    language, and to the raw key string if it is missing everywhere (so the
    UI never crashes on a missing translation).

    Examples::

        t("btn_print")                       # → "Drucken"
        t("status_loaded", n=5)              # → "5 Etiketten in der Warteschlange"
        t("page_indicator", current=1, total=3)
    """
    lang_dict = _STRINGS.get(_current_lang, {})
    text = lang_dict.get(key) or _STRINGS.get("DE", {}).get(key) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass  # return unformatted string rather than crash
    return text
