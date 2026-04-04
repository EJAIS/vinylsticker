"""
Avery label sheet dimensions as named constants.

All measurements are in millimetres. Internal conversion to ReportLab points
is done via mm_to_pt() / label_rect_pt().

To compensate for printer mechanical offsets, adjust the calibration_x_mm /
calibration_y_mm values for the target format before generating a PDF.
"""

MM_PER_PT = 25.4 / 72.0   # mm per point
PT_PER_MM = 72.0 / 25.4   # points per mm

AVERY_FORMATS: dict[str, dict] = {
    "4780": {
        "description":      "Avery Zweckform 4780 – 48.5×25.4 mm – 4×10 – A4",
        "page_width_mm":    210.0,
        "page_height_mm":   297.0,
        "label_width_mm":    48.5,
        "label_height_mm":   25.4,
        "margin_left_mm":     8.0,   # (210 - 4×48.5) / 2 = 8.0
        "margin_top_mm":     21.5,   # (297 - 10×25.4) / 2 = 21.5
        "col_gap_mm":         0.0,   # labels are edge-to-edge
        "row_gap_mm":         0.0,
        "cols":               4,
        "rows":              10,
        "calibration_x_mm":   0.0,   # fine-tune against physical sheet
        "calibration_y_mm":   0.0,
    }
}


def get_format(name: str) -> dict:
    """Return the format dict for the given Avery format name.

    Raises KeyError if the format is not defined.
    """
    return AVERY_FORMATS[name]


def mm_to_pt(mm: float) -> float:
    """Convert millimetres to ReportLab points."""
    return mm * PT_PER_MM


def label_rect_pt(
    fmt: dict,
    col: int,
    row: int,
) -> tuple[float, float, float, float]:
    """Return the ReportLab bounding box for a label cell.

    ReportLab uses a bottom-left origin, y increasing upward.

    Args:
        fmt: A format dict from AVERY_FORMATS.
        col: 0-indexed column (left → right).
        row: 0-indexed row (top → bottom in sheet coordinates).

    Returns:
        (x, y_bottom, width_pt, height_pt) all in points.
    """
    page_h_pt = mm_to_pt(fmt["page_height_mm"])

    col_pitch_mm = fmt["label_width_mm"] + fmt["col_gap_mm"]
    row_pitch_mm = fmt["label_height_mm"] + fmt["row_gap_mm"]

    x = mm_to_pt(
        fmt["margin_left_mm"]
        + col * col_pitch_mm
        + fmt["calibration_x_mm"]
    )
    # row 0 is the topmost row; ReportLab y grows upward, so invert
    y_bottom = page_h_pt - mm_to_pt(
        fmt["margin_top_mm"]
        + row * row_pitch_mm
        + fmt["label_height_mm"]
        - fmt["calibration_y_mm"]
    )

    w = mm_to_pt(fmt["label_width_mm"])
    h = mm_to_pt(fmt["label_height_mm"])

    return x, y_bottom, w, h
