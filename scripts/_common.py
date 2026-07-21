"""Shared helpers for Knesset ETL scripts (T1.x).

Path constants, atomic JSON-state (watermark) helpers, JSONL append, a stable
import bootstrap for ``mcp_server.odata_client``, and a common argparse skeleton.
Stdlib only. Every ETL script imports from here so behaviour stays consistent and
idempotent/resumable per CLAUDE.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# --- Paths -------------------------------------------------------------------
# Data lives OUTSIDE the repo by default (large + gitignored). Order of choice:
#   1. $KNESSET_DATA_DIR if set
#   2. /storage/knesset  if /storage exists (this deployment's dedicated folder)
#   3. <repo>/data       fallback for isolated/dev checkouts
REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_data_dir() -> Path:
    env = os.environ.get("KNESSET_DATA_DIR")
    if env:
        return Path(env)
    if Path("/storage").is_dir():
        return Path("/storage/knesset")
    return REPO_ROOT / "data"


DATA_DIR = _resolve_data_dir()
RAW_DIR = DATA_DIR / "raw"
DOCS_DIR = DATA_DIR / "docs"
TEXTS_DIR = DATA_DIR / "texts"
AGG_DIR = DATA_DIR / "aggregates"
DB_PATH = DATA_DIR / "knesset.db"
STATE_PATH = DATA_DIR / "state.json"

BILLS_JSONL = DATA_DIR / "bills.jsonl"
LAWS_JSONL = DATA_DIR / "laws.jsonl"
STATUSES_JSONL = DATA_DIR / "statuses.jsonl"
SUMMARIES_JSONL = DATA_DIR / "summaries.jsonl"

# Make ``import mcp_server.odata_client`` work regardless of CWD.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# --- State / watermark -------------------------------------------------------
def read_state() -> dict[str, Any]:
    """Return the persisted watermark dict (empty if none yet)."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def write_state(state: dict[str, Any]) -> None:
    """Atomically persist ``state`` to data/state.json (temp file + rename)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE_PATH)  # atomic on POSIX


# --- JSONL I/O ---------------------------------------------------------------
def append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    """Append rows to a UTF-8 JSONL file; return count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts (empty if missing)."""
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# --- Hebrew / RTL text handling ----------------------------------------------
# pdfplumber returns Hebrew PDF text in *visual* (reversed) order. Reversing each
# line restores logical order, but digit / Latin runs then need re-reversing.
_LTR_RUN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.,:/\-]*")


def fix_pdf_rtl(text: str) -> str:
    """Convert visually-ordered Hebrew (as pdfplumber emits) to logical order.

    Reverses each line, then flips digit/Latin runs back so numbers like 2026
    are not left as 6202. python-docx output is already logical — do NOT apply
    this to it.
    """
    fixed_lines = []
    for line in text.splitlines():
        rev = line[::-1]
        rev = _LTR_RUN.sub(lambda m: m.group(0)[::-1], rev)
        fixed_lines.append(rev)
    return "\n".join(fixed_lines)


# --- CLI skeleton ------------------------------------------------------------
def base_parser(description: str) -> argparse.ArgumentParser:
    """argparse skeleton with the flags every ETL script shares."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--dry-run", action="store_true",
                   help="fetch/plan but write nothing to disk or state")
    p.add_argument("--limit", type=int, default=None,
                   help="cap number of rows/items processed (for testing)")
    return p
