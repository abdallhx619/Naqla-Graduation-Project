# Naqla – Graduation Project

AI/ML work for Naqla (FitPilot roadmap), a fitness & nutrition app.

## Team (AI/ML)
- **Engineer 1 – Mohamed Khaled:** perception & nutrition (food photos, Gym Lens, InBody, food search)
- **Engineer 2 – Abdallh Mohamed:** calculations, workout reasoning, training & analytics

## Repository layout
| Folder | What goes there |
|---|---|
| `config/` | Versioned formulas, thresholds and bands shared by the AI and the app. Every value has a cited source. |
| `tests/vectors/` | Test vectors (inputs → expected outputs) the app's Dart code must pass. |

## Rules
- No number without a source: each formula/threshold in `config/` links to where it came from.
- Changing a value means bumping the config `version`.
- Health numbers are shown as ranges with a disclaimer, never as a diagnosis.
