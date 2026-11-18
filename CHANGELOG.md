# Changelog — formulas & vectors

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
