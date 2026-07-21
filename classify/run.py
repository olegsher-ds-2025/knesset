"""Phase 2 runner: classify bills on the 3-axis rubric.

Reads bills (titles) + summaries (explanatory notes), classifies each with the
selected backend, validates against the rubric, and writes an idempotent
data/classifications.jsonl (keyed by bill_id, rewritten in full each run).

Backend selection (--backend):
  auto (default) -> jetson if reachable, else anthropic if ANTHROPIC_API_KEY,
                    else heuristic (transparent placeholder).
Second pass (--second-pass): re-classify low-confidence bills (<0.5) using the
full document text, per the rubric.

Usage:
    python classify/run.py [--backend auto|heuristic|jetson|anthropic|stub]
                           [--second-pass] [--limit N] [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from _common import BILLS_JSONL, DATA_DIR, SUMMARIES_JSONL, TEXTS_DIR, read_jsonl  # noqa: E402
from classify.backends import (AnthropicClassifier, HeuristicClassifier,  # noqa: E402
                               JetsonLlamaClassifier, get_backend)
from classify.base import (BillInput, RUBRIC_VERSION, ClassifierError,  # noqa: E402
                           buckets_for, needs_second_pass, validate_classification)

CLASSIFICATIONS_JSONL = DATA_DIR / "classifications.jsonl"


def resolve_backend(name: str):
    if name != "auto":
        return get_backend(name)
    if JetsonLlamaClassifier.reachable():
        print("[classify] backend=auto -> jetson (reachable)")
        return JetsonLlamaClassifier()
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("[classify] backend=auto -> anthropic (API key present)")
        return AnthropicClassifier()
    print("[classify] backend=auto -> heuristic (no Jetson/API; placeholder scores)")
    return HeuristicClassifier()


def load_bill_inputs() -> list[BillInput]:
    """Join bills.jsonl (titles) with summaries.jsonl (explanatory notes)."""
    summaries = {int(s["bill_id"]): s.get("summary", "")
                 for s in read_jsonl(SUMMARIES_JSONL)}
    inputs = []
    for b in read_jsonl(BILLS_JSONL):
        bid = int(b["BillID"])
        inputs.append(BillInput(bill_id=bid, title=b.get("Name", ""),
                                summary=summaries.get(bid, "")))
    return inputs


def load_existing() -> dict[int, dict]:
    return {int(r["bill_id"]): r for r in read_jsonl(CLASSIFICATIONS_JSONL)}


def write_all(rows: dict[int, dict]) -> None:
    CLASSIFICATIONS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with CLASSIFICATIONS_JSONL.open("w", encoding="utf-8") as fh:
        for bid in sorted(rows):
            fh.write(json.dumps(rows[bid], ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify Knesset bills (Phase 2).")
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "heuristic", "jetson", "anthropic", "stub"])
    ap.add_argument("--second-pass", action="store_true",
                    help="re-run low-confidence bills with full document text")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="re-classify even if already done at this rubric version")
    args = ap.parse_args()

    backend = resolve_backend(args.backend)
    existing = load_existing()
    inputs = load_bill_inputs()
    if args.limit:
        inputs = inputs[: args.limit]

    done = 0
    second = 0
    for bill in inputs:
        prev = existing.get(bill.bill_id)

        if args.second_pass:
            # Only touch low-confidence bills that have full text available.
            if not prev or not needs_second_pass(_as_classification(prev)):
                continue
            text_path = TEXTS_DIR / f"{bill.bill_id}.txt"
            if not text_path.exists():
                continue
            bill.full_text = text_path.read_text(encoding="utf-8")
            pass_no = int(prev.get("pass_no", 1)) + 1
        else:
            if prev and prev.get("rubric_version") == RUBRIC_VERSION and not args.force:
                continue
            pass_no = 1

        try:
            raw = backend.classify(bill)
            c = validate_classification(raw, bill, model=backend.name, pass_no=pass_no)
        except ClassifierError as exc:
            print(f"[classify] bill {bill.bill_id}: ERROR {exc}")
            continue

        if not args.dry_run:
            existing[bill.bill_id] = c.to_row()
        done += 1
        second += int(args.second_pass)

    if args.dry_run:
        print(f"[classify] DRY-RUN: would classify {done} bills "
              f"(backend={backend.name}, second_pass={args.second_pass})")
        return 0

    write_all(existing)
    _print_summary(existing, backend.name)
    print(f"[classify] classified {done} bills"
          + (f" ({second} second-pass)" if args.second_pass else "")
          + f" -> {CLASSIFICATIONS_JSONL.name}")
    return 0


def _as_classification(row: dict):
    from classify.base import Classification
    return Classification(bill_id=row["bill_id"], axes=row["axes"],
                          confidence=row["confidence"], rationale=row.get("rationale", ""),
                          quotes=row.get("quotes", []), model=row.get("model", ""),
                          pass_no=row.get("pass_no", 1))


def _print_summary(rows: dict[int, dict], model: str) -> None:
    from collections import Counter
    bucket_counts: Counter = Counter()
    low = 0
    for r in rows.values():
        for b in buckets_for(r["axes"]):
            bucket_counts[b] += 1
        low += int(r["confidence"] < 0.5)
    print(f"[classify] total={len(rows)} model(last)={model} "
          f"low_confidence(<0.5)={low}")
    print(f"[classify] buckets: {dict(bucket_counts)}")


if __name__ == "__main__":
    raise SystemExit(main())
