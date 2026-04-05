# Vinyl Label Printer

A desktop application for printing 7" vinyl record labels on **Avery Zweckform 4780** label sheets (A4, 4 × 10 = 40 labels per sheet).

---

## Table of Contents

1. [User Manual](#user-manual)
   - [Requirements](#requirements)
   - [Installation](#installation)
   - [Starting the Application](#starting-the-application)
   - [Workflow](#workflow)
   - [Interface Overview](#interface-overview)
   - [Discogs Einrichtung](#discogs-einrichtung)
2. [Technical Reference](#technical-reference)
   - [Project Structure](#project-structure)
   - [Dependencies](#dependencies)
   - [Avery 4780 Sheet Dimensions](#avery-4780-sheet-dimensions)
   - [Label Layout](#label-layout)
   - [Module Reference](#module-reference)
   - [Printer Calibration](#printer-calibration)
   - [Adding a Language](#adding-a-language)

---

## User Manual

### Requirements

| Component | Details |
|---|---|
| Operating system | Linux (tested on Linux Mint) or Windows 11 |
| Python | 3.10 or newer |
| Poppler | Required for PDF preview (see [Installation](#installation)) |

### Installation

**1. Install Python dependencies**

```bash
cd vinyl-label-printer
pip install -r requirements.txt
```

**2. Install Poppler** (required for the PDF preview panel)

- **Linux (Debian/Ubuntu/Mint):**
  ```bash
  sudo apt install poppler-utils
  ```
- **Windows:**
  Download the pre-built binaries from [github.com/oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows), extract the archive, and add the `Library/bin` folder to your `PATH` environment variable.

**3. Place your Excel file**

Put your `database.xlsx` at `data/database.xlsx` inside the project folder, or select it later using the **Datei öffnen** button inside the app.

### Starting the Application

```bash
cd vinyl-label-printer
python main.py
```

### Workflow

**Step 1 — Prepare the Excel file**

The application reads from the **Print** sheet of your Excel workbook. Each row represents one label to be printed. Fill in the following columns:

| Column | Description | Example |
|---|---|---|
| Title | Record title | I Won't Let You Go |
| Artist | Artist or band name | Blues Busters |
| Label | Record label | Kentone, RE |
| Country | Country of origin | Japan |
| Year | Release year | 2014 |
| Side | Vinyl side — `A` or `B` | A |

The **Database** sheet is a read-only master reference and is never written to by the application.

**Step 2 — Open the database file**

On first run, click **Datei öffnen …** and navigate to your `database.xlsx`. The chosen path is remembered for future sessions. Use **Neu laden** to re-read the file after editing it externally (e.g., after adding new rows in LibreOffice Calc or Excel while the app is open).

**Step 3 — Set a start position (optional)**

If you are printing onto a partially used label sheet, click the desired starting cell in the **Startposition** grid:

- **Grey cells** — skipped (already used on the physical sheet)
- **Green cells** — will receive a printed label
- **White cells** — empty (no label queued)

The grid always shows 4 columns × 10 rows, mirroring the physical Avery 4780 sheet. Labels fill left-to-right, top-to-bottom from the chosen cell. If more labels are queued than slots remain on the first sheet, additional pages are generated automatically.

**Step 4 — Set a watermark (optional)**

Click **Wasserzeichen …** to select a PNG or JPG image. It will be printed as a faint background graphic on every label (approximately 10 % opacity), behind all text. The selected file path is saved permanently.

Click **Entfernen** to remove the watermark.

> If the watermark file has been moved or deleted since it was selected, the application will show an error when you try to generate a PDF and will not proceed until the issue is resolved.

**Step 5 — Generate the PDF**

Click **PDF erstellen**. The PDF is saved to `output/labels.pdf` and immediately displayed in the preview panel on the right.

Changing the start position after a PDF has been generated automatically regenerates the PDF and updates the preview.

**Step 6 — Print**

Click **Drucken** to open the operating system's print dialog.

- Make sure to select **actual size** (100 %) in the print dialog — do not scale to fit.
- Select the correct paper tray if your printer has multiple trays.
- Print a test page on plain paper first and hold it against the label sheet at a light source to verify alignment before printing on the actual labels.

### Interface Overview

```
┌─────────────────────────────────┬──────────────────────────────────────┐
│  [ Datei öffnen … ] [ Neu laden ]│                                      │
│                                  │                                      │
│  ┌─ Druckwarteschlange ────────┐ │           PDF-Vorschau               │
│  │  2 Etiketten in der         │ │                                      │
│  │  Warteschlange              │ │                                      │
│  └─────────────────────────────┘ │                                      │
│                                  │                                      │
│  ┌─ Startposition ─────────────┐ │                                      │
│  │  [ ][ ][ ][ ]               │ │                                      │
│  │  [ ][ ][ ][ ]   (4×10 grid) │ │                                      │
│  │  ...                        │ │                                      │
│  └─────────────────────────────┘ │                                      │
│                                  │                                      │
│  ┌─ Wasserzeichen ─────────────┐ │                                      │
│  │  logo.png                   │ │                                      │
│  │  [ Wasserzeichen … ][Entf.] │ │                                      │
│  └─────────────────────────────┘ │     [ ← Zurück ]  Seite 1 von 1     │
│                                  │                          [ Weiter → ]│
│  Sprache: [ DE ▾ ]               │                                      │
│  [ PDF erstellen ]               │                                      │
│  [ Drucken        ]              │                                      │
└─────────────────────────────────┴──────────────────────────────────────┘
```

### Discogs Einrichtung

Die App kann deine 7"-Singles direkt aus deiner Discogs-Sammlung importieren.

#### Schritt 1 — Persönlichen Token erstellen

1. Melde dich auf [discogs.com](https://www.discogs.com) an.
2. Öffne [discogs.com/settings/developers](https://www.discogs.com/settings/developers).
3. Klicke auf **Generate Token**.
4. Kopiere den angezeigten Token.

#### Schritt 2 — Token in der App eintragen

1. Klicke in der App auf **Aus Discogs laden**.
2. Trage deinen Discogs-Benutzernamen und den Token ein.
3. Klicke auf **Token prüfen und speichern**.
   Die App überprüft den Token einmalig gegen die Discogs-API und speichert ihn lokal.

#### Schritt 3 — Sammlung laden

1. Klicke auf **7" Singles laden**.
   Die App ruft alle Releases aus deiner Sammlung ab und filtert automatisch auf 7"-Formate.
2. Nutze die Suchleiste, um die Liste nach Interpret oder Titel zu filtern.
3. Wähle die gewünschten Singles aus und klicke auf **In Druckwarteschlange übernehmen**.

> **Hinweis zum Seitenfeld:** Discogs speichert keine A/B-Seiten-Information auf Sammlungsebene.
> Das Feld *Side* bleibt beim Import leer. Trage die Seite anschließend manuell in der Excel-Datei
> nach, oder wähle sie vor dem Drucken direkt im Programm aus.

#### Datenschutz & Sicherheit

- Der Token wird ausschließlich lokal in `config/credentials.json` gespeichert.
- Die Datei verlässt deinen Rechner nicht und ist in `.gitignore` eingetragen.
- Auf Linux/macOS werden die Dateiberechtigungen automatisch auf `600` gesetzt (nur Eigentümer darf lesen/schreiben).
- Über **Abmelden** im Dialog werden die gespeicherten Zugangsdaten sofort gelöscht.

---

## Technical Reference

### Project Structure

```
vinyl-label-printer/
├── main.py                        # Entry point — creates QApplication and MainWindow
├── requirements.txt               # pip dependencies
├── data/
│   └── database.xlsx              # Excel workbook (user-supplied)
├── output/
│   └── labels.pdf                 # Generated PDF (created on first run)
├── config/
│   ├── avery_formats.py           # Avery sheet dimensions and coordinate helpers
│   ├── settings.py                # Persistent JSON settings (watermark path)
│   ├── settings.json              # Auto-created on first save
│   ├── credentials.example.json   # Committed template — values intentionally empty
│   └── credentials.json           # Real credentials — NOT committed (see .gitignore)
├── modules/
│   ├── excel_reader.py            # openpyxl — loads/writes Print sheet, loads Database
│   ├── pdf_generator.py           # ReportLab — renders labels to PDF
│   ├── printer.py                 # Cross-platform OS print dialog trigger
│   ├── i18n.py                    # All UI strings, language switching
│   ├── discogs_client.py          # Discogs REST API client (fetch + filter)
│   └── credentials_manager.py     # Load/save/clear config/credentials.json
└── ui/
    ├── app.py                     # QMainWindow — wires all components together
    ├── grid_widget.py             # QWidget — interactive 4×10 start-position grid
    ├── preview_widget.py          # QWidget — pdf2image + QPixmap page viewer
    └── discogs_dialog.py          # QDialog — Discogs import (setup + collection panels)
```

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | UI framework |
| reportlab | ≥ 4.0 | PDF generation |
| openpyxl | ≥ 3.1 | Excel file reading and writing |
| pdf2image | ≥ 1.17 | PDF → image for preview (requires Poppler system library) |
| Pillow | ≥ 10.0 | Image loading and watermark alpha processing |
| requests | ≥ 2.31 | Discogs REST API HTTP client |

### Avery 4780 Sheet Dimensions

All values in millimetres. Defined in `config/avery_formats.py`.

| Parameter | Value (mm) | Notes |
|---|---|---|
| Page width | 210.0 | A4 |
| Page height | 297.0 | A4 |
| Label width | 48.5 | |
| Label height | 25.4 | |
| Left margin | 8.0 | (210 − 4 × 48.5) / 2 |
| Top margin | 21.5 | (297 − 10 × 25.4) / 2 |
| Column gap | 0.0 | Labels are edge-to-edge |
| Row gap | 0.0 | Labels are edge-to-edge |
| Labels per sheet | 40 | 4 columns × 10 rows |

ReportLab uses points (1 pt = 25.4 / 72 mm). All mm values are converted internally via `mm_to_pt()` in `config/avery_formats.py`. The coordinate origin is at the **bottom-left** of the page; y increases upward.

### Label Layout

Each label (48.5 × 25.4 mm) contains five centred text lines:

| Line | Content | Font | Size |
|---|---|---|---|
| 1 | Title | Helvetica | 7 pt |
| 2 | Artist | Helvetica-Bold | 7 pt |
| 3 | `---` | Helvetica | 5 pt |
| 4 | Label (Country, Year) | Helvetica | 5.5 pt |
| 5 | Side (A or B) | Helvetica-Bold | 12 pt |

The five-line block is vertically centred inside the label cell using:

```
total_block_height = sum(font_size × 1.25 for each line)
y_start = label_bottom + (label_height + total_block_height) / 2
```

If a watermark image is set it is drawn first (behind the text), centred and scaled to fit within a 4 pt inset, at approximately **10 % opacity**.

### Module Reference

#### `config/avery_formats.py`

| Symbol | Type | Description |
|---|---|---|
| `AVERY_FORMATS` | `dict` | Sheet specifications keyed by format name |
| `get_format(name)` | `→ dict` | Returns the format dict; raises `KeyError` for unknown names |
| `mm_to_pt(mm)` | `→ float` | Converts mm to ReportLab points |
| `label_rect_pt(fmt, col, row)` | `→ (x, y_bottom, w, h)` | Returns label bounding box in points for a given grid position |

#### `config/settings.py`

Reads and writes `config/settings.json`. Keys:

| Key | Type | Description |
|---|---|---|
| `watermark_path` | `string \| null` | Absolute path to the watermark image |

#### `modules/excel_reader.py`

| Symbol | Description |
|---|---|
| `LabelRecord` | Dataclass: `title`, `artist`, `label`, `country`, `year`, `side` |
| `load_print_queue(path)` | Reads the `Print` sheet; skips blank rows; normalises `side` to `"A"` or `"B"` |
| `load_database(path)` | Reads the `Database` sheet in read-only mode |

#### `modules/pdf_generator.py`

| Symbol | Description |
|---|---|
| `generate_pdf(records, output_path, format_name, start_position, watermark_path, debug_frames)` | Renders all records to a multi-page PDF; returns the resolved output path |
| `_WATERMARK_ALPHA` | Module constant (default `25`, range 0–255) — controls watermark opacity |

#### `modules/i18n.py`

| Symbol | Description |
|---|---|
| `AVAILABLE_LANGUAGES` | `list[str]` — e.g. `["DE", "EN"]` |
| `set_language(code)` | Switches the active language; raises `KeyError` for unknown codes |
| `get_language()` | Returns the current language code |
| `t(key, **kwargs)` | Returns the translated string, formatted with `kwargs` if supplied |

#### `ui/grid_widget.py`

`GridWidget(QWidget)` — 4 × 10 clickable grid.

| Signal / Method | Description |
|---|---|
| `startPositionChanged(int)` | Emitted when the user clicks a cell; carries the 0-based linear index |
| `set_total_records(n)` | Updates how many green (active) cells to show |
| `set_start_index(index)` | Programmatically sets the start cell |
| `start_index` | Property — current 0-based linear start position |

#### `ui/preview_widget.py`

`PreviewWidget(QWidget)` — PDF viewer.

| Method | Description |
|---|---|
| `load_pdf(path)` | Renders all pages at 150 DPI using `pdf2image`; shows page 1 |
| `retranslate()` | Updates button and label texts after a language switch |

#### `modules/printer.py`

| Platform | Mechanism |
|---|---|
| Windows | `os.startfile(path, "print")` |
| Linux | `lp` (CUPS); falls back to `xdg-open` |
| macOS | `open -a Preview` |

### Printer Calibration

If printed labels are slightly offset from the physical sheet, adjust the calibration offsets in `config/avery_formats.py`:

```python
"calibration_x_mm": 0.0,   # positive → shift all labels right
"calibration_y_mm": 0.0,   # positive → shift all labels up
```

Use `debug_frames=True` in `generate_pdf()` (from a Python script or temporary code change) to render thin red rectangles around each label cell, which makes alignment errors clearly visible.

### Adding a Language

1. Open `modules/i18n.py`.
2. Copy the `"EN"` block and paste it with a new ISO 639-1 key (e.g., `"FR"`).
3. Translate all string values.
4. The new language will automatically appear in the language selector dropdown at next launch — no other code changes are needed.
