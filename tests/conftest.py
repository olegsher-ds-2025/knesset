"""Pytest path bootstrap: make repo root, scripts/ and mcp_server/ importable
without installing the project. Offline only — no test here touches the network.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT, ROOT / "scripts", ROOT / "mcp_server"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
