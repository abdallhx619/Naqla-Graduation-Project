# tests/vectors/

Test vectors the app's Dart implementation must pass (absolute tolerance `1e-6`, no rounding).

| File | Cases | Shape |
|---|---|---|
| `calc_v1.1.json` | 411 | `{id, group, description, inputs, expected}` — full engine: class, REE, PAL, TDEE, goal applied, target kcal, protein/fat/carbs, flags, reasons |
| `bmi_v1.1.json` | 20 | `{id, input, expected, note}` — adult BMI and WHO class, incl. exact cut-offs and float-noise cases |

Groups in `calc_v1.1.json`: SPEC (the 20 spec cases), BMI cut-offs, TEEN / TEENZ (WHO BMI-for-age, incl. ±0.001 around every cut-off), AGE, PAL, DUR (every onboarding duration), CAP (PAL 2.5), DEF (500 kcal cap), FLOOR, BF (Cunningham), EXP, HEALTH, PCAP (protein cap).

Regenerate with `python3 reference/build_vectors.py`; never edit by hand.
