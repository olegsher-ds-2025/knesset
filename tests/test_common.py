"""Offline tests for scripts/_common.py helpers (no network)."""
import json

import _common
from conftest import FIXTURES


def test_fix_pdf_rtl_reverses_hebrew_and_preserves_numbers():
    # pdfplumber emits Hebrew in visual order: "8 ביוני 2026" comes out reversed.
    visual = "2026 ינויב 8"
    logical = _common.fix_pdf_rtl(visual)
    assert logical == "8 ביוני 2026"


def test_fix_pdf_rtl_multiline():
    visual = "קוח תעצה\n2026-דחא"
    out = _common.fix_pdf_rtl(visual)
    assert "הצעת חוק" in out
    assert "2026" in out  # digit run kept, not "6202"


def test_append_and_read_jsonl_roundtrip(tmp_path):
    path = tmp_path / "x.jsonl"
    rows = [{"a": 1, "heb": "שלום"}, {"a": 2}]
    n = _common.append_jsonl(path, rows)
    assert n == 2
    back = _common.read_jsonl(path)
    assert back == rows
    assert "שלום" in path.read_text(encoding="utf-8")  # UTF-8, not \u escapes


def test_state_atomic_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "DATA_DIR", tmp_path)
    monkeypatch.setattr(_common, "STATE_PATH", tmp_path / "state.json")
    assert _common.read_state() == {}
    _common.write_state({"last_bill_id_fetched": 42})
    assert _common.read_state()["last_bill_id_fetched"] == 42


def test_bill_fixture_loads_utf8():
    data = json.loads((FIXTURES / "kns_bill_sample.json").read_text(encoding="utf-8"))
    assert data[0]["BillID"] == 5
    assert "הכנסת" in data[0]["Name"]
