# Skill: Classification Rubric v1

Every classification is a model-generated OPINION. The site must publish this
rubric verbatim, the model name, and per-bill rationale. Neutral axis names.

## Axes (score -2..+2 each, independent)
### citizen_welfare
+2 broad direct benefit (healthcare, wages, housing, consumer/privacy rights)
+1 narrow/indirect benefit
 0 neutral / technical / procedural
-1 narrow harm or cost shifted to citizens
-2 broad direct harm (cuts to rights/services, regressive burden)

### corporate_benefit
+2 major benefit to large corporations/concentrated industries (subsidies,
   deregulation reducing liability, monopoly protection)
+1 mild business benefit incl. SMEs
 0 neutral
-1 mild new obligations on business
-2 major new obligations/antitrust/consumer-protection burdens on corporations

### executive_power
+2 major expansion of government/executive power at expense of oversight
   (courts, press, protest, elections, emergency powers)
+1 mild expansion / reduced transparency
 0 neutral
-1 mild strengthening of oversight/rights
-2 major strengthening of checks, transparency, civil liberties

## Required output JSON (strict)
{"bill_id": 0, "axes": {"citizen_welfare": 0, "corporate_benefit": 0,
 "executive_power": 0}, "confidence": 0.0, "rationale": "", "quotes": []}

## Rules
- Score the TEXT, not the proposing party. Never use party identity as evidence.
- quotes: 1-3 short Hebrew snippets (<15 words each) supporting the scores.
- confidence <0.5 => flag for second pass with full bill text (Haiku).
- If only a title is available, max confidence = 0.4.
- Procedural/budget-technical bills: all zeros, confidence 0.9, rationale "procedural".

## Site labeling
Buckets for charts (derived, not stored):
- "Citizen-oriented": citizen_welfare >= 1 and executive_power <= 0
- "Corporate-oriented": corporate_benefit >= 1
- "Power-concentrating": executive_power >= 1
- "Neutral/technical": otherwise
A bill can appear in multiple buckets; charts must say so.
