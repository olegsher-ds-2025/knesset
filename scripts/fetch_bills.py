"""T1.1 — Bills fetcher CLI.

Reads the BillID watermark from data/state.json, fetches every KNS_Bill with a
greater BillID via mcp_server.odata_client.KnessetClient, appends them to
data/bills.jsonl, and advances the watermark. Idempotent + resumable: re-running
fetches only bills newer than the stored watermark.

Usage:
    python scripts/fetch_bills.py [--dry-run] [--limit N]
"""
from __future__ import annotations

from _common import BILLS_JSONL, append_jsonl, base_parser, read_state, write_state

WATERMARK_KEY = "last_bill_id_fetched"


def fetch_new_bills(client, last_bill_id: int, limit: int | None) -> list[dict]:
    """Return bills with BillID > last_bill_id (ascending), capped at ``limit``."""
    return list(client.fetch_bills_since(last_bill_id, max_rows=limit))


def main() -> int:
    args = base_parser("Fetch new Knesset bills (incremental).").parse_args()

    from mcp_server.odata_client import KnessetClient

    state = read_state()
    last_id = int(state.get(WATERMARK_KEY) or 0)
    print(f"[fetch_bills] watermark {WATERMARK_KEY}={last_id}")

    client = KnessetClient()
    try:
        rows = fetch_new_bills(client, last_id, args.limit)
    finally:
        client.close()

    if not rows:
        print("[fetch_bills] no new bills.")
        return 0

    max_id = max(int(r["BillID"]) for r in rows)
    if args.dry_run:
        print(f"[fetch_bills] DRY-RUN: {len(rows)} new bills, "
              f"would advance watermark {last_id} -> {max_id}")
        return 0

    written = append_jsonl(BILLS_JSONL, rows)
    state[WATERMARK_KEY] = max_id
    write_state(state)
    print(f"[fetch_bills] wrote {written} bills -> {BILLS_JSONL.name}, "
          f"watermark -> {max_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
