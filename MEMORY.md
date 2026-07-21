# MEMORY — cross-session state
Last updated: 2026-07-21 (session 2, Phase 1)

## Status
- Phase 0: DONE — scaffold.
- Phase 1: DONE — ETL (scripts/ T1.1–T1.6 + fetch_statuses). Idempotent, --dry-run.
- Phase 2: DONE — classify/ (backends + rubric validation + runner). Ran heuristic
  placeholder over 73 bills; real model pass gated on T2.2a. See tasks/PHASE2_TASKS.md.
- Phase 3: DONE — scripts/aggregate.py + build_site.py -> docs/ (dashboard, browse,
  methodology). Theme-aware, inline-SVG charts, verbatim rubric + disclaimer.
  Verified via Playwright screenshots (light + dark, no JS errors). CI + Pages
  workflows added. 35 offline tests pass. All 3 phases committed + pushed to master.
- Current dataset: 73 bills (Knessets 1,7,16,17,25), 35 with full text, in /storage/knesset.
- Next actions: (1) enable GitHub Pages (serve docs/ or via pages.yml). (2) T2.2a:
  run classify/run.py --backend jetson on ~20 bills, spot-check Hebrew, then full run
  + anthropic/haiku second pass. (3) backfill: scripts/sync.py without --limit.

## Watermarks
- last_bill_id_fetched: 2245052
- last_sync_utc: 2026-07-21T10:06:21Z
- knesset_terms_covered: [1, 7, 16, 17, 25]


## Pending decisions
- [x] Hosting: GitHub Pages (confirmed with user, session 2)
- [ ] Final public names for the 3 axes (see rubric — neutral wording recommended)
- [ ] Hebrew-capable GGUF model chosen for Jetson triage: TBD (T2.2a)

## Task ledger
| ID | Owner | Status |
|----|-------|--------|
| T0-verify | Opus (this env) | DONE — API reachable, smoke test green |
| T1.1 bills fetcher | Opus | DONE — scripts/fetch_bills.py + tests |
| T1.2 laws fetcher | Opus | DONE — scripts/fetch_laws.py + tests |
| T1.3 docs downloader | Opus | DONE — scripts/fetch_docs.py + RTL fix |
| T1.4 sqlite loader | Opus | DONE — scripts/load_db.py + tests |
| T1.5 normalizer | Opus | DONE — scripts/normalize.py + tests |
| T1.6 sync orchestrator | Opus | DONE — scripts/sync.py |
| T2.x classification | Jetson/Haiku | pending — see plan doc |
| T3.x static site | Haiku | pending — see plan doc |

## Gotchas learned
- API access: knesset.gov.il **is reachable** from this dev environment (CLAUDE.md's
  "container cannot reach" note did not apply here; verified 2026-07-21, HTTP 200).
- Votes service confirmed live: https://knesset.gov.il/Odata/Votes.svc/ (NOT OdataV4/Votes/).
- Dates now arrive as ISO strings (e.g. 2026-07-07T14:02:25.433), not legacy /Date(ms)/;
  client handles both. KNS_Bill uses the {"value":[...]} shape.
- **pdfplumber returns Hebrew PDF text in VISUAL (reversed) order.** _common.fix_pdf_rtl()
  reverses each line and re-flips digit/Latin runs so 2026 doesn't become 6202. Do NOT
  apply it to python-docx output (already logical).
- Legacy binary .doc files are not extractable without external tools; fetch_docs prefers
  .pdf > .docx > .doc and skips .doc with a warning.
- Bill "title" comes from KNS_Bill.Name; "summary" = text after the "דברי הסבר" marker
  (rfind), else leading excerpt.
- OData caps page size; always paginate with $top/$skip (client does this transparently).
- Env note: work uses a local venv (.venv, gitignored) with requirements.txt + pytest.

## Handoff notes for cheaper models
Read CLAUDE.md + your task file in tasks/. Do ONLY your task.
Append results + any new gotchas to this file under "Gotchas learned".
