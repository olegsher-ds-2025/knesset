"""Core types, rubric rules, and strict output validation for classification.

Backends produce a raw dict; validate_classification() enforces the rubric's
constraints (axis ranges, confidence bounds, quote count, title-only cap) and
returns a clean record ready for classifications.jsonl. Stdlib only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

RUBRIC_VERSION = "v1"
AXES = ("citizen_welfare", "corporate_benefit", "executive_power")


@dataclass
class BillInput:
    """One unit of work for a classifier."""
    bill_id: int
    title: str
    summary: str = ""            # explanatory-notes text; "" => title-only
    full_text: str = ""          # full document text (second pass only)

    @property
    def has_body_text(self) -> bool:
        return bool(self.summary.strip() or self.full_text.strip())


@dataclass
class Classification:
    bill_id: int
    axes: dict[str, int]
    confidence: float
    rationale: str
    quotes: list[str] = field(default_factory=list)
    model: str = ""
    rubric_version: str = RUBRIC_VERSION
    pass_no: int = 1

    def to_row(self) -> dict[str, Any]:
        return {
            "bill_id": self.bill_id,
            "axes": self.axes,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "quotes": self.quotes,
            "model": self.model,
            "rubric_version": self.rubric_version,
            "pass_no": self.pass_no,
        }


class Classifier(Protocol):
    """A backend returns a raw dict: {axes, confidence, rationale, quotes}."""
    name: str

    def classify(self, bill: BillInput) -> dict: ...


class ClassifierError(RuntimeError):
    """Raised when a backend cannot produce a usable result."""


# --- parsing + validation ----------------------------------------------------
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def parse_model_json(text: str) -> dict:
    """Extract the first JSON object from a model's raw text output.

    Tolerates a common LLM slip (trailing commas). Any parse failure is raised
    as ClassifierError so the runner can skip the bill instead of crashing.
    """
    m = _JSON_RE.search(text)
    if not m:
        raise ClassifierError(f"no JSON object in model output: {text[:120]!r}")
    blob = m.group(0)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        try:
            return json.loads(_TRAILING_COMMA_RE.sub(r"\1", blob))
        except json.JSONDecodeError as exc:
            raise ClassifierError(f"invalid JSON from model: {exc}") from exc


def _clamp_int(value: Any, lo: int, hi: int) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    return max(lo, min(hi, n))


def _clamp_float(value: Any, lo: float, hi: float) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = 0.0
    return max(lo, min(hi, f))


def validate_classification(raw: dict, bill: BillInput, *, model: str,
                            pass_no: int = 1) -> Classification:
    """Coerce a backend's raw dict into a rubric-valid Classification.

    Enforces axis range [-2,2], confidence [0,1], <=3 quotes, and the
    title-only confidence cap (0.4 when no body text is available).
    """
    raw_axes = raw.get("axes") or {}
    axes = {ax: _clamp_int(raw_axes.get(ax, 0), -2, 2) for ax in AXES}
    confidence = _clamp_float(raw.get("confidence", 0.0), 0.0, 1.0)

    # Rubric: title-only => confidence capped at 0.4.
    if not bill.has_body_text:
        confidence = min(confidence, 0.4)

    quotes = raw.get("quotes") or []
    if not isinstance(quotes, list):
        quotes = [str(quotes)]
    quotes = [str(q).strip() for q in quotes if str(q).strip()][:3]

    rationale = str(raw.get("rationale", "")).strip()

    return Classification(
        bill_id=bill.bill_id, axes=axes, confidence=confidence,
        rationale=rationale, quotes=quotes, model=model, pass_no=pass_no,
    )


def needs_second_pass(c: Classification) -> bool:
    """Rubric: confidence < 0.5 flags a bill for a full-text second pass."""
    return c.confidence < 0.5


# --- derived site buckets (rubric "Site labeling") ---------------------------
def buckets_for(axes: dict[str, int]) -> list[str]:
    """Return the derived chart buckets a bill belongs to (may be multiple)."""
    cw, cb, ep = axes["citizen_welfare"], axes["corporate_benefit"], axes["executive_power"]
    out = []
    if cw >= 1 and ep <= 0:
        out.append("Citizen-oriented")
    if cb >= 1:
        out.append("Corporate-oriented")
    if ep >= 1:
        out.append("Power-concentrating")
    if not out:
        out.append("Neutral/technical")
    return out
