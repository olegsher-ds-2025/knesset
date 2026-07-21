"""Offline tests for the classification module (no network, no LLM)."""
from classify.backends import HeuristicClassifier, StubClassifier
from classify.base import (AXES, BillInput, buckets_for, needs_second_pass,
                           parse_model_json, validate_classification)


def test_parse_model_json_extracts_object_from_noise():
    raw = 'sure, here:\n{"axes": {"citizen_welfare": 2}, "confidence": 0.7} thanks'
    assert parse_model_json(raw)["confidence"] == 0.7


def test_validate_clamps_ranges():
    bill = BillInput(1, "כותרת", summary="יש טקסט הסבר")
    raw = {"axes": {"citizen_welfare": 5, "corporate_benefit": -9,
                    "executive_power": "1"}, "confidence": 3.0, "quotes": "לא רשימה"}
    c = validate_classification(raw, bill, model="test")
    assert c.axes["citizen_welfare"] == 2      # clamped to +2
    assert c.axes["corporate_benefit"] == -2   # clamped to -2
    assert c.axes["executive_power"] == 1       # string coerced
    assert c.confidence == 1.0                  # clamped to 1.0
    assert c.quotes == ["לא רשימה"]             # scalar wrapped into list


def test_title_only_caps_confidence():
    bill = BillInput(2, "כותרת בלבד")  # no summary/full_text
    c = validate_classification({"axes": {a: 0 for a in AXES}, "confidence": 0.95},
                                bill, model="test")
    assert c.confidence == 0.4


def test_quotes_capped_at_three():
    bill = BillInput(3, "t", summary="body")
    c = validate_classification(
        {"axes": {a: 0 for a in AXES}, "confidence": 0.6,
         "quotes": ["a", "b", "c", "d", "e"]}, bill, model="test")
    assert len(c.quotes) == 3


def test_needs_second_pass_threshold():
    bill = BillInput(4, "t", summary="body")
    low = validate_classification({"axes": {a: 0 for a in AXES}, "confidence": 0.3},
                                  bill, model="t")
    high = validate_classification({"axes": {a: 0 for a in AXES}, "confidence": 0.8},
                                   bill, model="t")
    assert needs_second_pass(low) and not needs_second_pass(high)


def test_buckets_multiple_membership():
    assert buckets_for({"citizen_welfare": 2, "corporate_benefit": 0,
                        "executive_power": 0}) == ["Citizen-oriented"]
    b = buckets_for({"citizen_welfare": 1, "corporate_benefit": 2,
                     "executive_power": 2})
    assert "Corporate-oriented" in b and "Power-concentrating" in b
    assert buckets_for({"citizen_welfare": 0, "corporate_benefit": 0,
                        "executive_power": 0}) == ["Neutral/technical"]


def test_heuristic_procedural_shortcut():
    bill = BillInput(5, "הצעת חוק (תיקון טכני) הארכת תוקף", summary="נוסח משולב")
    raw = HeuristicClassifier().classify(bill)
    assert raw["rationale"] == "procedural" and raw["confidence"] == 0.9
    assert all(v == 0 for v in raw["axes"].values())


def test_heuristic_detects_welfare_signal():
    bill = BillInput(6, "הצעת חוק זכויות", summary="הגנה על בריאות ושכר העובדים")
    raw = HeuristicClassifier().classify(bill)
    assert raw["axes"]["citizen_welfare"] >= 1
    assert raw["confidence"] < 0.5  # placeholder stays low-confidence


def test_stub_backend():
    raw = StubClassifier().classify(BillInput(7, "t"))
    assert set(raw["axes"]) == set(AXES)
