# Vinyl Label Printer

A desktop application for printing 7" vinyl record labels on **Avery Zweckform 4780** label sheets (A4, 4 × 10 = 40 labels per sheet).

Made with :heart: and ClaudeCode - by a Collector for Collectors.

+ Local print queue (SQLite), maintained in the app — entry form, editable table, CSV import / export — or imported from Discogs.
+ Discogs integration reads your 7" collection including **catalog numbers**, loads A/B sides on demand at import time, and caches data locally (SQLite, 6-hour expiry per Discogs API ToU — for the collection and for each release's details).
+ Catalog number is shown, editable and printed: the info line reads `Label CatNo (Country, Year)`, e.g. `Pyramid PYR 6013 (UK, 1967)`.
+ Sides are always printed as **A** or **B** (`A1`/`A2` → A, UK double-A side `AA` → B).
+ Discogs imports ask whether to **append** to or **replace** an existing print queue.
+ Watermark option available (main window sidebar and **⚙ Settings → Appearance**).
+ Dark / Light theme via **⚙ Settings → Appearance** — **Automatic (system setting)** follows the OS light/dark mode live; a switch applies at once, without a restart.
+ Printer calibration with X/Y fine-tuning and a built-in calibration PDF generator (**⚙ Settings → Appearance → Printer Calibration**).

![Picture of an example label](https://github.com/EJAIS/vinylsticker/blob/main/examples/label_with_watermark.png)

Currently in BETA status. Ready-to-install packages for Linux (.deb) and Windows (Setup.exe) are
attached to the releases (see [Installation](#installation)).
Please feel free to contact me for bugs and feature requests.

The application UI is available in **German (DE)** and **English (EN)**, switchable at runtime via **⚙ Settings → Appearance**. This README uses English throughout.

---

## Table of Contents

1. [Installation](#installation)
2. [Update](#update)
3. [Uninstall](#uninstall)
4. [Where your data is stored](#where-your-data-is-stored)
5. [Switching from the old script install](#switching-from-the-old-script-install)
6. [Run from source (developers)](#run-from-source-developers)
7. [User Manual](#user-manual)
   - [Workflow](#workflow)
   - [Collection (Local mode)](#collection-local-mode)
   - [Interface Overview](#interface-overview)
   - [Discogs Import](#discogs-import)
8. [Troubleshooting](#troubleshooting)
   - [Labels are misaligned](#labels-are-misaligned)
   - [PDF preview is blank or missing](#pdf-preview-is-blank-or-missing)
   - [Print dialog does not open](#print-dialog-does-not-open)
   - [Discogs import fails or stalls](#discogs-import-fails-or-stalls)
9. [Technical Reference](#technical-reference)
   - [Project Structure](#project-structure)
   - [Dependencies](#dependencies)
   - [Avery 4780 Sheet Dimensions](#avery-4780-sheet-dimensions)
   - [Label Layout](#label-layout)
   - [Module Reference](#module-reference)
   - [Printer Calibration](#printer-calibration)
   - [Calibration PDF](#calibration-pdf)
   - [Adding a Language](#adding-a-language)
   - [Building from source (PyInstaller)](#building-from-source-pyinstaller)

---

## Installation

The app is installed from a package. Both packages bring their own Python and Qt; download them
from the **[latest release](https://github.com/EJAIS/vinylsticker/releases/latest)**.

| System | Package |
|---|---|
| Linux Mint 21 / 22, Ubuntu 22.04 / 24.04 (64-bit) | `vinyl-label-printer_<version>_amd64.deb`, see [Linux Mint / Ubuntu (.deb)](#linux-mint--ubuntu-deb) |
| Windows 10 / 11 (64-bit) | `VinylLabelPrinterSetup-<version>.exe`, see [Windows (Setup.exe)](#windows-setupexe) |

Each release also lists `SHA256SUMS.txt` with the checksums of both files. Releases marked
*Pre-release* (tags like `v1.1.0-rc.1`) are test versions; the app's update check ignores them.
Their files carry the suffix (`vinyl-label-printer_1.1.0-rc.1_amd64.deb`,
`VinylLabelPrinterSetup-1.1.0-rc.1.exe`), and `apt` upgrades a pre-release to the final version.

Every build of `main` also produces both packages as artifacts in
[Actions → Build](https://github.com/EJAIS/vinylsticker/actions/workflows/build.yml)
(GitHub login required; each artifact is a zip that contains the package).

Other Linux distributions and macOS: see [Run from source (developers)](#run-from-source-developers).
If you installed the app with the old `install.sh` / `install.ps1` scripts, see
[Switching from the old script install](#switching-from-the-old-script-install).

### Linux Mint / Ubuntu (.deb)

The package installs the app to `/opt/vinyl-label-printer`, the `vinyl-label-printer` command
and a menu entry with icon. In the folder with the downloaded file (replace the version with the
one you downloaded):

```bash
sudo apt install ./vinyl-label-printer_1.0.0_amd64.deb
```

`apt` also installs the few system packages the app needs (e.g. `poppler-utils`). Start the app
from the menu (**Office → Vinyl Label Printer**) or with:

```bash
vinyl-label-printer
```

### Windows (Setup.exe)

The setup installs without administrator rights, for the current user only, to
`%LOCALAPPDATA%\Programs\Vinyl Label Printer`. It adds a Start Menu folder
**Vinyl Label Printer** and, if you tick the box, a desktop shortcut.

Run `VinylLabelPrinterSetup-<version>.exe` and follow the wizard (English or German).

> **SmartScreen warning:** the installer is not code-signed, so Windows may show
> *"Windows protected your PC"* with *Publisher: Unknown publisher*. Click **More info**, then
> **Run anyway**. (German Windows: *„Der Computer wurde durch Windows geschützt"* →
> **Weitere Informationen** → **Trotzdem ausführen**.)

---

## Update

**⚙ Settings → About → Check for updates** shows whether a newer release exists and links to
the [releases page](https://github.com/EJAIS/vinylsticker/releases). Your data is not touched
by an update.

**Linux:** download the newer `.deb` and install it over the installed one, the same way:

```bash
sudo apt install ./vinyl-label-printer_1.1.0_amd64.deb
```

**Windows:** download and run the newer `VinylLabelPrinterSetup-<version>.exe`. It replaces the
installed version in the same folder; if the app is still running, the setup offers to close it.

---

## Uninstall

### Linux

```bash
sudo apt remove vinyl-label-printer
```

`apt remove` removes the program, the command and the menu entry. Your user data —
settings and Discogs token in `~/.config/vinyl-label-printer`, the database in
`~/.local/share/vinyl-label-printer` — is **never removed by the package**, not even by
`sudo apt purge vinyl-label-printer`. To delete it as well, remove these folders yourself:

```bash
rm -rf ~/.config/vinyl-label-printer
```

```bash
rm -rf ~/.local/share/vinyl-label-printer
```

### Windows

Open **Settings → Apps → Installed apps** (Windows 10: **Settings → Apps → Apps & features**),
find **Vinyl Label Printer**, click **⋯** / the entry and choose **Uninstall**.

The uninstaller removes only the program folder and the shortcuts. Your data in
`%APPDATA%\vinyl-label-printer` and `%LOCALAPPDATA%\vinyl-label-printer` is **kept**; delete
these folders yourself if you want to remove it as well (see
[Where your data is stored](#where-your-data-is-stored)).

---

## Where your data is stored

The app keeps your files in per-user folders, separate from the program itself, so updating,
reinstalling or uninstalling the app never touches them. The folders are created on first use.

| Content | Linux | Windows |
|---|---|---|
| Settings (`settings.json`), Discogs credentials (`credentials.json`) | `~/.config/vinyl-label-printer/` | `%APPDATA%\vinyl-label-printer\` |
| Your print queue (`labels.db`) | `~/.local/share/vinyl-label-printer/` | `%APPDATA%\vinyl-label-printer\` |
| Discogs cache (`discogs_cache.db`), generated PDFs (`output/`) | `~/.cache/vinyl-label-printer/` | `%LOCALAPPDATA%\vinyl-label-printer\Cache\` |
| Log file (`app.log`) | `~/.local/state/vinyl-label-printer/log/` | `%LOCALAPPDATA%\vinyl-label-printer\Logs\` |

On Linux the `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` and `XDG_STATE_HOME`
variables are respected. On Windows, `%APPDATA%` is `C:\Users\<you>\AppData\Roaming` and
`%LOCALAPPDATA%` is `C:\Users\<you>\AppData\Local`.

The print queue and your local record collection are stored in `labels.db`, a single SQLite
file in the data folder. They are edited only inside the app: **Queue** (both modes) opens the
queue editor, **Load data** (Local mode) opens the collection (see
[Collection (Local mode)](#collection-local-mode)). To edit many entries at once, or to keep a
backup in a readable format, use **Export CSV** and **Import CSV** in the queue editor (see
[CSV import and export](#csv-import-and-export)) and in the collection (see
[Collection CSV import and export](#collection-csv-import-and-export)). To back up the whole
file, copy `labels.db` while the app is closed. **⚙ Settings → Data source** shows the data
folder and has an **Open folder** button.

A new installation starts with an empty print queue.

**Coming from 1.0:** Your old database.xlsx is not imported automatically. To take entries
over, open it in Excel or LibreOffice Calc, save the sheet 'Print' as CSV and use
'Import CSV' in the queue editor.

### One-time migration from older versions

Older versions kept all files next to the program code (`config/`, `data/`). On the first start
of a newer version the app **copies** `settings.json`, `credentials.json` and `discogs_cache.db`
into the folders above. It looks in:

1. the program folder itself (git clone or an old script install up to v0.4.0),
2. the program folder of the old script installs up to v0.4.0: `~/vinyl-label-printer` (Linux)
   or `%LOCALAPPDATA%\vinyl-label-printer` (Windows).

The original files are left untouched and existing files are never overwritten. Logs are not
migrated. The migration runs once — a marker file `legacy-migration.json` in the settings folder
records what was copied. To run it again, close the app, delete that marker file and start the
app (files that already exist in the new folders are still never overwritten).

---

## Switching from the old script install

Up to v1.0.0-rc.1 the app could also be installed with the scripts `install.sh` (Linux) and
`install.ps1` (Windows). They are no longer part of the project; the packages above replace
them. Do not keep both installations.

Old script installs up to v0.4.0 keep your data inside their program folder, and the old
uninstaller deletes that folder. So switch **in exactly this order**: the package version has to
copy your data out (see [One-time migration](#one-time-migration-from-older-versions)) before
the old uninstaller runs. The print queue of the old Local mode is not copied: if you still need
it, copy the `data` folder out of the old program folder before uninstalling and import it as
described under [Where your data is stored](#where-your-data-is-stored).

### Linux

1. Install the `.deb` (replace the version with the one you downloaded):

   ```bash
   sudo apt install ./vinyl-label-printer_1.0.0_amd64.deb
   ```

2. Start the package version **once from a terminal with the full path** — the old menu entry
   and the `vinyl-label-printer` command in `~/.local/bin` still start the script install at this
   point:

   ```bash
   /usr/bin/vinyl-label-printer
   ```

   Check that your library is there (your settings, and the Discogs account if you use it), then
   close the app.

3. Download the old uninstaller (the tag `v1.0.0-rc.1` is the last version that contains it):

   ```bash
   curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/v1.0.0-rc.1/install.sh -o /tmp/install.sh
   ```

   Then remove the script install. It asks for confirmation; your data now lives in `~/.config`
   and `~/.local/share` and is kept:

   ```bash
   bash /tmp/install.sh --uninstall
   ```

From now on the menu entry and the `vinyl-label-printer` command start the package version.
If a terminal still runs the old command, open a new terminal.

### Windows

1. Install with `VinylLabelPrinterSetup-<version>.exe`.

2. Start the new app once from the new Start Menu folder **Vinyl Label Printer** (the old
   **Vinyl Label Printer** entry directly in the Start Menu still starts the script install).
   Check that your library is there (your settings, and the Discogs account if you use it), then
   close the app.

3. Download the old uninstaller in PowerShell (the tag `v1.0.0-rc.1` is the last version that
   contains it):

   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/EJAIS/vinylsticker/v1.0.0-rc.1/install.ps1" -OutFile "$env:TEMP\install.ps1"
   ```

   Then remove the script install. It asks for confirmation; its Start Menu entry goes away
   with it, and the app's cache and log file in `%LOCALAPPDATA%\vinyl-label-printer` are deleted
   too and simply recreated:

   ```powershell
   powershell -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1" -Uninstall
   ```

---

## Run from source (developers)

For development, other Linux distributions or macOS. Requires Python 3.10+ and Git.

```bash
git clone https://github.com/EJAIS/vinylsticker.git
cd vinylsticker
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r vinyl-label-printer/requirements.txt
python vinyl-label-printer/main.py
```

Tests (headless, pytest from `requirements-dev.txt`):

```bash
pip install -r vinyl-label-printer/requirements-dev.txt
cd vinyl-label-printer
QT_QPA_PLATFORM=offscreen python -m pytest tests
```

The PDF preview needs **Poppler** as a system package:

- Linux (Debian/Ubuntu/Mint): `sudo apt install poppler-utils` (Qt also needs `libxcb-cursor0`)
- macOS: `brew install poppler`
- Windows: extract a [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
  release and add its `Library\bin` folder to `PATH`

Building the packages is described in [Building from source (PyInstaller)](#building-from-source-pyinstaller).

---

## User Manual

### Workflow

#### Choosing a data source

The app reads the print queue from one of two sources. Choose it in
**⚙ Settings → Data source**:

| Mode | Description |
|---|---|
| **Local database** | You keep your record collection in the app and pick the sides to print from it; the print queue is maintained in the app too — entry form, editable table, CSV import / export. Both are stored in `labels.db` in the [data folder](#where-your-data-is-stored). This is the default. |
| **Discogs** | Imports your 7" singles from your Discogs collection into the print queue. |

The selected mode is **persisted across sessions** and shown in the footer bar, together with
the Discogs connection status. If you select Discogs before a token is saved, the app says so
and opens the **Discogs account** tab (see [Discogs Import](#discogs-import)).

---

#### Option A — Local mode: enter records in the app

In Local mode you keep your records in the app's **collection** and pick the sides to print from
it (**Load data**), or you fill the print queue directly in the **queue editor** (**Queue**).
Typical round: **Load data** → tick the sides → **Add to print queue →** → **Create PDF** →
**Print** → confirm that the labels were printed. The collection, its printed dates and how it
stays in sync with the queue are described in [Collection (Local mode)](#collection-local-mode).

##### Print queue editor

Click **Queue** in the sidebar. The queue editor opens — also when the queue is empty.

- **Add entry …** opens a small form for one record: Artist, Label, Country, Year and Catalog
  number (shared by both sides) plus **Title side A** and **Title side B**. Each filled title
  becomes one row with side A or B. At least one title is required; the year is empty or four
  digits. **Add** adds the rows and closes the form; **Add and next** adds them, clears the form
  and puts the cursor into the first field for the next record. In Local mode the form has
  **Also save to collection** (on by default, the last state is remembered): the record is then
  also created in the collection and its queue entries are linked to it. Like every change in
  the editor, the record is only written when you click **Save** — **Cancel** leaves the
  collection unchanged.
- **Add row** adds an empty row to fill in directly in the table.
- **Import CSV …** / **Export CSV …** — see [CSV import and export](#csv-import-and-export).
- Edit cells, drag rows to reorder them, delete or duplicate rows via the context menu, filter
  with the search bar (the table works as described in
  [Step 5 — Review and confirm](#step-5--review-and-confirm)).

Nothing is stored until you click **Save**. Only checked rows are saved; unchecked rows are
removed from the queue. Rows without a title are not saved and an empty side is saved as **A** —
the app warns you before. Saving with no row checked empties the queue after a confirmation, e.g.
to clear it after printing. Closing the editor with unsaved changes asks whether to **Save**,
**Discard** them or **Cancel** (keep editing).

| Field | Description | Example |
|---|---|---|
| Title | Record title (required) | I Won't Let You Go |
| Artist | Artist or band name | Blues Busters |
| Label | Record label | Kentone |
| Country | Country of origin | Japan |
| Year | Release year, stored as text | 2014 |
| Side | Vinyl side — `A` or `B` (see below) | A |
| Cat. No. | Catalog number (optional) | RE-001 |

**Side values** are always normalised to `A` or `B` (case-insensitive): prefixes like `Seite`, `Side`, `-` or `:` are ignored; `A`, `A1`, `A2` → **A**; `B`, `B1`, `B2` → **B**; the UK double-A side `AA` → **B**; anything unrecognised → **A**.

##### CSV import and export

CSV is the way to edit many entries at once in a spreadsheet program and to back up the queue
in a readable format.

**Export CSV …** writes all rows currently in the table — also unchecked rows and rows hidden by
the search filter — to a file named `vinyl-labels-YYYY-MM-DD.csv` (proposed in your Documents
folder). Format: header row `Title;Artist;Label;Country;Year;Side;CatNo`, semicolon as
delimiter, UTF-8 with BOM, so umlauts show correctly in spreadsheet programs. An exported file
imports back to identical rows.

**Import CSV …** reads a CSV file:

- delimiter: comma, semicolon or tab — detected automatically;
- encoding: UTF-8 (with or without BOM) or Windows-1252 (e.g. a "CSV (semicolon separated)"
  file saved by a spreadsheet program on a German Windows);
- the first row must be a header row. Columns are matched by name — case-insensitive, in any
  order; other columns are ignored:

| Field | English header | German header |
|---|---|---|
| Title (required) | `Title` | `Titel` |
| Artist | `Artist` | `Künstler`, `Kuenstler`, `Interpret` |
| Label | `Label` | `Label` |
| Country | `Country` | `Land` |
| Year | `Year` | `Jahr` |
| Side | `Side` | `Seite` |
| Catalog number | `CatNo` | `Katalognummer` |

Without a Side column every row is side A. Rows without a title are skipped; afterwards the app
reports how many rows were imported and how many were skipped. If the table already has rows,
you are asked whether to **append** the imported rows or **replace** the table. As with every
change in the editor, nothing is stored until you click **Save**.

In Local mode the checkbox **Also save to collection** next to **Import CSV …** (the same setting
as in the entry form) also creates collection records on **Save**: a side A row directly
followed by a side B row with the same artist, label, country, year and catalog number becomes
one record with both titles, every other row a record with only its own side. A record that
is already in the collection — same artist and catalog number, or without a catalog number
same artist and titles (see [duplicates](#collection-csv-import-and-export)) — is not created
again: its rows are linked to the existing record. Records that appear several times in the
file are created once. The message after the import says how many records will be created and
how many rows will be linked.

This queue CSV has **one row per label**. The collection has its own CSV format with one row
per record — see [Collection CSV import and export](#collection-csv-import-and-export).

Bulk editing: **Export CSV** → edit the file in a spreadsheet → save it as CSV → **Import CSV**
→ **Replace** → **Save**.

---

#### Option B — Discogs import

Select **Discogs** in **⚙ Settings → Data source**, then click **Load data** in the sidebar to fetch your 7" singles directly from your Discogs collection. See [Discogs Import](#discogs-import) for a full walkthrough. After confirming the import the rows are written to the print queue automatically.

---

**Step 2 — Check the queue (optional)**

The **Queue** entry in the sidebar shows how many labels are queued. Click it to review and
edit the queue in the queue editor (see
[Option A — Local mode](#option-a--local-mode-enter-records-in-the-app)) — in both modes, also
when the queue is empty; **Save** replaces the queue with the checked rows.

**Step 3 — Set a start position (optional)**

If you are printing onto a partially used label sheet, click **Start position** in the sidebar
and pick the first free cell in the grid:

- **Dark grey cells** — skipped (already used on the physical sheet)
- **Green cells** — will receive a printed label
- **Light grey cells** — empty (no label queued)

The grid always shows 4 columns × 10 rows, mirroring the physical Avery 4780 sheet. Labels fill left-to-right, top-to-bottom from the chosen cell. If more labels are queued than slots remain on the first sheet, additional pages are generated automatically.

Changing the start position after a PDF has been generated automatically regenerates the PDF and updates the preview.

**Step 4 — Set a watermark (optional)**

In **⚙ Settings → Appearance → Watermark**, click **Select file...** to choose a PNG or JPG image. It will be printed as a faint background graphic on every label (approximately 10 % opacity), behind all text. The selected file path is saved permanently. Click **Remove** to remove the watermark.

> If the watermark file has been moved or deleted since it was selected, the application will show an error when you try to generate a PDF and will not proceed until the issue is resolved.

**Step 5 — Create the PDF**

Click **Create PDF**. The PDF is saved to `output/labels.pdf` in the [cache folder](#where-your-data-is-stored) and immediately displayed in the preview panel on the right.

**Step 6 — Print**

Click **Print** to send the PDF to your printer.

- On first use a reminder dialog appears listing the required print settings. Tick **Don't show again** to suppress it in future.
- On Windows the application tries to open the OS print dialog directly. If your default PDF viewer does not support that (e.g. Microsoft Edge on Windows 11), the PDF is opened in the viewer instead — use **Ctrl + P** from there.
- On Linux the PDF is opened in your default PDF viewer (via `xdg-open`) — print from the viewer with **Ctrl + P**. Nothing is sent to the printer without a print dialog.
- Make sure to select **actual size** (100 %) in the print dialog — do not scale to fit.
- Select the correct paper tray if your printer has multiple trays.
- Print a test page on plain paper first and hold it against the label sheet at a light source to verify alignment before printing on the actual labels.

### Collection (Local mode)

The collection is your list of records in `labels.db` — artist, label, country, year and
catalog number shared by both sides, a title for side A and / or side B, and the date each side
was last printed. It exists in Local mode only; switching to Discogs mode leaves it untouched,
it is simply not reachable there, and Discogs mode behaves exactly as without it.

#### Working with the collection

Click **Load data** in the sidebar. The collection opens — one row per record with the columns
**A**, **B**, Artist, Title A, Title B, Label, Year, Cat. no., Country, **Printed A** and
**Printed B**. Click a column header to sort (the printed columns sort by date); the search field
filters live over all text columns (every word must match).

- **New record …**, **Edit …** (or double-click a row) and **Delete** change the collection at
  once. The record form has the same fields and checks as **Add entry** in the queue editor:
  Artist, Label, Country, Year and Catalog number plus a title for side A and / or side B.
  Deleting a record keeps its entries in the print queue; they only lose the link to the record.
- Tick the **A** / **B** boxes of the sides you want to print (a side without a title shows
  "–"). **Select all sides** ticks every side of the visible records, **Clear selection**
  unticks everything.
- **Add to print queue →** creates one entry per ticked side and opens the review table, as for
  a Discogs import: check the rows, then choose whether to **append** them to the queue or
  **replace** it. The collection closes and the main window shows the new queue. These queue
  entries are **linked** to their record side; entries saved with **Also save to collection**
  in the queue editor are linked too.

#### Printed marking

**Printed A** / **Printed B** show the date a side was last printed, in your system's date
format, or nothing if it was never printed.

- After a successful **Print** or **Create PDF**, if labels of the PDF are linked to the
  collection, the app asks once: *"Mark the {n} labels from the collection as printed?"*
  **Yes** sets today's date for the side of every linked label; labels that are not linked
  (e.g. one-off entries) are ignored. For the same unchanged queue the question is not asked
  again in this session — so **Create PDF** followed by **Print** asks only once; change the
  queue and it is asked again. If the PDF could not be created or the print could not be
  started (e.g. the watermark file is missing), there is no question. The system's print
  dialog itself is outside the app: if you cancel printing there, answer **No**.
- By hand: select records (Ctrl / Shift + click) and use **Mark as printed** (today's date for
  every side with a title) or **Mark as not printed** (clears both sides) — as buttons or in
  the context menu (right-click).
- **Only not printed** shows only records with at least one side with a title that was never
  printed. While it is on, **Select all sides** becomes **Select all unprinted sides** and ticks
  only those sides — e.g. to print every new record once.

#### Sync between the print queue and the collection

A linked queue entry carries the title of its record side plus the shared fields of the record.
When one side changes, the app offers to update the other:

- **Queue editor → collection.** When you **Save** the queue editor, the app counts the saved,
  linked entries whose title or shared fields differ from their record. If there are any, it
  asks once: *"{n} changed entries belong to records in the collection. Apply the changes to
  the collection too?"* — **Update collection** writes the changes into the records in the same
  transaction as the queue, **Only the print queue** leaves the collection as it is. If the A
  and the B entry of the same record were changed differently (e.g. two different artists), the
  entry further down in the table wins; a field changed in only one entry is taken from that
  entry. Printed dates are not touched.
- **Collection → queue.** When you edit a record whose linked queue entries would change, the
  app asks once: *"Also update the {n} entries in the print queue?"* **Yes** gives each entry
  the title of its side and the shared fields (an entry whose side no longer has a title keeps
  its title), and the main window reloads the queue.
- **Changing the side** of a linked entry in the queue editor removes its link — it would point
  to the wrong side of the record otherwise.

#### Collection CSV import and export

**Export CSV …** in the collection writes **all** records — regardless of the search and the
**Only not printed** filter — to `vinyl-collection-YYYY-MM-DD.csv` (proposed in your Documents
folder). **Import CSV …** reads such a file back. The format differs from the
[queue CSV](#csv-import-and-export):

| | Queue CSV (queue editor) | Collection CSV (collection) |
|---|---|---|
| One row per | label (side) | record |
| Header (export) | `Title;Artist;Label;Country;Year;Side;CatNo` | `Artist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB` |
| Required column | `Title` | `TitleA` or `TitleB` |
| Rows skipped | without title | without any title |
| Printed dates | — | ISO `YYYY-MM-DD` or empty |

Both use the same rules otherwise: export with semicolons as UTF-8 with BOM; import detects the
delimiter (comma, semicolon, tab) and the encoding (UTF-8 with / without BOM, Windows-1252), and
matches the header names case-insensitively in any order:

| Field | English header | German header |
|---|---|---|
| Artist | `Artist` | `Künstler`, `Kuenstler`, `Interpret` |
| Label | `Label` | `Label` |
| Country | `Country` | `Land` |
| Year | `Year` | `Jahr` |
| Catalog number | `CatNo` | `Katalognummer` |
| Title side A / B | `TitleA`, `TitleB` | `Titel A`, `Titel B` |
| Printed side A / B | `PrintedA`, `PrintedB` | `Gedruckt A`, `Gedruckt B` |

Printed dates are imported as ISO dates; `DD.MM.YYYY` (as a German spreadsheet program saves
dates) is accepted too, anything else is ignored.

**Duplicates.** A row is a duplicate if a record with the same artist and catalog number exists
— or, if the catalog number is empty, one with the same artist, title A and title B (compared
ignoring case and surrounding spaces). Rows further down in the same file that repeat an earlier
row count as duplicates too. If there are duplicates, the app asks once for the whole file:

- **Skip** — duplicates are left out;
- **Update existing** — the record gets the row's shared fields and titles; a printed date only
  if the row has one;
- **Cancel** — nothing is imported.

The whole file is written in one transaction. Afterwards the app reports how many records were
imported, updated and skipped (rows without a title plus skipped duplicates) and how many were
already up to date. Exporting and importing the same file again with **Update existing** leaves
the collection unchanged.

### Interface Overview

```
┌──────────────────────────┬──────────────────────────────────────────────┐
│ Vinyl Label Printer      │                                              │
│                          │                                              │
│ DATA                     │                                              │
│  Load data               │                                              │
│    Local / Discogs mode  │               PDF preview                    │
│  Queue                   │                                              │
│    12 labels ready       │                                              │
│                          │                                              │
│ PRINT                    │                                              │
│  Start position          │                                              │
│    Label 1 (R1 C1)       │                                              │
│  Create PDF              │      [ ← Back ]  Page 1 of 1  [ Next → ]     │
│    Ready                 │                                              │
│  [ Print ]               │                                              │
├──────────────────────────┴──────────────────────────────────────────────┤
│ ⚙ Settings                                  ● Discogs status   Mode     │
└─────────────────────────────────────────────────────────────────────────┘
```

The **⚙ Settings** button in the footer opens the Settings dialog: **Appearance** (theme,
language, watermark, printer calibration, debug logging), **Data source**, **Discogs account**
and **About** (version check).

### Discogs Import

The app can fetch your 7" singles directly from your Discogs collection (including catalog numbers), resolve A- and B-side track names automatically, and write the result to the print queue.

#### Step 1 — Create a personal access token

1. Log in at [discogs.com](https://www.discogs.com).
2. Go to [discogs.com/settings/developers](https://www.discogs.com/settings/developers).
3. Click **Generate Token**.
4. Copy the displayed token.

#### Step 2 — Switch to Discogs mode and enter credentials

1. Open **⚙ Settings → Discogs account** and click **Change token** — the setup panel of the
   Discogs dialog opens.
2. Enter your Discogs username and the token and click **Verify and save token**.
   The app verifies the token against the Discogs API once and saves it locally.
3. Select **Discogs** in **⚙ Settings → Data source**, then click **Load data** in the sidebar
   to open the Discogs dialog.

After a successful verification the dialog switches automatically to the collection panel. On subsequent opens the saved credentials are used directly — the setup panel is skipped.

#### Step 3 — Load your collection

Click **Load 7" Singles**. The app fetches all releases from your Discogs collection (all pages) and filters automatically for 7" format singles. A progress indicator shows the current page being loaded.

> The collection list is **cached locally in a SQLite database** (`discogs_cache.db` in the [cache folder](#where-your-data-is-stored)). Re-opening the dialog reuses the cached data as long as it is less than 6 hours old — no API call is made. Once the cache expires, the status bar shows a warning and a **Aktualisieren / Reload** button appears. This behaviour is required by the Discogs API Terms of Use.
>
> The cache belongs to one Discogs account: logging out clears it, and a cache created for a different username is discarded.

The table shows Title, Artist, Label, **Cat. No.** and Year. Use the search bar to filter the list by artist, title or catalog number (e.g. `PYR`).

#### Step 4 — Select singles and import

1. Tick the checkbox next to each single you want to import. Use **Select all** / **Deselect all** for bulk selection.
   - **Selections persist across searches.** You can search for "country", tick a few results, then search for "reggae" and tick more — all ticked entries are remembered regardless of which search is currently active.
   - A **selection counter** appears to the right of the Select all / Deselect all buttons: e.g. `2 selected`. When the current search filter hides some of your selections, the counter shows both totals: `3 selected (1 visible)` in a highlighted colour so you know there are picks outside the current view.
   - **Deselect all** only removes the checkmarks for the releases currently visible in the table. Selections from other search terms remain intact. Clear the search bar to see (and deselect) everything at once.
2. Click **Add to print queue**.
   The app loads the details (tracklist and country) of each selected release **on demand** from the Discogs release endpoint. Details are cached per release and reused for 6 hours (Discogs API ToU); older details are fetched again. All requests are throttled globally (≥ 1.1 s apart) to stay below the Discogs limit of 60 requests/min. Sides are resolved as follows:
   - **Simple single (exactly 1 A-side + 1 B-side):** two rows are created, one for each side, with the individual track title. A UK double-A single (`A` / `AA`) becomes A and B.
   - **EP / Maxi-single (multiple tracks):** one row per track; the side is always `A` or `B` (e.g. `A1`, `A2`, `B1`, `B2` → A, A, B, B).
   - **Two tracks with numeric positions** (e.g. `1`, `2`): mapped to A and B in order.
   - **Other sides are skipped:** tracks on C/D (e.g. a double 7") or numeric positions on releases with more than two tracks are left out (logged at info level).
   - **No A/B tracks at all, or the details could not be loaded:** no row is created — the release is listed in the import warning instead. A queue row never has an empty side.

   You can close the dialog with **Cancel** at any time — running requests are stopped.

#### Step 5 — Review and confirm

A **Review dialog** opens showing all expanded rows before anything is written to the print queue.

| Column | Editable | Notes |
|---|---|---|
| ☐ | Checkbox | Uncheck to exclude a row from the import |
| Title | Yes | Red background if empty (required) |
| Artist | Yes | |
| Label | Yes | |
| Cat. No. | Yes | Catalog number — stored with the entry and printed on the label |
| Country | Yes | |
| Year | Yes | |
| Side | Yes | Red background if empty (required); free text like `Side b` is saved as `B` |

**Editing:**

- Double-click or start typing to edit a cell. Edited cells flash yellow briefly.
- Drag rows to reorder them.
- Right-click a row to **delete** or **duplicate** it.
- Use the toolbar buttons to select all / none, delete selected rows, or add a blank row.
- The search bar filters visible rows by title or artist.

**Status bar** at the bottom shows the total number of rows, how many are checked, and how many have incomplete required fields.

**Confirm** (blue button) becomes active once at least one row is checked — including rows currently hidden by the search filter. Clicking it writes all checked rows (visible or hidden) to the print queue and closes both dialogs; unchecked rows are not written. If a search filter hides checked rows, the status bar says so (e.g. `2 of them hidden`). The main window reloads the queue count automatically.

If the print queue already contains entries, you are asked how to proceed:

| Button | Effect |
|---|---|
| **Append** (default) | Existing entries are kept; the new rows are added at the end |
| **Replace** | The queue is replaced by the new rows |
| **Cancel** | Nothing is written; you return to the review dialog |

The queue editor (sidebar **Queue**) never asks — there **Save** always replaces the queue with
the checked rows.

**Cancel** returns to the collection panel — your selection is preserved. As the reviewed rows
are not stored yet, the app first asks whether to save them, discard them or keep reviewing.

#### Privacy & security

- The token is stored exclusively in `credentials.json` in the [settings folder](#where-your-data-is-stored) on your local machine — outside the program folder, so it can never be committed to version control.
- On Linux/macOS file permissions are set to `600` (owner read/write only) automatically.
- The Discogs collection cache (`discogs_cache.db`) stays local as well.
- Click **Log out** (collection panel or **Settings → Discogs account**) to delete the stored credentials and the local collection cache immediately.

---

## Troubleshooting

### Labels are misaligned

Printed labels do not line up with the physical Avery 4780 sheet.

**1. Verify print scaling — this is the most common cause.**

In your print dialog, make sure:

| Setting | Required value |
|---|---|
| Scale / Size | **Actual size** (100 %) |
| Fit to page / Shrink to fit | **Off** |
| Margins | None / No adjustment |
| Paper size | A4 |
| Borderless printing | **Off** |

> On Windows with Microsoft Edge as the default PDF viewer, the "print" verb may open Edge's built-in print dialog, which defaults to "Fit to page". Switch to Adobe Acrobat Reader or another viewer that respects actual size, or use **Ctrl + P** and set the scale manually.

**2. Use the calibration workflow.**

If scaling is already correct but labels are still offset by a consistent amount in every row:

1. Open **Settings → Appearance → Printer Calibration**.
2. Click **Generate calibration PDF** — the sheet opens automatically.
3. Print the calibration sheet at **100 %** on plain paper.
4. Hold the printout against a physical Avery 4780 sheet in front of a light source.
5. Measure the vertical offset for several rows and note whether it is consistent.
6. If the offset is the same for all rows, increase or decrease **Vertical (Y) in mm** by that amount in 0.5 mm steps.
7. If the offset varies per row the printer has a non-linear feed — use the average measured offset as a starting point.
8. Repeat for the horizontal axis using **Horizontal (X) in mm** if needed.

**3. Check for non-uniform misalignment.**

If some rows are correct but others are not, the issue is mechanical (paper feed or roller wear) and cannot be fully corrected by a single offset value. In this case use the calibration PDF to identify which rows are affected and report the measurements to help characterise the problem.

---

### PDF preview is blank or missing

The preview panel requires **Poppler** to convert PDF pages to images. The `.deb` installs it
(`poppler-utils`) and the Setup.exe bundles it; only when running from source you install it
yourself:

| Platform | Fix |
|---|---|
| Linux | `sudo apt install poppler-utils` |
| Windows | Download from [github.com/oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), extract to `C:\poppler`, and add `C:\poppler\Library\bin` to the system PATH. |

Restart the application after installing Poppler. If the preview still does not appear, enable **Debug logging** under **Settings → Appearance → Developer** and check `app.log` in the [log folder](#where-your-data-is-stored) for a Poppler-related error.

---

### Print dialog does not open

| Platform | Symptom | Fix |
|---|---|---|
| Windows | Nothing happens after clicking Print | Your default PDF viewer does not register the "print" shell verb. The app falls back to opening the file — press **Ctrl + P** in the viewer. |
| Linux | Nothing opens | The app opens the PDF with `xdg-open`. Make sure a default PDF viewer is set (e.g. `xdg-mime default org.gnome.Evince.desktop application/pdf`) and `xdg-utils` is installed. |
| Linux | File opens in viewer but no print dialog | This is intended — click **File → Print** or press **Ctrl + P** inside the viewer. |

---

### Discogs import fails or stalls

| Symptom | Cause | Fix |
|---|---|---|
| "Token invalid" | Token revoked or entered incorrectly | Regenerate at [discogs.com/settings/developers](https://www.discogs.com/settings/developers) and re-enter via **Settings → Discogs account → Change token**. |
| "No connection to Discogs" | Network or firewall issue | Check internet connectivity; verify that `api.discogs.com` is reachable. |
| Import stalls during collection load | Discogs rate limit (60 requests/min) | Requests are throttled automatically; on HTTP 429 the app waits (`Retry-After`, otherwise 60 s) and retries up to 2 times, then shows a countdown — wait for the timer. |
| Import of many releases takes a while | Release details are loaded on demand, ≥ 1.1 s per uncached release | Expected. Details are cached for 6 hours, so re-importing the same releases is fast. |
| Collection asks for a reload after an update | The cache schema gained the catalog number | Click **Load 7" Singles / Reload** once; the next sync fills in the catalog numbers. |
| Country is empty | Country comes from the release details, which may not list one | Edit the Country field in the Review dialog. |
| "Cache expired" warning in collection dialog | Cache is older than 6 hours | Click **Reload** to fetch a fresh copy. This is required by the Discogs API Terms of Use. |
| A selected release is listed in the import warning | Its details could not be loaded, or it has no A/B tracks (e.g. numbered tracks only) | Add the rows manually in the queue editor (**Add entry** or **Add row**). |

---

## Technical Reference

### Project Structure

```
vinyl-label-printer/
├── main.py                        # Entry point — creates QApplication and MainWindow
├── __version__.py                 # App version string — read by the CI build and version_checker.py
├── requirements.txt                # pip dependencies
├── requirements-dev.txt            # test tools (pytest) — not needed at runtime
├── config/
│   ├── avery_formats.py           # Avery sheet dimensions and coordinate helpers
│   ├── settings.py                # Persistent JSON settings (watermark path, data source mode, theme, ...)
│   ├── stylesheet.py              # Global in-house QSS stylesheet builder (dark/light theming)
│   ├── themes.py                  # ThemeColors dataclass — dark/light color palettes
│   └── credentials.example.json   # Committed template — values intentionally empty
├── modules/
│   ├── child_env.py               # Environment for started programs (frozen Linux build)
│   ├── data_source.py             # DataSourceMode enum (LOCAL / DISCOGS)
│   ├── records.py                 # LabelRecord / CollectionRecord, sides, duplicates, queue ↔ record sync
│   ├── label_store.py             # SQLite labels.db (queue + collection) — the only code that talks to it
│   ├── csv_io.py                  # CSV import / export of the queue and the collection
│   ├── logger.py                  # Centralised rotating-file logger; debug toggle
│   ├── paths.py                   # All file locations: bundled resources, user dirs, legacy migration
│   ├── pdf_generator.py           # ReportLab — renders labels to PDF, dynamic font sizing
│   ├── printer.py                 # Cross-platform OS print dialog trigger
│   ├── i18n.py                    # All UI strings, language switching (DE / EN)
│   ├── discogs_client.py          # Discogs REST API client (verify, collection, release details; global throttle)
│   ├── discogs_cache.py           # SQLite cache: collection fields + per-release details (6 h ToU each)
│   ├── version_checker.py         # GitHub release check + semantic version comparison
│   └── credentials_manager.py     # Load/save/clear credentials.json
├── ui/
│   ├── app.py                     # QMainWindow — wires all components together (no menu bar)
│   ├── styles.py                  # Table/search-field style helpers used by dialogs
│   ├── sidebar_widget.py          # QWidget — left panel: data source, print queue, start grid, watermark
│   ├── footer_widget.py           # QWidget — footer bar: ⚙ Settings button + Discogs/mode status
│   ├── settings_dialog.py         # QDialog — Settings (Appearance, Data source, Discogs account, About)
│   ├── grid_widget.py             # QWidget — interactive 4×10 start-position grid
│   ├── preview_widget.py          # QWidget — pdf2image + QPixmap page viewer
│   ├── discogs_dialog.py          # QDialog — Discogs import (setup + collection panels)
│   ├── review_widget.py           # QDialog — print queue editor and import review table
│   ├── entry_dialog.py            # QDialog — "Add entry" / record form (one record, side A and / or B)
│   ├── collection_dialog.py       # QDialog — local record collection: printed dates, CSV (LOCAL mode)
│   └── theme_manager.py           # ThemeManager — theme setting, global stylesheet, live switching
└── tests/
    ├── conftest.py                # Headless Qt + throw-away user directories
    ├── test_theme_switch.py       # Regression test: theme switches restyle every open window
    ├── test_label_store.py        # labels.db: schema, order, side CHECK, transactions, versions
    ├── test_data_setup.py         # Old labels.db files open; leftover user files stay untouched
    ├── test_csv_io.py             # CSV delimiters, headers, encodings, round trip
    ├── test_queue_editor.py       # Entry form, saving / clearing the queue, unsaved changes, CSV
    ├── test_collection.py         # Collection: schema 1 → 2, records, links, dialog, CSV grouping
    └── test_collection_sync.py    # Printed marking, queue ↔ collection sync, collection CSV
```

User files (`settings.json`, `credentials.json`, `labels.db`, `discogs_cache.db`, generated
PDFs, `app.log`) are not part of the project tree — see
[Where your data is stored](#where-your-data-is-stored).

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | UI framework |
| reportlab | ≥ 4.0 | PDF generation |
| pdf2image | ≥ 1.17 | PDF → image for preview (requires Poppler system library) |
| Pillow | ≥ 10.0 | Image loading and watermark alpha processing |
| requests | ≥ 2.31 | HTTP client (Discogs API + GitHub version check) |
| platformdirs | ≥ 4.0 | Per-user config, data, cache and log folders |

The print queue (`labels.db`) and the Discogs cache use `sqlite3` from the Python standard
library; CSV import / export uses the standard `csv` module.

Dark / Light / Auto theming is implemented in-house (`config/themes.py`, `config/stylesheet.py`,
`ui/theme_manager.py`) — no external theming package is used.

### Avery 4780 Sheet Dimensions

All values in millimetres. Defined in `config/avery_formats.py`.

| Parameter | Value (mm) | Notes |
|---|---|---|
| Page width | 210.0 | A4 |
| Page height | 297.0 | A4 |
| Label width | 48.5 | |
| Label height | 25.4 | |
| Left margin | 8.0 | (210 − 4 × 48.5) / 2 — symmetric |
| Top margin | 21.5 | (297 − 10 × 25.4) / 2 — symmetric |
| Column gap | 0.0 | labels are edge-to-edge |
| Row gap | 0.0 | labels are edge-to-edge |
| Labels per sheet | 40 | 4 columns × 10 rows |

ReportLab uses points (1 pt = 25.4 / 72 mm). All mm values are converted internally via `mm_to_pt()` in `config/avery_formats.py`. The coordinate origin is at the **bottom-left** of the page; y increases upward.

### Label Layout

Each label (48.5 × 25.4 mm) contains five centred text lines:

| Line | Content               | Font           | Max size | Min size |
|------|-----------------------|----------------|----------|----------|
| 1    | Title                 | Helvetica      | 9 pt     | 5 pt     |
| 2    | Artist                | Helvetica-Bold | 8 pt     | 5 pt     |
| 3    | `---`                 | Helvetica      | 6 pt     | 6 pt     |
| 4    | Label CatNo (Country, Year) | Helvetica | 7 pt   | 4.5 pt   |
| 5    | Side (A or B)         | Helvetica-Bold | 14 pt    | 14 pt    |

Each field is **independently scaled down** from its maximum font size until the text fits within the usable label width (label width minus 4 pt horizontal padding on each side). Scaling stops at the minimum size; text that is still too wide is shortened with `…` so it never leaves the label.

The five-line block is vertically centred inside the label cell. If a watermark image is set it is drawn first (behind the text), centred and scaled to fit within a 4 pt inset, at approximately 10 % opacity.

**Info line formatting:** `Label CatNo (Country, Year)`, e.g. `Pyramid PYR 6013 (UK, 1967)`. Empty fields are omitted along with their separator — e.g. without a catalog number and country the line reads `Pyramid (1967)`; if Country and Year are both empty, the parentheses are dropped entirely.

### Module Reference

#### `config/avery_formats.py`

| Symbol | Type | Description |
|---|---|---|
| `AVERY_FORMATS` | `dict` | Sheet specifications keyed by format name |
| `get_format(name)` | `→ dict` | Returns the format dict; raises `KeyError` for unknown names |
| `mm_to_pt(mm)` | `→ float` | Converts mm to ReportLab points |
| `label_rect_pt(fmt, col, row)` | `→ (x, y_bottom, w, h)` | Returns label bounding box in points for a given grid position |

#### `config/settings.py`

Reads and writes `settings.json` in the config folder (`modules.paths.get_settings_file()`). The file is not shipped with the app — missing keys (or a missing file) fall back to defaults, and the file is created on the first save. Keys:

| Key | Type | Description |
|---|---|---|
| `watermark_path` | `string \| null` | Absolute path to the watermark image |
| `data_source_mode` | `"local" \| "discogs"` | Active data source; persisted across sessions |
| `theme` | `"auto" \| "dark" \| "light"` | UI colour scheme; `"auto"` follows the OS setting |
| `language` | `"DE" \| "EN"` | Active UI language |
| `last_version_check` | `string` | ISO timestamp of the last GitHub version check |
| `last_known_version` | `string` | Latest release tag fetched from GitHub (e.g. `"v0.3.0"`) |
| `debug_logging` | `boolean` | Whether debug logging is active; persists across restarts |
| `calibration_x_mm` | `number` | Horizontal label offset in mm applied at PDF generation; default `0.0` |
| `calibration_y_mm` | `number` | Vertical label offset in mm applied at PDF generation; default `0.0` |
| `show_print_hint` | `boolean` | Whether to show the print-settings reminder before printing; default `true` |

#### `modules/data_source.py`

| Symbol           | Description                                                   |
|------------------|---------------------------------------------------------------|
| `DataSourceMode` | `Enum` with members `LOCAL = "local"` and `DISCOGS = "discogs"` |

#### `modules/records.py`

| Symbol | Description |
|---|---|
| `LabelRecord` | Dataclass: `title`, `artist`, `label`, `country`, `year`, `side`, `catno` (default `""`); plus `id` and `source` of the row in `labels.db`, the link `record_id` / `record_side` to a collection record side and `pending_record` (a collection record created together with the row) — all ignored by `==` and by the PDF generator |
| `CollectionRecord` | Dataclass of a collection record: shared fields, `title_a`, `title_b`; plus `id`, `printed_a_at`, `printed_b_at`, `created_at`, `updated_at`. `unprinted_sides()`: sides with a title and no printed date |
| `printed_date(value)` | The local date of a `printed_*_at` value (UTC timestamp or ISO date), `None` if empty |
| `duplicate_key(record)` | Duplicate detection of the CSV imports: artist + catalog number, without a catalog number artist + both titles; trimmed, casefolded |
| `row_matches_record(row, record)` | Whether a linked queue row has its side's title and the record's shared fields |
| `record_with_rows(record, rows)` | The record with the edits of its queue rows, field by field; on conflicting edits the later row (table order) wins |
| `row_from_record(row, record)` | The queue row with its side's title (kept if empty) and the record's shared fields |
| `queue_rows_for_sides(record, sides)` | One linked queue row per side with a title, A before B |
| `group_rows_into_records(rows)` | CSV import grouping: A row directly followed by a B row with identical shared fields (trimmed) → one record, every other row → one record |
| `record_from_rows(rows)` | A collection record from the queue rows of one record |
| `normalise_side(value)` | Maps any side / position to `"A"` or `"B"` (`AA` → `B`, `A1` → `A`, `Seite B` → `B`, empty → `A`) |
| `resolve_side(value)` | Like `normalise_side()` but returns `None` for values that name no A/B side (used by the Discogs import) |

#### `modules/label_store.py`

The only code that talks to `labels.db`. Every function opens a short-lived connection
(`PRAGMA foreign_keys = ON`) and runs in one transaction (`BEGIN IMMEDIATE` … `COMMIT`,
`ROLLBACK` on any error). Default rollback journal, no WAL — `labels.db` stays a single file.

| Symbol | Description |
|---|---|
| `load_queue()` | The print queue as `LabelRecord`s, ordered by `position` |
| `replace_queue(records, source, new_records, record_updates)` | Makes `records` the whole queue in this order; rows with a known `id` keep `id`, `source` and `created_at`. `new_records` and each row's `pending_record` are created in the same transaction and the rows linked to them; `record_updates` (existing records) are written in it too |
| `append_to_queue(records, source, meta, new_records)` | Appends new rows; optional `meta` key/value pairs and new records are written in the same transaction |
| `queue_count()`, `get_meta(key)` | Number of queued entries; a value of the `meta` table |
| `list_records(search)`, `record_count()` | The collection sorted by artist and titles; `search`: every word in any text column |
| `get_record(id)`, `add_record(record)`, `update_record(record, sync_queue)`, `delete_record(id)`, `delete_records(ids)` | Collection CRUD; deleting keeps the record's queue rows and drops their link. `sync_queue`: also update the linked queue rows, same transaction |
| `queue_rows_to_sync(record)` | The linked queue rows that `update_record(record, sync_queue=True)` would change |
| `mark_sides_printed(sides)`, `mark_records_printed(ids)`, `clear_printed(ids)` | Printed marks: `(record id, side)` pairs; every side with a title; both sides cleared. `updated_at` is not changed |
| `record_ids_by_key()`, `count_duplicates(records)`, `import_records(records, update_existing)` | Collection CSV import in one transaction: duplicates (`duplicate_key()`) of the collection or of earlier rows are skipped or update the record; returns imported / updated / unchanged / skipped |
| `SCHEMA_VERSION`, `_MIGRATIONS` | Ordered schema steps; `PRAGMA user_version` holds the number applied. Later versions append steps |

Schema version 1:

```sql
CREATE TABLE print_queue (
    id         INTEGER PRIMARY KEY,
    position   INTEGER NOT NULL,                          -- explicit order
    title      TEXT    NOT NULL CHECK (title <> ''),
    artist     TEXT    NOT NULL DEFAULT '',
    label      TEXT    NOT NULL DEFAULT '',
    country    TEXT    NOT NULL DEFAULT '',
    year       TEXT    NOT NULL DEFAULT '',               -- text, as entered
    side       TEXT    NOT NULL CHECK (side IN ('A', 'B')),
    catno      TEXT    NOT NULL DEFAULT '',
    source     TEXT    NOT NULL DEFAULT 'manual',         -- manual | csv | discogs
    created_at TEXT    NOT NULL,                          -- ISO 8601, UTC
    updated_at TEXT    NOT NULL
);
CREATE INDEX print_queue_position ON print_queue (position);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
```

Schema version 2 (app 1.2) — the local collection; applied automatically to a 1.1 `labels.db`
(queue rows are kept, their links are `NULL`):

```sql
CREATE TABLE records (
    id           INTEGER PRIMARY KEY,
    artist       TEXT NOT NULL DEFAULT '',
    label        TEXT NOT NULL DEFAULT '',
    country      TEXT NOT NULL DEFAULT '',
    year         TEXT NOT NULL DEFAULT '',
    catno        TEXT NOT NULL DEFAULT '',
    title_a      TEXT NOT NULL DEFAULT '',
    title_b      TEXT NOT NULL DEFAULT '',
    printed_a_at TEXT,                                    -- ISO timestamp (UTC), ISO date (CSV) or NULL
    printed_b_at TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    CHECK (title_a <> '' OR title_b <> '')
);
CREATE INDEX records_artist  ON records (artist  COLLATE NOCASE);
CREATE INDEX records_title_a ON records (title_a COLLATE NOCASE);
CREATE INDEX records_title_b ON records (title_b COLLATE NOCASE);
ALTER TABLE print_queue ADD COLUMN record_id INTEGER
    REFERENCES records (id) ON DELETE SET NULL;           -- NULL: Discogs, one-off, 1.1 rows
ALTER TABLE print_queue ADD COLUMN record_side TEXT CHECK (record_side IN ('A', 'B'));
CREATE INDEX print_queue_record ON print_queue (record_id);
```

A `labels.db` written by a 1.1 pre-release may contain an extra `meta` key and `source` value of
a since removed one-time import; both are kept and ignored.

#### `modules/csv_io.py`

| Symbol | Description |
|---|---|
| `read_csv(path)` | Detects encoding (UTF-8 with / without BOM, else Windows-1252) and delimiter (`,` `;` tab), maps the header row (English / German names), returns the records and the number of rows skipped for an empty title; raises `CsvImportError` |
| `write_csv(path, records)` | English header, `;`, UTF-8 with BOM |
| `default_export_name()` | `vinyl-labels-YYYY-MM-DD.csv` |
| `read_collection_csv(path)` | Collection CSV (one row per record): same detection and header matching, `TitleA` / `TitleB` required, printed dates as ISO dates; returns `CollectionRecord`s and the number of rows without a title |
| `write_collection_csv(path, records)`, `default_collection_export_name()` | `Artist;Label;Country;Year;CatNo;TitleA;TitleB;PrintedA;PrintedB`, UTF-8 with BOM; `vinyl-collection-YYYY-MM-DD.csv` |

#### `modules/pdf_generator.py`

| Symbol | Description |
|---|---|
| `generate_pdf(records, output_path, format_name, start_position, watermark_path, debug_frames)` | Renders all records to a multi-page PDF; returns the resolved output path |
| `generate_calibration_pdf(output_path, fmt)` | Renders a diagnostic calibration sheet with row/column indices, expected X/Y ranges, crosshairs, corner marks, and mm rulers; saved to `output/calibration_avery4780.pdf` in the cache folder |
| `fit_text_to_width(c, text, max_width, font_name, size_max, size_min, step)` | Returns the largest font size ≤ `size_max` at which `text` fits within `max_width`; floors at `size_min` (the caller then truncates with `…` if needed) |
| `_WATERMARK_ALPHA` | Module constant (default `25`, range 0–255) — controls watermark opacity |

#### `modules/discogs_client.py`

| Symbol | Description |
|---|---|
| `DiscogsClient(username, token, cancel_event=None)` | Initialises a `requests.Session` with Discogs auth headers; setting the optional `threading.Event` aborts pending waits |
| `verify_token()` | `GET /oauth/identity` — returns `True` if valid, `False` if 401, raises `ConnectionError` on network failure |
| `fetch_collection(progress_callback)` | Paginates through all collection pages (sort: newest first); calls `progress_callback(page, total_pages)` between pages |
| `normalize_for_cache(releases)` | Normalises ALL releases for SQLite storage (collection fields only): `is_7inch`, `formats_json`, `date_added`, label name without disambiguation suffix (`Pyramid (2)` → `Pyramid`), `catno` (`none` → empty) |
| `fetch_release_details(release_id)` | `GET /releases/{id}` — returns `{"tracks": list[dict], "country": str}` with each `track` entry (headings / index entries skipped) mapped to side `A`/`B` via `map_tracks_to_sides()`; other sides are skipped |
| `map_tracks_to_sides(tracks, release_id)` | Maps positions to `A`/`B` (`AA` → `B`, `A2` → `A`); skips C/D and numeric positions, except exactly two numeric tracks → A, B |
| `REQUEST_TIMEOUT` | `(5, 30)` — connect / read timeout applied to every request |
| `MIN_REQUEST_INTERVAL_S` | `1.1` — minimum spacing between any two requests, enforced across all instances and threads |
| `DiscogsRequestCancelled` | Raised when a wait is aborted via the cancel event |

All HTTP calls go through a private `_request()` that applies the global throttle, logs `X-Discogs-Ratelimit-Remaining` (debug level) and retries HTTP 429 up to 2 times after `Retry-After` seconds (default 60 s); afterwards `requests.HTTPError` is raised as before.

#### `modules/discogs_cache.py`

SQLite-based persistent cache for Discogs data. Enforces the Discogs API Terms of Use: data older than 6 hours is treated as expired and must not be displayed. Two groups of fields have separate freshness:

| Group | Fields | Freshness |
|---|---|---|
| Collection | `title`, `artist`, `label`, `catno`, `year`, `formats_json`, `is_7inch`, `date_added` | Refreshed by every full sync; validity via `cache_meta.cached_at` |
| Details | `country`, `tracklist_json`, `details_fetched_at` | Fetched on demand per release; each release has its own 6 h TTL |

| Symbol | Description |
|---|---|
| `DiscogsCache()` | Opens (or creates) `discogs_cache.db` in the cache folder; runs schema migrations (adding `catno` invalidates the cache once so the next sync fills it) |
| `get_cache_status()` | Returns `has_cache`, `is_valid`, `cached_at`, `age_hours`, `total_items`, `items_7inch`, `username` |
| `get_7inch_releases()` | Returns all 7" releases ordered by `date_added DESC`; raises `RuntimeError` if cache is expired |
| `sync_releases(releases, username)` | Three-way diff on all collection fields: INSERT new, UPDATE changed (collection fields only — details are never touched), DELETE removed; returns `{"added", "updated", "removed", "unchanged"}` |
| `get_details(discogs_id)` | Returns `{"tracks", "country"}` if details are younger than 6 h, otherwise `None` |
| `save_details(discogs_id, tracks, country)` | Stores details with the current UTC timestamp |
| `is_date_added_populated()` | Returns `True` if any release has a `date_added` value (migration guard) |
| `clear()` | Wipes all cached releases and metadata |

Timestamps are stored as timezone-aware UTC ISO strings; naive values from older caches are read as UTC. Every connection is committed (or rolled back) and closed after use.

#### `modules/credentials_manager.py`

| Symbol | Description |
|---|---|
| `CredentialsManager()` | Reads/writes `credentials.json` in the config folder; copies from the bundled `credentials.example.json` if missing |
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

#### `modules/logger.py`

| Symbol | Description |
|---|---|
| `setup_logger(debug)` | Called once at startup; creates a `RotatingFileHandler` for `app.log` in the log folder (2 MB max, 3 backups) and, when `debug=True`, a `StreamHandler` for the console |
| `get_logger()` | Returns the named logger (`"vinyl_label_printer"`) for use in any module |
| `set_debug_mode(enabled)` | Switches the log level at runtime (WARNING ↔ DEBUG) without a restart; adds/removes the console handler accordingly; called when the user toggles the setting |

The toggle is exposed in **Settings → Appearance → Developer → Debug logging**. When active, a red badge appears in the footer; clicking it reopens the settings dialog on the Appearance tab.

#### `modules/paths.py`

| Symbol | Description |
|---|---|
| `resource_path(relative)` | Absolute path of a read-only resource shipped with the app — relative to `vinyl-label-printer/` when running from source, relative to the PyInstaller bundle (`sys._MEIPASS`) when frozen |
| `get_poppler_path()` | Bundled Poppler `bin` folder (Windows builds only) or `None`, in which case pdf2image uses Poppler from the system `PATH` |
| `get_config_dir()` / `get_data_dir()` / `get_cache_dir()` / `get_log_dir()` | Per-user directories via [platformdirs](https://github.com/tox-dev/platformdirs) (app name `vinyl-label-printer`, no author folder), created on demand; config and data use the roaming profile on Windows |
| `get_settings_file()`, `get_credentials_file()`, `get_labels_db_file()`, `get_discogs_cache_file()`, `get_output_dir()`, `get_log_file()` | Locations of the individual user files |
| `migrate_legacy_data()` | One-time copy of user files from the legacy app-relative layout; never overwrites, never raises; writes `legacy-migration.json` into the config dir on success |

#### `modules/version_checker.py`

| Symbol | Description |
|---|---|
| `GITHUB_API_URL` | Endpoint: `GET /repos/EJAIS/vinylsticker/releases` — called with `per_page=10`; the newest release with a plain `MAJOR.MINOR.PATCH` tag (optional `v` / `v.`) is used — pre-release tags such as `v0.4.0-rc1` are never reported as an update |
| `GITHUB_RELEASES_URL` | Releases page: linked in the update hint, and the fallback when `release_url` is unavailable |
| `get_latest_version(timeout)` | Fetches the newest release; returns a dict with `success`, `latest_version`, `tag_name`, `release_url`, `error` (`"network"` / `"api"` / `"no_releases"` / `"unknown"`) |
| `is_update_available(latest_version)` | Compares `latest_version` against the running `__version__` using tuple comparison; returns `True` if an update exists |
| `is_newer_than_latest(latest_version)` | `True` if the running `__version__` is newer than the latest stable release (e.g. 1.0.0 while only `v1.0.0-rc.1` is newer than `v0.4.0`); the About tab then says so instead of "latest version" |

#### `modules/child_env.py`

`restore_user_environment()` runs first in `main()`. In the frozen Linux build it gives the
programs the app starts (`xdg-open` → file manager / browser / PDF viewer, `QDesktopServices`,
pdf2image's `pdfinfo` / `pdftoppm`) the environment the user started the app with:
`LD_LIBRARY_PATH` is restored from `LD_LIBRARY_PATH_ORIG` (or removed), and the bundle-only
variables `LD_LIBRARY_PATH_ORIG`, `QT_PLUGIN_PATH`, `QML2_IMPORT_PATH` and `_PYI_*` are removed.
Otherwise these programs load the bundle's older libraries and crash. The running app is not
affected (glibc reads `LD_LIBRARY_PATH` only at process start). From source and on Windows it
does nothing. `main.py --print-child-env` (hidden, used by CI) prints the resulting environment
and runs the preview's Poppler call once.

#### `modules/printer.py`

Before opening the OS print dialog, `print_pdf()` shows a one-time `QMessageBox` reminding the user to select **Actual Size (100 %)** and disable **Fit to page**. The dialog includes a **Don't show again** checkbox; if checked, `show_print_hint` is set to `false` in `settings.json` and the dialog is suppressed on all subsequent prints.

| Platform | Mechanism |
|---|---|
| Windows | `os.startfile(path, "print")`; falls back to `os.startfile(path)` if no "print" verb is registered (e.g. Microsoft Edge as default viewer) |
| Linux | `xdg-open` — opens the default PDF viewer; the user prints from its print dialog (no direct `lp` printing) |
| macOS | `open -a Preview` |

#### `ui/styles.py`

`apply_table_style(table)` and `apply_search_style(widget)` — kept as no-op call sites in `review_widget.py` for backward compatibility. Table and search-field styling (border, grid colour, hover/selected states, focus ring) is now generated globally by `config/stylesheet.py` and applies automatically; these functions no longer do anything.

#### `ui/settings_dialog.py`

`SettingsDialog(QDialog)` — 4-tab settings panel, opened via the **⚙ Settings** button in the footer.

| Tab | Contents |
|---|---|
| Appearance | Theme (Automatic / Dark / Light), language (DE / EN), watermark select/clear, Printer Calibration, Developer (debug logging) |
| Data source | Switch between Local database and Discogs mode |
| Discogs account | Token setup, change token, log out |
| About | App info, license, author, version check, GitHub link |

Emits `mode_changed(str)` and `language_changed()` to `MainWindow`. A theme card calls
`ThemeManager.set_setting()`; the dialog restyles itself on `ThemeManager.theme_changed` like
every other window.

#### `ui/theme_manager.py`

`ThemeManager` (one per `QApplication`, `ThemeManager.instance()`) is the only place that
resolves and applies the theme:

| Member | Purpose |
|---|---|
| `set_setting(setting, persist=True)` | `"auto"`, `"dark"` or `"light"`; saves it (unless `persist=False`, used at startup) and applies it at once |
| `setting` / `resolved` / `colors` | Saved setting, applied theme (`"dark"` / `"light"`), active `ThemeColors` |
| `theme_changed(ThemeColors)` | Emitted after the global stylesheet was replaced |
| `setting_changed(str)` | Emitted when the setting changes, even if the applied theme stays the same |

`"auto"` uses `QStyleHints.colorScheme()` and follows `colorSchemeChanged` (and `paletteChanged`)
live. If the color scheme is unknown (e.g. Linux without a working xdg-desktop-portal), the
lightness of the platform palette's window color decides. The resolved theme and the reason are
logged.

Widgets that set colors themselves read `current_colors()` when they are built and connect one
method that re-applies them to `theme_changed`. `ThemedStyles` keeps per-widget stylesheet
builders for dialogs with many styled widgets. Connections to bound methods are dropped by PyQt
when the widget is destroyed, so closed dialogs never receive the signal.

#### `ui/discogs_dialog.py`

`DiscogsDialog(QDialog)` — two-panel stacked dialog.

| Panel      | Shown when                                                     |
|------------|----------------------------------------------------------------|
| Setup      | No valid credentials saved                                     |
| Collection | Valid credentials found or after successful token verification |

Table columns: ☐, Title, Artist, Label, Cat. No., Year; the live search matches artist, title and catalog number.

On open the dialog checks the SQLite cache via `DiscogsCache`: if valid (< 6 h) it populates the table instantly; if expired it shows a warning and blocks the table; if empty (or created for another account) it shows a first-load prompt. A full API pull syncs the cache and shows a brief sync report. There is no background tracklist prefetch — details are loaded at import time.

Selections persist across live-search queries via an internal `_selected_ids: set[int]` keyed on `discogs_id`. The table's `itemChanged` signal is blocked during repopulation to prevent recursive updates. **Select all** / **Deselect all** operate only on currently visible rows; hidden selections are preserved. A counter label shows `N selected` or `N selected (M visible)` when filtered results hide part of the selection. **Add to print queue** always reads from `_selected_ids` rather than from visible table rows.

Background workers:

| Class | Signal(s) | Description |
|---|---|---|
| `_VerifyWorker` | `success`, `failure(str)` | Calls `verify_token()` off the UI thread |
| `_FetchWorker` | `progress(int,int)`, `fetch_done(list)`, `error(int,str)` | Paginates `fetch_collection()`; a persistent 429 starts a 60 s countdown + auto-retry |
| `_ImportWorker` | `progress(int,int)`, `import_done(list,list)` | Per selected release: `get_details()` from the cache, otherwise `fetch_release_details()` + `save_details()`; maps tracks to A/B and expands into per-side rows |

All workers share one cancel event. Closing the dialog in any way (Cancel, Esc, after import, window close) calls `_shutdown_workers()` via `done()`, which sets the event and waits for the workers to stop.

#### `ui/review_widget.py`

`ReviewDialog(QDialog)` — the print queue editor (queue mode) and the review table of a Discogs
import (import mode). Writes through `label_store`; nothing is written before the user confirms.

| Feature | Details |
|---|---|
| Columns | ☐, Title, Artist, Label, Cat. No., Country, Year, Side |
| Required fields | Title, Side — highlighted red when empty |
| Edit feedback | Edited cell flashes yellow (600 ms) then returns to normal or red |
| Row operations | Drag & drop reorder; context menu delete / duplicate; toolbar add / delete |
| Editor tools (queue mode) | **Add entry** (`ui/entry_dialog.py`), **Import CSV** (append / replace the table), **Export CSV** (all rows, also unchecked and hidden) |
| Search | Live filter by title or artist (`setRowHidden`); **Select all / none** only affect visible rows |
| Confirm | Writes all checked rows (visible or hidden) via `label_store`; sides saved via `normalise_side()`; rows without a title are not saved. Queue mode (**Save**): `replace_queue()`, nothing checked empties the queue after a confirmation. Import mode: disabled until ≥ 1 row is checked |
| Unsaved changes | Cancel, Esc and the window's close button ask **Save / Discard / Cancel** if the table differs from what is stored |
| `import_mode` | `True` when opened from the Discogs import or the collection: asks **Append / Replace / Cancel** if the print queue is not empty (rows get source `discogs` / `collection`). `False` (the queue editor) always replaces |
| `collection` | Queue editor in Local mode: **Also save to collection** in the entry form and for the CSV import. Such rows belong to a pending record that is created on **Save** from the rows still in the table (checked or not), in the same transaction as the queue; CSV rows that duplicate an existing record are linked to it instead. Every row keeps its `record_id` / `record_side` through the editor, in both modes, unless its side is changed. On **Save**, edited linked rows trigger the **Update collection / Only the print queue** question (`collection_changes()`) |

#### `ui/collection_dialog.py`

`CollectionDialog(QDialog)` — the local record collection, opened by **Load data** in Local mode.

| Feature | Details |
|---|---|
| Columns | A ☐, B ☐, Artist, Title A, Title B, Label, Year, Cat. no., Country, Printed A, Printed B — sortable (printed columns by date); a side without a title shows "–" instead of a checkbox |
| Search | Live, via `label_store.list_records(search)` over all text columns; checked sides hidden by the search stay checked. **Only not printed** hides records without an unprinted side; **Select all sides** then becomes **Select all unprinted sides** |
| Record tools | **New record**, **Edit** (also double-click) — `EntryDialog` in record mode —, **Delete** (confirmation); written at once. An edit that changes linked queue rows asks whether to update them and emits `queue_changed` |
| Printed marks | **Mark as printed** / **Mark as not printed** for the selected records (buttons and context menu) |
| CSV | **Import CSV** (duplicates: Skip / Update existing / Cancel, one transaction) and **Export CSV** (all records) — `csv_io` collection format |
| Empty collection | A hint and a **New record** button in place of the table |
| Add to print queue | One queue row per checked side (`queue_rows_for_sides()`), reviewed in `ReviewDialog` (import mode, source `collection`); on confirm the dialog is accepted and the main window reloads the queue |

### Printer Calibration

If printed labels are slightly offset from the physical sheet, open **Settings → Appearance → Printer Calibration**:

| Control | Effect |
|---|---|
| **Horizontal (X) in mm** | Shifts all labels left (negative) or right (positive). Range: −5.0 to +5.0 mm, step 0.5 mm. |
| **Vertical (Y) in mm** | Shifts all labels up (positive) or down (negative). Range: −5.0 to +5.0 mm, step 0.5 mm. |
| **Reset** | Sets both values back to 0.0. |
| **Generate calibration PDF** | Creates `output/calibration_avery4780.pdf` in the cache folder and opens it immediately (see below). |

Values are applied to every generated PDF in real time and persisted to `settings.json` as `calibration_x_mm` and `calibration_y_mm`.

Use `debug_frames=True` in `generate_pdf()` (from a Python script or temporary code change) to render thin red rectangles around each label cell, which makes alignment errors clearly visible. When debug logging is enabled (**Settings → Appearance → Developer**), each PDF generation also logs all format values and a width/height consistency check to `app.log`.

### Calibration PDF

Click **Generate calibration PDF** in the Printer Calibration section to produce a diagnostic sheet (`output/calibration_avery4780.pdf` in the cache folder). The PDF opens automatically in the system viewer after generation.

Each of the 40 label cells contains:

- Row/column identifier (`R1 / C1` … `R10 / C4`)
- Expected Y range from the top of the sheet (e.g. `Y: 21.5–46.9 mm`)
- Expected X range from the left edge (e.g. `X: 8.0–56.5 mm`)
- A crosshair at the label centre
- Corner marks at the two top corners

Left-margin and top-margin mm rulers are printed along the page edges.

**How to use:**

1. Print the calibration PDF at **100 % (Actual Size)** on plain paper — no scaling.
2. Hold the printout against a physical Avery 4780 sheet in front of a light source.
3. For each row note the vertical offset between the printed crosshair and the physical label centre.
4. If all rows are equally offset → adjust `calibration_y_mm` by that amount.
5. If offsets differ per row → the printer has a non-linear feed error; use the per-row measurements to determine the best average correction.
6. Repeat for the horizontal axis using `calibration_x_mm`.

### Adding a Language

1. Open `modules/i18n.py`.
2. Copy the `"DE"` block and paste it with a new ISO 639-1 key (e.g., `"FR"`).
3. Translate all string values.
4. The new language will automatically appear in **⚙ Settings → Appearance** at next launch — no other code changes are needed.

### Building from source (PyInstaller)

The app can be bundled into a self-contained folder with [PyInstaller](https://pyinstaller.org/)
using the spec file in `packaging/`. Run from the repository root with the app's requirements
installed:

```bash
pip install -r vinyl-label-printer/requirements.txt pyinstaller
pyinstaller --noconfirm --clean packaging/vinyl-label-printer.spec
dist/vinyl-label-printer/vinyl-label-printer --version
```

The result is `dist/vinyl-label-printer/` (onedir build). On Linux, Poppler is not bundled —
install `poppler-utils` as usual. On Windows, extract the `Library/bin` folder of a
[Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) release to
`packaging/poppler/bin` before building to bundle it; otherwise Poppler is taken from `PATH`.
The CI workflow `.github/workflows/build.yml` builds both platforms the same way.

On Linux, `packaging/linux/build_deb.sh` turns the bundle into
`vinyl-label-printer_<version>_amd64.deb` with [fpm](https://fpm.readthedocs.io/). The CI builds
it on Ubuntu 22.04 and installs it in fresh Ubuntu 22.04 and 24.04 containers as a test; the
script's header lists its requirements and the package layout.

On Windows, [Inno Setup](https://jrsoftware.org/isinfo.php) 6.3+ turns the bundle into
`dist\VinylLabelPrinterSetup-<version>.exe`; pass the version from `__version__.py`:

```powershell
ISCC /DAppVersion=0.4.0 packaging\windows\vinyl-label-printer.iss
```

Versions and releases: `__version__.py` always holds a plain `X.Y.Z`. The CI computes the
package version once with `packaging/package_version.sh` and passes it to both builds. Branch
and pull request builds and a tag `vX.Y.Z` build `X.Y.Z`; a tag `vX.Y.Z-<suffix>` (e.g.
`v1.0.0-rc.1`, `X.Y.Z` must match `__version__.py`) builds `1.0.0-rc.1`, with the Debian
version `1.0.0~rc.1` so it sorts before `1.0.0`. On `v*` tags the release job publishes the
GitHub Release. Every other run executes it as a dry run (downloads the packages, computes
`SHA256SUMS.txt`, lists the files in the job summary, creates nothing); a manual run
(*Actions → Build → Run workflow*) can set `release_dry_run` or simulate a tag with
`dry_run_tag` to check a release's file names before tagging it.

The app icon is drawn in `packaging/icons/icon.svg`; the `.ico` and the Linux hicolor PNGs next
to it, plus the window icon `vinyl-label-printer/icons/vinyl-label-printer.png` (a copy of the
256 px PNG, used from source and in the frozen build), are
generated from it and committed. After changing the SVG, regenerate them with
`packaging/icons/build_icons.py` (instructions in its docstring).
