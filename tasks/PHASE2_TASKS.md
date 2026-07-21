# Phase 2 — Classification (status + specs)

Rubric source of truth: skills/classification-rubric.md (v1). Every score is a
model-generated OPINION and must be published with the model name + rationale.

## Built (this session)
- `classify/base.py` — BillInput/Classification types, strict validation
  (axis range [-2,2], confidence [0,1], <=3 quotes, title-only cap 0.4),
  `needs_second_pass` (<0.5), derived `buckets_for()`.
- `classify/prompt.py` — system prompt embedding the rubric verbatim + strict
  JSON output schema.
- `classify/backends.py` — pluggable backends behind one interface:
  StubClassifier, HeuristicClassifier (deterministic Hebrew-keyword placeholder,
  intentionally low-confidence), JetsonLlamaClassifier (llama.cpp OpenAI API),
  AnthropicClassifier (needs ANTHROPIC_API_KEY).
- `classify/run.py` — runner. `--backend auto|heuristic|jetson|anthropic|stub`,
  `--second-pass`, `--limit`, `--dry-run`, `--force`. Idempotent (keyed by
  bill_id + rubric_version), writes data/classifications.jsonl.
- Loaded via existing `scripts/load_db.py` (classifications table).
- Offline tests in tests/test_classify.py.

## Current data
Bulk pass + full-text second pass run with the **heuristic** backend
(placeholder). All scores are low-confidence by design — these are NOT a real
model opinion yet.

## T2.2a — Hebrew-quality gate (PENDING, blocking for real scores)
The Jetson llama.cpp @ 10.0.0.20 was reachable but its first JSON outputs were
malformed. Before trusting it for the real first pass:
  1. Pick a Hebrew-capable GGUF; run `classify/run.py --backend jetson --limit 20`.
  2. Have Opus/Sonnet spot-check Hebrew comprehension + rubric adherence + JSON validity.
  3. If it passes, run full `--backend jetson`, then `--backend anthropic --second-pass`
     (or Haiku) for confidence<0.5 bills. Record the chosen model in MEMORY.md.

## T2.4 — Calibration (Opus/Sonnet, later)
Hand-score a ~30-bill gold set, compare, tune rubric wording / few-shot examples,
bump RUBRIC_VERSION on any change (invalidates cached rows for re-run).
