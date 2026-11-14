# config/

Single source of truth for formulas and thresholds (BMI, BMR, TDEE, PAL, body-fat, macros…).

- One file: `formulas.yaml`, with a top-level `version`.
- Every entry has `formula`, `unit`, `source` (link) and, where relevant, `accuracy_note`.
- The app reads the same values; the test vectors in `tests/vectors/` are generated from them.
