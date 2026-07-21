# Knesset Legislation Analyzer
Pipeline: Knesset OData → 3-axis classification → static site with charts.

**All classification scores are model-generated opinions**, not facts. See the
methodology page and `skills/classification-rubric.md`.

## Quick start (on a machine with access to knesset.gov.il)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Phase 1 — ETL (fetch bills/laws/docs, extract text, load SQLite)
python scripts/sync.py                 # add --limit N for a bounded run

# Phase 2 — classify on the 3-axis rubric
python classify/run.py                 # --backend auto|heuristic|jetson|anthropic
python classify/run.py --second-pass   # full-text re-run for low-confidence bills
python scripts/load_db.py              # load classifications into the DB

# Phase 3 — build the static site into docs/
python scripts/aggregate.py
python scripts/build_site.py           # -> docs/index.html, bills.html, methodology.html
```

Run `pytest tests/` for the offline test suite (no network required).

## Data location
Downloaded data (JSONL, SQLite DB, raw cache, docs, extracted text, aggregates)
is stored **outside the repo** under `/storage/knesset` by default. Override with
`KNESSET_DATA_DIR=/path`. Only the built site in `docs/` is committed.

## Layout
- `mcp_server/` — OData client + FastMCP tool server
- `scripts/` — Phase 1 ETL (T1.x) + Phase 3 aggregate/build (T3.x)
- `classify/` — Phase 2 classification (pluggable backends + rubric validation)
- `skills/` — API quirks + classification rubric (published verbatim on the site)
- `tasks/` — per-phase task specs
- `docs/` — the generated static site (GitHub Pages)
- `MEMORY.md` — cross-session state

## Hosting
GitHub Pages serves `docs/` (see `.github/workflows/pages.yml`). CI runs the
offline tests (`.github/workflows/ci.yml`).

Read `CLAUDE.md` for architecture and delegation rules.
