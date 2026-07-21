"""Offline tests for scripts/load_db.py: schema, mapping, idempotent upsert."""
import sqlite3

import load_db


def test_schema_creates_all_tables():
    conn = sqlite3.connect(":memory:")
    load_db.init_db(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"bills", "laws", "statuses", "initiators",
            "summaries", "classifications"} <= names


def test_map_bill_picks_expected_columns():
    row = {"BillID": 15752, "KnessetNum": 16, "Name": "חוק", "SubTypeDesc": "ממשלתית",
           "StatusID": 118, "Number": 3, "PrivateNumber": None, "CommitteeID": 4191,
           "LastUpdatedDate": "2014-09-10T14:26:43.75"}
    m = load_db._map_bill(row)
    assert m["bill_id"] == 15752 and m["name"] == "חוק" and m["committee_id"] == 4191


def test_map_law_routes_by_source_table():
    il = load_db._map_law({"_table": "KNS_IsraelLaw", "IsraelLawID": 2000001, "Name": "a"})
    kl = load_db._map_law({"_table": "KNS_Law", "LawID": 2001427, "Name": "b"})
    assert il["law_id"] == 2000001 and kl["law_id"] == 2001427


def test_upsert_is_idempotent():
    conn = sqlite3.connect(":memory:")
    load_db.init_db(conn)
    rows = [load_db._map_bill({"BillID": 5, "Name": "חוק שכר"})]
    load_db.upsert(conn, "bills", rows)
    load_db.upsert(conn, "bills", rows)  # second load must not duplicate
    assert conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0] == 1
    # a changed row overwrites in place
    load_db.upsert(conn, "bills", [load_db._map_bill({"BillID": 5, "Name": "חדש"})])
    assert conn.execute("SELECT name FROM bills WHERE bill_id=5").fetchone()[0] == "חדש"


def test_map_classification_encodes_axes_and_quotes():
    m = load_db._map_classification({
        "bill_id": 5, "axes": {"citizen_welfare": 2, "corporate_benefit": 0,
                               "executive_power": -1},
        "confidence": 0.8, "rationale": "טוב לציבור", "quotes": ["ציטוט"],
        "model": "test", "rubric_version": "v1"})
    assert m["citizen_welfare"] == 2 and m["executive_power"] == -1
    assert "ציטוט" in m["quotes"]  # JSON-encoded, UTF-8 preserved
