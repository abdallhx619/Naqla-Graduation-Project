# Naqla – Graduation Project

AI/ML work for Naqla (نقلة), a fitness & nutrition app.

## Team (AI/ML)
- **Engineer 1 – Mohamed Khaled:** perception & nutrition (food photos, Gym Lens, InBody, food search)
- **Engineer 2 – Abdallh Mohamed:** calculations, workout reasoning, training & analytics

## Repository layout
| Folder | What goes there |
|---|---|
| `config/` | Versioned formulas, thresholds and bands shared by the AI and the app (`formulas.yaml`, WHO LMS table, `texts.yaml`). Every value has a cited source. |
| `reference/` | Python reference implementation + test runner. |
| `tests/vectors/` | Test vectors (inputs → expected outputs) the app's Dart code must pass. |

Current formula version: **v1.2** — see [`CHANGELOG.md`](CHANGELOG.md).

## Rules
- No number without a source: each formula/threshold in `config/` links to where it came from.
- Changing a value means bumping the config `version`, regenerating the vectors and updating `CHANGELOG.md`.
- **No rounding** in calculations; results are exact. Health numbers are estimates for fitness, never a diagnosis.
- CI (`.github/workflows/formula-tests.yml`) fails if the vectors are stale or any test fails.
