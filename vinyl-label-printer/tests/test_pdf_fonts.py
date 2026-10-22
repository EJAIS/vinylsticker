"""
Fallback font of the labels: text outside Windows-1252 is drawn in the bundled
DejaVu Sans, Western European text stays in Helvetica exactly as before.
"""

from __future__ import annotations

import logging

import pytest
from reportlab import rl_config
from reportlab.pdfgen import canvas

from config.avery_formats import get_format
from modules import pdf_generator
from modules.paths import resource_path
from modules.pdf_generator import generate_calibration_pdf, generate_pdf
from modules.records import LabelRecord

_DEJAVU = {"DejaVuSans", "DejaVuSans-Bold"}


def _label(title: str, artist: str = "Artist", label: str = "Label") -> LabelRecord:
    return LabelRecord(title, artist, label, "UK", "1969", "A", "R 1")


@pytest.fixture
def fonts_used(monkeypatch):
    """Record every canvas.setFont() call as (font name, size)."""
    calls: list[tuple[str, float]] = []
    real_set_font = canvas.Canvas.setFont

    def set_font(self, name, size, *args, **kwargs):
        calls.append((name, size))
        return real_set_font(self, name, size, *args, **kwargs)

    monkeypatch.setattr(canvas.Canvas, "setFont", set_font)
    return calls


def test_fonts_are_found_from_source():
    for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "LICENSE"):
        assert resource_path(f"fonts/{name}").is_file()
    assert pdf_generator._register_fallback_fonts() is True


@pytest.mark.parametrize("title", ["Łódź", "Ελλάδα", "Кино", "Dvořák"])
def test_non_western_title_uses_dejavu(tmp_path, fonts_used, title):
    generate_pdf([_label(title)], tmp_path / "out.pdf")
    # Lines: title, artist, "---", info, side
    assert [name for name, _ in fonts_used] == [
        "DejaVuSans", "Helvetica-Bold", "Helvetica", "Helvetica", "Helvetica-Bold",
    ]
    assert b"DejaVuSans" in (tmp_path / "out.pdf").read_bytes()


def test_bold_field_uses_dejavu_bold(tmp_path, fonts_used):
    generate_pdf([_label("Song", artist="Кино", label="Мелодия")], tmp_path / "out.pdf")
    assert [name for name, _ in fonts_used] == [
        "Helvetica", "DejaVuSans-Bold", "Helvetica", "DejaVuSans", "Helvetica-Bold",
    ]


def test_western_label_uses_helvetica(tmp_path, fonts_used):
    generate_pdf([_label("Café Müller", artist="Mötley Crüe – Live")], tmp_path / "out.pdf")
    assert {name for name, _ in fonts_used} == {"Helvetica", "Helvetica-Bold"}
    assert b"DejaVu" not in (tmp_path / "out.pdf").read_bytes()


def test_western_labels_render_byte_for_byte_as_before(tmp_path, monkeypatch):
    """With only cp1252 text the PDF equals the one without any fallback logic."""
    monkeypatch.setattr(rl_config, "invariant", 1)        # no dates / random IDs
    records = [
        _label("Café Müller", artist="Ärzte"),
        _label("A very long title that has to be scaled down and then truncated " * 2),
        _label("Œuvre – „Zitat“ … €5", artist="Señor Coconut"),
    ]
    generate_pdf(records, tmp_path / "new.pdf", start_position=3)
    monkeypatch.setattr(pdf_generator, "_font_for", lambda text, font: font)
    generate_pdf(records, tmp_path / "old.pdf", start_position=3)
    assert (tmp_path / "new.pdf").read_bytes() == (tmp_path / "old.pdf").read_bytes()


def test_width_fitting_measures_with_the_font_used(tmp_path, monkeypatch, fonts_used):
    measured: list[str] = []
    real_fit = pdf_generator.fit_text_to_width

    def fit(c, text, max_width, font_name, *args, **kwargs):
        measured.append(font_name)
        return real_fit(c, text, max_width, font_name, *args, **kwargs)

    monkeypatch.setattr(pdf_generator, "fit_text_to_width", fit)
    long_title = "Кино — Группа крови на рукаве, Звезда по имени Солнце"
    generate_pdf([_label(long_title)], tmp_path / "out.pdf")
    assert measured[0] == "DejaVuSans"
    title_size = fonts_used[0][1]
    c = canvas.Canvas(str(tmp_path / "scratch.pdf"))
    fmt = get_format("4780")
    max_width = pdf_generator.label_rect_pt(fmt, 0, 0)[2] - 2 * pdf_generator._H_PADDING_PT
    # The title was shortened until it fits in DejaVu Sans (not Helvetica widths)
    assert title_size == 5.0
    assert c.stringWidth(long_title, "DejaVuSans", title_size) > max_width


def test_characters_without_any_glyph_warn_once(tmp_path, caplog, fonts_used):
    caplog.set_level(logging.WARNING, logger="vinyl_label_printer")
    records = [_label("日本の歌"), _label("Fine"), _label("Ελλάδα", artist="東京")]
    generate_pdf(records, tmp_path / "out.pdf")
    assert fonts_used[0][0] == "DejaVuSans"                # drawn anyway, no crash
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "'日本の歌'" in message and "'Ελλάδα'" in message
    assert "'Fine'" not in message


def test_calibration_pdf_is_unchanged(tmp_path, fonts_used):
    generate_calibration_pdf(tmp_path / "cal.pdf", get_format("4780"))
    assert {name for name, _ in fonts_used} == {"Helvetica", "Helvetica-Bold"}
