"""T3.1 — Aggregate the DB into small JSON files for the static site.

Reads data/knesset.db and writes data/aggregates/*.json. These aggregates are the
ONLY data the site consumes, keeping the published page fully static. Includes the
derived rubric buckets (Citizen-oriented / Corporate-oriented / Power-concentrating
/ Neutral-technical); a bill may appear in multiple.

Usage:
    python scripts/aggregate.py [--dry-run]
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

from _common import AGG_DIR, DB_PATH, base_parser
from classify.base import AXES, buckets_for

BUCKET_ORDER = ["Citizen-oriented", "Corporate-oriented",
                "Power-concentrating", "Neutral/technical"]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_bills(conn: sqlite3.Connection) -> list[dict]:
    """Join bills + classifications + status into per-bill site records."""
    rows = conn.execute("""
        SELECT b.bill_id, b.name, b.knesset_num, b.subtype_desc,
               s.desc AS status_desc,
               c.citizen_welfare, c.corporate_benefit, c.executive_power,
               c.confidence, c.rationale, c.quotes, c.model, c.rubric_version
        FROM bills b
        LEFT JOIN classifications c ON c.bill_id = b.bill_id
        LEFT JOIN statuses s ON s.status_id = b.status_id
        ORDER BY b.bill_id DESC
    """).fetchall()
    out = []
    for r in rows:
        classified = r["citizen_welfare"] is not None
        axes = {a: (r[a] if classified else None) for a in AXES}
        rec = {
            "bill_id": r["bill_id"],
            "title": r["name"] or "",
            "knesset_num": r["knesset_num"],
            "subtype": r["subtype_desc"],
            "status": r["status_desc"],
            "axes": axes,
            "confidence": r["confidence"],
            "rationale": r["rationale"] or "",
            "quotes": json.loads(r["quotes"]) if r["quotes"] else [],
            "model": r["model"],
            "buckets": buckets_for(axes) if classified else [],
        }
        out.append(rec)
    return out


def build_aggregates(bills: list[dict], n_with_text: int) -> dict[str, object]:
    classified = [b for b in bills if b["axes"]["citizen_welfare"] is not None]

    # axis score distributions (-2..+2)
    axis_dist = {a: {str(k): 0 for k in range(-2, 3)} for a in AXES}
    for b in classified:
        for a in AXES:
            axis_dist[a][str(b["axes"][a])] += 1

    # bucket counts (a bill may be in several)
    bucket_counts = {k: 0 for k in BUCKET_ORDER}
    for b in classified:
        for bucket in b["buckets"]:
            bucket_counts[bucket] += 1

    # per-Knesset counts
    by_knesset: dict[str, int] = {}
    for b in bills:
        k = str(b["knesset_num"])
        by_knesset[k] = by_knesset.get(k, 0) + 1

    low_conf = sum(1 for b in classified if (b["confidence"] or 0) < 0.5)
    models = sorted({b["model"] for b in classified if b["model"]})

    return {
        "summary": {
            "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "n_bills": len(bills),
            "n_classified": len(classified),
            "n_with_text": n_with_text,
            "low_confidence": low_conf,
            "models": models,
            "knesset_terms": sorted({b["knesset_num"] for b in bills
                                     if b["knesset_num"] is not None}),
        },
        "axis_distributions": axis_dist,
        "buckets": bucket_counts,
        "by_knesset": by_knesset,
    }


def main() -> int:
    args = base_parser("Aggregate DB -> data/aggregates/*.json.").parse_args()
    conn = _connect()
    try:
        bills = build_bills(conn)
        n_with_text = conn.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
    finally:
        conn.close()
    aggregates = build_aggregates(bills, n_with_text)

    if args.dry_run:
        print(f"[aggregate] DRY-RUN: {aggregates['summary']}")
        return 0

    AGG_DIR.mkdir(parents=True, exist_ok=True)
    (AGG_DIR / "bills.json").write_text(
        json.dumps(bills, ensure_ascii=False), encoding="utf-8")
    for name, obj in aggregates.items():
        (AGG_DIR / f"{name}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[aggregate] wrote {len(bills)} bills + "
          f"{len(aggregates)} aggregate files -> {AGG_DIR}")
    print(f"[aggregate] summary: {aggregates['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
