"""
PDF generation module.

Renders vinyl record labels onto Avery 4780 label sheets using ReportLab.
All measurements are converted from millimetres to points internally.

Label layout (centred, top → bottom):
  Line 1 — Title          Helvetica        7 pt
  Line 2 — Artist         Helvetica-Bold   7 pt
  Line 3 — "---"          Helvetica        5 pt
  Line 4 — Label (Ctry, Year)  Helvetica  5.5 pt
  Line 5 — Side A/B       Helvetica-Bold  12 pt
"""

from __future__ import annotations

import io
from math import ceil
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from config.avery_formats import get_format, label_rect_pt, mm_to_pt
from modules.excel_reader import LabelRecord

# Opacity of the watermark image (0 = invisible, 255 = fully opaque)
_WATERMARK_ALPHA = 25   # ≈ 10 %

# ── Font / layout constants ───────────────────────────────────────────────────

_LINE_SPACING_FACTOR = 1.25   # multiplied by font size for line height

_LINES_SPEC: list[tuple[str, str, float]] = [
    # (field_name | literal,  font_name,         font_size_pt)
    ("title",                 "Helvetica",        7.0),
    ("artist",                "Helvetica-Bold",   7.0),
    ("---",                   "Helvetica",        5.0),
    ("info",                  "Helvetica",        5.5),
    ("side",                  "Helvetica-Bold",  12.0),
]


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    records: list[LabelRecord],
    output_path: Path,
    format_name: str = "4780",
    start_position: int = 0,
    watermark_path: Path | None = None,
    debug_frames: bool = False,
) -> Path:
    """Render *records* to a multi-page PDF and save to *output_path*.

    Args:
        records:         List of records to print.
        output_path:     Destination path for the generated PDF.
        format_name:     Avery format key (default "4780").
        start_position:  0-based linear index of the first label slot to use
                         on page 1.  Slots before this index are left blank.
        watermark_path:  Optional path to a PNG/JPG used as a semi-transparent
                         background image on every label.
        debug_frames:    If True, draw a hairline rectangle around each cell.

    Returns:
        The resolved *output_path*.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = get_format(format_name)
    labels_per_sheet: int = fmt["cols"] * fmt["rows"]

    page_w = mm_to_pt(fmt["page_width_mm"])
    page_h = mm_to_pt(fmt["page_height_mm"])

    # Load and prepare the watermark image once for the whole PDF
    watermark_reader: ImageReader | None = None
    if watermark_path is not None:
        watermark_reader = _prepare_watermark(watermark_path)

    c = canvas.Canvas(str(output_path), pagesize=(page_w, page_h))

    if not records:
        c.save()
        return output_path.resolve()

    total_slots = len(records) + start_position
    total_pages = ceil(total_slots / labels_per_sheet)

    for page_idx in range(total_pages):
        if page_idx > 0:
            c.showPage()

        for slot in range(labels_per_sheet):
            global_slot = page_idx * labels_per_sheet + slot
            record_idx  = global_slot - start_position

            if record_idx < 0 or record_idx >= len(records):
                if debug_frames:
                    x, y_bottom, w, h = label_rect_pt(fmt, slot % fmt["cols"],
                                                       slot // fmt["cols"])
                    _draw_debug_frame(c, x, y_bottom, w, h, empty=True)
                continue

            col = slot % fmt["cols"]
            row = slot // fmt["cols"]
            x, y_bottom, w, h = label_rect_pt(fmt, col, row)

            if debug_frames:
                _draw_debug_frame(c, x, y_bottom, w, h, empty=False)

            _draw_label(c, records[record_idx], x, y_bottom, w, h,
                        watermark_reader)

    c.save()
    return output_path.resolve()


# ── Internal rendering ────────────────────────────────────────────────────────

def _draw_label(
    c: canvas.Canvas,
    record: LabelRecord,
    x: float,
    y_bottom: float,
    w: float,
    h: float,
    watermark: ImageReader | None = None,
) -> None:
    """Draw watermark (if any) then all 5 text lines, centred in the cell."""
    if watermark is not None:
        _draw_watermark(c, watermark, x, y_bottom, w, h)

    lines = _resolve_lines(record)

    # Total block height (sum of line heights with spacing)
    total_block_h = sum(size * _LINE_SPACING_FACTOR for _, _, size in lines)

    # y_cursor starts at the top of the centred text block
    y_cursor = y_bottom + (h + total_block_h) / 2.0

    for text, font, size in lines:
        # Move down by one line height before drawing baseline
        y_cursor -= size * _LINE_SPACING_FACTOR
        c.setFont(font, size)
        c.drawCentredString(x + w / 2.0, y_cursor, text)


def _prepare_watermark(image_path: Path) -> ImageReader | None:
    """Load *image_path*, bake in transparency, return an ImageReader.

    The image is converted to RGBA and its alpha channel is scaled to
    _WATERMARK_ALPHA so it renders as a faint background behind the text.
    Returns None if the file cannot be opened.
    """
    try:
        img = PILImage.open(image_path).convert("RGBA")
        r, g, b, a = img.split()
        # Scale existing alpha by the watermark opacity factor
        a = a.point(lambda v: int(v * _WATERMARK_ALPHA / 255))
        img.putalpha(a)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def _draw_watermark(
    c: canvas.Canvas,
    reader: ImageReader,
    x: float,
    y_bottom: float,
    w: float,
    h: float,
) -> None:
    """Draw the watermark image centred and scaled to fit inside the label."""
    padding = 4.0   # points of breathing room around the image
    max_w = w - 2 * padding
    max_h = h - 2 * padding

    img_w, img_h = reader.getSize()
    scale = min(max_w / img_w, max_h / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale

    img_x = x + (w - draw_w) / 2.0
    img_y = y_bottom + (h - draw_h) / 2.0

    c.drawImage(reader, img_x, img_y, draw_w, draw_h, mask="auto")


def _resolve_lines(record: LabelRecord) -> list[tuple[str, str, float]]:
    """Build the 5-line list by substituting record field values."""
    info_text = f"{record.label} ({record.country}, {record.year})"
    resolved = []
    for field, font, size in _LINES_SPEC:
        if field == "info":
            text = info_text
        elif field == "---":
            text = "---"
        else:
            text = getattr(record, field, "")
        resolved.append((text, font, size))
    return resolved


def _draw_debug_frame(
    c: canvas.Canvas,
    x: float,
    y_bottom: float,
    w: float,
    h: float,
    empty: bool,
) -> None:
    """Draw a thin hairline rectangle for alignment testing."""
    c.saveState()
    if empty:
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
    else:
        c.setStrokeColorRGB(0.6, 0.0, 0.0)
    c.setLineWidth(0.3)
    c.rect(x, y_bottom, w, h)
    c.restoreState()
