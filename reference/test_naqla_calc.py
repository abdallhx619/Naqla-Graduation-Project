"""Tests for the Naqla v1.1 engine. Run from the repo root: python3 reference/test_naqla_calc.py

1. Hand-checked cases: expected values worked out by hand, not by the engine.
2. Regression: every vector in the JSON must reproduce within 1e-6.
3. Invariants on 50,000 random valid profiles.
4. Bad inputs must raise.
5. WHO LMS z-score round trip.
"""
import json
import math
import random
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
import naqla_calc as E  # noqa: E402

TOL = 1e-6
fails = 0


def close(a, b, what):
    global fails
    if abs(a - b) > TOL:
        fails += 1
        print(f"FAIL {what}: got {a!r} expected {b!r}")


# ---------- 1. hand-checked ----------
# H1 M30 180/95 sed lose: REE=950+1125-150+5=1930, TDEE=1930*1.25=2412.5,
# BMI 29.32 -> 20% = 482.5 -> target 1930. Protein 2.0*95=190 > cap .35*1930/4=168.875.
r = E.compute(sex="M", age=30, h=180, w=95, goal="lose")
close(r["ree"], 1930, "H1 ree"); close(r["tdee"], 2412.5, "H1 tdee"); close(r["target_kcal"], 1930, "H1 target")
close(r["protein_g"], 168.875, "H1 protein cap"); close(r["fat_g"], 0.25 * 1930 / 9, "H1 fat")
close(r["carbs_g"], (1930 - 4 * 168.875 - 9 * (0.25 * 1930 / 9)) / 4, "H1 carbs")
# H2 TDEE exactly 2500 -> deficit exactly 500 -> 2000
r = E.compute(sex="M", age=25, h=190, w=93.25, goal="lose")
close(r["tdee"], 2500, "H2 tdee"); close(r["target_kcal"], 2000, "H2 target")
# H3 F70 150/45: REE=450+937.5-350-161=876.5, TDEE=1095.625 <= 1200 -> maintain at TDEE
r = E.compute(sex="F", age=70, h=150, w=45, goal="lose")
close(r["target_kcal"], 1095.625, "H3 target"); assert r["goal_applied"] == "maintain" and r["floor_hit"]
# H4 teen Normal cannot lose (rule A); teen Overweight can
assert E.compute(sex="F", age=16, h=160, w=52, age_months=192, goal="lose")["goal_applied"] == "maintain"
r = E.compute(sex="F", age=16, h=160, w=70, age_months=192, goal="lose")
assert r["class"] == "overweight" and r["goal_applied"] == "lose"
# H5 teen growth +25: F16 160/52 REE=520+1000-80-161=1279, TDEE=1279*1.25+25=1623.75
close(E.compute(sex="F", age=16, h=160, w=52, age_months=192, goal="maintain")["tdee"], 1623.75, "H5 teen +25")
# H6 teen protein cap 30%: M17 175/110 obesity: TDEE=2113.75*1.25+25=2667.1875, target=2167.1875,
# protein 2*91.875=183.75 > .30*2167.1875/4=162.5390625
close(E.compute(sex="M", age=17, h=175, w=110, age_months=204, goal="lose")["protein_g"], 0.30 * 2167.1875 / 4, "H6")
# H7 PAL cap for women: 1.39+3.5*1.42*120/1440 + 8.3*1.42*60/1440 + 2.5*1.42*90/1440 = 2.5170 -> 2.5
r = E.compute(sex="F", age=25, h=165, w=60, base="heavy", acts=[("run", 7, 60), ("strength", 7, 90)], goal="maintain")
close(r["pal"], 2.5, "H7 pal cap"); assert r["pal_capped"]
# H8 Cunningham: 370 + 21.6*90*0.85 = 2022.4
close(E.compute(sex="M", age=32, h=180, w=90, bf_device=0.15, goal="maintain")["ree"], 2022.4, "H8")
# H9 gain advanced +5%, beginner +10%
r = E.compute(sex="M", age=27, h=175, w=68, exp=">2y", goal="gain"); close(r["target_kcal"], r["tdee"] * 1.05, "H9a")
r = E.compute(sex="M", age=27, h=175, w=68, exp="6m-2y", goal="gain"); close(r["target_kcal"], r["tdee"] * 1.10, "H9b")
# H10 BMI exactly on a cut-off goes up (float noise tolerated)
assert E.adult_class(72.25 / (1.7 * 1.7)) == "pre_obese"
assert E.adult_class(53.465 / (1.7 * 1.7)) == "normal"
assert E.adult_class(24.999) == "normal"
print("hand-checked: done")

# ---------- 2. regression ----------
data = json.load(open(ROOT / "tests" / "vectors" / "calc_v1.1.json", encoding="utf-8"))
for v in data["vectors"]:
    got = E.compute(**{k: (tuple(map(tuple, x)) if k == "acts" else x) for k, x in v["inputs"].items()})
    for key, exp in v["expected"].items():
        if isinstance(exp, float):
            close(got[key], exp, f"{v['id']} {key}")
        elif got[key] != exp and key != "spec_version":
            fails += 1; print(f"FAIL {v['id']} {key}: {got[key]} != {exp}")
bv = json.load(open(ROOT / "tests" / "vectors" / "bmi_v1.1.json", encoding="utf-8"))
for v in bv["vectors"]:
    x = E.bmi(v["input"]["weight_kg"], v["input"]["height_cm"])
    close(x, v["expected"]["bmi"], v["id"])
    if E.adult_class(x) != v["expected"]["class"]:
        fails += 1; print("FAIL", v["id"])
print(f"regression: {len(data['vectors'])} calc vectors + {len(bv['vectors'])} BMI vectors checked")

# ---------- 3. invariants ----------
rng = random.Random(425)
N = 50_000
for i in range(N):
    sex = rng.choice("MF"); age = rng.randint(16, 90)
    h = rng.uniform(145, 205); w = rng.uniform(38, 200)
    acts = []
    if rng.random() < .6: acts.append(("strength", rng.randint(0, 7), rng.choice(E.STRENGTH_MINUTES)))
    if rng.random() < .5: acts.append((rng.choice(["brisk", "jog", "run", "bike"]), rng.randint(0, 7), rng.choice(E.CARDIO_MINUTES)))
    kw = dict(sex=sex, age=age, h=h, w=w, goal=rng.choice(["lose", "gain", "maintain"]),
              base=rng.choice(["sed", "stand", "heavy"]), acts=acts, exp=rng.choice(E.EXPERIENCE),
              bf_device=rng.choice([None, None, rng.uniform(.05, .5)]),
              age_months=age * 12 + rng.randint(0, 11) if age <= 17 else None, health_flag=rng.random() < .05)
    r = E.compute(**kw)
    t, tdee, floor = r["target_kcal"], r["tdee"], (1200 if sex == "F" else 1500)
    ok = True
    ok &= r["pal"] <= 2.5 + 1e-12
    ok &= abs(4 * r["protein_g"] + 9 * r["fat_g"] + 4 * r["carbs_g"] - t) < 1e-6   # macros add up exactly
    ok &= r["carbs_g"] > 0 and r["protein_g"] > 0
    ok &= 4 * r["protein_g"] <= (0.30 if age <= 17 else 0.35) * t + 1e-9
    if r["goal_applied"] == "lose":
        ok &= t >= floor - 1e-9 and tdee - t <= 500 + 1e-9 and t < tdee
    if r["goal_applied"] == "maintain":
        ok &= abs(t - tdee) < 1e-9
    if r["goal_applied"] == "gain":
        ok &= abs(t / tdee - (1.05 if kw["exp"] == ">2y" else 1.10)) < 1e-12
    if kw["health_flag"]:
        ok &= r["goal_applied"] == "maintain"
    if r["class"] in ("underweight", "thinness", "severe_thinness") or (age <= 17 and r["class"] == "normal"):
        ok &= r["goal_applied"] != "lose"
    if r["class"] in ("obese_1", "obese_2", "obese_3", "obesity"):
        ok &= r["goal_applied"] != "gain"
    if not ok:
        fails += 1; print("INVARIANT FAIL", kw, r); break
print(f"invariants: {N} random profiles")

# ---------- 4. bad inputs ----------
bad = [dict(sex="M", age=15, h=170, w=60, goal="lose"),
       dict(sex="M", age=17, h=170, w=60, goal="lose"),                      # teen without age_months
       dict(sex="M", age=17, h=170, w=60, goal="lose", age_months=192),      # months don't match age
       dict(sex="M", age=30, h=170, w=60, goal="lose", acts=[("strength", 5, 75)]),
       dict(sex="M", age=30, h=170, w=60, goal="lose", acts=[("run", 8, 30)]),
       dict(sex="M", age=30, h=170, w=60, goal="lose", acts=[("swim", 3, 30)]),
       dict(sex="X", age=30, h=170, w=60, goal="lose"),
       dict(sex="M", age=30, h=170, w=60, goal="cut"),
       dict(sex="M", age=30, h=170, w=60, goal="gain", exp="1y"),
       dict(sex="M", age=30, h=170, w=60, goal="lose", bf_device=15)]
for kw in bad:
    try:
        E.compute(**kw); fails += 1; print("FAIL no error for", kw)
    except ValueError:
        pass
print(f"bad inputs: {len(bad)} rejected")

# ---------- 5. LMS ----------
L, M, S = -1.2, 21.0, 0.13   # synthetic but realistic LMS triple
for z in (-2.5, -2.0, -1.0, 0.0, 1.0, 2.0, 2.9):
    b = M * (1 + L * S * z) ** (1 / L)
    close(E.who_bmi_z(b, L, M, S), z, f"LMS round trip z={z}")
assert E.teen_class_from_z(1.0) == "normal" and E.teen_class_from_z(1.0001) == "overweight"
assert E.teen_class_from_z(-2.0) == "normal" and E.teen_class_from_z(-2.0001) == "thinness"
assert E.who_bmi_z(M * (1 + L * S * 3) ** (1 / L) + 1, L, M, S) > 3
# real WHO table: girls 17:0 cut-offs published as 16.4 / 18.4 / 24.5 / 29.3
L, M, S = E.lms("F", 204)
for z, pub in ((-2, 16.4), (-1, 18.4), (1, 24.5), (2, 29.3)):
    v = M * (1 + L * S * z) ** (1 / L)
    if abs(v - pub) > 0.05:
        fails += 1; print("FAIL WHO table", z, v, pub)
print("LMS: done (incl. WHO published cut-offs)")

# ---------- 6. config/formulas.yaml matches the engine ----------
try:
    import yaml
except ImportError:
    print("config check: skipped (pip install pyyaml)")
else:
    cfg = yaml.safe_load(open(ROOT / "config" / "formulas.yaml", encoding="utf-8"))
    checks = [
        (cfg["version"], E.SPEC_VERSION, "version"),
        (cfg["pal"]["k"]["men"], E.K["M"], "k men"), (cfg["pal"]["k"]["women"], E.K["F"], "k women"),
        (cfg["pal"]["base"]["sed"]["value"], E.BASE_PAL["sed"], "base sed"),
        (cfg["pal"]["base"]["stand"]["value"], E.BASE_PAL["stand"], "base stand"),
        (cfg["pal"]["met"]["strength"]["value"], E.MET["strength"], "MET strength"),
        (cfg["pal"]["met"]["brisk_walk"]["value"], E.MET["brisk"], "MET brisk"),
        (cfg["pal"]["met"]["jog"]["value"], E.MET["jog"], "MET jog"),
        (cfg["pal"]["met"]["run"]["value"], E.MET["run"], "MET run"),
        (cfg["pal"]["met"]["stationary_bike"]["value"], E.MET["bike"], "MET bike"),
        (cfg["pal"]["onboarding_options"]["strength_minutes"], list(E.STRENGTH_MINUTES), "strength minutes"),
        (cfg["pal"]["onboarding_options"]["cardio_minutes"], list(E.CARDIO_MINUTES), "cardio minutes"),
        (cfg["goals"]["gain"]["experience_levels"], list(E.EXPERIENCE), "experience levels"),
    ]
    for a, b, what in checks:
        if a != b:
            fails += 1; print(f"FAIL config {what}: yaml={a!r} engine={b!r}")
    print(f"config check: {len(checks)} values match")

print("\nRESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
