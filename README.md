# Vinyl Label Printer

A desktop application for printing 7" vinyl record labels on **Avery Zweckform 4780** label sheets (A4, 4 × 10 = 40 labels per sheet).

Made with :heart: and ClaudeCode - by a Collector for Collectors.

+ Local database (Excel) or Discogs integration.
+ Discogs integration reads your 7" collection including **catalog numbers**, loads A/B sides on demand at import time, and caches data locally (SQLite, 6-hour expiry per Discogs API ToU — for the collection and for each release's details).
+ Catalog number is shown, editable and printed: the info line reads `Label CatNo (Country, Year)`, e.g. `Pyramid PYR 6013 (UK, 1967)`.
+ Sides are always printed as **A** or **B** (`A1`/`A2` → A, UK double-A side `AA` → B).
+ Discogs imports ask whether to **append** to or **replace** an existing print queue.
+ Watermark option available (main window sidebar and **⚙ Settings → Appearance**).
+ Dark / Light theme via **⚙ Settings → Appearance** — follows the OS setting until you pick one explicitly.
+ Printer calibration with X/Y fine-tuning and a built-in calibration PDF generator (**⚙ Settings → Appearance → Printer Calibration**).

![Picture of an example label](https://github.com/EJAIS/vinylsticker/blob/main/examples/label_with_watermark.png)

Currently in BETA status; please get yourself familiar (if you arent already) with the needed tools. Executables are planned, but not ready yet.
Please feel free to contact me for bugs and feature requests.

The application UI is available in **German (DE)** and **English (EN)**, switchable at runtime via **⚙ Settings → Appearance**. This README uses English throughout.

---

## Table of Contents

1. [Installation (Linux)](#installation-linux)
2. [Installation (Windows)](#installation-windows)
3. [Where your data is stored](#where-your-data-is-stored)
4. [User Manual](#user-manual)
   - [Requirements](#requirements)
   - [Manual Installation](#manual-installation)
   - [Workflow](#workflow)
   - [Interface Overview](#interface-overview)
   - [Discogs Import](#discogs-import)
5. [Troubleshooting](#troubleshooting)
   - [Labels are misaligned](#labels-are-misaligned)
   - [PDF preview is blank or missing](#pdf-preview-is-blank-or-missing)
   - [Print dialog does not open](#print-dialog-does-not-open)
   - [Discogs import fails or stalls](#discogs-import-fails-or-stalls)
6. [Technical Reference](#technical-reference)
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

## Installation (Linux)

### Schnellinstallation / Quick install

```bash
curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh | bash
```

### Update

```bash
curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh | bash
```

> **Note:** When updating via `curl | bash`, the script runs non-interactively
> and updates automatically without a confirmation prompt.
> To update interactively (with confirmation prompt):
>
>     curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh \
>          -o /tmp/install.sh && bash /tmp/install.sh

The script automatically detects whether an installation already
exists and performs a fresh install or an update accordingly.
Your user data (database, settings, Discogs token) is stored outside
the program folder and is not touched by updates (see
[Where your data is stored](#where-your-data-is-stored)).

### Uninstall

If you have `install.sh` saved locally:

```bash
bash install.sh --uninstall
```

Via curl (recommended):

```bash
curl -sSL https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.sh \
     -o /tmp/install.sh && bash /tmp/install.sh --uninstall
```

> Your user data (database.xlsx, settings, Discogs token) is stored outside
> the program folder and is not removed (see
> [Where your data is stored](#where-your-data-is-stored)). Files left in the
> program folder by older versions are backed up first; the backup location
> is shown at the end.

### Voraussetzungen / Prerequisites

- Linux Mint, Ubuntu 22.04+ oder Debian 12+
- Python 3.10+
- Internetverbindung (für Download)
- sudo-Rechte (nur für System-Pakete)

Poppler and the required Qt system libraries are installed automatically via `apt` during setup.

### Database

The app ships with an example database that is copied automatically on first start
to `~/.local/share/vinyl-label-printer/database.xlsx` (see
[Where your data is stored](#where-your-data-is-stored)). If the file is missing, restart the
app and it is created again.

### Manual installation (other Linux distributions)

For distributions the script doesn't target, or to run from source, see [Manual Installation](#manual-installation) below.

---

## Installation (Windows)

### Schnellinstallation / Quick install

Open PowerShell, then run:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.ps1" -OutFile "$env:TEMP\install.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1"
```

### Update

Run the same command again:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.ps1" -OutFile "$env:TEMP\install.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1"
```

The script automatically detects whether an installation already
exists and performs a fresh install or an update accordingly.
Your user data (database, settings, Discogs token) is stored outside
the program folder and is not touched by updates (see
[Where your data is stored](#where-your-data-is-stored)).

> **Note:** The Windows installer always runs interactively
> and will ask for confirmation before updating.
> There is no silent/pipe mode on Windows.

### Uninstall

If you have `install.ps1` saved locally:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
```

Via web (recommended):

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/EJAIS/vinylsticker/main/install.ps1" -OutFile "$env:TEMP\install.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\install.ps1" -Uninstall
```

> Your user data (database.xlsx, settings, Discogs token) is stored outside
> the program folder and is not removed (see
> [Where your data is stored](#where-your-data-is-stored)). Files left in the
> program folder by older versions are backed up first; the backup location
> is shown at the end.

### Voraussetzungen / Prerequisites

- Windows 10 oder Windows 11
- Python 3.10+ (<https://www.python.org/downloads/>)
  → Check "Add Python to PATH" during installation!
- PowerShell 5.1+ (pre-installed)
- Internetverbindung

Poppler for the PDF preview is downloaded and configured automatically.

### Database

The app ships with an example database that is copied automatically on first start
to `%APPDATA%\vinyl-label-printer\database.xlsx` (see
[Where your data is stored](#where-your-data-is-stored)). If the file is missing, restart the
app and it is created again.

### Manual installation (macOS / running from source)

To run from source instead of using the installer, see [Manual Installation](#manual-installation) below.

---

## Where your data is stored

The app keeps your files in per-user folders, separate from the program itself, so updating,
reinstalling or uninstalling the app never touches them. The folders are created on first use.

| Content | Linux | Windows |
|---|---|---|
| Settings (`settings.json`), Discogs credentials (`credentials.json`) | `~/.config/vinyl-label-printer/` | `%APPDATA%\vinyl-label-printer\` |
| Your database (`database.xlsx`) | `~/.local/share/vinyl-label-printer/` | `%APPDATA%\vinyl-label-printer\` |
| Discogs cache (`discogs_cache.db`), generated PDFs (`output/`) | `~/.cache/vinyl-label-printer/` | `%LOCALAPPDATA%\vinyl-label-printer\Cache\` |
| Log file (`app.log`) | `~/.local/state/vinyl-label-printer/log/` | `%LOCALAPPDATA%\vinyl-label-printer\Logs\` |

On Linux the `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` and `XDG_STATE_HOME`
variables are respected. On Windows, `%APPDATA%` is `C:\Users\<you>\AppData\Roaming` and
`%LOCALAPPDATA%` is `C:\Users\<you>\AppData\Local`.

To edit your database in Excel or LibreOffice Calc, open **⚙ Settings → Data source** — the
**Data folder** section shows the path and has an **Open folder** button.

If no `database.xlsx` exists when the app starts, the example database is copied into the
data folder automatically.

### One-time migration from older versions

Older versions kept all files next to the program code (`config/`, `data/`). On the first start
of a newer version the app **copies** `settings.json`, `credentials.json`, `database.xlsx` and
`discogs_cache.db` into the folders above. It looks in:

1. the program folder itself (git clone or `install.sh` / `install.ps1` installation),
2. the default `install.sh` folder `~/vinyl-label-printer` (Linux) or the `install.ps1` folder
   `%LOCALAPPDATA%\vinyl-label-printer` (Windows).

The original files are left untouched and existing files are never overwritten. Logs are not
migrated. The migration runs once — a marker file `legacy-migration.json` in the settings folder
records what was copied. To run it again, close the app, delete that marker file and start the
app (files that already exist in the new folders are still never overwritten).

---

## User Manual

### Requirements

| Component | Details |
|---|---|
| Operating system | Windows 10/11, or Linux Mint / Ubuntu 22.04+ / Debian 12+ |
| Python | 3.10 or newer |
| Poppler | Required for PDF preview — installed automatically by the installer, or manually for [source installs](#manual-installation) |

### Manual Installation

> Most users should use the automated installer instead — see [Installation (Linux)](#installation-linux) or [Installation (Windows)](#installation-windows) above; it installs the app, creates the launcher/start script and desktop entry, and handles updates automatically.
> Use the steps below only to run from source — for development, contributing, or a platform the installer doesn't cover (e.g. macOS or an unsupported Linux distribution).

---

#### Manual Installation — Windows

##### Prerequisites (Windows)

+ Python 3.10+ — <https://www.python.org/downloads/>
  Important: check "Add Python to PATH" during installation!
+ Git — <https://git-scm.com>

##### Setup (Windows)

```powershell
git clone https://github.com/EJAIS/vinylsticker.git
cd vinylsticker/vinyl-label-printer

python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` fails:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

##### Install Poppler (Windows)

Required for PDF preview.

1. Download: <https://github.com/oschwartz10612/poppler-windows/releases>
2. Extract to: `C:\poppler`
3. Add to PATH: Search → "Environment Variables" → Path → New: `C:\poppler\Library\bin`

##### Create start.bat (Windows)

`start.bat` is **not** included in the repository — create it manually. Add a file
`start.bat` in the `vinyl-label-printer/` folder with the following content:

```bat
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
echo.
echo === App closed. Press any key to exit ===
pause
```

##### Start the app (Windows)

```powershell
venv\Scripts\Activate.ps1
python main.py
```

Or double-click `start.bat` (created above).

---

#### Manual Installation — Linux (Ubuntu/Debian/Mint)

##### Prerequisites (Linux)

```bash
sudo apt install python3 python3-venv python3-pip
sudo apt install poppler-utils libxcb-cursor0
```

##### Setup (Linux)

```bash
git clone https://github.com/EJAIS/vinylsticker.git
cd vinylsticker/vinyl-label-printer

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

##### Create start.sh (Linux)

`start.sh` is **not** included in the repository — create it manually. Add a file
`start.sh` in the `vinyl-label-printer/` folder with the following content:

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 main.py
echo ""
echo "=== App closed. Press Enter to exit ==="
read
```

Make executable:

```bash
chmod +x start.sh
```

##### Start the app (Linux)

```bash
source venv/bin/activate
python3 main.py
```

Or: `./start.sh` — or double-click in the file manager.

##### Linux Desktop Shortcut (optional)

For an entry in the application menu, create
`~/.local/share/applications/vinyl-label-printer.desktop`:

```ini
[Desktop Entry]
Name=Vinyl Label Printer
Comment=Print 7" vinyl record labels
Exec=/bin/bash -c "cd /PATH/TO/vinyl-label-printer && source venv/bin/activate && python3 main.py"
Icon=printer
Terminal=false
Type=Application
Categories=Utility;
```

Replace `/PATH/TO` with the actual path, e.g.:
`/home/alexander/Coding_Local/vinylsticker/vinyl-label-printer`

---

> **Note on `pip`:** Always activate the venv first — then `pip` works identically on both
> platforms. On Linux without a venv, use `pip3` instead.

#### Place your Excel file

On first start the app copies the example from the `/examples` folder into its data folder.
Replace that `database.xlsx` with your own file — **⚙ Settings → Data source → Open folder**
opens the folder (see [Where your data is stored](#where-your-data-is-stored)).

---

### Workflow

#### Choosing a data source

At the top of the left panel, the **Data source** group lets you choose between two modes:

| Mode | Description |
|---|---|
| **Local database** | Reads the print queue from the Excel file (`database.xlsx` in the [data folder](#where-your-data-is-stored)). This is the default. |
| **Discogs** | Fetches your 7" singles from your Discogs collection. The **Load from Discogs** button is enabled only in this mode. |

The selected mode is **persisted across sessions**.

**Switching to Discogs:**

- If no Discogs credentials are saved yet, a setup dialog appears. You can set up the token immediately or cancel — the switch is reverted on cancel.
- If the local print queue already contains entries, a confirmation dialog points out that the queue will be changed by the next import. When you confirm an import, the app asks whether to **Append** the new entries or **Replace** the queue (see [Discogs Import](#discogs-import)).

**Switching back to Local database:**

- An informational message confirms the switch. The existing print queue is preserved; no data is deleted.

**Status bar** at the bottom of the window reflects the active mode:

- Local: 🗄 Local database | N entries
- Discogs: 🌐 Discogs | Signed in as _username_ | N entries

---

#### Option A — Manual: prepare the Excel file

The application reads from the **Print** sheet of your Excel workbook. Each row represents one label to be printed. Fill in the following columns (A–G):

| Column | Header | Description | Example |
|---|---|---|---|
| A | Title | Record title | I Won't Let You Go |
| B | Artist | Artist or band name | Blues Busters |
| C | Label | Record label | Kentone |
| D | Country | Country of origin | Japan |
| E | Year | Release year | 2014 |
| F | Side | Vinyl side — `A` or `B` (see below) | A |
| G | CatNo | Catalog number (optional) | RE-001 |

Files created before column G existed still load — the catalog number is simply empty.

**Side values** are always normalised to `A` or `B` (case-insensitive): prefixes like `Seite`, `Side`, `-` or `:` are ignored; `A`, `A1`, `A2` → **A**; `B`, `B1`, `B2` → **B**; the UK double-A side `AA` → **B**; anything unrecognised → **A**.

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

Click **Generate PDF**. The PDF is saved to `output/labels.pdf` in the [cache folder](#where-your-data-is-stored) and immediately displayed in the preview panel on the right.

Changing the start position after a PDF has been generated automatically regenerates the PDF and updates the preview.

**Step 5 — Print**

Click **Print** to send the PDF to your printer.

- On first use a reminder dialog appears listing the required print settings. Tick **Don't show again** to suppress it in future.
- On Windows the application tries to open the OS print dialog directly. If your default PDF viewer does not support that (e.g. Microsoft Edge on Windows 11), the PDF is opened in the viewer instead — use **Ctrl + P** from there.
- On Linux the PDF is opened in your default PDF viewer (via `xdg-open`) — print from the viewer with **Ctrl + P**. Nothing is sent to the printer without a print dialog.
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
│ [ Generate PDF ]                 │                                      │
│ [ Print        ]                 │                                      │
└──────────────────────────────────┴──────────────────────────────────────┘

Footer bar (not shown above): **⚙ Settings** button on the left opens the Settings dialog
(**Appearance** — theme + language, **Data source**, **Discogs account**, **About**);
the Discogs connection status and active mode badge are shown on the right.
```

### Discogs Import

The app can fetch your 7" singles directly from your Discogs collection (including catalog numbers), resolve A- and B-side track names automatically, and write the result to the print queue — all without touching the Excel file manually.

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

A **Review dialog** opens showing all expanded rows before anything is written to the Excel file.

| Column | Editable | Notes |
|---|---|---|
| ☐ | Checkbox | Uncheck to exclude a row from the import |
| Title | Yes | Red background if empty (required) |
| Artist | Yes | |
| Label | Yes | |
| Cat. No. | Yes | Catalog number — written to column G and printed on the label |
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

**Confirm** (blue button) becomes active once at least one row is checked — including rows currently hidden by the search filter. Clicking it writes all checked rows (visible or hidden) to the Print sheet and closes both dialogs; unchecked rows are not written. If a search filter hides checked rows, the status bar says so (e.g. `2 of them hidden`). The main window reloads the queue count automatically.

If the print queue already contains entries, you are asked how to proceed:

| Button | Effect |
|---|---|
| **Append** (default) | Existing entries are kept; the new rows are added at the end |
| **Replace** | The queue is replaced by the new rows |
| **Cancel** | Nothing is written; you return to the review dialog |

Opening the queue for editing via the sidebar never asks — there the edited list always replaces the queue.

**Cancel** returns to the collection panel — your selection is preserved.

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

The preview panel requires **Poppler** to convert PDF pages to images.

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
| A selected release is listed in the import warning | Its details could not be loaded, or it has no A/B tracks (e.g. numbered tracks only) | Add the rows manually in the Review dialog (**Add row**) or via the Excel file. |

---

## Technical Reference

### Project Structure

```
vinyl-label-printer/
├── main.py                        # Entry point — creates QApplication and MainWindow
├── __version__.py                 # App version string — read by the installer and version_checker.py
├── requirements.txt                # pip dependencies
├── start.sh                       # Linux launcher (generated by install.sh; create manually for source installs)
├── config/
│   ├── avery_formats.py           # Avery sheet dimensions and coordinate helpers
│   ├── settings.py                # Persistent JSON settings (watermark path, data source mode, theme, ...)
│   ├── stylesheet.py              # Global in-house QSS stylesheet builder (dark/light theming)
│   ├── themes.py                  # ThemeColors dataclass — dark/light color palettes
│   └── credentials.example.json   # Committed template — values intentionally empty
├── modules/
│   ├── data_source.py             # DataSourceMode enum (LOCAL / DISCOGS)
│   ├── excel_reader.py            # openpyxl — loads/writes Print sheet, loads Database
│   ├── logger.py                  # Centralised rotating-file logger; debug toggle
│   ├── paths.py                   # All file locations: bundled resources, user dirs, legacy migration
│   ├── pdf_generator.py           # ReportLab — renders labels to PDF, dynamic font sizing
│   ├── printer.py                 # Cross-platform OS print dialog trigger
│   ├── i18n.py                    # All UI strings, language switching (DE / EN)
│   ├── discogs_client.py          # Discogs REST API client (verify, collection, release details; global throttle)
│   ├── discogs_cache.py           # SQLite cache: collection fields + per-release details (6 h ToU each)
│   ├── version_checker.py         # GitHub release check + semantic version comparison
│   └── credentials_manager.py     # Load/save/clear credentials.json
└── ui/
    ├── app.py                     # QMainWindow — wires all components together (no menu bar)
    ├── styles.py                  # Table/search-field style helpers used by dialogs
    ├── sidebar_widget.py          # QWidget — left panel: data source, print queue, start grid, watermark
    ├── footer_widget.py           # QWidget — footer bar: ⚙ Settings button + Discogs/mode status
    ├── settings_dialog.py         # QDialog — Settings (Appearance, Data source, Discogs account, About)
    ├── grid_widget.py             # QWidget — interactive 4×10 start-position grid
    ├── preview_widget.py          # QWidget — pdf2image + QPixmap page viewer
    ├── discogs_dialog.py          # QDialog — Discogs import (setup + collection panels)
    └── review_widget.py           # QDialog — editable review table before queue write
```

User files (`settings.json`, `credentials.json`, `database.xlsx`, `discogs_cache.db`, generated
PDFs, `app.log`) are not part of the project tree — see
[Where your data is stored](#where-your-data-is-stored).

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.4 | UI framework |
| reportlab | ≥ 4.0 | PDF generation |
| openpyxl | ≥ 3.1 | Excel file reading and writing |
| pdf2image | ≥ 1.17 | PDF → image for preview (requires Poppler system library) |
| Pillow | ≥ 10.0 | Image loading and watermark alpha processing |
| requests | ≥ 2.31 | HTTP client (Discogs API + GitHub version check) |

Dark / Light / Auto theming is implemented in-house (`config/themes.py`, `config/stylesheet.py`) — no external theming package is used.

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

#### `modules/excel_reader.py`

| Symbol | Description |
|---|---|
| `LabelRecord` | Dataclass: `title`, `artist`, `label`, `country`, `year`, `side`, `catno` (default `""`) |
| `COLUMNS` | Sheet header: `Title`, `Artist`, `Label`, `Country`, `Year`, `Side`, `CatNo` (columns A–G) |
| `load_print_queue(path)` | Reads the `Print` sheet; skips blank rows; normalises `side`; files without column G load with `catno=""` |
| `load_database(path)` | Reads the `Database` sheet in read-only mode |
| `write_print_queue(path, records)` | Overwrites the `Print` sheet with the given `LabelRecord` list (all 7 columns) |
| `normalise_side(value)` | Maps any side / position to `"A"` or `"B"` (`AA` → `B`, `A1` → `A`, `Seite B` → `B`, empty → `A`) |

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
| `get_settings_file()`, `get_credentials_file()`, `get_database_file()`, `get_discogs_cache_file()`, `get_output_dir()`, `get_log_file()` | Locations of the individual user files |
| `migrate_legacy_data()` | One-time copy of user files from the legacy app-relative layout; never overwrites, never raises; writes `legacy-migration.json` into the config dir on success |
| `seed_example_database()` | Copies the bundled example `database.xlsx` into the data dir if none exists |

#### `modules/version_checker.py`

| Symbol | Description |
|---|---|
| `GITHUB_API_URL` | Endpoint: `GET /repos/EJAIS/vinylsticker/releases` — called with `per_page=10`; the newest release with a plain `MAJOR.MINOR.PATCH` tag (optional `v` / `v.`) is used — pre-release tags such as `v0.4.0-rc1` are never reported as an update |
| `GITHUB_RELEASES_URL` | Fallback URL opened when `release_url` is unavailable |
| `get_latest_version(timeout)` | Fetches the newest release; returns a dict with `success`, `latest_version`, `tag_name`, `release_url`, `error` (`"network"` / `"api"` / `"no_releases"` / `"unknown"`) |
| `is_update_available(latest_version)` | Compares `latest_version` against the running `__version__` using tuple comparison; returns `True` if an update exists |

#### `modules/printer.py`

Before opening the OS print dialog, `print_pdf()` shows a one-time `QMessageBox` reminding the user to select **Actual Size (100 %)** and disable **Fit to page**. The dialog includes a **Don't show again** checkbox; if checked, `show_print_hint` is set to `false` in `settings.json` and the dialog is suppressed on all subsequent prints.

| Platform | Mechanism |
|---|---|
| Windows | `os.startfile(path, "print")`; falls back to `os.startfile(path)` if no "print" verb is registered (e.g. Microsoft Edge as default viewer) |
| Linux | `xdg-open` — opens the default PDF viewer; the user prints from its print dialog (no direct `lp` printing) |
| macOS | `open -a Preview` |

#### `ui/styles.py`

`apply_table_style(table)` and `apply_search_style(widget)` — kept as no-op call sites in `discogs_dialog.py` and `review_widget.py` for backward compatibility. Table and search-field styling (border, grid colour, hover/selected states, focus ring) is now generated globally by `config/stylesheet.py` and applies automatically; these functions no longer do anything.

#### `ui/settings_dialog.py`

`SettingsDialog(QDialog)` — 4-tab settings panel, opened via the **⚙ Settings** button in the footer.

| Tab | Contents |
|---|---|
| Appearance | Theme (Dark / Light), language (DE / EN), watermark select/clear, Printer Calibration, Developer (debug logging) |
| Data source | Switch between Local database and Discogs mode |
| Discogs account | Token setup, change token, log out |
| About | App info, license, author, version check, GitHub link |

Emits `theme_changed(str)`, `mode_changed(str)`, and `language_changed()` to `MainWindow`.

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

`ReviewDialog(QDialog)` — editable preview table before writing to the Print sheet.

| Feature | Details |
|---|---|
| Columns | ☐, Title, Artist, Label, Cat. No., Country, Year, Side |
| Required fields | Title, Side — highlighted red when empty |
| Edit feedback | Edited cell flashes yellow (600 ms) then returns to normal or red |
| Row operations | Drag & drop reorder; context menu delete / duplicate; toolbar add / delete |
| Search | Live filter by title or artist (`setRowHidden`); **Select all / none** only affect visible rows |
| Confirm | Writes all checked rows (visible or hidden) via `write_print_queue()`; sides saved via `normalise_side()`; disabled until ≥ 1 row is checked |
| `import_mode` | `True` when opened from the Discogs import: asks **Append / Replace / Cancel** if the Print sheet is not empty. `False` (editing the queue from the sidebar) always replaces |

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

The app icon is drawn in `packaging/icons/icon.svg`; the `.ico` and the Linux hicolor PNGs next
to it are generated from it and committed. After changing the SVG, regenerate them with
`packaging/icons/build_icons.py` (instructions in its docstring).
