# MEMORY — cross-session state
Last updated: 2026-07-11 (session 1, Phase 0)

## Status
- Phase 0: DONE — repo scaffold, CLAUDE.md, skills, MCP server scaffold created
- Phase 1: NOT STARTED
- Next action: run T0-verify (below) on user machine, then dispatch T1.1 to Haiku

## Watermarks
- last_bill_id_fetched: null
- last_sync_utc: null
- knesset_terms_covered: []

## Pending decisions
- [ ] Confirm hosting: GitHub Pages assumed ("Google pages" ambiguous)
- [ ] Final public names for the 3 axes (see rubric — neutral wording recommended)
- [ ] Hebrew-capable GGUF model chosen for Jetson triage: TBD (T2.2a)

## Task ledger
| ID | Owner | Status |
|----|-------|--------|
| T0-verify | user machine | pending — `python mcp_server/odata_client.py --smoke` against live API |
| T1.1 bills fetcher | Haiku | pending |
| T1.2 laws fetcher | Haiku | pending |
| T1.4 sqlite loader | Haiku | pending |

## Gotchas learned
- Container has no access to knesset.gov.il — use fixtures for tests
- OData caps page size; always paginate with $top/$skip
- Votes are in a separate OData service from ParliamentInfo

## Handoff notes for cheaper models
Read CLAUDE.md + your task file in tasks/. Do ONLY your task.
Append results + any new gotchas to this file under "Gotchas learned".
