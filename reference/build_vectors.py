"""Builds tests/vectors/*.json — every rule branch, cut-off and input option."""
"""Run from the repo root: python3 reference/build_vectors.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
from naqla_calc import (compute, adult_class, bmi, lms, SPEC_VERSION,  # noqa: E402
                        STRENGTH_MINUTES, CARDIO_MINUTES)

V = []


def add(group, desc, **kw):
    V.append({"id": f"{group}-{sum(1 for v in V if v['group'] == group) + 1:03d}",
              "group": group, "description": desc, "inputs": kw, "expected": compute(**kw)})


# 1. The 20 spec cases (with the two fixes; case 3 now hits teen rule A)
S = [
 ("M25 sedentary strength 4x60 lose", dict(sex="M", age=25, h=178, w=80, acts=[("strength", 4, 60)], goal="lose")),
 ("F30 sedentary maintain", dict(sex="F", age=30, h=162, w=60, goal="maintain")),
 ("F16 Normal lose -> maintain (rule A)", dict(sex="F", age=16, h=160, w=52, age_months=192, goal="lose")),
 ("M17 Obesity lose, 500 cap", dict(sex="M", age=17, h=175, w=110, age_months=204, goal="lose")),
 ("M17 Normal standing strength 3x60 gain", dict(sex="M", age=17, h=175, w=60, age_months=204, base="stand", acts=[("strength", 3, 60)], goal="gain")),
 ("M35 obese III lose", dict(sex="M", age=35, h=175, w=130, goal="lose")),
 ("F40 BMI 29.9 lose", dict(sex="F", age=40, h=165, w=81.4, goal="lose")),
 ("F40 BMI 30.0 lose", dict(sex="F", age=40, h=165, w=81.7, goal="lose")),
 ("F55 lose, floor", dict(sex="F", age=55, h=152, w=50, goal="lose")),
 ("F22 underweight lose -> maintain", dict(sex="F", age=22, h=168, w=50, goal="lose")),
 ("M28 advanced strength 5x60 gain", dict(sex="M", age=28, h=180, w=85, acts=[("strength", 5, 60)], goal="gain", exp=">2y")),
 ("M30 obese gain -> maintain", dict(sex="M", age=30, h=175, w=105, goal="gain")),
 ("M26 heavy + run 6x60 + strength 5x90", dict(sex="M", age=26, h=172, w=62, base="heavy", acts=[("run", 6, 60), ("strength", 5, 90)], goal="maintain")),
 ("M32 BF 15% device (Cunningham)", dict(sex="M", age=32, h=180, w=90, bf_device=0.15, acts=[("strength", 4, 60)], goal="lose")),
 ("M32 BF from tape (Mifflin)", dict(sex="M", age=32, h=180, w=90, acts=[("strength", 4, 60)], goal="lose")),
 ("F27 standing brisk 3x30 lose", dict(sex="F", age=27, h=165, w=70, base="stand", acts=[("brisk", 3, 30)], goal="lose")),
 ("M45 heavy work lose", dict(sex="M", age=45, h=170, w=95, base="heavy", goal="lose")),
 ("F19 gain beginner", dict(sex="F", age=19, h=158, w=48, goal="gain")),
 ("F17 Thinness lose -> maintain", dict(sex="F", age=17, h=158, w=40, age_months=204, goal="lose")),
 ("F24 strength 3x45 + bike 2x30", dict(sex="F", age=24, h=170, w=65, acts=[("strength", 3, 45), ("bike", 2, 30)], goal="maintain")),
]
for d, kw in S:
    add("SPEC", d, **kw)

# 2. Adult BMI cut-offs (height 170 cm) x goal x sex
for target_bmi in (18.4, 18.5, 24.9, 25.0, 29.9, 30.0, 34.9, 35.0, 39.9, 40.0):
    w = target_bmi * 1.7 * 1.7
    for sex in ("M", "F"):
        for goal in ("lose", "gain", "maintain"):
            add("BMI", f"{sex} BMI {target_bmi} {goal}", sex=sex, age=30, h=170, w=w, goal=goal)

# 3. Teens: real WHO LMS cut-offs. For each sex x age-month, weights just
#    inside each class (z = -3.2, -2.5, 0, 1.5, 2.5) x goal
for age_m in (192, 198, 204, 210, 215):
    for sex in ("M", "F"):
        L, M, S = lms(sex, age_m)
        for z in (-3.2, -2.5, 0.0, 1.5, 2.5):
            zz = max(min(z, 3), -3)
            b_ = M * (1 + L * S * zz) ** (1 / L)
            w = b_ * 1.7 * 1.7
            for goal in ("lose", "gain", "maintain"):
                add("TEEN", f"{sex} {age_m // 12}y{age_m % 12}m z~{z} {goal}", sex=sex, age=age_m // 12, h=170, w=w,
                    age_months=age_m, goal=goal)

# 3b. Teens exactly around each WHO cut-off (z = cut-off -/+ 0.001)
for age_m in (192, 204, 215):
    for sex in ("M", "F"):
        L, M, S = lms(sex, age_m)
        for cut in (-3, -2, 1, 2):
            for d in (-0.001, 0.001):
                b_ = M * (1 + L * S * (cut + d)) ** (1 / L)
                add("TEENZ", f"{sex} {age_m}m z={cut + d:+.3f}", sex=sex, age=age_m // 12, h=170, w=b_ * 2.89,
                    age_months=age_m, goal="lose")

# 4. Ages (adult switch at 18, Mifflin range 19-78, older)
for age in (18, 19, 30, 59, 60, 78, 85):
    for sex in ("M", "F"):
        add("AGE", f"{sex} age {age} lose", sex=sex, age=age, h=170, w=80, goal="lose")

# 5. PAL: base x sex x strength days (60 min)
for base in ("sed", "stand", "heavy"):
    for sex in ("M", "F"):
        for d in range(8):
            add("PAL", f"{sex} {base} strength {d}x60", sex=sex, age=30, h=175, w=75, base=base,
                acts=[("strength", d, 60)] if d else [], goal="maintain")

# 6. Every onboarding duration option
for mins in STRENGTH_MINUTES:
    for sex in ("M", "F"):
        add("DUR", f"{sex} strength 4x{mins}", sex=sex, age=30, h=175, w=75, acts=[("strength", 4, mins)], goal="maintain")
for kind in ("brisk", "jog", "run", "bike"):
    for mins in CARDIO_MINUTES:
        for sex in ("M", "F"):
            add("DUR", f"{sex} {kind} 3x{mins}", sex=sex, age=30, h=175, w=75, acts=[(kind, 3, mins)], goal="maintain")

# 7. PAL cap (only reachable for women)
add("CAP", "F heavy + run 7x60 + strength 7x90 -> PAL 2.5", sex="F", age=25, h=165, w=60, base="heavy",
    acts=[("run", 7, 60), ("strength", 7, 90)], goal="maintain")
add("CAP", "M heavy + run 7x60 + strength 7x90 (max male, below 2.5)", sex="M", age=25, h=180, w=80, base="heavy",
    acts=[("run", 7, 60), ("strength", 7, 90)], goal="maintain")

# 8. Deficit cap & obesity share
add("DEF", "M TDEE exactly 2500, 20% = 500", sex="M", age=25, h=190, w=93.25, goal="lose")
add("DEF", "M heavy work, 20% of TDEE > 500 -> capped at 500", sex="M", age=25, h=190, w=93.25, base="heavy", goal="lose")
add("DEF", "F obese, 25% under 500", sex="F", age=45, h=160, w=85, goal="lose")
add("DEF", "M obese, 25% over 500 -> 500", sex="M", age=30, h=180, w=120, base="stand", goal="lose")

# 9. Calorie floors
add("FLOOR", "F70 small: floor >= TDEE -> maintain", sex="F", age=70, h=150, w=45, goal="lose")
add("FLOOR", "F55: target under floor -> 1200", sex="F", age=55, h=152, w=50, goal="lose")
add("FLOOR", "M80 small: floor >= TDEE -> maintain", sex="M", age=80, h=160, w=55, goal="lose")
add("FLOOR", "M65: target under 1500 -> 1500", sex="M", age=65, h=165, w=62, goal="lose")

# 10. Body fat from device (Cunningham) vs none
for bf in (0.05, 0.15, 0.30, 0.45):
    for sex in ("M", "F"):
        add("BF", f"{sex} device BF {int(bf*100)}%", sex=sex, age=30, h=175, w=85, bf_device=bf, goal="lose")

# 11. Experience levels for gain
for exp in ("<6m", "6m-2y", ">2y"):
    for sex in ("M", "F"):
        add("EXP", f"{sex} gain exp {exp}", sex=sex, age=27, h=175, w=68, exp=exp, goal="gain")

# 12. Health screen
for goal in ("lose", "gain", "maintain"):
    add("HEALTH", f"health flag, {goal} -> maintain", sex="F", age=30, h=165, w=75, health_flag=True, goal=goal)

# 13. Protein cap
add("PCAP", "M pre-obese lose, protein hits 35%", sex="M", age=30, h=180, w=95, goal="lose")
add("PCAP", "F lose, protein hits 35%", sex="F", age=40, h=165, w=68, goal="lose")
add("PCAP", "M17 obesity lose, teen protein hits 30%", sex="M", age=17, h=175, w=110, age_months=204, goal="lose")
add("PCAP", "very tall heavy man, BMI-30 reference weight", sex="M", age=30, h=200, w=150, goal="lose")

out = ROOT / "tests" / "vectors"
with open(out / "calc.json", "w", encoding="utf-8") as f:
    json.dump({"spec_version": SPEC_VERSION, "tolerance_abs": 1e-6, "count": len(V),
               "note": "No rounding anywhere. Teens are classified from the WHO 2007 LMS table.",
               "vectors": V}, f, ensure_ascii=False, indent=1)

# BMI-only vectors (adults)
BV = []
for cid, w, h, why in [
    ("N01", 80, 178, "normal case"), ("N02", 60, 162, "normal"), ("N03", 130, 175, "obese III"),
    ("N04", 50, 168, "underweight"), ("N05", 105, 175, "obese I"), ("N06", 95, 170, "obese I"),
    ("B01", 81.4, 165, "29.90 just under 30"), ("B02", 81.7, 165, "30.01 just over 30"),
    ("B03", 53.465, 170, "exactly 18.50 -> higher class"), ("B04", 53.17, 170, "18.398"),
    ("B05", 72.25, 170, "exactly 25.00 (float noise)"), ("B06", 72.1, 170, "24.948"),
    ("B07", 72.13, 170, "24.958 stays normal (no rounding)"), ("B08", 86.58, 170, "29.958 stays pre-obese"),
    ("B09", 101.15, 170, "exactly 35.00"), ("B10", 115.6, 170, "exactly 40.00"),
    ("B11", 115.5, 170, "39.965 stays obese II"), ("E01", 45, 150, "20.0"),
    ("E02", 40, 190, "very low 11.08"), ("E03", 200, 160, "very high 78.1")]:
    x = bmi(w, h)
    BV.append({"id": cid, "input": {"weight_kg": w, "height_cm": h},
               "expected": {"bmi": x, "class": adult_class(x)}, "note": why})
with open(out / "bmi.json", "w", encoding="utf-8") as f:
    json.dump({"spec_version": SPEC_VERSION, "tolerance_abs": 1e-6, "count": len(BV),
               "rule": "exact BMI, no rounding; float tolerance 1e-9 at cut-offs; cut-off values go to the higher class",
               "vectors": BV}, f, ensure_ascii=False, indent=1)
import vectors_v12  # noqa: E402
extra = vectors_v12.build(out)
groups = {}
for v in V:
    groups[v["group"]] = groups.get(v["group"], 0) + 1
print(len(V), "calc vectors:", groups)
print(len(BV), "bmi vectors;", "v1.2 modules:", extra)
