"""T1.4 — SQLite loader.

Creates/upgrades data/knesset.db (idempotent CREATE TABLE IF NOT EXISTS) and
loads the pipeline's JSONL outputs into normalized tables, upserting on primary
key (INSERT OR REPLACE) so re-runs never duplicate rows.

Tables: bills, laws, statuses, initiators, summaries, classifications.
Each source file is optional — missing files are simply skipped.

Usage:
    python scripts/load_db.py [--dry-run]
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable

from _common import (BILLS_JSONL, DATA_DIR, DB_PATH, LAWS_JSONL, STATUSES_JSONL,
                     SUMMARIES_JSONL, base_parser, read_jsonl)

CLASSIFICATIONS_JSONL = DATA_DIR / "classifications.jsonl"
INITIATORS_JSONL = DATA_DIR / "initiators.jsonl"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY,
    knesset_num INTEGER,
    name TEXT,
    subtype_desc TEXT,
    status_id INTEGER,
    number INTEGER,
    private_number INTEGER,
    committee_id INTEGER,
    last_updated_date TEXT
);
CREATE TABLE IF NOT EXISTS laws (
    source_table TEXT,
    law_id INTEGER,
    name TEXT,
    knesset_num INTEGER,
    publication_date TEXT,
    last_updated_date TEXT,
    PRIMARY KEY (source_table, law_id)
);
CREATE TABLE IF NOT EXISTS statuses (
    status_id INTEGER PRIMARY KEY,
    desc TEXT,
    type_desc TEXT
);
CREATE TABLE IF NOT EXISTS initiators (
    bill_id INTEGER,
    person_id INTEGER,
    is_initiator INTEGER,
    ordinal INTEGER,
    PRIMARY KEY (bill_id, person_id)
);
CREATE TABLE IF NOT EXISTS summaries (
    bill_id INTEGER PRIMARY KEY,
    title TEXT,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS classifications (
    bill_id INTEGER PRIMARY KEY,
    citizen_welfare INTEGER,
    corporate_benefit INTEGER,
    executive_power INTEGER,
    confidence REAL,
    rationale TEXT,
    quotes TEXT,          -- JSON-encoded list
    model TEXT,
    rubric_version TEXT
);
"""


def _map_bill(r: dict) -> dict:
    return {
        "bill_id": r.get("BillID"),
        "knesset_num": r.get("KnessetNum"),
        "name": r.get("Name"),
        "subtype_desc": r.get("SubTypeDesc"),
        "status_id": r.get("StatusID"),
        "number": r.get("Number"),
        "private_number": r.get("PrivateNumber"),
        "committee_id": r.get("CommitteeID"),
        "last_updated_date": r.get("LastUpdatedDate"),
    }


def _map_law(r: dict) -> dict:
    return {
        "source_table": r.get("_table"),
        "law_id": r.get("IsraelLawID") if r.get("_table") == "KNS_IsraelLaw" else r.get("LawID"),
        "name": r.get("Name"),
        "knesset_num": r.get("KnessetNum"),
        "publication_date": r.get("PublicationDate"),
        "last_updated_date": r.get("LastUpdatedDate"),
    }


def _map_status(r: dict) -> dict:
    return {"status_id": r.get("StatusID"), "desc": r.get("Desc"),
            "type_desc": r.get("TypeDesc")}


def _map_initiator(r: dict) -> dict:
    return {"bill_id": r.get("BillID"), "person_id": r.get("PersonID"),
            "is_initiator": 1 if r.get("IsInitiator") else 0,
            "ordinal": r.get("Ordinal")}


def _map_summary(r: dict) -> dict:
    return {"bill_id": r.get("bill_id"), "title": r.get("title"),
            "summary": r.get("summary")}


def _map_classification(r: dict) -> dict:
    axes = r.get("axes", {})
    return {
        "bill_id": r.get("bill_id"),
        "citizen_welfare": axes.get("citizen_welfare"),
        "corporate_benefit": axes.get("corporate_benefit"),
        "executive_power": axes.get("executive_power"),
        "confidence": r.get("confidence"),
        "rationale": r.get("rationale"),
        "quotes": json.dumps(r.get("quotes", []), ensure_ascii=False),
        "model": r.get("model"),
        "rubric_version": r.get("rubric_version"),
    }


# table -> (source jsonl path, row-mapper)
LOADERS: dict[str, tuple[Path, Callable[[dict], dict]]] = {
    "bills": (BILLS_JSONL, _map_bill),
    "laws": (LAWS_JSONL, _map_law),
    "statuses": (STATUSES_JSONL, _map_status),
    "initiators": (INITIATORS_JSONL, _map_initiator),
    "summaries": (SUMMARIES_JSONL, _map_summary),
    "classifications": (CLASSIFICATIONS_JSONL, _map_classification),
}


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def upsert(conn: sqlite3.Connection, table: str, mapped: list[dict]) -> int:
    """INSERT OR REPLACE mapped rows into ``table``; return count."""
    if not mapped:
        return 0
    cols = list(mapped[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    conn.executemany(sql, [[row[c] for c in cols] for row in mapped])
    return len(mapped)


def load_all(conn: sqlite3.Connection, *, dry_run: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, (path, mapper) in LOADERS.items():
        rows = read_jsonl(path)
        mapped = [mapper(r) for r in rows]
        # drop rows with a NULL primary key component we cannot key on
        if table in ("bills", "statuses", "summaries", "classifications"):
            mapped = [m for m in mapped if list(m.values())[0] is not None]
        counts[table] = len(mapped)
        if not dry_run:
            upsert(conn, table, mapped)
    return counts


def main() -> int:
    args = base_parser("Load JSONL outputs into data/knesset.db.").parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        counts = load_all(conn, dry_run=args.dry_run)
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()
    verb = "DRY-RUN would load" if args.dry_run else "loaded"
    print(f"[load_db] {verb} {counts} -> {DB_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
