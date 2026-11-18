# Changelog — formulas & vectors

## v1.2 — 18 Nov 2026
- **Body:** tape body fat (Navy 1984, ±SEE range, own method record), lean/fat mass with range propagation, Boer fallback ("rough"), waist-to-height (NICE), waist-to-hip and waist circumference (WHO 2008), healthy-weight range (adults BMI 18.5–25; teens WHO z −2 to +1).
- **Training:** exercise kcal from 22 Compendium 2024 activities, e1RM (Brzycki, 1–10 reps), fractional weekly volume (Pelland 2026), PR detection with typo/spike guards.
- **Tracking:** weight trend (time-aware EWMA, 7-day half-life), the v1.1 periodic adjustment implemented (only the change that applies is stored), daily remaining, recipe per serving with cooking yield.
- `config/texts.yaml`: neutral AR/EN texts and the fixed disclaimer.
- Vector files renamed without version (`calc.json`, `bmi.json`, `body.json`, `training.json`, `tracking.json`); the version lives inside each file.
- Tests: 199 new vectors, 25,000 more random-profile checks, 14 more bad-input checks.

## v1.1 — 18 Nov 2026
- **No rounding anywhere.** Removed "round target to the nearest 50 kcal"; every step keeps full precision.
- **Teens 16–17 may choose weight loss only if overweight or obesity** (WHO BMI-for-age z > +1). Normal and thinness → maintenance.
- **Teen protein cap 30 %** of kcal (IOM AMDR for ages 4–18 is 10–30 %); adults stay at 35 %.
- **Teens classified from the official WHO 2007 LMS table** (`config/who2007_bmi_for_age_lms.csv`), age in completed months, including WHO's adjustment beyond ±3 SD.
- Onboarding inputs validated (strength 30/45/60/90 min, cardio 15/30/45/60 min, 0–7 days).
- Spec test-case fixes: case 11 uses 5×60 min (75 is not an option); case 19 uses 40 kg (BMI 17.6 at 17 is *Normal* by WHO, not Thinness).
- Tests: 411 calc vectors + 20 BMI vectors, 10 hand-checked cases, 50,000 random-profile rule checks, CI on every push.

## v1.0 — 15 Nov 2026
- First full calculation spec (Mifflin/Cunningham, IOM PAL method with Compendium 2024 METs, goal rules, floors, macros, periodic adjustment).
