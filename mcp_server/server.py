"""Knesset MCP server (scaffold).

Exposes Knesset OData as MCP tools for any MCP-capable client
(Claude Desktop/Code, local llama.cpp orchestrator, etc).

Run:  pip install "mcp[cli]" httpx
      python server.py            # stdio transport

Claude Desktop config snippet:
  "knesset": {"command": "python", "args": ["/abs/path/mcp_server/server.py"]}
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from odata_client import KnessetClient

mcp = FastMCP("knesset")
_client = KnessetClient()


@mcp.tool()
def fetch_bills(last_bill_id: int = 0, limit: int = 50) -> str:
    """Fetch bills with BillID greater than last_bill_id (incremental sync).

    Returns JSON list of bill records (Hebrew names, status IDs, dates).
    """
    rows = list(_client.fetch_bills_since(last_bill_id, max_rows=limit))
    return json.dumps(rows, ensure_ascii=False)


@mcp.tool()
def fetch_laws(limit: int = 50, skip: int = 0) -> str:
    """Fetch enacted Israeli laws (KNS_IsraelLaw table)."""
    rows = list(_client.fetch_table("KNS_IsraelLaw", top=min(limit, 100),
                                    skip=skip, max_rows=limit))
    return json.dumps(rows, ensure_ascii=False)


@mcp.tool()
def fetch_bill_documents(bill_id: int) -> str:
    """Get document links (bill text + explanatory notes) for a bill."""
    rows = list(_client.fetch_table("KNS_DocumentBill",
                                    filter_=f"BillID eq {bill_id}"))
    return json.dumps(rows, ensure_ascii=False)


@mcp.tool()
def fetch_bill_initiators(bill_id: int) -> str:
    """Get initiating MKs for a bill (join to person/faction done downstream)."""
    rows = list(_client.fetch_table("KNS_BillInitiator",
                                    filter_=f"BillID eq {bill_id}"))
    return json.dumps(rows, ensure_ascii=False)


@mcp.tool()
def fetch_statuses() -> str:
    """Fetch status code lookup table (KNS_Status) — needed to identify enacted bills."""
    rows = list(_client.fetch_table("KNS_Status", max_rows=500))
    return json.dumps(rows, ensure_ascii=False)


# Votes service confirmed live 2026-07-21: https://knesset.gov.il/Odata/Votes.svc/
# (the OdataV4/Votes/ candidate is NOT available). fetch_votes is a Phase-2 task.


if __name__ == "__main__":
    mcp.run()
