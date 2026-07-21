"""Offline tests for the fetcher scripts using a stub OData client (no network)."""
import json

import fetch_bills
import fetch_docs
import fetch_laws
from conftest import FIXTURES


class StubClient:
    """Minimal stand-in for KnessetClient backed by fixture rows."""

    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def fetch_bills_since(self, last_bill_id=0, max_rows=None):
        out = [r for r in self._rows if int(r["BillID"]) > last_bill_id]
        out.sort(key=lambda r: r["BillID"])
        return out[:max_rows] if max_rows else out

    def fetch_table(self, table, *, filter_=None, orderby=None, top=100,
                    skip=0, max_rows=None):
        rows = self._rows
        return rows[:max_rows] if max_rows else rows

    def close(self):
        self.closed = True


def _bills():
    return json.loads((FIXTURES / "kns_bill_sample.json").read_text(encoding="utf-8"))


def test_fetch_new_bills_respects_watermark():
    client = StubClient(_bills())
    assert [b["BillID"] for b in fetch_bills.fetch_new_bills(client, 0, None)] == [5, 20, 15752]
    assert [b["BillID"] for b in fetch_bills.fetch_new_bills(client, 20, None)] == [15752]
    assert fetch_bills.fetch_new_bills(client, 15752, None) == []


def test_fetch_new_bills_limit():
    client = StubClient(_bills())
    assert len(fetch_bills.fetch_new_bills(client, 0, 2)) == 2


def test_fetch_laws_tags_source_table():
    rows = [{"IsraelLawID": 2000001, "Name": "חוק"}]
    tagged = fetch_laws.fetch_new_rows(StubClient(rows), "KNS_IsraelLaw",
                                       "IsraelLawID", 0, None)
    assert tagged[0]["_table"] == "KNS_IsraelLaw"


def test_choose_document_prefers_pdf_over_docx_over_doc():
    docs = json.loads(
        (FIXTURES / "kns_documentbill_sample.json").read_text(encoding="utf-8"))
    chosen = fetch_docs.choose_document(docs)
    assert chosen["FilePath"].endswith(".pdf")


def test_choose_document_none_when_no_downloadable():
    assert fetch_docs.choose_document([{"FilePath": "http://x/y.zip"}]) is None
