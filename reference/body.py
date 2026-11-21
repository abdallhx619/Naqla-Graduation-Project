"""Naqla body-composition reference (spec v1.2) — no rounding anywhere.

CALC-06 tape body fat (US Navy 1984), CALC-07 lean/fat mass (+ Boer fallback),
CALC-09 waist-to-height / waist-to-hip / waist circumference, CALC-10 healthy-weight range.
"""
from __future__ import annotations

import math

from naqla_calc import EPS, ge, lms

# ---------- CALC-06: tape body fat, Hodgdon & Beckett 1984 (NHRC 84-11 men, 84-29 women) ----------
NAVY_SEE = {"M": 3.52, "F": 3.72}       # standard error of estimate, % body fat
# measurement sites: men waist = abdomen at the navel ("abdomen II");
# women waist = natural waist, the narrowest point between sternum and navel ("abdomen I");
# women hip = greatest protrusion of the buttocks. All in cm.
TAPE_LIMITS = {"height": (120, 230), "neck": (20, 70), "waist": (40, 200), "hip": (50, 200)}


def _check(name, value):
    lo, hi = TAPE_LIMITS[name]
    if not (lo <= value <= hi):
        raise ValueError(f"{name} {value} cm outside {lo}-{hi} cm")


def navy_body_fat(sex: str, height_cm: float, neck_cm: float, waist_cm: float, hip_cm: float | None = None) -> dict:
    """%BF from circumferences. Returns the estimate and a ±SEE range, labelled as the tape method.

    Kept as its own method record: never merged or averaged with photo or InBody values,
    and never used to switch REE to Cunningham (device body fat only).
    """
    if sex not in NAVY_SEE:
        raise ValueError("sex must be 'M' or 'F'")
    _check("height", height_cm); _check("neck", neck_cm); _check("waist", waist_cm)
    if sex == "M":
        if waist_cm <= neck_cm:
            raise ValueError("waist must be larger than neck")
        density = 1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)
    else:
        if hip_cm is None:
            raise ValueError("women need a hip measurement")
        _check("hip", hip_cm)
        if waist_cm + hip_cm <= neck_cm:
            raise ValueError("waist + hip must be larger than neck")
        density = 1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm)
    bf = 495 / density - 450                     # Siri 1961
    see = NAVY_SEE[sex]
    return {"bf_pct": bf, "bf_low": bf - see, "bf_high": bf + see, "see": see,
            "density": density, "method": "tape_navy_1984",
            "in_validated_range": 2 <= bf <= 60,   # outside 2-60 %: do not show; ask to re-measure
            "can_drive_cunningham": False}


# ---------- CALC-07: lean / fat mass ----------
def mass_from_body_fat(weight_kg: float, bf_pct: float, bf_low: float | None = None,
                       bf_high: float | None = None, method: str = "unknown") -> dict:
    if not (0 < bf_pct < 100):
        raise ValueError("bf_pct must be between 0 and 100")
    out = {"lbm_kg": weight_kg * (1 - bf_pct / 100), "fat_kg": weight_kg * bf_pct / 100,
           "method": method, "rough": False}
    if bf_low is not None and bf_high is not None:   # propagate the BF% range
        out.update(lbm_low=weight_kg * (1 - bf_high / 100), lbm_high=weight_kg * (1 - bf_low / 100),
                   fat_low=weight_kg * bf_low / 100, fat_high=weight_kg * bf_high / 100)
    return out


def lbm_boer(sex: str, weight_kg: float, height_cm: float) -> dict:
    """Fallback when no body-fat % exists. Boer 1984, Am J Physiol 247:F632-F636. Labelled 'rough'."""
    if sex == "M":
        lbm = 0.407 * weight_kg + 0.267 * height_cm - 19.2
    elif sex == "F":
        lbm = 0.252 * weight_kg + 0.473 * height_cm - 48.3
    else:
        raise ValueError("sex must be 'M' or 'F'")
    lbm = min(max(lbm, 0.0), weight_kg)
    return {"lbm_kg": lbm, "fat_kg": weight_kg - lbm, "bf_pct": (weight_kg - lbm) / weight_kg * 100,
            "method": "boer_1984", "rough": True}


# ---------- CALC-09: central adiposity ----------
def waist_ratios(sex: str, age: int, height_cm: float, waist_cm: float, hip_cm: float | None = None,
                 bmi: float | None = None) -> dict:
    """Waist-to-height (NICE 2022/2025; Ashwell), waist-to-hip and waist circumference (WHO 2008)."""
    whtr = waist_cm / height_cm
    if ge(whtr, 0.6):
        whtr_class = "high"
    elif ge(whtr, 0.5):
        whtr_class = "increased"
    elif ge(whtr, 0.4):
        whtr_class = "healthy"
    else:
        whtr_class = "below_0_4"
    out = {"whtr": whtr, "whtr_class": whtr_class,
           "whtr_applies": bmi is None or bmi < 35 - EPS}     # NICE: use when BMI < 35
    adult = age >= 18
    if adult:
        inc, sub = (94, 102) if sex == "M" else (80, 88)
        out["waist_class"] = "substantially_increased" if ge(waist_cm, sub) else "increased" if ge(waist_cm, inc) else "not_increased"
    else:
        out["waist_class"] = None                               # adult cut-offs only
    if hip_cm is not None:
        whr = waist_cm / hip_cm
        cut = 0.90 if sex == "M" else 0.85
        out["whr"] = whr
        out["whr_class"] = ("substantially_increased" if ge(whr, cut) else "not_increased") if adult else None
    return out


# ---------- CALC-10: healthy-weight range ----------
def healthy_weight_range(height_cm: float, age: int, sex: str | None = None, age_months: int | None = None) -> dict:
    """Range only — never a single 'ideal weight'.
    Adults: BMI 18.5 to <25 (WHO TRS 894). Teens 16-17: WHO BMI-for-age z -2 to +1."""
    h2 = (height_cm / 100) ** 2
    if age >= 18:
        return {"min_kg": 18.5 * h2, "max_kg": 25.0 * h2, "max_exclusive": True, "basis": "adult_bmi_18.5_25"}
    if age_months is None or sex is None:
        raise ValueError("teens need sex and age_months")
    L, M, S = lms(sex, age_months)
    at = lambda z: M * (1 + L * S * z) ** (1 / L)  # noqa: E731
    return {"min_kg": at(-2) * h2, "max_kg": at(1) * h2, "max_exclusive": False, "basis": "who2007_z_-2_to_+1"}
