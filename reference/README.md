# reference/

Python reference implementation of `config/formulas.yaml` (spec v1.2). The app's
Dart code must reproduce the vectors in `tests/vectors/` within 1e-6.

| File | What it is |
|---|---|
| `naqla_calc.py` | The engine: BMI, WHO BMI-for-age (16–17), REE, PAL, TDEE, goal rules, floors, macros. Standard library only. |
| `body.py` | Tape body fat, lean/fat mass, Boer fallback, waist ratios, healthy-weight range. |
| `training.py` | MET kcal, e1RM, weekly volume, PR detection. |
| `tracking.py` | Weight trend, periodic adjustment, daily remaining, recipe per serving. |
| `build_vectors.py` (+ `vectors_v12.py`) | Regenerates every file in `tests/vectors/`. |
| `test_naqla_calc.py` | Calorie engine: hand-checked cases, vectors, 50,000 random profiles, bad inputs, WHO table, config check. |
| `test_body_training.py` | v1.2 modules: hand-checked cases, vectors, 25,000 random profiles, bad inputs. |

```bash
python3 reference/build_vectors.py      # after changing a formula
python3 reference/test_naqla_calc.py    # must print RESULT: ALL PASS
python3 reference/test_body_training.py # must print RESULT: ALL PASS
```

## Notes for the Dart port
- **No rounding** at any step. Compare doubles with an absolute tolerance of `1e-6`.
- Cut-offs use a float tolerance: `a >= b - 1e-9`. This is not rounding; it only stops values like `24.999999999999996` from missing 25.
- Teens (16–17) need `age_months` (completed months). Classification comes from `config/who2007_bmi_for_age_lms.csv`.
- Reject inputs the onboarding cannot produce (e.g. a 75-minute session), as `compute()` does.
- `compute()` returns `reasons` (e.g. `floor_applied`, `teen_not_overweight`) so the UI can show the right message.
