# Knesset Legislation Analyzer
Pipeline: Knesset OData -> classification (3-axis rubric) -> static site with charts.

Quick start (on a machine with internet access to knesset.gov.il):
    pip install -r requirements.txt
    python mcp_server/odata_client.py --smoke   # T0-verify
    python mcp_server/server.py                 # run MCP server (stdio)

Read CLAUDE.md for architecture and delegation rules. MEMORY.md holds session state.
All classification scores are model-generated opinions; see skills/classification-rubric.md.
