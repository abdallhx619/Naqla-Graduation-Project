# tests/vectors/

Test vectors the app's Dart implementation must pass (absolute tolerance `1e-6`, no rounding). The spec version is inside each file.

| File | Cases | What it covers |
|---|---|---|
| `calc.json` | 411 | Full calorie/macro engine: class (adult WHO / teen WHO LMS), REE, PAL, TDEE, goal rules, floors, macros |
| `bmi.json` | 20 | Adult BMI and class, exact cut-offs and float-noise cases |
| `body.json` | 80 | Tape body fat (Navy), lean/fat mass, Boer fallback, waist ratios, healthy-weight range |
| `training.json` | 99 | MET kcal (22 activities), e1RM, fractional weekly volume, PR detection and guards |
| `tracking.json` | 20 | Weight trend, periodic adjustment, daily remaining, recipe per serving |

`calc.json`/`bmi.json` use `{id, group, description, inputs, expected}`; the v1.2 files add `function` (the reference function to call).
Regenerate with `python3 reference/build_vectors.py`; never edit by hand.
