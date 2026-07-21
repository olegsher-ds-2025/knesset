"""T1.2 — Laws fetcher CLI.

Same incremental pattern as fetch_bills, for the two law tables:
  - KNS_IsraelLaw (consolidated Israeli laws, key IsraelLawID)
  - KNS_Law       (individual law publications, key LawID)

Each row is tagged with ``_table`` so the DB loader (T1.4) can route it. Separate
watermarks per table are kept in data/state.json. Appends to data/laws.jsonl.

Usage:
    python scripts/fetch_laws.py [--dry-run] [--limit N]
"""
from __future__ import annotations

from _common import LAWS_JSONL, append_jsonl, base_parser, read_state, write_state

# table -> (key field, watermark key in state.json)
LAW_TABLES = {
    "KNS_IsraelLaw": ("IsraelLawID", "last_israellaw_id_fetched"),
    "KNS_Law": ("LawID", "last_law_id_fetched"),
}


def fetch_new_rows(client, table: str, key: str, last_id: int,
                   limit: int | None) -> list[dict]:
    """Return rows of ``table`` with key > last_id, ascending, tagged with _table."""
    rows = list(client.fetch_table(
        table, filter_=f"{key} gt {last_id}", orderby=key, max_rows=limit))
    for r in rows:
        r["_table"] = table
    return rows


def main() -> int:
    args = base_parser("Fetch new Knesset laws (incremental).").parse_args()

    from mcp_server.odata_client import KnessetClient

    state = read_state()
    client = KnessetClient()
    all_rows: list[dict] = []
    new_watermarks: dict[str, int] = {}
    try:
        for table, (key, wm_key) in LAW_TABLES.items():
            last_id = int(state.get(wm_key) or 0)
            rows = fetch_new_rows(client, table, key, last_id, args.limit)
            print(f"[fetch_laws] {table}: {len(rows)} new (watermark {wm_key}={last_id})")
            if rows:
                new_watermarks[wm_key] = max(int(r[key]) for r in rows)
                all_rows.extend(rows)
    finally:
        client.close()

    if not all_rows:
        print("[fetch_laws] no new laws.")
        return 0

    if args.dry_run:
        print(f"[fetch_laws] DRY-RUN: {len(all_rows)} rows, "
              f"would set watermarks {new_watermarks}")
        return 0

    written = append_jsonl(LAWS_JSONL, all_rows)
    state.update(new_watermarks)
    write_state(state)
    print(f"[fetch_laws] wrote {written} rows -> {LAWS_JSONL.name}, "
          f"watermarks -> {new_watermarks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
