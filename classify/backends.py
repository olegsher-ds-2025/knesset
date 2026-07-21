"""Classification backends behind one interface.

  StubClassifier       - canned output for tests (no deps).
  HeuristicClassifier  - deterministic Hebrew-keyword scorer; a transparent
                         placeholder that runs anywhere. LOW confidence on purpose
                         so bills are flagged for a real second pass.
  JetsonLlamaClassifier - HTTP to a llama.cpp OpenAI-compatible server (10.0.0.20).
  AnthropicClassifier   - Claude via the Anthropic SDK (needs ANTHROPIC_API_KEY).

Only StubClassifier and HeuristicClassifier have no external requirements.
"""
from __future__ import annotations

import json
import os

from .base import AXES, BillInput, ClassifierError, parse_model_json
from .prompt import SYSTEM, user_prompt

# --- keyword signals for the heuristic (Hebrew) ------------------------------
_SIGNALS: dict[str, dict[int, tuple[str, ...]]] = {
    "citizen_welfare": {
        +1: ("בריאות", "שכר", "דיור", "פנסיה", "זכויות", "צרכן", "פרטיות",
             "נגישות", "קצבה", "חינוך", "רווחה", "הגנה על", "שכר מינימום"),
        -1: ("קיצוץ", "ביטול זכות", "אגרה", "ייקור", "גזרה", "צמצום שירות"),
    },
    "corporate_benefit": {
        +1: ("פטור", "הקלה", "דרגולציה", "הטבה", "סובסידיה", "תמריץ",
             "עידוד השקעות", "הקלות רגולטוריות"),
        -1: ("חובת דיווח", "פיקוח על", "אנטי-מונופול", "הגבלת ריכוזיות",
             "אחריות תאגידית", "קנס"),
    },
    "executive_power": {
        +1: ("סמכות השר", "מצב חירום", "צו שעה", "עוקף", "הגבלת הפגנ",
             "פיקוח על העיתונות", "מינוי פוליטי", "ריכוז סמכויות", "האצלת סמכויות"),
        -1: ("ביקורת שיפוטית", "שקיפות", "זכויות אדם", "חופש המידע",
             "איזונים ובלמים", "חיזוק הפיקוח"),
    },
}
_PROCEDURAL = ("תקציב", "תיקון טכני", "נוסח משולב", "ועדת הכנסת", "הארכת תוקף",
               "פקיעת", "נוהל")


class StubClassifier:
    name = "stub"

    def __init__(self, canned: dict | None = None):
        self._canned = canned or {"axes": {a: 0 for a in AXES}, "confidence": 0.5,
                                  "rationale": "stub", "quotes": []}

    def classify(self, bill: BillInput) -> dict:
        return dict(self._canned)


class HeuristicClassifier:
    name = "heuristic-v0"

    def classify(self, bill: BillInput) -> dict:
        text = f"{bill.title}\n{bill.full_text or bill.summary}"
        # Procedural short-circuit (rubric rule).
        if any(p in text for p in _PROCEDURAL) and not _any_signal(text):
            return {"axes": {a: 0 for a in AXES}, "confidence": 0.9,
                    "rationale": "procedural", "quotes": []}

        axes: dict[str, int] = {}
        hits: list[str] = []
        for axis, levels in _SIGNALS.items():
            score = 0
            for sign, words in levels.items():
                for w in words:
                    if w in text:
                        score += sign
                        hits.append(w)
            axes[axis] = max(-2, min(2, score))

        n_hits = len(set(hits))
        # Deliberately low: heuristic is a placeholder pending a real model pass.
        confidence = min(0.45, 0.15 + 0.06 * n_hits)
        rationale = ("keyword-heuristic placeholder; matched: "
                     + ", ".join(sorted(set(hits))[:6]) if hits
                     else "keyword-heuristic placeholder; no strong signals")
        quotes = [w for w in sorted(set(hits))[:3]]
        return {"axes": axes, "confidence": confidence,
                "rationale": rationale, "quotes": quotes}


def _any_signal(text: str) -> bool:
    for levels in _SIGNALS.values():
        for words in levels.values():
            if any(w in text for w in words):
                return True
    return False


class JetsonLlamaClassifier:
    """llama.cpp server with an OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(self, base_url: str = "http://10.0.0.20:8080",
                 model: str = "local-gguf", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.name = f"jetson:{model}"
        self._model = model
        self._timeout = timeout

    def classify(self, bill: BillInput) -> dict:
        import httpx
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user_prompt(bill)}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            r = httpx.post(f"{self.base_url}/v1/chat/completions",
                           json=payload, timeout=self._timeout)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise ClassifierError(f"jetson backend failed: {exc}") from exc
        return parse_model_json(content)

    @staticmethod
    def reachable(base_url: str = "http://10.0.0.20:8080", timeout: float = 4.0) -> bool:
        import httpx
        try:
            httpx.get(f"{base_url.rstrip('/')}/v1/models", timeout=timeout)
            return True
        except Exception:  # noqa: BLE001
            return False


class AnthropicClassifier:
    """Claude via the Anthropic SDK. Requires ANTHROPIC_API_KEY."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 1024):
        self.name = model
        self._model = model
        self._max_tokens = max_tokens

    def classify(self, bill: BillInput) -> dict:
        try:
            import anthropic
        except ImportError as exc:
            raise ClassifierError("anthropic SDK not installed") from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ClassifierError("ANTHROPIC_API_KEY not set")
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self._model, max_tokens=self._max_tokens, temperature=0.2,
            system=SYSTEM,
            messages=[{"role": "user", "content": user_prompt(bill)}],
        )
        return parse_model_json(msg.content[0].text)


def get_backend(name: str):
    """Factory for --backend selection ('auto' resolves at runtime in run.py)."""
    return {
        "stub": StubClassifier,
        "heuristic": HeuristicClassifier,
        "jetson": JetsonLlamaClassifier,
        "anthropic": AnthropicClassifier,
    }[name]()
