"""Offline tests — no network. Run: python -m pytest tests/ or python tests/test_odata_parsing.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))
from odata_client import _extract_rows, _parse_odata_date  # noqa: E402


def test_v4_shape():
    rows = _extract_rows({"value": [{"BillID": 1, "Name": "חוק לדוגמה"}]})
    assert rows == [{"BillID": 1, "Name": "חוק לדוגמה"}]


def test_v2_shape_strips_metadata():
    payload = {"d": {"results": [{"__metadata": {"uri": "x"}, "BillID": 2}]}}
    assert _extract_rows(payload) == [{"BillID": 2}]


def test_legacy_date():
    assert _parse_odata_date("/Date(1700000000000)/").startswith("2023-11-14")
    assert _parse_odata_date("2024-01-01T00:00:00") == "2024-01-01T00:00:00"
    assert _parse_odata_date(42) == 42


if __name__ == "__main__":
    test_v4_shape(); test_v2_shape_strips_metadata(); test_legacy_date()
    print("All offline tests passed")
