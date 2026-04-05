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

        # Discogs button in main window
        "btn_discogs":           "Aus Discogs laden",
        "tooltip_discogs":       "7\" Singles aus der Discogs-Sammlung importieren",
        "status_discogs_done":   "Discogs-Import abgeschlossen.",

        # Discogs dialog — window title
        "dlg_discogs_title":     "Aus Discogs laden",

        # Setup panel
        "discogs_setup_heading": "Discogs Token einrichten",
        "discogs_setup_info":    (
            "Erstelle unter <a href='https://www.discogs.com/settings/developers'>"
            "discogs.com/settings/developers</a> einen persönlichen Token "
            "und trage ihn hier ein. Der Token wird ausschließlich lokal in "
            "<tt>config/credentials.json</tt> gespeichert und verlässt deinen "
            "Rechner nicht."
        ),
        "discogs_group_creds":   "Zugangsdaten",
        "discogs_lbl_username":  "Discogs Benutzername:",
        "discogs_lbl_token":     "Persönlicher Token:",
        "discogs_ph_username":   "dein_benutzername",
        "discogs_ph_token":      "••••••••••••••••••••",
        "discogs_btn_verify":    "Token prüfen und speichern",
        "discogs_enter_fields":  "Bitte Benutzername und Token eintragen.",
        "discogs_verifying":     "Prüfe Token…",
        "discogs_err_token":     "Token ungültig – bitte prüfen.",
        "discogs_err_network":   "Keine Verbindung zu Discogs.",

        # Collection panel
        "discogs_logged_in":     "Angemeldet als: <b>{username}</b>",
        "discogs_btn_logout":    "Abmelden",
        "discogs_btn_fetch":     "7\" Singles laden",
        "discogs_connecting":    "Verbinde…",
        "discogs_progress":      "Lade Seite {current} von {total}…",
        "discogs_found":         "{n} Singles gefunden.",
        "discogs_cached":        "{n} Singles (zwischengespeichert)",
        "discogs_search_lbl":    "Suche:",
        "discogs_search_ph":     "Nach Interpret oder Titel filtern…",
        "discogs_col_title":     "Titel",
        "discogs_col_artist":    "Interpret",
        "discogs_col_label":     "Label",
        "discogs_col_year":      "Jahr",
        "discogs_btn_all":       "Alle auswählen",
        "discogs_btn_none":      "Auswahl aufheben",
        "discogs_btn_import":    "In Druckwarteschlange übernehmen",
        "discogs_btn_cancel":    "Abbrechen",

        # Collection panel — messages
        "discogs_no_results_title": "Keine Ergebnisse",
        "discogs_no_results_msg":   "Keine 7\" Singles in deiner Sammlung gefunden.",
        "discogs_token_expired_title": "Token abgelaufen",
        "discogs_token_expired_msg":   "Token abgelaufen. Bitte neu einrichten.",
        "discogs_rate_limit":    "Rate Limit – warte {n}s…",
        "discogs_no_sel_title":  "Keine Auswahl",
        "discogs_no_sel_msg":    "Bitte mindestens einen Eintrag auswählen.",
        "discogs_write_err_title": "Fehler beim Schreiben",
        "discogs_write_err_msg": "Die Druckwarteschlange konnte nicht gespeichert werden:\n{detail}",
        "discogs_imported_title":"Importiert",
        "discogs_imported_msg":  "{n} Singles in Druckwarteschlange übernommen.",
        "discogs_err_title":     "Fehler",

        # Tracklist fetch progress / errors
        "discogs_tracklist_progress":  "Lade Tracklist {n} von {total}…",
        "discogs_tracklist_warn_title": "Hinweis",
        "discogs_tracklist_warn_msg":  (
            "Für {n} Release(s) konnte keine Trackliste geladen werden. "
            "Die Seite wurde leer gelassen."
        ),

        # Review dialog — window titles
        "review_title":          "Druckwarteschlange prüfen – {n} Einträge",
        "review_title_warning":  "Druckwarteschlange prüfen – {n} Einträge ⚠️ Prüfung erforderlich",
        "review_title_ok":       "Druckwarteschlange prüfen – {n} Einträge ✓ Bereit zum Drucken",

        # Review dialog — info banner
        "review_banner_line1":   "Bitte prüfe die übernommenen Daten vor dem Druck.",
        "review_banner_line2":   "Klicke in eine Zelle, um sie zu bearbeiten. Einträge mit roter Markierung erfordern deine Aufmerksamkeit.",

        # Review dialog — column headers (editable cols get ✎ appended in code)
        "review_col_title":     "Titel",
        "review_col_artist":    "Interpret",
        "review_col_label":     "Label",
        "review_col_country":   "Country",
        "review_col_year":      "Jahr",
        "review_col_side":      "Seite",
        "review_col_edit_tip":  "Doppelklick oder F2 zum Bearbeiten",

        # Review dialog — toolbar
        "review_btn_all":       "Alle auswählen",
        "review_btn_none":      "Auswahl aufheben",
        "review_btn_delete_sel":"Ausgewählte Zeilen löschen",
        "review_btn_add_row":   "Zeile hinzufügen",
        "review_search_ph":     "Titel oder Interpret suchen…",

        # Review dialog — context menu
        "review_ctx_delete":    "Zeile löschen",
        "review_ctx_duplicate": "Zeile duplizieren",

        # Review dialog — status bar
        "review_status_counts": "{n} Einträge gesamt | {m} ausgewählt zum Drucken",
        "review_status_warning":"⚠️  {k} Einträge haben leere Pflichtfelder",
        "review_status_ok":     "✓ Alle Einträge vollständig",

        # Review dialog — cell tooltip
        "review_cell_required_tip": "Pflichtfeld – bitte ausfüllen",

        # Review dialog — bottom buttons
        "review_btn_cancel":    "Abbrechen",
        "review_btn_confirm":   "Weiter zum Drucken →",
        "review_btn_confirm_tip": "Überträgt die markierten Einträge in die Druckwarteschlange",

        # Review dialog — validation messages
        "review_warn_title":    "Unvollständige Einträge",
        "review_warn_msg":      "{k} Einträge haben leere Felder (markiert in Rot).\nMöchtest du trotzdem fortfahren?",
        "review_warn_continue": "Fortfahren",
        "review_warn_back":     "Zurück zur Liste",
        "review_no_sel_msg":    "Keine Zeilen ausgewählt.",
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

        # Discogs button in main window
        "btn_discogs":           "Load from Discogs",
        "tooltip_discogs":       "Import 7\" singles from your Discogs collection",
        "status_discogs_done":   "Discogs import complete.",

        # Discogs dialog — window title
        "dlg_discogs_title":     "Load from Discogs",

        # Setup panel
        "discogs_setup_heading": "Set up Discogs Token",
        "discogs_setup_info":    (
            "Create a personal token at "
            "<a href='https://www.discogs.com/settings/developers'>"
            "discogs.com/settings/developers</a> and enter it below. "
            "The token is stored locally in "
            "<tt>config/credentials.json</tt> only and never leaves your machine."
        ),
        "discogs_group_creds":   "Credentials",
        "discogs_lbl_username":  "Discogs Username:",
        "discogs_lbl_token":     "Personal Token:",
        "discogs_ph_username":   "your_username",
        "discogs_ph_token":      "••••••••••••••••••••",
        "discogs_btn_verify":    "Verify and save token",
        "discogs_enter_fields":  "Please enter username and token.",
        "discogs_verifying":     "Verifying token…",
        "discogs_err_token":     "Token invalid – please check.",
        "discogs_err_network":   "No connection to Discogs.",

        # Collection panel
        "discogs_logged_in":     "Logged in as: <b>{username}</b>",
        "discogs_btn_logout":    "Log out",
        "discogs_btn_fetch":     "Load 7\" Singles",
        "discogs_connecting":    "Connecting…",
        "discogs_progress":      "Loading page {current} of {total}…",
        "discogs_found":         "{n} singles found.",
        "discogs_cached":        "{n} singles (cached)",
        "discogs_search_lbl":    "Search:",
        "discogs_search_ph":     "Filter by artist or title…",
        "discogs_col_title":     "Title",
        "discogs_col_artist":    "Artist",
        "discogs_col_label":     "Label",
        "discogs_col_year":      "Year",
        "discogs_btn_all":       "Select all",
        "discogs_btn_none":      "Deselect all",
        "discogs_btn_import":    "Add to print queue",
        "discogs_btn_cancel":    "Cancel",

        # Collection panel — messages
        "discogs_no_results_title": "No results",
        "discogs_no_results_msg":   "No 7\" singles found in your collection.",
        "discogs_token_expired_title": "Token expired",
        "discogs_token_expired_msg":   "Token expired. Please set it up again.",
        "discogs_rate_limit":    "Rate limit – waiting {n}s…",
        "discogs_no_sel_title":  "No selection",
        "discogs_no_sel_msg":    "Please select at least one entry.",
        "discogs_write_err_title": "Write error",
        "discogs_write_err_msg": "Could not save print queue:\n{detail}",
        "discogs_imported_title":"Imported",
        "discogs_imported_msg":  "{n} singles added to print queue.",
        "discogs_err_title":     "Error",

        # Tracklist fetch progress / errors
        "discogs_tracklist_progress":  "Loading tracklist {n} of {total}…",
        "discogs_tracklist_warn_title": "Note",
        "discogs_tracklist_warn_msg":  (
            "Could not load tracklist for {n} release(s). Side left blank."
        ),

        # Review dialog — window titles
        "review_title":          "Review print queue – {n} entries",
        "review_title_warning":  "Review print queue – {n} entries ⚠️ Review required",
        "review_title_ok":       "Review print queue – {n} entries ✓ Ready to print",

        # Review dialog — info banner
        "review_banner_line1":   "Please review the imported data before printing.",
        "review_banner_line2":   "Click a cell to edit it. Entries with red marking require your attention.",

        # Review dialog — column headers (editable cols get ✎ appended in code)
        "review_col_title":     "Title",
        "review_col_artist":    "Artist",
        "review_col_label":     "Label",
        "review_col_country":   "Country",
        "review_col_year":      "Year",
        "review_col_side":      "Side",
        "review_col_edit_tip":  "Double-click or F2 to edit",

        # Review dialog — toolbar
        "review_btn_all":       "Select all",
        "review_btn_none":      "Deselect all",
        "review_btn_delete_sel":"Delete selected rows",
        "review_btn_add_row":   "Add row",
        "review_search_ph":     "Search title or artist…",

        # Review dialog — context menu
        "review_ctx_delete":    "Delete row",
        "review_ctx_duplicate": "Duplicate row",

        # Review dialog — status bar
        "review_status_counts": "{n} entries total | {m} selected for printing",
        "review_status_warning":"⚠️  {k} entries have empty required fields",
        "review_status_ok":     "✓ All entries complete",

        # Review dialog — cell tooltip
        "review_cell_required_tip": "Required field – please fill in",

        # Review dialog — bottom buttons
        "review_btn_cancel":    "Cancel",
        "review_btn_confirm":   "Continue to print →",
        "review_btn_confirm_tip": "Transfers the checked entries to the print queue",

        # Review dialog — validation messages
        "review_warn_title":    "Incomplete entries",
        "review_warn_msg":      "{k} entries have empty fields (marked in red).\nContinue anyway?",
        "review_warn_continue": "Continue",
        "review_warn_back":     "Back to list",
        "review_no_sel_msg":    "No rows selected.",
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
