"""Tests for body.py, training.py, tracking.py (spec v1.2). Run from the repo root:
python3 reference/test_body_training.py
"""
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
import body as B  # noqa: E402
import training as T  # noqa: E402
import tracking as K  # noqa: E402

TOL = 1e-6
fails = 0


def close(a, b, what, tol=TOL):
    global fails
    if abs(a - b) > tol:
        fails += 1
        print(f"FAIL {what}: got {a!r} expected {b!r}")


def check(cond, what):
    global fails
    if not cond:
        fails += 1
        print("FAIL", what)


# ---------- 1. hand-checked ----------
# Navy man 175/38/85: density = 1.0324 - 0.19077*log10(47) + 0.15456*log10(175); %BF = 495/d - 450
d = 1.0324 - 0.19077 * math.log10(47) + 0.15456 * math.log10(175)
r = B.navy_body_fat("M", 175, 38, 85)
close(r["bf_pct"], 495 / d - 450, "navy M"); close(r["bf_high"] - r["bf_pct"], 3.52, "navy M SEE")
# independent cross-check: the NRC-published rounded coefficients land within 1 point
d_r = 1.032 - 0.191 * math.log10(47) + 0.155 * math.log10(175)
close(r["bf_pct"], 100 * (4.95 / d_r - 4.5), "navy M vs NRC rounded", tol=1.0)
d = 1.29579 - 0.35004 * math.log10(72 + 96 - 32) + 0.22100 * math.log10(165)
close(B.navy_body_fat("F", 165, 32, 72, 96)["bf_pct"], 495 / d - 450, "navy F")
close(B.lbm_boer("M", 80, 178)["lbm_kg"], 60.886, "Boer M 80/178")
close(B.lbm_boer("F", 65, 165)["lbm_kg"], 0.252 * 65 + 0.473 * 165 - 48.3, "Boer F")
m = B.mass_from_body_fat(80, 20, 16.48, 23.52)
close(m["lbm_kg"], 64, "lbm"); close(m["lbm_low"], 80 * (1 - 0.2352), "lbm low"); close(m["fat_high"], 80 * 0.2352, "fat high")
hw = B.healthy_weight_range(170, 30); close(hw["min_kg"], 53.465, "hwr min"); close(hw["max_kg"], 72.25, "hwr max")
check(B.waist_ratios("M", 30, 180, 90)["whtr_class"] == "increased", "WHtR 0.5 -> increased")
check(B.waist_ratios("F", 30, 150, 90)["whtr_class"] == "high", "WHtR 0.6 -> high")
check(B.waist_ratios("M", 30, 180, 89.9)["whtr_class"] == "healthy", "WHtR 0.4994 -> healthy")
check(B.waist_ratios("M", 30, 175, 90, 100)["whr_class"] == "substantially_increased", "WHR 0.90 man")
check(B.waist_ratios("F", 30, 165, 84.9, 100)["whr_class"] == "not_increased", "WHR 0.849 woman")
check(B.waist_ratios("M", 30, 175, 102)["waist_class"] == "substantially_increased", "waist 102 man")
check(B.waist_ratios("F", 30, 165, 79.9)["waist_class"] == "not_increased", "waist 79.9 woman")
check(B.waist_ratios("F", 40, 160, 105, 120, bmi=36)["whtr_applies"] is False, "BMI 36 not applicable")
close(T.e1rm(100, 1), 100, "e1rm r=1"); close(T.e1rm(100, 5), 112.5, "e1rm r=5")
close(T.e1rm(100, 10), 100 * (1 + 10 / 30), "Brzycki = Epley at 10")
check(T.e1rm(100, 11) is None and T.e1rm(100, 8, rir=3) is None, "e1rm > 10 -> None")
close(T.exercise_kcal("02054", 85, 60)["kcal_gross"], 297.5, "MET kcal")
close(T.exercise_kcal("12050", 70, 30)["kcal_net"], 8.3 * 70 * 0.5, "MET net")
rice = {"raw_g": 300, "per100g": {"kcal": 360, "protein_g": 6.7, "fat_g": 0.6, "carbs_g": 79.0}}
chicken = {"raw_g": 500, "per100g": {"kcal": 120, "protein_g": 22.5, "fat_g": 2.6, "carbs_g": 0.0}}
oil = {"raw_g": 20, "per100g": {"kcal": 884, "protein_g": 0.0, "fat_g": 100.0, "carbs_g": 0.0}}
rp = K.recipe_per_serving([rice, chicken, oil], 4, cooked_total_g=1500)
close(rp["per_serving"]["kcal"], (1080 + 600 + 176.8) / 4, "recipe kcal/serving")
close(rp["serving_weight_g"], 375, "serving weight"); close(rp["yield_pct"], 1500 / 820 * 100, "yield")
tr = K.weight_trend([("2026-01-01", 80.0), ("2026-01-08", 82.0)])
close(tr[-1]["trend"], 81.0, "7-day gap -> alpha 0.5")
close(K.week_mean([("2026-01-0%d" % i, 80.0 + i) for i in range(1, 8)], "2026-01-07"), 84.0, "week mean")
check(K.week_mean([("2026-01-01", 80.0)] * 5, "2026-01-07") is None, "same day x5 counts as 1 day")
print("hand-checked: done")

# ---------- 2. regression ----------
mods = {"body": B, "training": T, "tracking": K}
n = 0


def same(a, b, path):
    global fails
    if isinstance(b, float) and isinstance(a, (int, float)):
        close(a, b, path)
    elif isinstance(b, dict):
        if set(a) != set(b):
            fails += 1; print("FAIL keys", path, set(a) ^ set(b)); return
        for k in b:
            same(a[k], b[k], f"{path}.{k}")
    elif isinstance(b, list):
        if len(a) != len(b):
            fails += 1; print("FAIL len", path); return
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, f"{path}[{i}]")
    elif a != b:
        fails += 1; print(f"FAIL {path}: {a!r} != {b!r}")


for name, mod in mods.items():
    data = json.load(open(ROOT / "tests" / "vectors" / f"{name}.json", encoding="utf-8"))
    for v in data["vectors"]:
        got = json.loads(json.dumps(getattr(mod, v["function"])(**v["inputs"])))
        same(got, v["expected"], v["id"]); n += 1
print(f"regression: {n} vectors checked")

# ---------- 3. invariants ----------
rng = random.Random(1202)
for _ in range(20000):
    sex = rng.choice("MF"); h = rng.uniform(145, 205); neck = rng.uniform(28, 48)
    waist = rng.uniform(max(neck + 15, 60), 140); hip = rng.uniform(80, 140)
    a = B.navy_body_fat(sex, h, neck, waist, hip if sex == "F" else None)
    b2 = B.navy_body_fat(sex, h, neck, waist + 1, hip if sex == "F" else None)
    ok = b2["bf_pct"] > a["bf_pct"] and a["bf_low"] <= a["bf_pct"] <= a["bf_high"]
    w = rng.uniform(40, 180)
    mm = B.mass_from_body_fat(w, min(max(a["bf_pct"], 3), 60))
    ok &= abs(mm["lbm_kg"] + mm["fat_kg"] - w) < 1e-9
    bo = B.lbm_boer(sex, w, h); ok &= 0 <= bo["lbm_kg"] <= w
    hw = B.healthy_weight_range(h, 30); ok &= hw["min_kg"] < hw["max_kg"]
    load = rng.uniform(5, 250); reps = rng.randint(1, 9)
    ok &= T.e1rm(load, reps) >= load and T.e1rm(load, reps + 1) > T.e1rm(load, reps)
    if not ok:
        fails += 1; print("INVARIANT FAIL body/e1rm", sex, h, neck, waist, hip, w, load, reps); break
for _ in range(5000):
    sex = rng.choice("MF"); tdee = rng.uniform(1300, 3500); goal = rng.choice(["lose", "gain", "maintain"])
    base = tdee - min(0.2 * tdee, 500) if goal == "lose" else tdee * 1.1 if goal == "gain" else tdee
    floor = 1200 if sex == "F" else 1500
    base = max(base, min(floor, tdee)) if goal != "gain" else base
    start = rng.uniform(55, 130); per_wk = rng.uniform(-1.5, 1.0)
    d0 = date(2026, 3, 1)
    ws = [((d0 + timedelta(days=i)).isoformat(), start * (1 + per_wk / 100 * i / 7) + rng.uniform(-0.6, 0.6))
          for i in range(29) if rng.random() < 0.8]
    cum = rng.choice([0.0, 0.05, -0.05, 0.10, -0.10, 0.15, -0.15])
    r = K.periodic_adjustment(ws, "2026-03-29", "2026-03-01", None, goal, rng.choice(["<6m", ">2y"]),
                              tdee, base, cum, sex)
    t = r["target_kcal"]
    ok = abs(r["cum"]) <= 0.15 + 1e-9 and t >= min(floor, tdee) - 1e-9
    if goal == "lose":
        ok &= t <= tdee + 1e-9 and t >= tdee - 500 - 1e-9
    ok &= abs(base + r["cum"] * tdee - t) < 1e-6
    tw = K.weight_trend(ws)
    ok &= all(min(x[1] for x in ws) - 1e-9 <= p["trend"] <= max(x[1] for x in ws) + 1e-9 for p in tw)
    if not ok:
        fails += 1; print("INVARIANT FAIL tracking", goal, tdee, base, cum, r); break
print("invariants: 20,000 body/e1RM + 5,000 tracking profiles")

# ---------- 4. bad inputs ----------
bad = [lambda: B.navy_body_fat("M", 175, 40, 38), lambda: B.navy_body_fat("F", 165, 32, 72),
       lambda: B.navy_body_fat("M", 300, 40, 90), lambda: B.navy_body_fat("X", 175, 40, 90),
       lambda: B.mass_from_body_fat(80, 0), lambda: B.lbm_boer("X", 80, 180),
       lambda: B.healthy_weight_range(170, 16), lambda: T.exercise_kcal("99999", 80, 30),
       lambda: T.exercise_kcal("02054", 0, 30), lambda: T.e1rm(0, 5), lambda: T.e1rm(80, 0),
       lambda: T.weekly_volume([{"exercise_id": "unknown", "weight_kg": 50, "reps": 10}], {}),
       lambda: K.weight_trend([("2026-01-01", 5.0)]), lambda: K.recipe_per_serving([], 0)]
for f in bad:
    try:
        f(); fails += 1; print("FAIL no error")
    except ValueError:
        pass
print(f"bad inputs: {len(bad)} rejected")

print("\nRESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
