# config/

Single source of truth for formulas and thresholds (BMI, REE, PAL, TDEE, goals, macros…).

- `formulas.yaml` — every formula/value with `source`, top-level `version` (now 1.1).
- `who2007_bmi_for_age_lms.csv` — WHO 2007 BMI-for-age L, M, S by sex and age in months (60–229), used for ages 16–17.
- The app reads the same values; `tests/vectors/` are generated from them by `reference/build_vectors.py`, and a test checks that the YAML and the engine agree.
