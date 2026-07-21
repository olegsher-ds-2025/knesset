"""T1.3 — Bill documents downloader + text extractor.

For each bill in data/bills.jsonl that has no data/texts/{bill_id}.txt yet:
  1. query KNS_DocumentBill (BillID eq N) for document links,
  2. download the first usable .pdf/.docx to data/docs/{bill_id}.<ext>,
  3. extract UTF-8 text to data/texts/{bill_id}.txt.

PDFs come out of pdfplumber in visual order, so fix_pdf_rtl() restores logical
Hebrew. .docx is read via python-docx (already logical). Legacy .doc (old binary
Word) is not extractable without external tools and is skipped with a warning.
Skips bills whose text already exists. Rate-limited to ~1 req/s.

Usage:
    python scripts/fetch_docs.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

from _common import (BILLS_JSONL, DOCS_DIR, TEXTS_DIR, base_parser, fix_pdf_rtl,
                     read_jsonl)

RATE_DELAY_S = 1.0
# Preference order: extractable formats first.
_EXT_PRIORITY = {".pdf": 0, ".docx": 1, ".doc": 2}


def _ext(url: str) -> str:
    return Path(url.split("?")[0]).suffix.lower()


def choose_document(docs: list[dict]) -> dict | None:
    """Pick the best downloadable document (prefer .pdf, then .docx, then .doc)."""
    candidates = [d for d in docs if d.get("FilePath") and _ext(d["FilePath"]) in _EXT_PRIORITY]
    if not candidates:
        return None
    return min(candidates, key=lambda d: _EXT_PRIORITY[_ext(d["FilePath"])])


def extract_text(path: Path) -> str:
    """Extract UTF-8 text from a .pdf or .docx (logical Hebrew order)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pdfplumber
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return fix_pdf_rtl("\n".join(parts))
    if suffix == ".docx":
        import docx
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)
    raise ValueError(f"unsupported extension for extraction: {suffix}")


def process_bill(client, http: httpx.Client, bill_id: int) -> str:
    """Download + extract one bill's text. Returns a short status string."""
    text_path = TEXTS_DIR / f"{bill_id}.txt"
    if text_path.exists():
        return "skip-exists"

    docs = list(client.fetch_table("KNS_DocumentBill",
                                   filter_=f"BillID eq {bill_id}"))
    doc = choose_document(docs)
    if doc is None:
        return "no-doc"

    ext = _ext(doc["FilePath"])
    if ext == ".doc":
        return "skip-legacy-doc"

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    doc_path = DOCS_DIR / f"{bill_id}{ext}"
    resp = http.get(doc["FilePath"])
    resp.raise_for_status()
    doc_path.write_bytes(resp.content)

    try:
        text = extract_text(doc_path)
    except Exception as exc:  # noqa: BLE001 - keep the batch alive
        return f"extract-error:{type(exc).__name__}"
    text_path.write_text(text, encoding="utf-8")
    return f"ok:{len(text)}chars"


def main() -> int:
    args = base_parser("Download + extract bill document text.").parse_args()

    from mcp_server.odata_client import KnessetClient

    bills = read_jsonl(BILLS_JSONL)
    todo = [int(b["BillID"]) for b in bills
            if not (TEXTS_DIR / f"{int(b['BillID'])}.txt").exists()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[fetch_docs] {len(todo)} bills missing text "
          f"(of {len(bills)} total in {BILLS_JSONL.name})")

    if args.dry_run:
        print(f"[fetch_docs] DRY-RUN: would fetch docs for {len(todo)} bills")
        return 0

    client = KnessetClient()
    http = httpx.Client(timeout=60, follow_redirects=True,
                        headers={"User-Agent": "knesset-analyzer/0.1 (research; polite)"})
    counts: dict[str, int] = {}
    try:
        for i, bill_id in enumerate(todo, 1):
            status = process_bill(client, http, bill_id)
            key = status.split(":")[0]
            counts[key] = counts.get(key, 0) + 1
            print(f"[fetch_docs] {i}/{len(todo)} bill {bill_id}: {status}")
            time.sleep(RATE_DELAY_S)
    finally:
        client.close()
        http.close()

    print(f"[fetch_docs] done. summary: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
