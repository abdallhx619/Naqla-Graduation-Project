"""Vectors for the v1.2 modules: body.json, training.json, tracking.json. Called by build_vectors.py."""
import json
from datetime import date, timedelta

import body as B
import training as T
import tracking as K
from naqla_calc import SPEC_VERSION, lms


def _dump(path, name, vectors, note):
    with open(path / name, "w", encoding="utf-8") as f:
        json.dump({"spec_version": SPEC_VERSION, "tolerance_abs": 1e-6, "count": len(vectors),
                   "note": note, "vectors": vectors}, f, ensure_ascii=False, indent=1)
    return len(vectors)


def build(out):
    counts = {}
    # ---------------- body ----------------
    V = []
    def add(fn, group, desc, **kw):
        V.append({"id": f"{group}-{sum(1 for v in V if v['group'] == group) + 1:03d}", "group": group,
                  "function": fn.__name__, "description": desc, "inputs": kw, "expected": fn(**kw)})
    for h in (160, 175, 190):
        for neck, waist in ((34, 76), (38, 85), (40, 95), (43, 110), (46, 125)):
            add(B.navy_body_fat, "NAVY_M", f"M h{h} neck{neck} waist{waist}", sex="M", height_cm=h, neck_cm=neck, waist_cm=waist)
    for h in (150, 165, 180):
        for neck, waist, hip in ((30, 64, 88), (32, 72, 96), (34, 82, 104), (36, 95, 115), (38, 110, 130)):
            add(B.navy_body_fat, "NAVY_F", f"F h{h} neck{neck} waist{waist} hip{hip}", sex="F", height_cm=h,
                neck_cm=neck, waist_cm=waist, hip_cm=hip)
    for w, bf in ((60, 12.0), (80, 20.0), (100, 30.0), (120, 40.0)):
        add(B.mass_from_body_fat, "MASS", f"{w} kg, {bf}% (device)", weight_kg=w, bf_pct=bf, method="device")
        add(B.mass_from_body_fat, "MASS", f"{w} kg, {bf}% ±3.52 (tape range)", weight_kg=w, bf_pct=bf,
            bf_low=bf - 3.52, bf_high=bf + 3.52, method="tape_navy_1984")
    for sex in ("M", "F"):
        for w, h in ((55, 160), (70, 170), (85, 180), (110, 175), (150, 185)):
            add(B.lbm_boer, "BOER", f"{sex} {w} kg {h} cm", sex=sex, weight_kg=w, height_cm=h)
    for sex in ("M", "F"):
        for waist in (60, 75, 85, 88, 95, 102, 110):
            add(B.waist_ratios, "RATIO", f"{sex} adult waist {waist}, h170, hip 100", sex=sex, age=30,
                height_cm=170, waist_cm=waist, hip_cm=100, bmi=26.0)
    add(B.waist_ratios, "RATIO", "WHtR exactly 0.5", sex="M", age=30, height_cm=180, waist_cm=90, hip_cm=100, bmi=24.0)
    add(B.waist_ratios, "RATIO", "WHtR exactly 0.6", sex="F", age=30, height_cm=150, waist_cm=90, hip_cm=110, bmi=30.0)
    add(B.waist_ratios, "RATIO", "BMI 36: WHtR not applicable", sex="F", age=40, height_cm=160, waist_cm=105, hip_cm=120, bmi=36.0)
    add(B.waist_ratios, "RATIO", "teen: WHtR only, no adult cut-offs", sex="M", age=16, height_cm=175, waist_cm=80, hip_cm=92, bmi=21.0)
    add(B.waist_ratios, "RATIO", "WHR exactly 0.90 man", sex="M", age=30, height_cm=175, waist_cm=90, hip_cm=100, bmi=25.0)
    add(B.waist_ratios, "RATIO", "WHR exactly 0.85 woman", sex="F", age=30, height_cm=165, waist_cm=85, hip_cm=100, bmi=25.0)
    for h in (150, 160, 170, 180, 190, 200):
        add(B.healthy_weight_range, "HWR", f"adult {h} cm", height_cm=h, age=30)
    for sex in ("M", "F"):
        for am in (192, 204, 215):
            add(B.healthy_weight_range, "HWR", f"teen {sex} {am} months 170 cm", height_cm=170, age=am // 12, sex=sex, age_months=am)
    counts["body"] = _dump(out, "body.json", V, "Tape BF% (Navy 1984), lean/fat mass, Boer fallback, waist ratios, healthy-weight range.")

    # ---------------- training ----------------
    V = []
    for code in sorted(T.MET_TABLE):
        for w, m in ((60, 30), (85, 60)):
            add(T.exercise_kcal, "MET", f"{code} {w} kg {m} min", code=code, weight_kg=w, minutes=m)
    add(T.exercise_kcal, "MET", "age 65 flag", code="17200", weight_kg=70, minutes=45, age=65)
    for w in (20, 60, 100, 140):
        for r in range(1, 11):
            add(T.e1rm, "E1RM", f"{w} kg x {r}", weight_kg=w, reps=r)
    add(T.e1rm, "E1RM", "8 reps + 2 RIR = 10 (valid)", weight_kg=80, reps=8, rir=2)
    add(T.e1rm, "E1RM", "8 reps + 3 RIR = 11 (None)", weight_kg=80, reps=8, rir=3)
    add(T.e1rm, "E1RM", "12 reps (None)", weight_kg=50, reps=12)
    mm = {"bench": {"primary": ["chest"], "secondary": ["triceps", "front_delt"]},
          "row": {"primary": ["lats", "upper_back"], "secondary": ["biceps", "rear_delt"]},
          "squat": {"primary": ["quads", "glutes"], "secondary": ["adductors"]},
          "pushdown": {"primary": ["triceps"], "secondary": []}}
    week = ([{"exercise_id": "bench", "weight_kg": 40, "reps": 10, "warmup": True}] +
            [{"exercise_id": "bench", "weight_kg": 80, "reps": 8, "rir": 2}] * 4 +
            [{"exercise_id": "row", "weight_kg": 70, "reps": 10, "rir": 1}] * 3 +
            [{"exercise_id": "squat", "weight_kg": 100, "reps": 5, "rir": 3}] * 3 +
            [{"exercise_id": "pushdown", "weight_kg": 25, "reps": 15, "rir": 6}] * 2 +
            [{"exercise_id": "pushdown", "weight_kg": 25, "reps": 12}] * 2)
    add(T.weekly_volume, "VOL", "mixed week: warm-up excluded, RIR 6 not hard, fractional secondaries", sets=week, muscle_map=mm)
    add(T.weekly_volume, "VOL", "only warm-ups", sets=[{"exercise_id": "bench", "weight_kg": 40, "reps": 10, "warmup": True}], muscle_map=mm)
    hist = [{"exercise_id": "bench", "weight_kg": 80, "reps": 8, "session_id": "s1"},
            {"exercise_id": "bench", "weight_kg": 80, "reps": 7, "session_id": "s1"},
            {"exercise_id": "bench", "weight_kg": 85, "reps": 5, "session_id": "s2"},
            {"exercise_id": "squat", "weight_kg": 100, "reps": 5, "session_id": "s2"}]
    for desc, sess in (
        ("heavier weight -> weight PR (e1RM not beaten)", [{"exercise_id": "bench", "weight_kg": 87.5, "reps": 5}]),
        ("more reps at 80 -> reps PR", [{"exercise_id": "bench", "weight_kg": 80, "reps": 9}]),
        ("bigger session volume", [{"exercise_id": "bench", "weight_kg": 80, "reps": 8}] * 3),
        ("no PR", [{"exercise_id": "bench", "weight_kg": 70, "reps": 8}]),
        ("typo 850 kg -> needs confirmation", [{"exercise_id": "bench", "weight_kg": 850, "reps": 5}]),
        ("e1RM jump >30% -> needs confirmation", [{"exercise_id": "bench", "weight_kg": 120, "reps": 6}]),
        ("new exercise -> baseline only", [{"exercise_id": "deadlift", "weight_kg": 140, "reps": 5}]),
        ("zero reps -> invalid", [{"exercise_id": "bench", "weight_kg": 80, "reps": 0}]),
        ("warm-up ignored", [{"exercise_id": "squat", "weight_kg": 120, "reps": 5, "warmup": True}]),
    ):
        add(T.detect_prs, "PR", desc, history=hist, session=sess)
    counts["training"] = _dump(out, "training.json", V, "MET kcal (Compendium 2024), e1RM (Brzycki), fractional volume, PR rules.")

    # ---------------- tracking ----------------
    V = []
    d0 = date(2026, 1, 1)
    def series(start_w, per_week, days, skip=()):
        return [((d0 + timedelta(days=i)).isoformat(), start_w + per_week * i / 7 + (0.4 if i % 7 in (0, 1) else -0.2))
                for i in range(days) if i not in skip]
    add(K.weight_trend, "TREND", "steady loss with weekend bumps", weighins=series(90, -0.6, 28))
    add(K.weight_trend, "TREND", "gaps (missed days 5-11)", weighins=series(80, -0.4, 21, skip=range(5, 12)))
    add(K.weight_trend, "TREND", "two weigh-ins on one day averaged", weighins=[("2026-01-01", 80.0), ("2026-01-01", 81.0), ("2026-01-02", 80.2)])
    common = dict(tdee=2500.0, base_target=2000.0, sex="M", exp="<6m")
    add(K.periodic_adjustment, "ADJ", "day 10: too early", weighins=series(90, -0.6, 10), today="2026-01-10",
        plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.0, **common)
    add(K.periodic_adjustment, "ADJ", "losing ~1.3%/wk -> +5%", weighins=series(90, -1.2, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.0, **common)
    add(K.periodic_adjustment, "ADJ", "losing ~0.2%/wk -> -5%", weighins=series(90, -0.2, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.0, **common)
    add(K.periodic_adjustment, "ADJ", "on track ~0.7%/wk", weighins=series(90, -0.6, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.0, **common)
    add(K.periodic_adjustment, "ADJ", "too few weigh-ins", weighins=series(90, -0.6, 29, skip=range(16, 29)),
        today="2026-01-29", plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.0, **common)
    add(K.periodic_adjustment, "ADJ", "adjusted 7 days ago", weighins=series(90, -1.2, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust="2026-01-22", goal="lose", cum=0.05, **common)
    add(K.periodic_adjustment, "ADJ", "cap reached -> needs review", weighins=series(90, -1.2, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust="2026-01-14", goal="lose", cum=0.15, **common)
    add(K.periodic_adjustment, "ADJ", "lose: +5% capped at maintenance", weighins=series(90, -1.2, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="lose", cum=0.10, tdee=2100.0, base_target=1900.0, sex="M", exp="<6m")
    add(K.periodic_adjustment, "ADJ", "gain >2y too fast -> -5%", weighins=series(70, 0.5, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="gain", exp=">2y", cum=0.0, tdee=2600.0, base_target=2730.0, sex="M")
    add(K.periodic_adjustment, "ADJ", "maintain drifting down -> +5%", weighins=series(65, -0.4, 29), today="2026-01-29",
        plan_start="2026-01-01", last_adjust=None, goal="maintain", exp="<6m", cum=0.0, tdee=2000.0, base_target=2000.0, sex="F")
    tgt = {"kcal": 2000.0, "protein_g": 150.0, "fat_g": 55.5555555556, "carbs_g": 222.0}
    add(K.daily_remaining, "DAY", "half way", target=tgt, consumed={"kcal": 1000.0, "protein_g": 70.0, "fat_g": 30.0, "carbs_g": 100.0})
    add(K.daily_remaining, "DAY", "over on kcal and fat", target=tgt, consumed={"kcal": 2300.0, "protein_g": 140.0, "fat_g": 90.0, "carbs_g": 200.0})
    add(K.daily_remaining, "DAY", "nothing logged", target=tgt, consumed={})
    add(K.daily_remaining, "DAY", "exactly on target", target=tgt, consumed=dict(tgt))
    rice = {"raw_g": 300, "per100g": {"kcal": 360, "protein_g": 6.7, "fat_g": 0.6, "carbs_g": 79.0}}
    chicken = {"raw_g": 500, "per100g": {"kcal": 120, "protein_g": 22.5, "fat_g": 2.6, "carbs_g": 0.0}}
    oil = {"raw_g": 20, "per100g": {"kcal": 884, "protein_g": 0.0, "fat_g": 100.0, "carbs_g": 0.0}}
    add(K.recipe_per_serving, "RECIPE", "4 servings, weighed cooked 1500 g", ingredients=[rice, chicken, oil], servings=4, cooked_total_g=1500)
    add(K.recipe_per_serving, "RECIPE", "4 servings, yield 75%", ingredients=[rice, chicken, oil], servings=4, yield_pct=75)
    add(K.recipe_per_serving, "RECIPE", "no cooked weight -> raw weight", ingredients=[rice, chicken, oil], servings=3)
    counts["tracking"] = _dump(out, "tracking.json", V, "Weight trend (EWMA, 7-day half-life), periodic adjustment, daily remaining, recipe maths.")
    return counts
