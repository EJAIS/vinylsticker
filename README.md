# Vinyl Label Printer

A desktop application for printing 7" vinyl record labels on **Avery Zweckform 4780** label sheets (A4, 4 × 10 = 40 labels per sheet).

Made with :heart: and ClaudeCode by a Collector for Collectors.

+ Local database (Excel) or Discogs integration.
+ Discogs integration reads your 7" collection and also pulls A/B sides and more.
+ Watermark option available.

Currently in BETA status; please get yourself familiar (if you arent already) with the needed tools. Executables are planned, but not ready yet.
Please feel free to contact me for bugs and feature requests.

The application UI is available in **German (DE)** and **English (EN)**, switchable at runtime via the Language selector. This README uses English throughout.

---

## Table of Contents

1. [User Manual](#user-manual)
   - [Requirements](#requirements)
   - [Installation](#installation)
   - [Starting the Application](#starting-the-application)
   - [Workflow](#workflow)
   - [Interface Overview](#interface-overview)
   - [Discogs Import](#discogs-import)
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
| Operating system | Windows 11 or Linux (tested on Linux Mint) |
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

Put your `database.xlsx` at `data/database.xlsx` inside the project folder, or select it later using the **Open file …** button inside the app.

### Starting the Application

```bash
cd vinyl-label-printer
python main.py
```

### Workflow

#### Choosing a data source

At the top of the left panel, the **Data source** group lets you choose between two modes:

| Mode | Description |
|---|---|
| **Local database** | Reads the print queue from the Excel file (`data/database.xlsx`). This is the default. |
| **Discogs** | Fetches your 7" singles from your Discogs collection. The **Load from Discogs** button is enabled only in this mode. |

The selected mode is **persisted across sessions**.

**Switching to Discogs:**

- If no Discogs credentials are saved yet, a setup dialog appears. You can set up the token immediately or cancel — the switch is reverted on cancel.
- If the local print queue already contains entries, a confirmation dialog warns that they will be overwritten on the next import.

**Switching back to Local database:**

- An informational message confirms the switch. The existing print queue is preserved; no data is deleted.

**Status bar** at the bottom of the window reflects the active mode:

- Local: 🗄 Local database | N entries
- Discogs: 🌐 Discogs | Signed in as _username_ | N entries

---

#### Option A — Manual: prepare the Excel file

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

##### Open the database file

On first run click **Open file …** and navigate to your `database.xlsx`. The chosen path is remembered for future sessions. Use **Reload** to re-read the file after editing it externally (e.g. after adding new rows in LibreOffice Calc or Excel while the app is open).

---

#### Option B — Discogs import

Switch the **Data source** toggle to **Discogs**, then click **Load from Discogs** to fetch your 7" singles directly from your Discogs collection. See [Discogs Import](#discogs-import) for a full walkthrough. After confirming the import the print queue is written automatically — no manual Excel editing required.

---

**Step 2 — Set a start position (optional)**

If you are printing onto a partially used label sheet, click the desired starting cell in the **Start position** grid:

- **Grey cells** — skipped (already used on the physical sheet)
- **Green cells** — will receive a printed label
- **White cells** — empty (no label queued)

The grid always shows 4 columns × 10 rows, mirroring the physical Avery 4780 sheet. Labels fill left-to-right, top-to-bottom from the chosen cell. If more labels are queued than slots remain on the first sheet, additional pages are generated automatically.

**Step 3 — Set a watermark (optional)**

Click **Watermark …** to select a PNG or JPG image. It will be printed as a faint background graphic on every label (approximately 10 % opacity), behind all text. The selected file path is saved permanently.

Click **Remove** to remove the watermark.

> If the watermark file has been moved or deleted since it was selected, the application will show an error when you try to generate a PDF and will not proceed until the issue is resolved.

**Step 4 — Generate the PDF**

Click **Generate PDF**. The PDF is saved to `output/labels.pdf` and immediately displayed in the preview panel on the right.

Changing the start position after a PDF has been generated automatically regenerates the PDF and updates the preview.

**Step 5 — Print**

Click **Print** to send the PDF to your printer.

- On Windows the application tries to open the OS print dialog directly. If your default PDF viewer does not support that (e.g. Microsoft Edge on Windows 11), the PDF is opened in the viewer instead — use **Ctrl + P** from there.
- Make sure to select **actual size** (100 %) in the print dialog — do not scale to fit.
- Select the correct paper tray if your printer has multiple trays.
- Print a test page on plain paper first and hold it against the label sheet at a light source to verify alignment before printing on the actual labels.

### Interface Overview

```
┌──────────────────────────────────┬──────────────────────────────────────┐
│ ┌─ Data source ────────────────┐ │                                      │
│ │  ○ Local database  ● Discogs │ │                                      │
│ └──────────────────────────────┘ │                                      │
│ [Open file…] [Reload]            │                                      │
│ [Load from Discogs]  (disabled   │           PDF preview                │
│                       in Local)  │                                      │
│ ┌─ Print queue ────────────────┐ │                                      │
│ │  2 labels in queue           │ │                                      │
│ └──────────────────────────────┘ │                                      │
│ ┌─ Start position ─────────────┐ │                                      │
│ │  [ ][ ][ ][ ]                │ │                                      │
│ │  [ ][ ][ ][ ]   (4×10 grid)  │ │                                      │
│ │  ...                         │ │                                      │
│ └──────────────────────────────┘ │                                      │
│ ┌─ Watermark ──────────────────┐ │                                      │
│ │  logo.png                    │ │    [ ← Back ]  Page 1 of 1          │
│ │  [Watermark …]  [Remove]     │ │                          [Next → ]  │
│ └──────────────────────────────┘ │                                      │
│ Language: [ EN ▾ ]               │                                      │
│ [ Generate PDF ]                 │                                      │
│ [ Print        ]                 │                                      │
└──────────────────────────────────┴──────────────────────────────────────┘
```

### Discogs Import

The app can fetch your 7" singles directly from your Discogs collection, resolve A- and B-side track names automatically, and write the result to the print queue — all without touching the Excel file manually.

#### Step 1 — Create a personal access token

1. Log in at [discogs.com](https://www.discogs.com).
2. Go to [discogs.com/settings/developers](https://www.discogs.com/settings/developers).
3. Click **Generate Token**.
4. Copy the displayed token.

#### Step 2 — Switch to Discogs mode and enter credentials

1. Select **Discogs** in the **Data source** group at the top of the left panel.
   - If no credentials are saved yet, the setup dialog opens automatically.
2. Enter your Discogs username and the token.
3. Click **Verify and save token**.
   The app verifies the token against the Discogs API once and saves it locally.

After a successful verification the dialog switches automatically to the collection panel. On subsequent opens the saved credentials are used directly — the setup panel is skipped.

#### Step 3 — Load your collection

Click **Load 7" Singles**. The app fetches all releases from your Discogs collection (all pages) and filters automatically for 7" format singles. A progress indicator shows the current page being loaded.

> The collection list is **cached for the duration of the session**. Closing and reopening the dialog does not trigger a new API call as long as you are logged in with the same account. Use **Load 7" Singles** again to force a refresh.

Use the search bar to filter the list by artist or title.

#### Step 4 — Select singles and import

1. Tick the checkbox next to each single you want to import. Use **Select all** / **Deselect all** for bulk selection.
2. Click **Add to print queue**.
   The app fetches the tracklist for each selected release from the Discogs release endpoint and resolves A- and B-sides:
   - **Simple single (exactly 1 A-side + 1 B-side):** two rows are created, one for each side, with the individual track title.
   - **EP / Maxi-single (multiple tracks):** one row per track, with the full position (A1, A2, B1 …) as the side value.
   - **No tracklist available:** one row with the release title and an empty Side field.

#### Step 5 — Review and confirm

A **Review dialog** opens showing all expanded rows before anything is written to the Excel file.

| Column | Editable | Notes |
|---|---|---|
| ☐ | Checkbox | Uncheck to exclude a row from the import |
| Title | Yes | Red background if empty (required) |
| Artist | Yes | |
| Label | Yes | |
| Country | Yes | |
| Year | Yes | |
| Side | Yes | Red background if empty (required) |

**Editing:**

- Double-click or start typing to edit a cell. Edited cells flash yellow briefly.
- Drag rows to reorder them.
- Right-click a row to **delete** or **duplicate** it.
- Use the toolbar buttons to select all / none, delete selected rows, or add a blank row.
- The search bar filters visible rows by title or artist.

**Status bar** at the bottom shows the total number of rows, how many are checked, and how many have incomplete required fields.

**Confirm** (blue button) becomes active once at least one row is checked. Clicking it writes only the checked, visible rows to the Print sheet and closes both dialogs. The main window reloads the queue count automatically.

**Cancel** returns to the collection panel — your selection is preserved.

#### Privacy & security

- The token is stored exclusively in `config/credentials.json` on your local machine.
- The file is listed in `.gitignore` and is never committed to version control.
- On Linux/macOS file permissions are set to `600` (owner read/write only) automatically.
- Click **Log out** in the collection panel to delete the stored credentials immediately and return to the setup panel. This also clears the session cache.

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
│   ├── settings.py                # Persistent JSON settings (watermark path, data source mode)
│   ├── settings.json              # Auto-created on first save
│   ├── credentials.example.json   # Committed template — values intentionally empty
│   └── credentials.json           # Real credentials — NOT committed (see .gitignore)
├── modules/
│   ├── data_source.py             # DataSourceMode enum (LOCAL / DISCOGS)
│   ├── excel_reader.py            # openpyxl — loads/writes Print sheet, loads Database
│   ├── pdf_generator.py           # ReportLab — renders labels to PDF, dynamic font sizing
│   ├── printer.py                 # Cross-platform OS print dialog trigger
│   ├── i18n.py                    # All UI strings, language switching (DE / EN)
│   ├── discogs_client.py          # Discogs REST API client (verify, fetch, filter, tracklist)
│   └── credentials_manager.py     # Load/save/clear config/credentials.json
└── ui/
    ├── app.py                     # QMainWindow — wires all components together
    ├── styles.py                  # Shared QSS stylesheet constants and helpers
    ├── grid_widget.py             # QWidget — interactive 4×10 start-position grid
    ├── preview_widget.py          # QWidget — pdf2image + QPixmap page viewer
    ├── discogs_dialog.py          # QDialog — Discogs import (setup + collection panels)
    └── review_widget.py           # QDialog — editable review table before queue write
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

| Line | Content               | Font           | Max size | Min size |
|------|-----------------------|----------------|----------|----------|
| 1    | Title                 | Helvetica      | 9 pt     | 5 pt     |
| 2    | Artist                | Helvetica-Bold | 8 pt     | 5 pt     |
| 3    | `---`                 | Helvetica      | 6 pt     | 6 pt     |
| 4    | Label (Country, Year) | Helvetica      | 7 pt     | 4.5 pt   |
| 5    | Side (A or B)         | Helvetica-Bold | 14 pt    | 14 pt    |

Each field is **independently scaled down** from its maximum font size until the text fits within the usable label width (label width minus 4 pt horizontal padding on each side). Scaling stops at the minimum size — text is never clipped.

The five-line block is vertically centred inside the label cell. If a watermark image is set it is drawn first (behind the text), centred and scaled to fit within a 4 pt inset, at approximately 10 % opacity.

**Info line formatting:** Country and Year are shown in parentheses after the label name. Empty fields are omitted along with their separator — e.g. if Country is empty, the line reads `Label (Year)` rather than `Label (, Year)`. If both are empty, the parentheses are dropped entirely.

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
| `data_source_mode` | `"local" \| "discogs"` | Active data source; persisted across sessions |

#### `modules/data_source.py`

| Symbol           | Description                                                   |
|------------------|---------------------------------------------------------------|
| `DataSourceMode` | `Enum` with members `LOCAL = "local"` and `DISCOGS = "discogs"` |

#### `modules/excel_reader.py`

| Symbol | Description |
|---|---|
| `LabelRecord` | Named tuple: `title`, `artist`, `label`, `country`, `year`, `side` |
| `load_print_queue(path)` | Reads the `Print` sheet; skips blank rows; normalises `side` to `"A"` or `"B"` |
| `load_database(path)` | Reads the `Database` sheet in read-only mode |
| `write_print_queue(path, records)` | Overwrites the `Print` sheet with the given `LabelRecord` list |

#### `modules/pdf_generator.py`

| Symbol | Description |
|---|---|
| `generate_pdf(records, output_path, format_name, start_position, watermark_path, debug_frames)` | Renders all records to a multi-page PDF; returns the resolved output path |
| `fit_text_to_width(c, text, max_width, font_name, size_max, size_min, step)` | Returns the largest font size ≤ `size_max` at which `text` fits within `max_width`; floors at `size_min` |
| `_WATERMARK_ALPHA` | Module constant (default `25`, range 0–255) — controls watermark opacity |

#### `modules/discogs_client.py`

| Symbol | Description |
|---|---|
| `DiscogsClient(username, token)` | Initialises a `requests.Session` with Discogs auth headers |
| `verify_token()` | `GET /oauth/identity` — returns `True` if valid, `False` if 401, raises `ConnectionError` on network failure |
| `fetch_collection(progress_callback)` | Paginates through all collection pages (sort: newest first); calls `progress_callback(page, total_pages)` between pages |
| `filter_7inch(releases)` | Returns only releases that have `'7"'` in their format descriptions; strips disambiguation suffixes from artist names |
| `fetch_tracklist(release_id)` | `GET /releases/{id}` — returns `{"tracks": list[dict], "country": str}`; normalises `A1`/`B1` positions to `A`/`B` for simple singles |

#### `modules/credentials_manager.py`

| Symbol | Description |
|---|---|
| `CredentialsManager()` | Reads/writes `config/credentials.json`; copies from `credentials.example.json` if missing |
| `load()` | Returns `{"discogs_username": str, "discogs_token": str}` |
| `save(username, token)` | Writes credentials and sets file permissions to `600` on Linux/macOS |
| `are_valid()` | Returns `True` if both username and token are non-empty |
| `clear()` | Overwrites the file with empty values |

#### `modules/i18n.py`

| Symbol | Description |
|---|---|
| `AVAILABLE_LANGUAGES` | `list[str]` — e.g. `["DE", "EN"]` |
| `set_language(code)` | Switches the active language; raises `KeyError` for unknown codes |
| `get_language()` | Returns the current language code |
| `t(key, **kwargs)` | Returns the translated string, formatted with `kwargs` if supplied |

#### `modules/printer.py`

| Platform | Mechanism |
|---|---|
| Windows | `os.startfile(path, "print")`; falls back to `os.startfile(path)` if no "print" verb is registered (e.g. Microsoft Edge as default viewer) |
| Linux | `lp` (CUPS); falls back to `xdg-open` if `lp` is not available |
| macOS | `open -a Preview` |

#### `ui/styles.py`

Shared stylesheet constants and helpers used by both `discogs_dialog.py` and `review_widget.py`.

| Symbol | Description |
|---|---|
| `TABLE_STYLESHEET` | QSS string: consistent table border, grid colour, item colour, hover and selected states, header section style |
| `SEARCH_FIELD_STYLESHEET` | QSS string: neutral border, blue focus ring, no inherited red underline |
| `apply_table_style(table)` | Applies `TABLE_STYLESHEET` to a `QTableWidget` |
| `apply_search_style(widget)` | Applies `SEARCH_FIELD_STYLESHEET` to a `QLineEdit` |

#### `ui/discogs_dialog.py`

`DiscogsDialog(QDialog)` — two-panel stacked dialog.

| Panel      | Shown when                                                     |
|------------|----------------------------------------------------------------|
| Setup      | No valid credentials saved                                     |
| Collection | Valid credentials found or after successful token verification |

Session cache: the filtered 7" release list is held in class-level variables (`_cached_releases`, `_cache_username`) and reused across dialog instances within the same application session. The cache is keyed by username and cleared on logout.

Background workers:

| Class | Signal(s) | Description |
|---|---|---|
| `_VerifyWorker` | `success`, `failure(str)` | Calls `verify_token()` off the UI thread |
| `_FetchWorker` | `progress(int,int)`, `finished(list)`, `error(int,str)` | Paginates `fetch_collection()`; handles 429 rate-limit with a 60 s countdown + auto-retry |
| `_TracklistWorker` | `progress(int,int)`, `finished(list,list)` | Calls `fetch_tracklist()` per selected release; expands into per-side rows |

#### `ui/review_widget.py`

`ReviewDialog(QDialog)` — editable preview table before writing to the Print sheet.

| Feature | Details |
|---|---|
| Columns | ☐, Title, Artist, Label, Country, Year, Side |
| Required fields | Title, Side — highlighted red when empty |
| Edit feedback | Edited cell flashes yellow (600 ms) then returns to normal or red |
| Row operations | Drag & drop reorder; context menu delete / duplicate; toolbar add / delete |
| Search | Live filter by title or artist (`setRowHidden`) |
| Confirm | Writes only checked, visible rows via `write_print_queue()`; disabled until ≥ 1 row checked |

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
