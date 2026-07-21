"""T1.5 — Text normalizer.

Builds data/summaries.jsonl {bill_id, title, summary} from extracted bill texts.

  - title:   the bill's official Name (from data/bills.jsonl); falls back to the
             first non-empty text line if the bill is unknown.
  - summary: the explanatory-notes section, i.e. text after the marker
             "דברי הסבר" (Divrei Hesber). If the marker is absent, the leading
             portion of the document is used instead.

Deterministic + idempotent: the output file is rebuilt in full from the texts
each run. UTF-8 preserved throughout.

Usage:
    python scripts/normalize.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import json

from _common import (BILLS_JSONL, SUMMARIES_JSONL, TEXTS_DIR, base_parser,
                     read_jsonl)

MARKER = "דברי הסבר"
SUMMARY_MAX_CHARS = 4000


def extract_summary(text: str) -> str:
    """Return the explanatory-notes section, or a leading excerpt if absent."""
    idx = text.rfind(MARKER)
    section = text[idx + len(MARKER):] if idx != -1 else text
    section = section.strip()
    return section[:SUMMARY_MAX_CHARS]


def first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def build_summaries(limit: int | None = None) -> list[dict]:
    """Produce {bill_id, title, summary} records from data/texts/*.txt."""
    names = {int(b["BillID"]): b.get("Name", "") for b in read_jsonl(BILLS_JSONL)}
    out: list[dict] = []
    text_files = sorted(TEXTS_DIR.glob("*.txt")) if TEXTS_DIR.exists() else []
    if limit:
        text_files = text_files[:limit]
    for path in text_files:
        try:
            bill_id = int(path.stem)
        except ValueError:
            continue
        text = path.read_text(encoding="utf-8")
        title = (names.get(bill_id) or first_line(text)).strip()
        out.append({"bill_id": bill_id, "title": title,
                    "summary": extract_summary(text)})
    return out


def main() -> int:
    args = base_parser("Extract title + explanatory notes -> summaries.jsonl.").parse_args()
    records = build_summaries(args.limit)
    print(f"[normalize] built {len(records)} summaries from {TEXTS_DIR}")
    if args.dry_run:
        print("[normalize] DRY-RUN: not writing summaries.jsonl")
        return 0
    SUMMARIES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARIES_JSONL.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[normalize] wrote {len(records)} -> {SUMMARIES_JSONL.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
