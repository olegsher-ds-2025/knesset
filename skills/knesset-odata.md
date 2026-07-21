# Skill: Knesset OData API

Base: https://knesset.gov.il/Odata/ParliamentInfo.svc/
Always append `?$format=json`. Response shape: {"value": [...]} (OData v3/v4 style)
or {"d": {"results": [...]}} on older v2 endpoints — client must handle both.

## Pagination
- `$top=100&$skip=N`; server may cap $top (commonly 100). Loop until page < $top.
- Prefer `$orderby=BillID` + `$filter=BillID gt {watermark}` for incremental sync.

## Key tables (ParliamentInfo.svc)
- KNS_Bill: BillID, KnessetNum, Name, SubTypeDesc, StatusID, PrivateNumber, LastUpdatedDate
- KNS_Status: StatusID -> Desc (e.g. approved in 3rd reading = law)
- KNS_IsraelLaw / KNS_Law: enacted laws
- KNS_DocumentBill: BillID -> FilePath (doc/pdf of bill text + explanatory notes)
- KNS_BillInitiator: BillID -> PersonID (join KNS_Person, KNS_PersonToPosition, KNS_Faction for party)

## Votes
Separate service — verify exact URL live (T0-verify), candidates:
- https://knesset.gov.il/Odata/Votes.svc/
- https://knesset.gov.il/OdataV4/Votes/
Do NOT hardcode; keep in config, confirm during smoke test.

## Practical gotchas
- Hebrew UTF-8 everywhere; RTL text — never strip/normalize aggressively.
- Dates as /Date(1234567890000)/ on v2 responses — parse both formats.
- Bill documents are .doc/.docx/.pdf on fs.knesset.gov.il — download separately,
  extract text with python-docx / pdfplumber.
- Be polite: <=2 req/s, retry with backoff on 5xx, cache raw JSON to data/raw/.
- A "bill" != a "law": filter by StatusID for enacted; keep proposals separately
  (site shows both, labeled).
