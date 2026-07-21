"""Prompt construction for LLM classification backends.

The rubric text is embedded so the model scores against the exact published
criteria. Output is constrained to the strict JSON schema.
"""
from __future__ import annotations

from .base import BillInput

RUBRIC = """\
Score each Knesset bill on THREE independent axes, each an integer -2..+2.

citizen_welfare:
 +2 broad direct benefit (healthcare, wages, housing, consumer/privacy rights)
 +1 narrow/indirect benefit
  0 neutral / technical / procedural
 -1 narrow harm or cost shifted to citizens
 -2 broad direct harm (cuts to rights/services, regressive burden)

corporate_benefit:
 +2 major benefit to large corporations/concentrated industries (subsidies,
    deregulation reducing liability, monopoly protection)
 +1 mild business benefit incl. SMEs
  0 neutral
 -1 mild new obligations on business
 -2 major new obligations/antitrust/consumer-protection burdens on corporations

executive_power:
 +2 major expansion of government/executive power at expense of oversight
    (courts, press, protest, elections, emergency powers)
 +1 mild expansion / reduced transparency
  0 neutral
 -1 mild strengthening of oversight/rights
 -2 major strengthening of checks, transparency, civil liberties

RULES:
- Score the TEXT, not the proposing party. Never use party identity as evidence.
- quotes: 1-3 short Hebrew snippets (<15 words each) supporting the scores.
- Procedural/budget-technical bills: all zeros, confidence 0.9, rationale "procedural".
- confidence is your 0..1 certainty given the text you were shown.
"""

SYSTEM = (
    "You are a careful, non-partisan legislative analyst. You output ONLY a single "
    "JSON object, no prose. The scores are explicitly labeled model opinions.\n\n"
    + RUBRIC +
    '\nOutput exactly this shape:\n'
    '{"bill_id": <int>, "axes": {"citizen_welfare": <int>, '
    '"corporate_benefit": <int>, "executive_power": <int>}, '
    '"confidence": <float 0..1>, "rationale": "<1-2 sentences>", '
    '"quotes": ["<hebrew>", ...]}'
)


def user_prompt(bill: BillInput) -> str:
    body = bill.full_text or bill.summary or "(no body text — title only)"
    return (f'bill_id: {bill.bill_id}\n'
            f'title (Hebrew): {bill.title}\n'
            f'text (Hebrew):\n{body[:6000]}')
