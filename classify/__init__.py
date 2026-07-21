"""Phase 2: Knesset bill classification on the 3-axis rubric (v1).

Pluggable backends (Jetson llama.cpp, Anthropic, deterministic heuristic, stub)
behind one interface, plus strict output validation and the rubric's scoring
rules. Every score is a model-generated OPINION — see skills/classification-rubric.md.
"""
