"""T1.6 — Incremental sync orchestrator.

Runs the Phase-1 ETL steps in dependency order, logs per-step counts, then writes
watermarks back into MEMORY.md so cross-session state stays current:

    fetch_bills -> fetch_laws -> fetch_statuses -> fetch_docs -> normalize -> load_db

Each step is a separate script invoked with the same interpreter, so a failure is
isolated and the whole run stays idempotent/resumable. --dry-run and --limit are
propagated to every step.

Usage:
    python scripts/sync.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

from _common import BILLS_JSONL, REPO_ROOT, base_parser, read_jsonl, read_state

SCRIPTS_DIR = Path(__file__).resolve().parent
MEMORY_PATH = REPO_ROOT / "MEMORY.md"

STEPS = [
    "fetch_bills.py",
    "fetch_laws.py",
    "fetch_statuses.py",
    "fetch_docs.py",
    "normalize.py",
    "load_db.py",
]


def run_step(script: str, dry_run: bool, limit: int | None) -> int:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)]
    if dry_run:
        cmd.append("--dry-run")
    if limit is not None:
        cmd += ["--limit", str(limit)]
    print(f"\n=== [sync] {script} ===")
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


def update_memory_watermarks() -> None:
    """Rewrite the '## Watermarks' block of MEMORY.md from state + bills data."""
    if not MEMORY_PATH.exists():
        return
    state = read_state()
    last_bill = state.get("last_bill_id_fetched")
    terms = sorted({int(b["KnessetNum"]) for b in read_jsonl(BILLS_JSONL)
                    if b.get("KnessetNum") is not None})
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    block = ("## Watermarks\n"
             f"- last_bill_id_fetched: {last_bill if last_bill is not None else 'null'}\n"
             f"- last_sync_utc: {now}\n"
             f"- knesset_terms_covered: {terms}\n")

    text = MEMORY_PATH.read_text(encoding="utf-8")
    # Replace the existing "## Watermarks" section (up to the next "## ").
    pattern = re.compile(r"## Watermarks\n(?:.*?\n)*?(?=\n## |\Z)", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(block + "\n", text, count=1)
    else:
        text += "\n" + block
    MEMORY_PATH.write_text(text, encoding="utf-8")
    print(f"[sync] MEMORY.md watermarks updated (bill={last_bill}, terms={terms})")


def main() -> int:
    args = base_parser("Run the full Phase-1 ETL pipeline in order.").parse_args()
    failures = []
    for script in STEPS:
        rc = run_step(script, args.dry_run, args.limit)
        if rc != 0:
            failures.append((script, rc))
            print(f"[sync] WARNING: {script} exited {rc}")

    if not args.dry_run:
        update_memory_watermarks()

    if failures:
        print(f"\n[sync] completed with failures: {failures}")
        return 1
    print("\n[sync] all steps completed OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
