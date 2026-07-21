"""Knesset OData client. Stdlib + httpx only.

Handles both OData response shapes ({"value": [...]} and {"d": {"results": [...]}}),
pagination, polite rate limiting, retries, and raw JSON caching.

Smoke test (run on a machine with access to knesset.gov.il):
    python odata_client.py --smoke
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterator

import httpx

BASE_URL = "https://knesset.gov.il/Odata/ParliamentInfo.svc"
PAGE_SIZE = 100
RATE_DELAY_S = 0.5


def _data_dir() -> Path:
    """Match scripts/_common: $KNESSET_DATA_DIR, else /storage/knesset, else repo/data."""
    env = os.environ.get("KNESSET_DATA_DIR")
    if env:
        return Path(env)
    if Path("/storage").is_dir():
        return Path("/storage/knesset")
    return Path(__file__).resolve().parent.parent / "data"


RAW_DIR = _data_dir() / "raw"

_DATE_RE = re.compile(r"/Date\((\d+)([+-]\d{4})?\)/")


def _parse_odata_date(value: Any) -> Any:
    """Convert legacy /Date(ms)/ strings to ISO-8601; pass everything else through."""
    if isinstance(value, str):
        m = _DATE_RE.fullmatch(value)
        if m:
            ts = int(m.group(1)) / 1000
            return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts))
    return value


def _extract_rows(payload: dict) -> list[dict]:
    if "value" in payload:
        rows = payload["value"]
    elif "d" in payload:
        d = payload["d"]
        rows = d.get("results", d) if isinstance(d, dict) else d
    else:
        raise ValueError(f"Unrecognized OData payload keys: {list(payload)[:5]}")
    return [{k: _parse_odata_date(v) for k, v in r.items() if not k.startswith("__")}
            for r in rows]


class KnessetClient:
    def __init__(self, base_url: str = BASE_URL, cache_raw: bool = True):
        self.base_url = base_url.rstrip("/")
        self.cache_raw = cache_raw
        self._http = httpx.Client(timeout=60, headers={
            "Accept": "application/json",
            "User-Agent": "knesset-analyzer/0.1 (research; polite)",
        })

    def _get(self, url: str, retries: int = 4) -> dict:
        for attempt in range(retries):
            try:
                resp = self._http.get(url)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("5xx", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, httpx.TransportError):
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("unreachable")

    def fetch_table(
        self,
        table: str,
        *,
        filter_: str | None = None,
        orderby: str | None = None,
        top: int = PAGE_SIZE,
        skip: int = 0,
        max_rows: int | None = None,
    ) -> Iterator[dict]:
        """Yield rows from an OData table, paginating transparently.

        ``skip`` sets the starting ``$skip`` offset (default 0); pagination then
        advances from there.
        """
        yielded = 0
        while True:
            params = [f"$format=json", f"$top={top}", f"$skip={skip}"]
            if filter_:
                params.append(f"$filter={filter_}")
            if orderby:
                params.append(f"$orderby={orderby}")
            url = f"{self.base_url}/{table}?" + "&".join(params)
            payload = self._get(url)
            if self.cache_raw:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                (RAW_DIR / f"{table}_{skip}.json").write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows = _extract_rows(payload)
            for row in rows:
                yield row
                yielded += 1
                if max_rows and yielded >= max_rows:
                    return
            if len(rows) < top:
                return
            skip += top
            time.sleep(RATE_DELAY_S)

    def fetch_bills_since(self, last_bill_id: int = 0, max_rows: int | None = None) -> Iterator[dict]:
        return self.fetch_table(
            "KNS_Bill",
            filter_=f"BillID gt {last_bill_id}",
            orderby="BillID",
            max_rows=max_rows,
        )

    def close(self) -> None:
        self._http.close()


def smoke_test() -> None:
    c = KnessetClient()
    bills = list(c.fetch_table("KNS_Bill", orderby="BillID desc", max_rows=3))
    assert bills and "BillID" in bills[0], "KNS_Bill fetch failed"
    print(f"OK: fetched {len(bills)} bills, newest BillID={bills[0]['BillID']}")
    print(json.dumps(bills[0], ensure_ascii=False, indent=2)[:800])
    c.close()


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        smoke_test()
    else:
        print(__doc__)
