"""T1.x helper — Status lookup fetcher.

KNS_Status is a small lookup table (status_id -> Hebrew description) needed to tell
enacted bills from pending ones. It is fully re-fetched each run and written to
data/statuses.jsonl (overwrite), since it is tiny and has no natural watermark.

Usage:
    python scripts/fetch_statuses.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import json

from _common import STATUSES_JSONL, base_parser


def main() -> int:
    args = base_parser("Fetch KNS_Status lookup table.").parse_args()

    from mcp_server.odata_client import KnessetClient

    client = KnessetClient()
    try:
        rows = list(client.fetch_table("KNS_Status", max_rows=args.limit or 2000))
    finally:
        client.close()
    print(f"[fetch_statuses] fetched {len(rows)} statuses")

    if args.dry_run:
        print("[fetch_statuses] DRY-RUN: not writing statuses.jsonl")
        return 0

    STATUSES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with STATUSES_JSONL.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[fetch_statuses] wrote {len(rows)} -> {STATUSES_JSONL.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
