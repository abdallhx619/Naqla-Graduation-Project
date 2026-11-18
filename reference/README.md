# reference/

Python reference implementation of `config/formulas.yaml` (spec v1.1). The app's
Dart code must reproduce the vectors in `tests/vectors/` within 1e-6.

| File | What it is |
|---|---|
| `naqla_calc.py` | The engine: BMI, WHO BMI-for-age (16–17), REE, PAL, TDEE, goal rules, floors, macros. Standard library only. |
| `build_vectors.py` | Regenerates `tests/vectors/calc_v1.1.json` (411 cases) and `bmi_v1.1.json` (20 cases). |
| `test_naqla_calc.py` | Hand-checked cases, all vectors, 50,000 random profiles against the rules, bad inputs, WHO table check, config check. |

```bash
python3 reference/build_vectors.py      # after changing a formula
python3 reference/test_naqla_calc.py    # must print RESULT: ALL PASS
```

## Notes for the Dart port
- **No rounding** at any step. Compare doubles with an absolute tolerance of `1e-6`.
- Cut-offs use a float tolerance: `a >= b - 1e-9`. This is not rounding; it only stops values like `24.999999999999996` from missing 25.
- Teens (16–17) need `age_months` (completed months). Classification comes from `config/who2007_bmi_for_age_lms.csv`.
- Reject inputs the onboarding cannot produce (e.g. a 75-minute session), as `compute()` does.
- `compute()` returns `reasons` (e.g. `floor_applied`, `teen_not_overweight`) so the UI can show the right message.
