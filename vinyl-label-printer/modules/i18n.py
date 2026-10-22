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

        # Status bar messages
        "status_loaded":     "{n} Etiketten in der Warteschlange",
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
        "err_pdf":           "PDF konnte nicht erstellt werden:\n{detail}",
        "err_queue_load":    "Die Druckwarteschlange konnte nicht geladen werden:\n{detail}",
        "err_print":         "Druckfehler:\n{detail}",

        # Tooltips
        "tooltip_grid":      (
            "Klicken Sie auf eine Zelle,\num die Startposition zu wählen."
        ),
        "tooltip_watermark": "PNG- oder JPG-Bild als Wasserzeichen auswählen",
        "tooltip_watermark_clear": "Wasserzeichen entfernen",

        # File dialog
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

        # Generic buttons
        "btn_cancel_generic":    "Abbrechen",

        # Data source toggle
        "datasource_group":          "Datenquelle",
        "datasource_local":          "\U0001f5c4 Lokale Datenbank",
        "datasource_discogs":        "\U0001f310 Discogs",
        "datasource_no_creds_title": "Discogs nicht eingerichtet",
        "datasource_no_creds_msg":   (
            "Bitte zuerst einen Discogs-Token einrichten, "
            "bevor du zu Discogs wechselst."
        ),
        "datasource_no_creds_btn":       "Jetzt einrichten",
        "datasource_overwrite_title":    "Lokale Daten überschreiben?",
        "datasource_overwrite_msg":      (
            "Die lokale Druckwarteschlange enthält {n} Einträge. "
            "Bei einer Übernahme aus Discogs wirst du gefragt, ob die neuen "
            "Einträge angehängt werden oder die Warteschlange ersetzen sollen. "
            "Möchtest du fortfahren?"
        ),
        "datasource_overwrite_continue": "Fortfahren",
        "datasource_switch_local_title": "Zu lokaler Datenbank wechseln",
        "datasource_switch_local_msg":   (
            "Du wechselst zur lokalen Datenbank. "
            "Die Druckwarteschlange bleibt erhalten. „Daten laden“ öffnet deine "
            "lokale Plattensammlung, „Warteschlange“ bearbeitet die "
            "Druckwarteschlange – einzeln oder per CSV-Import."
        ),
        "datasource_discogs_hint":       (
            "\u2139 Änderungen an der Druckwarteschlange werden in die "
            "lokale Datenbank geschrieben und beim nächsten Start geladen."
        ),
        "tooltip_discogs_disabled":      (
            "Wechsle zu Discogs als Datenquelle, um diese Funktion zu nutzen"
        ),
        "status_mode_local":         "\U0001f5c4 Lokale Datenbank | {n} Einträge",
        "status_mode_local_empty":   "\U0001f5c4 Lokale Datenbank | Keine Einträge",
        "status_mode_discogs":       (
            "\U0001f310 Discogs | Angemeldet als {username} | {n} Einträge"
        ),
        "status_mode_discogs_empty": (
            "\U0001f310 Discogs | Angemeldet als {username} | Keine Einträge"
        ),

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
        "discogs_search_ph":     "Nach Interpret, Titel oder Kat.-Nr. filtern…",
        "discogs_col_title":     "Titel",
        "discogs_col_artist":    "Interpret",
        "discogs_col_label":     "Label",
        "discogs_col_catno":     "Kat.-Nr.",
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

        # Cache status / attribution
        "discogs_attribution_label":   "Rechtlicher Hinweis / Legal notice",
        "cache_last_pull":             "Letzter Discogs-Pull: {datetime} (vor {hours} Stunden)",
        "cache_expired":               "⚠ Cache veraltet (vor {hours} Stunden) — bitte neu laden.",
        "cache_no_data":               "Noch keine Sammlung geladen.",
        "cache_migrating":             "Cache wird aktualisiert (neue Sortierung) …",
        "cache_reload":                "Aktualisieren",
        "cache_load_now":              "Jetzt laden",
        "cache_singles_count":         "{total} Singles · {count} × 7\"",
        "cache_summary":               "Gesamt-Sammlung: {total} · davon 7\": {count}",
        "cache_sync_report":           "✓ Synchronisiert: +{added} neu, ~{updated} aktualisiert, -{removed} entfernt",
        "dialog_title_with_count":     "Aus Discogs laden — {count} × 7\" Singles",
        "cache_expired_reason":        (
            "ℹ Gemäss Discogs API-Nutzungsbedingungen dürfen Daten nicht länger als "
            "6 Stunden ohne Aktualisierung angezeigt werden."
        ),
        "discogs_cache_notice":        (
            "Diese Anwendung cached Discogs-Daten lokal für maximal 6 Stunden gemäss "
            "den API-Nutzungsbedingungen. Nach Ablauf ist ein erneuter Datenabruf erforderlich."
        ),

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
        "review_banner_queue_line1": "Hier bearbeitest du die Druckwarteschlange. Änderungen werden erst mit „Speichern“ übernommen.",
        "review_banner_queue_line2": (
            "Neue Einträge über „Eintrag hinzufügen“ oder per CSV-Import. "
            "Gespeichert werden nur markierte Einträge; Einträge mit roter "
            "Markierung erfordern deine Aufmerksamkeit."
        ),

        # Review dialog — column headers (editable cols get ✎ appended in code)
        "review_col_title":     "Titel",
        "review_col_artist":    "Interpret",
        "review_col_label":     "Label",
        "review_col_catno":     "Kat.-Nr.",
        "review_col_country":   "Country",
        "review_col_year":      "Jahr",
        "review_col_side":      "Seite",
        "review_col_edit_tip":  "Doppelklick oder F2 zum Bearbeiten",

        # Review dialog — toolbar
        "review_btn_all":       "Alle auswählen",
        "review_btn_none":      "Auswahl aufheben",
        "review_btn_delete_sel":"Ausgewählte Zeilen löschen",
        "review_btn_add_row":   "Zeile hinzufügen",
        "review_btn_add_entry": "Eintrag hinzufügen …",
        "review_btn_add_entry_tip": "Formular für eine Platte: Titel für Seite A und / oder B",
        "review_btn_import_csv": "CSV importieren …",
        "review_btn_import_csv_tip": "Einträge aus einer CSV-Datei übernehmen (anhängen oder ersetzen)",
        "review_btn_export_csv": "CSV exportieren …",
        "review_btn_export_csv_tip": (
            "Alle Zeilen der Tabelle als CSV speichern – zum Sichern oder "
            "zum Bearbeiten in einer Tabellenkalkulation"
        ),
        "review_search_ph":     "Titel oder Interpret suchen…",
        "review_drag_blocked_tip": "Zum Verschieben die Suche leeren",

        # Review dialog — context menu
        "review_ctx_delete":    "Zeile löschen",
        "review_ctx_duplicate": "Zeile duplizieren",

        # Review dialog — status bar
        "review_status_counts": "{n} Einträge gesamt | {m} ausgewählt zum Drucken",
        "review_status_hidden": "{h} davon ausgeblendet",
        "review_status_warning":"⚠️  {k} Einträge haben leere Pflichtfelder",
        "review_status_ok":     "✓ Alle Einträge vollständig",

        # Review dialog — cell tooltip
        "review_cell_required_tip": "Pflichtfeld – bitte ausfüllen",

        # Review dialog — bottom buttons
        "review_btn_cancel":    "Abbrechen",
        "review_btn_confirm":   "Weiter zum Drucken →",
        "review_btn_confirm_tip": "Überträgt die markierten Einträge in die Druckwarteschlange",
        "review_btn_save":      "Speichern",
        "review_btn_save_tip":  (
            "Speichert die markierten Einträge als Druckwarteschlange; "
            "nicht markierte Einträge werden entfernt"
        ),

        # Review dialog — validation messages
        "review_warn_title":    "Unvollständige Einträge",
        "review_warn_msg":      (
            "{k} Einträge haben leere Pflichtfelder (markiert in Rot).\n"
            "Einträge ohne Titel werden nicht gespeichert, eine leere Seite wird "
            "als Seite A gespeichert.\nMöchtest du trotzdem fortfahren?"
        ),
        "review_warn_continue": "Fortfahren",
        "review_warn_back":     "Zurück zur Liste",
        "review_queue_exists_title": "Druckwarteschlange nicht leer",
        "review_queue_exists_msg":   "Die Druckwarteschlange enthält bereits {n} Einträge.\n"
                                     "Neue Einträge anhängen oder die Warteschlange ersetzen?",
        "review_queue_append":       "Anhängen",
        "review_queue_replace":      "Ersetzen",
        "review_queue_cancel":       "Abbrechen",
        "review_no_sel_msg":    "Keine Zeilen ausgewählt.",
        "review_clear_title":   "Druckwarteschlange leeren?",
        "review_clear_msg":     (
            "Es ist kein Eintrag markiert. Beim Speichern wird die "
            "Druckwarteschlange geleert – {n} Einträge werden gelöscht."
        ),
        "review_clear_confirm": "Warteschlange leeren",
        "review_unsaved_title": "Ungespeicherte Änderungen",
        "review_unsaved_msg":   "Die Druckwarteschlange hat ungespeicherte Änderungen. Speichern?",
        "review_unsaved_save":  "Speichern",
        "review_unsaved_discard": "Verwerfen",
        "review_unsaved_cancel": "Abbrechen",

        # CSV import / export
        "csv_filter":           "CSV-Dateien (*.csv *.txt);;Alle Dateien (*)",
        "csv_import_title":     "CSV importieren",
        "csv_import_done":      "{n} Einträge importiert, {k} übersprungen (ohne Titel).",
        "csv_import_none":      "Die Datei enthält keine Einträge mit Titel ({k} übersprungen).",
        "csv_err_empty":        "Die Datei ist leer. Die erste Zeile muss eine Kopfzeile sein.",
        "csv_err_no_title":     (
            "Keine Titel-Spalte gefunden. Die erste Zeile muss eine Kopfzeile sein, "
            "z. B.:\nTitle;Artist;Label;Country;Year;Side;CatNo\n"
            "Titel;Interpret;Label;Land;Jahr;Seite;Katalognummer\n\n"
            "Gefundene Spalten: {columns}"
        ),
        "csv_err_read":         "Die CSV-Datei konnte nicht gelesen werden:\n{detail}",
        "csv_export_title":     "CSV exportieren",
        "csv_export_done":      "{n} Einträge exportiert:\n{path}",
        "csv_export_err":       "Die CSV-Datei konnte nicht geschrieben werden:\n{detail}",

        # Add entry form
        "entry_title":          "Eintrag hinzufügen",
        "entry_lbl_artist":     "Interpret",
        "entry_lbl_label":      "Label",
        "entry_lbl_country":    "Land",
        "entry_lbl_year":       "Jahr",
        "entry_ph_year":        "z. B. 1969",
        "entry_lbl_catno":      "Katalognummer",
        "entry_lbl_title_a":    "Titel Seite A",
        "entry_lbl_title_b":    "Titel Seite B",
        "entry_hint":           (
            "Pro ausgefülltem Titel entsteht ein Label (Seite A / B) mit den "
            "gemeinsamen Angaben. Gespeichert wird erst mit „Speichern“ in der "
            "Warteschlange."
        ),
        "entry_btn_add":        "Hinzufügen",
        "entry_btn_add_next":   "Hinzufügen und nächster",
        "entry_btn_close":      "Schließen",
        "entry_err_no_title":   "Bitte mindestens einen Titel eingeben (Seite A oder B).",
        "entry_err_year":       "Jahr: leer lassen oder vierstellig eingeben (z. B. 1969).",
        "entry_added":          "{n} Zeile(n) zur Tabelle hinzugefügt.",

        # Add entry form — local collection (LOCAL mode)
        "entry_save_to_collection": "Auch in Sammlung speichern",
        "entry_save_to_collection_tip": (
            "Legt beim Speichern der Warteschlange eine Platte in der lokalen "
            "Sammlung an und verknüpft die Einträge mit ihr"
        ),
        "review_csv_collection_tip": (
            "CSV-Import: Beim Speichern der Warteschlange werden die importierten "
            "Zeilen als Platten in die lokale Sammlung übernommen (Seite A und "
            "direkt folgende Seite B mit gleichen Angaben = eine Platte)"
        ),
        "csv_import_collection": "Beim Speichern werden {r} Platte(n) in der Sammlung angelegt.",

        # Record form (collection)
        "record_title_new":     "Neue Platte",
        "record_title_edit":    "Platte bearbeiten",
        "record_hint":          (
            "Interpret, Label, Land, Jahr und Katalognummer gelten für beide "
            "Seiten. Mindestens ein Titel ist nötig."
        ),
        "record_btn_save":      "Speichern",
        "record_btn_cancel":    "Abbrechen",

        # Collection dialog
        "collection_title":         "Sammlung",
        "collection_btn_new":       "Neue Platte …",
        "collection_btn_edit":      "Bearbeiten …",
        "collection_btn_edit_tip":  "Markierte Platte bearbeiten (auch per Doppelklick)",
        "collection_btn_delete":    "Löschen",
        "collection_search_ph":     "Interpret, Titel, Label, Jahr … suchen",
        "collection_btn_all":       "Alle Seiten auswählen",
        "collection_btn_all_tip":   "Alle Seiten mit Titel der sichtbaren Platten auswählen",
        "collection_btn_none":      "Auswahl aufheben",
        "collection_col_a":         "A",
        "collection_col_b":         "B",
        "collection_col_artist":    "Interpret",
        "collection_col_title_a":   "Titel A",
        "collection_col_title_b":   "Titel B",
        "collection_col_label":     "Label",
        "collection_col_year":      "Jahr",
        "collection_col_catno":     "Kat.-Nr.",
        "collection_col_country":   "Land",
        "collection_col_side_tip":  "Seite für die Druckwarteschlange auswählen",
        "collection_side_tip":      "Seite {side} drucken",
        "collection_side_no_title": "Seite {side} hat keinen Titel",
        "collection_empty":         (
            "Die Sammlung ist noch leer.\nLege deine erste Platte an – oder "
            "speichere Einträge der Warteschlange mit „Auch in Sammlung speichern“."
        ),
        "collection_status":        "{n} Platte(n) | {m} Seite(n) ausgewählt",
        "collection_btn_close":     "Schließen",
        "collection_btn_to_queue":  "In Druckwarteschlange übernehmen →",
        "collection_btn_to_queue_tip": (
            "Erzeugt einen Eintrag pro ausgewählter Seite und öffnet die Prüfung "
            "(anhängen oder ersetzen)"
        ),
        "collection_delete_title":  "Platten löschen?",
        "collection_delete_one":    "„{name}“ aus der Sammlung löschen?",
        "collection_delete_many":   "{n} Platten aus der Sammlung löschen?",
        "collection_delete_queue_note": (
            "Einträge in der Druckwarteschlange bleiben erhalten, sie verlieren "
            "nur die Verknüpfung zur Platte."
        ),
        "collection_delete_confirm": "Löschen",
        "collection_load_err":      "Die Sammlung konnte nicht geladen werden:\n{detail}",
        "collection_write_err":     "Die Sammlung konnte nicht gespeichert werden:\n{detail}",
        "collection_col_printed_a": "Gedruckt A",
        "collection_col_printed_b": "Gedruckt B",
        "collection_col_printed_tip": "Wann die Seite zuletzt gedruckt wurde (leer = noch nie)",
        "collection_btn_mark_printed":   "Als gedruckt markieren",
        "collection_btn_mark_printed_tip": (
            "Setzt für jede Seite mit Titel der markierten Platten das heutige Datum"
        ),
        "collection_btn_mark_unprinted": "Als nicht gedruckt markieren",
        "collection_btn_mark_unprinted_tip": (
            "Entfernt das Druckdatum beider Seiten der markierten Platten"
        ),
        "collection_chk_unprinted":      "Nur nicht gedruckte",
        "collection_chk_unprinted_tip":  (
            "Nur Platten mit mindestens einer Seite mit Titel, die noch nie gedruckt wurde"
        ),
        "collection_btn_all_unprinted":  "Alle ungedruckten Seiten auswählen",
        "collection_btn_all_unprinted_tip": (
            "Alle noch nie gedruckten Seiten mit Titel der sichtbaren Platten auswählen"
        ),
        "collection_btn_import_csv":     "CSV importieren …",
        "collection_btn_import_csv_tip": (
            "Platten aus einer CSV-Datei übernehmen (eine Zeile pro Platte)"
        ),
        "collection_btn_export_csv":     "CSV exportieren …",
        "collection_btn_export_csv_tip": (
            "Alle Platten der Sammlung als CSV-Datei speichern (unabhängig vom Filter)"
        ),
        "collection_csv_err_no_title":   (
            "Keine Titel-Spalte gefunden. Die erste Zeile muss eine Kopfzeile sein, "
            "z. B.:\nArtist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB\n"
            "Künstler;Label;Land;Jahr;Katalognummer;Titel A;Titel B;Gedruckt A;Gedruckt B"
            "\n\nGefundene Spalten: {columns}"
        ),
        "collection_csv_none":           (
            "Die Datei enthält keine Platten mit Titel ({k} übersprungen)."
        ),
        "collection_csv_dup_title":      "Doppelte Platten",
        "collection_csv_dup_msg":        (
            "{n} Zeile(n) der Datei entsprechen Platten, die schon in der Sammlung "
            "oder weiter oben in der Datei stehen (gleicher Interpret und gleiche "
            "Katalognummer, ohne Katalognummer gleicher Interpret und gleiche Titel)."
        ),
        "collection_csv_dup_skip":       "Überspringen",
        "collection_csv_dup_update":     "Vorhandene aktualisieren",
        "collection_csv_import_done":    (
            "{i} Platte(n) importiert, {u} aktualisiert, {s} übersprungen."
        ),
        "collection_csv_import_unchanged": "{c} Platte(n) waren bereits aktuell.",
        "collection_csv_export_done":    "{n} Platte(n) exportiert:\n{path}",
        "collection_sync_queue_title":   "Druckwarteschlange aktualisieren?",
        "collection_sync_queue_msg":     (
            "Auch die {n} Einträge in der Druckwarteschlange aktualisieren?"
        ),

        # Printed marking / sync between queue and collection
        "btn_yes":                  "Ja",
        "btn_no":                   "Nein",
        "printed_ask_title":        "Als gedruckt markieren?",
        "printed_ask_msg":          "Die {n} Etiketten aus der Sammlung als gedruckt markieren?",
        "printed_mark_err":         "Das Druckdatum konnte nicht gespeichert werden:\n{detail}",
        "review_sync_title":        "Sammlung aktualisieren?",
        "review_sync_msg":          (
            "{n} geänderte Einträge gehören zu Platten in der Sammlung. "
            "Änderungen auch in der Sammlung übernehmen?"
        ),
        "review_sync_collection":   "Sammlung aktualisieren",
        "review_sync_queue_only":   "Nur die Druckwarteschlange",
        "csv_import_collection_linked": (
            "{l} Zeile(n) werden mit vorhandenen Platten der Sammlung verknüpft."
        ),

        # Settings menu / theme / language
        "menu_settings":            "Einstellungen",
        "menu_appearance":          "Erscheinungsbild",
        "menu_language":            "Sprache",
        "theme_auto":               "Automatisch (Systemeinstellung)",
        "theme_light":              "Hell",
        "theme_dark":               "Dunkel",

        # Settings dialog tabs
        "settings_tab_datasource":  "Datenquelle",
        "settings_tab_discogs":     "Discogs-Konto",
        "settings_tab_updates":     "Updates",
        "settings_tab_about":       "Über die App",

        # Settings dialog — appearance tab
        "settings_theme_label":         "Theme",
        "settings_theme_auto_desc":     "Folgt dem Betriebssystem – aktuell {theme}",
        "settings_theme_dark_name":     "Dark Teal",
        "settings_theme_dark_desc":     "Dunkles Theme mit Teal-Akzent",
        "settings_theme_light_name":    "Light Teal",
        "settings_theme_light_desc":    "Helles Theme mit Teal-Akzent",
        "settings_lang_change_info":    "Sprachänderung wird sofort übernommen.",
        "watermark_section":            "WASSERZEICHEN",
        "watermark_active":             "Aktiv: {filename}",
        "watermark_none":               "Kein Wasserzeichen gesetzt",
        "watermark_select":             "Datei auswählen...",
        "watermark_clear":              "Entfernen",
        "debug_section":                "ENTWICKLER",
        "debug_logging_label":          "Debug-Logging",
        "debug_logging_subtitle":       "Detaillierte Logs in logs/app.log speichern",
        "debug_mode_active":            "⚠ Debug-Modus aktiv",

        # Settings dialog — data source tab
        "settings_active_mode":         "Aktiver Modus",
        "settings_mode_local_sub":      "in der App erfasst",
        "settings_mode_discogs_sub":    "Sammlung via Discogs API",
        "settings_mode_switch_warn":    (
            "Beim Wechsel des Modus werden vorhandene "
            "Warteschlangen-Daten überschrieben."
        ),
        "settings_data_folder":         "Datenordner",
        "settings_data_folder_info":    (
            "Hier liegt die Datenbank labels.db mit Ihrer Druckwarteschlange. "
            "Bearbeitet wird sie in der App (Warteschlange); für Massenänderungen "
            "und Sicherungen gibt es CSV-Import und -Export."
        ),
        "settings_open_folder":         "Ordner öffnen",
        "err_open_folder":              "Ordner konnte nicht geöffnet werden:\n{path}\n\n{detail}",

        # Settings dialog — Discogs account tab
        "settings_discogs_connected":   "Verbunden",
        "settings_discogs_logged_in_as":"Angemeldet als",
        "settings_discogs_show_token":  "Token anzeigen",
        "settings_discogs_hide_token":  "Token verbergen",
        "settings_discogs_change_token":"Token ändern",

        # Settings dialog — updates tab
        "settings_current_version":     "Aktuelle Version",
        "settings_check_updates":       "Auf Updates prüfen",
        "settings_updates_wip":         "Wird implementiert...",
        "settings_github_link":         "Projekt auf GitHub öffnen",

        # Settings dialog — about tab (version check + github section)
        "version_check":               "Versionsprüfung",
        "installed_version":           "Installierte Version",
        "available_version":           "Verfügbare Version (GitHub)",
        "not_yet_checked":             "—",
        "check_updates":               "Auf Updates prüfen",
        "will_be_implemented":         "Wird in einer zukünftigen Version implementiert.",
        "checking_version":            "Prüfe auf Updates…",
        "up_to_date":                  "✓ Du nutzt die aktuellste Version.",
        "newer_than_latest":           (
            "Sie nutzen eine neuere Version als die neueste stabile Version ({version})."
        ),
        "update_available":            "↑ Update verfügbar: {version}",
        "check_failed_network":        "Keine Verbindung zu GitHub.",
        "check_failed_error":          "Prüfung fehlgeschlagen.",
        "no_releases_yet":             "Noch kein Release auf GitHub verfügbar.",
        "release_notes":               "Release Notes anzeigen →",
        "update_hint_linux":           (
            "Laden Sie das neue .deb-Paket herunter und installieren Sie es."
        ),
        "update_hint_windows":         (
            "Laden Sie die neue Setup.exe herunter und führen Sie sie aus."
        ),
        "update_releases_link":        "Downloads auf GitHub (Releases)",
        "open_github":                 "Projekt auf GitHub öffnen →",
        "settings_license":             "Lizenz",
        "settings_author":              "Autor",

        # Discogs dialog — selection counter
        "selection_count":           "{count} ausgewählt",
        "selection_with_hidden":     "{total} ausgewählt ({visible} sichtbar)",

        # Sidebar / footer
        "sidebar_load_data":        "Daten laden",
        "sidebar_queue":            "Warteschlange",
        "sidebar_load_data_tip_local": (
            "Lokale Plattensammlung öffnen: Platten erfassen und ausgewählte "
            "Seiten in die Druckwarteschlange übernehmen"
        ),
        "sidebar_load_data_tip_discogs": "7\" Singles aus der Discogs-Sammlung importieren",
        "sidebar_queue_tip":        "Druckwarteschlange anzeigen und bearbeiten",
        "sidebar_labels_ready":     "Labels bereit",
        "sidebar_empty":            "Leer",
        "sidebar_start_pos":        "Startposition",
        "sidebar_create_pdf":       "PDF erstellen",
        "sidebar_status_ready":     "Bereit",
        "sidebar_status_generating":"Generiere...",
        "sidebar_status_created":   "Erstellt",
        "sidebar_not_connected":    "Nicht verbunden",
        "sidebar_local_mode":       "Lokal-Modus",
        "sidebar_discogs_mode":     "Discogs-Modus",
        "sidebar_local":            "Lokal",
        "sidebar_collection":       "Sammlung (lokal)",
        "sidebar_section_data":     "Daten",
        "sidebar_section_print":    "Druck",

        # Footer: collection status (LOCAL mode) and mode badge
        "footer_collection_status": "{n} Platten · {m} nicht gedruckt",
        "footer_collection_empty":  "Sammlung leer",
        "footer_mode_tip":          "Datenquelle in den Einstellungen wählen",

        # Preview placeholder
        "preview_hint_empty_local": "Wähle über „Daten laden“ Platten aus deiner Sammlung.",
        "preview_hint_empty_discogs": "Lade über „Daten laden“ Platten aus Discogs.",
        "preview_hint_no_pdf": (
            "{n} Etiketten in der Warteschlange – „PDF erstellen“ zeigt die Vorschau."
        ),

        # Keyboard shortcut tooltips
        "shortcut_search":          "Suchen",

        # Printer calibration (settings dialog)
        "print_calibration":            "DRUCKERKALIBRIERUNG",
        "calibration_x":                "Horizontal (X) in mm",
        "calibration_y":                "Vertikal (Y) in mm",
        "calibration_reset":            "Zurücksetzen",
        "generate_calibration_pdf":     "Kalibrierungs-PDF erstellen",
        "calibration_info": (
            "Falls die Labels leicht versetzt gedruckt werden, "
            "passe hier die Feinkorrektur an. Positiver Wert verschiebt nach rechts/unten."
        ),

        # Print hint dialog
        "print_hint_title":         "Druckeinstellungen",
        "print_hint_text": (
            "Bitte stelle sicher, dass im Druckdialog folgendes eingestellt ist:\n\n"
            "✓ Skalierung: 'Tatsächliche Größe' (100 %)\n"
            "✓ KEIN 'An Seite anpassen'\n"
            "✓ Seitenränder: Keine / Keine Anpassung\n\n"
            "Falsche Skalierung verschiebt alle Labels!"
        ),
        "dont_show_again":          "Nicht mehr anzeigen",
    },

    "EN": {
        # Window / application
        "app_title":         "Vinyl Label Printer",

        # Group boxes
        "group_queue":       "Print Queue",
        "group_start":       "Start Position",

        # Buttons
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

        # Status bar messages
        "status_loaded":     "{n} labels in queue",
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
        "err_pdf":           "Could not create PDF:\n{detail}",
        "err_queue_load":    "Could not load the print queue:\n{detail}",
        "err_print":         "Print error:\n{detail}",

        # Tooltips
        "tooltip_grid":      "Click a cell to set the start position.",
        "tooltip_watermark": "Select a PNG or JPG image to use as watermark",
        "tooltip_watermark_clear": "Remove the watermark",

        # File dialog
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

        # Generic buttons
        "btn_cancel_generic":    "Cancel",

        # Data source toggle
        "datasource_group":          "Data source",
        "datasource_local":          "\U0001f5c4 Local database",
        "datasource_discogs":        "\U0001f310 Discogs",
        "datasource_no_creds_title": "Discogs not configured",
        "datasource_no_creds_msg":   (
            "Please set up a Discogs token before switching to Discogs."
        ),
        "datasource_no_creds_btn":       "Set up now",
        "datasource_overwrite_title":    "Overwrite local data?",
        "datasource_overwrite_msg":      (
            "The local print queue contains {n} entries. "
            "When importing from Discogs you will be asked whether to append "
            "the new entries or replace the queue. "
            "Continue?"
        ),
        "datasource_overwrite_continue": "Continue",
        "datasource_switch_local_title": "Switch to local database",
        "datasource_switch_local_msg":   (
            "You are switching to the local database. "
            "The print queue is preserved. “Load data” opens your local record "
            "collection, “Queue” edits the print queue – entry by entry or by "
            "CSV import."
        ),
        "datasource_discogs_hint":       (
            "\u2139 Changes to the print queue are written to the local "
            "database and loaded on next start."
        ),
        "tooltip_discogs_disabled":      (
            "Switch to Discogs as data source to use this feature"
        ),
        "status_mode_local":         "\U0001f5c4 Local database | {n} entries",
        "status_mode_local_empty":   "\U0001f5c4 Local database | No entries",
        "status_mode_discogs":       (
            "\U0001f310 Discogs | Signed in as {username} | {n} entries"
        ),
        "status_mode_discogs_empty": (
            "\U0001f310 Discogs | Signed in as {username} | No entries"
        ),

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
        "discogs_search_ph":     "Filter by artist, title or cat. no.…",
        "discogs_col_title":     "Title",
        "discogs_col_artist":    "Artist",
        "discogs_col_label":     "Label",
        "discogs_col_catno":     "Cat. No.",
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

        # Cache status / attribution
        "discogs_attribution_label":   "Legal notice",
        "cache_last_pull":             "Last Discogs pull: {datetime} ({hours} hours ago)",
        "cache_expired":               "⚠ Cache expired ({hours} hours ago) — please reload.",
        "cache_no_data":               "No collection loaded yet.",
        "cache_migrating":             "Updating cache (new sort order) …",
        "cache_reload":                "Reload",
        "cache_load_now":              "Load now",
        "cache_singles_count":         "{total} singles · {count} × 7\"",
        "cache_summary":               "Total collection: {total} · thereof 7\": {count}",
        "cache_sync_report":           "✓ Synced: +{added} new, ~{updated} updated, -{removed} removed",
        "dialog_title_with_count":     "Load from Discogs — {count} × 7\" singles",
        "cache_expired_reason":        (
            "ℹ According to Discogs API Terms of Use, data may not be displayed "
            "for more than 6 hours without being refreshed."
        ),
        "discogs_cache_notice":        (
            "This application caches Discogs data locally for a maximum of 6 hours "
            "as per the API Terms of Use. A refresh is required after expiry."
        ),

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
        "review_banner_queue_line1": "Edit your print queue here. Changes are only kept when you click “Save”.",
        "review_banner_queue_line2": (
            "Add new entries with “Add entry” or by CSV import. Only checked "
            "entries are saved; entries with red marking require your attention."
        ),

        # Review dialog — column headers (editable cols get ✎ appended in code)
        "review_col_title":     "Title",
        "review_col_artist":    "Artist",
        "review_col_label":     "Label",
        "review_col_catno":     "Cat. No.",
        "review_col_country":   "Country",
        "review_col_year":      "Year",
        "review_col_side":      "Side",
        "review_col_edit_tip":  "Double-click or F2 to edit",

        # Review dialog — toolbar
        "review_btn_all":       "Select all",
        "review_btn_none":      "Deselect all",
        "review_btn_delete_sel":"Delete selected rows",
        "review_btn_add_row":   "Add row",
        "review_btn_add_entry": "Add entry …",
        "review_btn_add_entry_tip": "Form for one record: titles for side A and / or B",
        "review_btn_import_csv": "Import CSV …",
        "review_btn_import_csv_tip": "Take over entries from a CSV file (append or replace)",
        "review_btn_export_csv": "Export CSV …",
        "review_btn_export_csv_tip": (
            "Save all rows of the table as CSV – as a backup or to edit them "
            "in a spreadsheet"
        ),
        "review_search_ph":     "Search title or artist…",
        "review_drag_blocked_tip": "Clear the search to reorder rows",

        # Review dialog — context menu
        "review_ctx_delete":    "Delete row",
        "review_ctx_duplicate": "Duplicate row",

        # Review dialog — status bar
        "review_status_counts": "{n} entries total | {m} selected for printing",
        "review_status_hidden": "{h} of them hidden",
        "review_status_warning":"⚠️  {k} entries have empty required fields",
        "review_status_ok":     "✓ All entries complete",

        # Review dialog — cell tooltip
        "review_cell_required_tip": "Required field – please fill in",

        # Review dialog — bottom buttons
        "review_btn_cancel":    "Cancel",
        "review_btn_confirm":   "Continue to print →",
        "review_btn_confirm_tip": "Transfers the checked entries to the print queue",
        "review_btn_save":      "Save",
        "review_btn_save_tip":  (
            "Saves the checked entries as the print queue; unchecked entries "
            "are removed"
        ),

        # Review dialog — validation messages
        "review_warn_title":    "Incomplete entries",
        "review_warn_msg":      (
            "{k} entries have empty required fields (marked in red).\n"
            "Entries without a title are not saved, an empty side is saved as "
            "side A.\nContinue anyway?"
        ),
        "review_warn_continue": "Continue",
        "review_warn_back":     "Back to list",
        "review_queue_exists_title": "Print queue not empty",
        "review_queue_exists_msg":   "The print queue already contains {n} entries.\n"
                                     "Append the new entries or replace the queue?",
        "review_queue_append":       "Append",
        "review_queue_replace":      "Replace",
        "review_queue_cancel":       "Cancel",
        "review_no_sel_msg":    "No rows selected.",
        "review_clear_title":   "Empty the print queue?",
        "review_clear_msg":     (
            "No entry is checked. Saving empties the print queue – "
            "{n} entries will be deleted."
        ),
        "review_clear_confirm": "Empty queue",
        "review_unsaved_title": "Unsaved changes",
        "review_unsaved_msg":   "The print queue has unsaved changes. Save them?",
        "review_unsaved_save":  "Save",
        "review_unsaved_discard": "Discard",
        "review_unsaved_cancel": "Cancel",

        # CSV import / export
        "csv_filter":           "CSV files (*.csv *.txt);;All files (*)",
        "csv_import_title":     "Import CSV",
        "csv_import_done":      "{n} entries imported, {k} skipped (no title).",
        "csv_import_none":      "The file contains no entries with a title ({k} skipped).",
        "csv_err_empty":        "The file is empty. The first row must be a header row.",
        "csv_err_no_title":     (
            "No title column found. The first row must be a header row, "
            "e.g.:\nTitle;Artist;Label;Country;Year;Side;CatNo\n"
            "Titel;Interpret;Label;Land;Jahr;Seite;Katalognummer\n\n"
            "Columns found: {columns}"
        ),
        "csv_err_read":         "Could not read the CSV file:\n{detail}",
        "csv_export_title":     "Export CSV",
        "csv_export_done":      "{n} entries exported:\n{path}",
        "csv_export_err":       "Could not write the CSV file:\n{detail}",

        # Add entry form
        "entry_title":          "Add entry",
        "entry_lbl_artist":     "Artist",
        "entry_lbl_label":      "Label",
        "entry_lbl_country":    "Country",
        "entry_lbl_year":       "Year",
        "entry_ph_year":        "e.g. 1969",
        "entry_lbl_catno":      "Catalog number",
        "entry_lbl_title_a":    "Title side A",
        "entry_lbl_title_b":    "Title side B",
        "entry_hint":           (
            "Each filled title becomes one label (side A / B) with the shared "
            "details. Nothing is saved until you click “Save” in the queue."
        ),
        "entry_btn_add":        "Add",
        "entry_btn_add_next":   "Add and next",
        "entry_btn_close":      "Close",
        "entry_err_no_title":   "Please enter at least one title (side A or B).",
        "entry_err_year":       "Year: leave empty or enter four digits (e.g. 1969).",
        "entry_added":          "{n} row(s) added to the table.",

        # Add entry form — local collection (LOCAL mode)
        "entry_save_to_collection": "Also save to collection",
        "entry_save_to_collection_tip": (
            "When the queue is saved, a record is created in the local collection "
            "and the entries are linked to it"
        ),
        "review_csv_collection_tip": (
            "CSV import: when the queue is saved, the imported rows are added to "
            "the local collection as records (side A directly followed by side B "
            "with the same details = one record)"
        ),
        "csv_import_collection": "On save, {r} record(s) will be created in the collection.",

        # Record form (collection)
        "record_title_new":     "New record",
        "record_title_edit":    "Edit record",
        "record_hint":          (
            "Artist, label, country, year and catalog number apply to both "
            "sides. At least one title is required."
        ),
        "record_btn_save":      "Save",
        "record_btn_cancel":    "Cancel",

        # Collection dialog
        "collection_title":         "Collection",
        "collection_btn_new":       "New record …",
        "collection_btn_edit":      "Edit …",
        "collection_btn_edit_tip":  "Edit the selected record (also by double-click)",
        "collection_btn_delete":    "Delete",
        "collection_search_ph":     "Search artist, title, label, year …",
        "collection_btn_all":       "Select all sides",
        "collection_btn_all_tip":   "Select every side with a title of the visible records",
        "collection_btn_none":      "Clear selection",
        "collection_col_a":         "A",
        "collection_col_b":         "B",
        "collection_col_artist":    "Artist",
        "collection_col_title_a":   "Title A",
        "collection_col_title_b":   "Title B",
        "collection_col_label":     "Label",
        "collection_col_year":      "Year",
        "collection_col_catno":     "Cat. no.",
        "collection_col_country":   "Country",
        "collection_col_side_tip":  "Select the side for the print queue",
        "collection_side_tip":      "Print side {side}",
        "collection_side_no_title": "Side {side} has no title",
        "collection_empty":         (
            "The collection is still empty.\nAdd your first record – or save "
            "queue entries with “Also save to collection”."
        ),
        "collection_status":        "{n} record(s) | {m} side(s) selected",
        "collection_btn_close":     "Close",
        "collection_btn_to_queue":  "Add to print queue →",
        "collection_btn_to_queue_tip": (
            "Creates one entry per selected side and opens the review "
            "(append or replace)"
        ),
        "collection_delete_title":  "Delete records?",
        "collection_delete_one":    "Delete “{name}” from the collection?",
        "collection_delete_many":   "Delete {n} records from the collection?",
        "collection_delete_queue_note": (
            "Entries in the print queue are kept, they only lose the link to "
            "the record."
        ),
        "collection_delete_confirm": "Delete",
        "collection_load_err":      "The collection could not be loaded:\n{detail}",
        "collection_write_err":     "The collection could not be saved:\n{detail}",
        "collection_col_printed_a": "Printed A",
        "collection_col_printed_b": "Printed B",
        "collection_col_printed_tip": "When the side was last printed (empty = never)",
        "collection_btn_mark_printed":   "Mark as printed",
        "collection_btn_mark_printed_tip": (
            "Sets today's date for every side with a title of the selected records"
        ),
        "collection_btn_mark_unprinted": "Mark as not printed",
        "collection_btn_mark_unprinted_tip": (
            "Removes the printed date of both sides of the selected records"
        ),
        "collection_chk_unprinted":      "Only not printed",
        "collection_chk_unprinted_tip":  (
            "Only records with at least one side with a title that was never printed"
        ),
        "collection_btn_all_unprinted":  "Select all unprinted sides",
        "collection_btn_all_unprinted_tip": (
            "Select every never printed side with a title of the visible records"
        ),
        "collection_btn_import_csv":     "Import CSV …",
        "collection_btn_import_csv_tip": (
            "Take over records from a CSV file (one row per record)"
        ),
        "collection_btn_export_csv":     "Export CSV …",
        "collection_btn_export_csv_tip": (
            "Save every record of the collection as a CSV file (regardless of the filter)"
        ),
        "collection_csv_err_no_title":   (
            "No title column found. The first row must be a header row, "
            "e.g.:\nArtist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB\n"
            "Künstler;Label;Land;Jahr;Katalognummer;Titel A;Titel B;Gedruckt A;Gedruckt B"
            "\n\nColumns found: {columns}"
        ),
        "collection_csv_none":           (
            "The file contains no records with a title ({k} skipped)."
        ),
        "collection_csv_dup_title":      "Duplicate records",
        "collection_csv_dup_msg":        (
            "{n} row(s) of the file match records that are already in the collection "
            "or further up in the file (same artist and catalog number; without a "
            "catalog number same artist and titles)."
        ),
        "collection_csv_dup_skip":       "Skip",
        "collection_csv_dup_update":     "Update existing",
        "collection_csv_import_done":    (
            "{i} record(s) imported, {u} updated, {s} skipped."
        ),
        "collection_csv_import_unchanged": "{c} record(s) were already up to date.",
        "collection_csv_export_done":    "{n} record(s) exported:\n{path}",
        "collection_sync_queue_title":   "Update the print queue?",
        "collection_sync_queue_msg":     "Also update the {n} entries in the print queue?",

        # Printed marking / sync between queue and collection
        "btn_yes":                  "Yes",
        "btn_no":                   "No",
        "printed_ask_title":        "Mark as printed?",
        "printed_ask_msg":          "Mark the {n} labels from the collection as printed?",
        "printed_mark_err":         "The printed date could not be saved:\n{detail}",
        "review_sync_title":        "Update the collection?",
        "review_sync_msg":          (
            "{n} changed entries belong to records in the collection. "
            "Apply the changes to the collection too?"
        ),
        "review_sync_collection":   "Update collection",
        "review_sync_queue_only":   "Only the print queue",
        "csv_import_collection_linked": (
            "{l} row(s) will be linked to existing records of the collection."
        ),

        # Settings menu / theme / language
        "menu_settings":            "Settings",
        "menu_appearance":          "Appearance",
        "menu_language":            "Language",
        "theme_auto":               "Automatic (system setting)",
        "theme_light":              "Light",
        "theme_dark":               "Dark",

        # Settings dialog tabs
        "settings_tab_datasource":  "Data source",
        "settings_tab_discogs":     "Discogs account",
        "settings_tab_updates":     "Updates",
        "settings_tab_about":       "About",

        # Settings dialog — appearance tab
        "settings_theme_label":         "Theme",
        "settings_theme_auto_desc":     "Follows the operating system – currently {theme}",
        "settings_theme_dark_name":     "Dark Teal",
        "settings_theme_dark_desc":     "Dark theme with teal accent",
        "settings_theme_light_name":    "Light Teal",
        "settings_theme_light_desc":    "Light theme with teal accent",
        "settings_lang_change_info":    "Language change is applied immediately.",
        "watermark_section":            "WATERMARK",
        "watermark_active":             "Active: {filename}",
        "watermark_none":               "No watermark set",
        "watermark_select":             "Select file...",
        "watermark_clear":              "Remove",
        "debug_section":                "DEVELOPER",
        "debug_logging_label":          "Debug logging",
        "debug_logging_subtitle":       "Save detailed logs to logs/app.log",
        "debug_mode_active":            "⚠ Debug mode active",

        # Settings dialog — data source tab
        "settings_active_mode":         "Active mode",
        "settings_mode_local_sub":      "entered in the app",
        "settings_mode_discogs_sub":    "Collection via Discogs API",
        "settings_mode_switch_warn":    (
            "When switching modes, existing queue data may be overwritten."
        ),
        "settings_data_folder":         "Data folder",
        "settings_data_folder_info":    (
            "Your print queue database labels.db is stored here. Edit the "
            "queue in the app (Queue); use CSV import and export for bulk "
            "changes and backups."
        ),
        "settings_open_folder":         "Open folder",
        "err_open_folder":              "Could not open the folder:\n{path}\n\n{detail}",

        # Settings dialog — Discogs account tab
        "settings_discogs_connected":   "Connected",
        "settings_discogs_logged_in_as":"Logged in as",
        "settings_discogs_show_token":  "Show token",
        "settings_discogs_hide_token":  "Hide token",
        "settings_discogs_change_token":"Change token",

        # Settings dialog — updates tab
        "settings_current_version":     "Current version",
        "settings_check_updates":       "Check for updates",
        "settings_updates_wip":         "Will be implemented...",
        "settings_github_link":         "Open project on GitHub",

        # Settings dialog — about tab (version check + github section)
        "version_check":               "Version check",
        "installed_version":           "Installed version",
        "available_version":           "Available version (GitHub)",
        "not_yet_checked":             "—",
        "check_updates":               "Check for updates",
        "will_be_implemented":         "Will be implemented in a future version.",
        "checking_version":            "Checking for updates…",
        "up_to_date":                  "✓ You are using the latest version.",
        "newer_than_latest":           (
            "You are using a newer version than the latest stable release ({version})."
        ),
        "update_available":            "↑ Update available: {version}",
        "check_failed_network":        "Could not connect to GitHub.",
        "check_failed_error":          "Version check failed.",
        "no_releases_yet":             "No release published on GitHub yet.",
        "release_notes":               "Show release notes →",
        "update_hint_linux":           "Download and install the new .deb package.",
        "update_hint_windows":         "Download and run the new Setup.exe.",
        "update_releases_link":        "Downloads on GitHub (releases)",
        "open_github":                 "Open project on GitHub →",
        "settings_license":             "License",
        "settings_author":              "Author",

        # Discogs dialog — selection counter
        "selection_count":           "{count} selected",
        "selection_with_hidden":     "{total} selected ({visible} visible)",

        # Sidebar / footer
        "sidebar_load_data":        "Load data",
        "sidebar_queue":            "Queue",
        "sidebar_load_data_tip_local": (
            "Open the local record collection: add records and put selected "
            "sides into the print queue"
        ),
        "sidebar_load_data_tip_discogs": "Import 7\" singles from your Discogs collection",
        "sidebar_queue_tip":        "Show and edit the print queue",
        "sidebar_labels_ready":     "Labels ready",
        "sidebar_empty":            "Empty",
        "sidebar_start_pos":        "Start position",
        "sidebar_create_pdf":       "Create PDF",
        "sidebar_status_ready":     "Ready",
        "sidebar_status_generating":"Generating...",
        "sidebar_status_created":   "Created",
        "sidebar_not_connected":    "Not connected",
        "sidebar_local_mode":       "Local mode",
        "sidebar_discogs_mode":     "Discogs mode",
        "sidebar_local":            "Local",
        "sidebar_collection":       "Collection (local)",
        "sidebar_section_data":     "Data",
        "sidebar_section_print":    "Print",

        # Footer: collection status (LOCAL mode) and mode badge
        "footer_collection_status": "{n} records · {m} not printed",
        "footer_collection_empty":  "Collection empty",
        "footer_mode_tip":          "Choose the data source in the settings",

        # Preview placeholder
        "preview_hint_empty_local": "Choose records from your collection via “Load data”.",
        "preview_hint_empty_discogs": "Load records from Discogs via “Load data”.",
        "preview_hint_no_pdf": (
            "{n} labels in the queue – “Create PDF” shows the preview."
        ),

        # Keyboard shortcut tooltips
        "shortcut_search":          "Search",

        # Printer calibration (settings dialog)
        "print_calibration":            "PRINTER CALIBRATION",
        "calibration_x":                "Horizontal (X) in mm",
        "calibration_y":                "Vertical (Y) in mm",
        "calibration_reset":            "Reset",
        "generate_calibration_pdf":     "Generate calibration PDF",
        "calibration_info": (
            "If labels print slightly offset, adjust the fine-tuning here. "
            "Positive value shifts right/down."
        ),

        # Print hint dialog
        "print_hint_title":         "Print settings",
        "print_hint_text": (
            "Please ensure the following in the print dialog:\n\n"
            "✓ Scale: 'Actual size' (100 %)\n"
            "✓ NO 'Fit to page'\n"
            "✓ Margins: None / No adjustment\n\n"
            "Wrong scaling will misalign all labels!"
        ),
        "dont_show_again":          "Don't show again",
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
