"""Offline tests for aggregate.py + build_site.py (pure functions, no DB/network)."""
import importlib

import aggregate
import build_site

_BILLS = [
    {"bill_id": 1, "title": "חוק א", "knesset_num": 25,
     "axes": {"citizen_welfare": 2, "corporate_benefit": 0, "executive_power": 0},
     "confidence": 0.8, "rationale": "r", "quotes": [], "model": "m",
     "buckets": ["Citizen-oriented"]},
    {"bill_id": 2, "title": "חוק ב", "knesset_num": 25,
     "axes": {"citizen_welfare": 0, "corporate_benefit": 2, "executive_power": 1},
     "confidence": 0.3, "rationale": "r", "quotes": [], "model": "m",
     "buckets": ["Corporate-oriented", "Power-concentrating"]},
    {"bill_id": 3, "title": "חוק ג", "knesset_num": 24,
     "axes": {"citizen_welfare": None, "corporate_benefit": None,
              "executive_power": None},
     "confidence": None, "rationale": "", "quotes": [], "model": None, "buckets": []},
]


def test_build_aggregates_counts():
    agg = aggregate.build_aggregates(_BILLS, n_with_text=2)
    s = agg["summary"]
    assert s["n_bills"] == 3 and s["n_classified"] == 2 and s["n_with_text"] == 2
    assert s["low_confidence"] == 1                       # bill 2 conf 0.3
    assert agg["buckets"]["Corporate-oriented"] == 1
    assert agg["buckets"]["Power-concentrating"] == 1
    assert agg["axis_distributions"]["citizen_welfare"]["2"] == 1
    assert agg["by_knesset"]["25"] == 2


def test_hbar_chart_svg_wellformed():
    svg = build_site.hbar_chart([("A", 3), ("B", 1)], ["red", "blue"])
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert svg.count("<rect") == 2 and ">3<" in svg  # direct value label


def test_stacked_axis_chart_has_all_axes():
    dist = {a: {str(k): 1 for k in range(-2, 3)} for a in build_site.AXES}
    svg = build_site.stacked_axis_chart(dist)
    for label in build_site.AXIS_LABELS.values():
        assert label in svg


def test_esc_escapes_html():
    assert build_site.esc("<b>&") == "&lt;b&gt;&amp;"
