"""Offline tests for scripts/normalize.py explanatory-notes extraction."""
import normalize
from conftest import FIXTURES


def test_extract_summary_after_marker():
    text = (FIXTURES / "sample_text_divrei.txt").read_text(encoding="utf-8")
    summary = normalize.extract_summary(text)
    assert summary.startswith("מוצע לקבוע")      # begins right after "דברי הסבר"
    assert "דברי הסבר" not in summary
    assert "זכויות האזרח" in summary


def test_extract_summary_without_marker_uses_leading_text():
    text = "סתם טקסט ללא כותרת סעיפים"
    assert normalize.extract_summary(text) == text


def test_first_line_skips_blanks():
    assert normalize.first_line("\n\n  שורה ראשונה\nשנייה") == "שורה ראשונה"


def test_build_summaries_uses_bill_name_as_title(tmp_path, monkeypatch):
    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "15752.txt").write_text(
        (FIXTURES / "sample_text_divrei.txt").read_text(encoding="utf-8"),
        encoding="utf-8")
    monkeypatch.setattr(normalize, "TEXTS_DIR", texts)
    monkeypatch.setattr(normalize, "BILLS_JSONL", FIXTURES / "bills_sample.jsonl")
    recs = normalize.build_summaries()
    assert len(recs) == 1
    assert recs[0]["bill_id"] == 15752
    assert recs[0]["title"].startswith("חוק רשות הספנות")  # from bill Name
    assert recs[0]["summary"].startswith("מוצע לקבוע")
