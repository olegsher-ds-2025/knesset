# Knesset Legislation Analyzer

## Mission
Fetch Knesset bills/laws via official OData API, classify each on 3 axes
(citizen welfare / business & regulation / executive power expansion),
publish static site (GitHub Pages) with charts and full methodology page.

## Architecture
- `mcp_server/` — custom MCP server (Python, FastMCP) exposing Knesset OData tools
- `data/` — SQLite DB + raw JSON cache (gitignored except aggregates)
- `skills/` — knowledge files: API quirks, classification rubric
- `tasks/` — small task specs sized for Haiku / local llama.cpp
- `MEMORY.md` — cross-session state. READ FIRST, UPDATE BEFORE ENDING SESSION.

## Data source
Official Knesset OData: https://knesset.gov.il/Odata/ParliamentInfo.svc/
- JSON: append `?$format=json`
- Pagination: `$top=100&$skip=N` (server caps page size)
- Key tables: KNS_Bill, KNS_Law, KNS_IsraelLaw, KNS_DocumentBill,
  KNS_BillInitiator, KNS_Status, KNS_Person, KNS_Faction
- Votes live in a separate service (see skills/knesset-odata.md)
- Text is Hebrew (UTF-8). Never mojibake-fix by re-encoding; keep UTF-8 end to end.

## Classification rules (summary — full rubric in skills/classification-rubric.md)
Per bill, output JSON:
{ "bill_id": int, "axes": { "citizen_welfare": -2..2,
  "corporate_benefit": -2..2, "executive_power": -2..2 },
  "confidence": 0..1, "rationale": "1-2 sentences", "quotes": [..] }
Scores are model-generated opinions — site MUST show disclaimer + methodology.

## Delegation policy
- Opus/Sonnet: architecture, rubric changes, calibration, code review only
- Haiku: all ETL scripts, site build, tests, second-pass classification
- Jetson Nano llama.cpp @ 10.0.0.20 (JetPack 7): bulk first-pass triage on
  titles/summaries, container test runs. Verify Hebrew quality first (task T2.2a).
- Gemini/ChatGPT free accounts: graphics assets only

## Conventions
- Python 3.11+, httpx, sqlite3 stdlib. Type hints. No heavy frameworks.
- Every script idempotent + resumable (watermark stored in MEMORY.md and DB).
- Small commits, one task = one commit referencing task ID (e.g. T1.1).

## Environment notes
- Claude.ai container CANNOT reach knesset.gov.il (network allowlist).
  Live API runs happen on the user's machine / Jetson. Write code + offline
  tests (fixtures) in container; integration tests run locally.
