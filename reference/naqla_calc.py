"""Naqla calorie & macro reference engine — spec v1.1 (18 Nov 2026).

Changes from v1.0
  1. No rounding anywhere (step 9 "nearest 50 kcal" removed). Full double
     precision end to end; only a float tolerance EPS at cut-offs.
  2. Teens 16–17 may choose weight loss ONLY if BMI-for-age z > +1
     (Overweight or Obesity). Normal / Thinness teens get maintenance.
  3. Teen protein cap = 30 % of kcal (IOM AMDR 4–18 y: protein 10–30 %);
     adults keep 35 %.
  4. Onboarding inputs are validated (strength 30/45/60/90 min,
     cardio 15/30/45/60 min, 0–7 days).
  5. Teens are classified from the official WHO 2007 BMI-for-age LMS table
     (config/who2007_bmi_for_age_lms.csv) using age in completed months.

Sources: Mifflin 1990; Cunningham 1991; IOM 2005 (PAL method, k factors,
+25 kcal growth, AMDR); Compendium 2024 (MET); WHO TRS 894 & WHO 2007
BMI-for-age; Garthe 2011; Murphy & Koehler 2022; AHA/ACC/TOS 2013;
Iraki 2019; Helms 2023; ISSN 2017; Morton 2018; Weijs 2024.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

SPEC_VERSION = "1.2"
EPS = 1e-9

K = {"M": 1.34, "F": 1.42}            # IOM: 1.15/0.9/0.95 (men), 1.15/0.9/0.91 (women)
MET = {"strength": 3.5,               # 02054
       "brisk": 4.8,                  # 17200
       "jog": 8.5,                    # 12030
       "run": 9.3,                    # 12050
       "bike": 6.8}                   # 01200
HEAVY_WORK_MET = 4.5                   # 11476, 2 h/day assumption (team estimate)
BASE_PAL = {"sed": 1.25, "stand": 1.39}
STRENGTH_MINUTES = (30, 45, 60, 90)
CARDIO_MINUTES = (15, 30, 45, 60)
EXPERIENCE = ("<6m", "6m-2y", ">2y")

ADULT_OBESE = {"obese_1", "obese_2", "obese_3"}
LMS_PATH = Path(__file__).resolve().parent.parent / "config" / "who2007_bmi_for_age_lms.csv"
_LMS = None


def lms(sex: str, age_months: int):
    global _LMS
    if _LMS is None:
        with open(LMS_PATH, newline="") as f:
            _LMS = {(r["sex"], int(r["age_months"])): (float(r["L"]), float(r["M"]), float(r["S"]))
                    for r in csv.DictReader(f)}
    return _LMS[(sex, age_months)]
TEEN_CLASSES = {"severe_thinness", "thinness", "normal", "overweight", "obesity"}


def ge(a: float, b: float) -> bool:
    return a >= b - EPS


# ---------- classification ----------
def bmi(weight_kg: float, height_cm: float) -> float:
    h = height_cm / 100
    return weight_kg / (h * h)


def adult_class(b: float) -> str:
    if ge(b, 40): return "obese_3"
    if ge(b, 35): return "obese_2"
    if ge(b, 30): return "obese_1"
    if ge(b, 25): return "pre_obese"
    if ge(b, 18.5): return "normal"
    return "underweight"


def who_bmi_z(b: float, L: float, M: float, S: float) -> float:
    """WHO 2007 LMS z-score, with WHO's adjustment beyond ±3 SD."""
    def at(z):
        return M * (1 + L * S * z) ** (1 / L)
    z = ((b / M) ** L - 1) / (L * S) if abs(L) > 1e-12 else math.log(b / M) / S
    if z > 3:
        return 3 + (b - at(3)) / (at(3) - at(2))
    if z < -3:
        return -3 + (b - at(-3)) / (at(-2) - at(-3))
    return z


def teen_class_from_z(z: float) -> str:
    if z > 2: return "obesity"
    if z > 1: return "overweight"
    if z < -3: return "severe_thinness"
    if z < -2: return "thinness"
    return "normal"


# ---------- energy ----------
def ree(sex, age, h, w, bf_device=None):
    if bf_device is not None:
        if not 0 < bf_device < 1:
            raise ValueError("bf_device must be a fraction between 0 and 1")
        return 370 + 21.6 * (w * (1 - bf_device)), "cunningham"
    return 10 * w + 6.25 * h - 5 * age + (5 if sex == "M" else -161), "mifflin"


def pal(sex, base, acts):
    if base == "heavy":
        total = BASE_PAL["stand"] + (HEAVY_WORK_MET - 1) * K[sex] * 120 / 1440
    elif base in BASE_PAL:
        total = BASE_PAL[base]
    else:
        raise ValueError(f"unknown base {base}")
    for kind, days, mins in acts:
        if kind not in MET:
            raise ValueError(f"unknown activity {kind}")
        allowed = STRENGTH_MINUTES if kind == "strength" else CARDIO_MINUTES
        if mins not in allowed:
            raise ValueError(f"{kind} {mins} min is not an onboarding option {allowed}")
        if not (isinstance(days, int) and 0 <= days <= 7):
            raise ValueError("days must be an integer 0-7")
        total += (MET[kind] - 1) * K[sex] * (days * mins / 7) / 1440
    capped = total > 2.5
    return min(total, 2.5), capped


# ---------- main ----------
def compute(sex, age, h, w, goal, base="sed", acts=(), exp="<6m",
            bf_device=None, age_months=None, health_flag=False):
    if sex not in K:
        raise ValueError("sex must be 'M' or 'F'")
    if age < 16:
        raise ValueError("under 16 is not supported")
    if goal not in ("lose", "gain", "maintain"):
        raise ValueError("goal must be lose/gain/maintain")
    if exp not in EXPERIENCE:
        raise ValueError(f"exp must be one of {EXPERIENCE}")
    teen = age <= 17
    b = bmi(w, h)
    z = None
    if teen:
        if age_months is None or age_months // 12 != age:
            raise ValueError("teens need age_months (completed months, matching age)")
        z = who_bmi_z(b, *lms(sex, age_months))
        cls = teen_class_from_z(z)
        obese = cls == "obesity"
        thin = cls in ("thinness", "severe_thinness")
        may_lose = cls in ("overweight", "obesity")          # v1.1 rule A
    else:
        cls = adult_class(b)
        obese = cls in ADULT_OBESE
        thin = cls == "underweight"
        may_lose = not thin

    r, method = ree(sex, age, h, w, bf_device)
    p, pal_capped = pal(sex, base, acts)
    tdee = r * p + (25 if teen else 0)

    applied, reasons = goal, []
    if health_flag and goal != "maintain":
        applied = "maintain"; reasons.append("health_screen")
    elif goal == "lose" and not may_lose:
        applied = "maintain"; reasons.append("thinness" if (teen and thin) else "teen_not_overweight" if teen else "underweight")
    elif goal == "gain" and obese:
        applied = "maintain"; reasons.append("obese_no_gain")

    if applied == "lose":
        deficit = min((0.25 if obese else 0.20) * tdee, 500)
        target = tdee - deficit
    elif applied == "gain":
        target = tdee * (1.05 if exp == ">2y" else 1.10)
    else:
        target = tdee

    floor = 1200 if sex == "F" else 1500
    floor_hit = False
    if applied == "lose":
        if ge(floor, tdee):
            applied, target, floor_hit = "maintain", tdee, True
            reasons.append("floor_at_or_above_maintenance")
        elif target < floor:
            target, floor_hit = float(floor), True
            reasons.append("floor_applied")

    ref_w = min(w, 30 * (h / 100) ** 2)
    p_cap_share = 0.30 if teen else 0.35
    protein_raw = (2.0 if applied == "lose" else 1.6) * ref_w
    protein_cap = p_cap_share * target / 4
    protein = min(protein_raw, protein_cap)
    fat = (0.30 if teen else 0.25) * target / 9
    carbs = (target - 4 * protein - 9 * fat) / 4
    return {"bmi": b, "bmi_for_age_z": z, "class": cls, "ree": r, "ree_method": method, "pal": p,
            "pal_capped": pal_capped, "tdee": tdee, "goal_requested": goal,
            "goal_applied": applied, "reasons": reasons, "target_kcal": target,
            "floor_hit": floor_hit, "protein_g": protein,
            "protein_capped": protein_raw > protein_cap, "fat_g": fat, "carbs_g": carbs,
            "spec_version": SPEC_VERSION}
