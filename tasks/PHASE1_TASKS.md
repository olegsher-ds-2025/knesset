# Phase 1 task specs (dispatch one file section per Haiku/local session)
Read CLAUDE.md + skills/knesset-odata.md first. Update MEMORY.md when done.

## T1.1 — Bills fetcher CLI
File: scripts/fetch_bills.py. Use mcp_server/odata_client.KnessetClient.
Read watermark from data/state.json (create if missing), fetch all new bills,
write JSONL to data/bills.jsonl (append), update watermark. Idempotent.

## T1.2 — Laws fetcher CLI
File: scripts/fetch_laws.py. Same pattern for KNS_IsraelLaw + KNS_Law.

## T1.3 — Bill documents downloader
File: scripts/fetch_docs.py. For each bill in DB missing text: query
KNS_DocumentBill, download first .docx/.pdf to data/docs/{bill_id}.*,
extract text (python-docx / pdfplumber) to data/texts/{bill_id}.txt.
Rate limit 1 req/s. Skip existing files.

## T1.4 — SQLite loader
File: scripts/load_db.py. Schema: bills, laws, statuses, initiators,
classifications (bill_id PK/FK, axes ints, confidence real, rationale text,
model text, rubric_version text). Load JSONL -> data/knesset.db. Upsert on ID.

## T1.5 — Text normalizer
File: scripts/normalize.py. From data/texts/*.txt extract title + explanatory
notes section (heuristic: after "דברי הסבר"). Preserve UTF-8. Output
data/summaries.jsonl {bill_id, title, summary}.

## T1.6 — Incremental sync orchestrator
File: scripts/sync.py. Run T1.1 -> T1.3 -> T1.4 -> T1.5 in order, log counts,
update MEMORY.md watermarks section programmatically.

## Definition of done (all tasks)
- Type hints, docstring, `--dry-run` flag, no crash on empty input
- Offline unit test using a fixture in tests/fixtures/ (no live network in CI)
