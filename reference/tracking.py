"""Naqla tracking reference (spec v1.2) — no rounding anywhere.

CALC-15 weight trend, the v1.1 periodic calorie adjustment, NUT-07 daily remaining, NUT-08 recipe maths.
Dates are ISO strings 'YYYY-MM-DD'.
"""
from __future__ import annotations

from datetime import date, timedelta

# ---------- CALC-15: weight trend ----------
HALF_LIFE_DAYS = 7.0                       # design choice: one week, matching the weekly weight rhythm
ALPHA_DAILY = 1 - 0.5 ** (1 / HALF_LIFE_DAYS)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def weight_trend(weighins: list[tuple[str, float]]) -> list[dict]:
    """Time-aware EWMA: a gap of n days uses alpha = 1 - (1 - alpha_daily)^n, so missed days
    are handled without inventing data. Several weigh-ins on one day are averaged first."""
    if not weighins:
        return []
    by_day = {}
    for d, w in weighins:
        if not (20 <= w <= 400):
            raise ValueError(f"implausible weight {w}")
        by_day.setdefault(d, []).append(w)
    days = sorted(by_day)
    out, trend, prev = [], None, None
    for d in days:
        w = sum(by_day[d]) / len(by_day[d])
        if trend is None:
            trend = w
        else:
            gap = (_d(d) - _d(prev)).days
            a = 1 - (1 - ALPHA_DAILY) ** gap
            trend = trend + a * (w - trend)
        out.append({"date": d, "weight": w, "trend": trend})
        prev = d
    return out


def week_mean(weighins: list[tuple[str, float]], end: str, min_count: int = 4) -> float | None:
    """Mean of the weigh-ins in the 7 days ending on `end` (inclusive); None if fewer than min_count days."""
    e = _d(end)
    start = e - timedelta(days=6)
    vals = {}
    for d, w in weighins:
        if start <= _d(d) <= e:
            vals.setdefault(d, []).append(w)
    if len(vals) < min_count:
        return None
    day_means = [sum(v) / len(v) for v in vals.values()]
    return sum(day_means) / len(day_means)


# ---------- periodic adjustment (spec v1.1, practice — owner-approved) ----------
TARGET_RATES = {                            # % body weight per week; negative = losing
    "lose": (-1.0, -0.5),
    "gain_under_2y": (0.25, 0.5),
    "gain_over_2y": (0.15, 0.35),           # "about 0.25 %" -> ±0.1 band (design choice)
    "maintain": (-0.25, 0.25),
}
STEP = 0.05
CUM_CAP = 0.15


def periodic_adjustment(weighins, today: str, plan_start: str, last_adjust: str | None, goal: str,
                        exp: str, tdee: float, base_target: float, cum: float, sex: str) -> dict:
    """Every 14 days compare the current week's mean with the week before last.
    Returns the new cumulative adjustment (fraction of TDEE) and the new target."""
    t = _d(today)
    res = {"cum": cum, "step": 0.0, "reason": None, "needs_review": False, "weekly_rate_pct": None}
    if (t - _d(plan_start)).days < 14:
        res["reason"] = "first_14_days"
    elif last_adjust is not None and (t - _d(last_adjust)).days < 14:
        res["reason"] = "adjusted_recently"
    else:
        now = week_mean(weighins, today)
        prev = week_mean(weighins, (t - timedelta(days=14)).isoformat())
        if now is None or prev is None:
            res["reason"] = "not_enough_weigh_ins"
        else:
            rate = (now - prev) / prev / 2 * 100
            res["weekly_rate_pct"] = rate
            key = goal if goal in ("lose", "maintain") else ("gain_over_2y" if exp == ">2y" else "gain_under_2y")
            lo, hi = TARGET_RATES[key]
            if rate > hi:
                res["step"], res["reason"] = -STEP, "faster_gain_or_slower_loss_than_planned"
            elif rate < lo:
                res["step"], res["reason"] = STEP, "faster_loss_or_slower_gain_than_planned"
            else:
                res["reason"] = "on_track"
    new_cum = cum + res["step"]
    if abs(new_cum) > CUM_CAP + 1e-12:
        new_cum = CUM_CAP if new_cum > 0 else -CUM_CAP
        res["needs_review"] = True
    wanted = base_target + new_cum * tdee
    floor = 1200 if sex == "F" else 1500
    target = max(wanted, min(floor, tdee))                    # never below the floor (or TDEE if lower)
    if goal == "lose":
        target = min(max(target, tdee - 500), tdee)           # keep the 500 kcal deficit cap; never above TDEE
    res["limited"] = abs(target - wanted) > 1e-9
    res["cum"] = (target - base_target) / tdee                # store only the change that actually applies
    res["target_kcal"] = target
    return res


# ---------- NUT-07: daily remaining ----------
def daily_remaining(target: dict, consumed: dict) -> dict:
    """target/consumed: {kcal, protein_g, fat_g, carbs_g}. Exact remaining values (negative = over).
    Returns a neutral message key per nutrient (see config/texts.yaml)."""
    out = {}
    for k in ("kcal", "protein_g", "fat_g", "carbs_g"):
        rem = target[k] - consumed.get(k, 0.0)
        out[k] = {"remaining": rem,
                  "pct_of_target": consumed.get(k, 0.0) / target[k] * 100 if target[k] else None,
                  "message": "over_target" if rem < 0 else "on_target" if rem == 0 else "under_target"}
    return out


# ---------- NUT-08: recipe per serving ----------
def recipe_per_serving(ingredients: list[dict], servings: float, cooked_total_g: float | None = None,
                       yield_pct: float | None = None) -> dict:
    """ingredients: {raw_g, per100g: {kcal, protein_g, fat_g, carbs_g}} using raw-ingredient nutrients.
    Cooking changes weight (mostly water), not the macros of what goes in: per-serving macros =
    total / servings; cooked weight from a weighing or a USDA cooking-yield % (Yield = cooked / raw x 100)."""
    if servings <= 0:
        raise ValueError("servings must be positive")
    keys = ("kcal", "protein_g", "fat_g", "carbs_g")
    totals = {k: sum(i["raw_g"] / 100 * i["per100g"][k] for i in ingredients) for k in keys}
    raw_total = sum(i["raw_g"] for i in ingredients)
    if cooked_total_g is None and yield_pct is not None:
        cooked_total_g = raw_total * yield_pct / 100
    cooked = cooked_total_g if cooked_total_g is not None else raw_total
    return {"per_serving": {k: v / servings for k, v in totals.items()},
            "serving_weight_g": cooked / servings,
            "per100g_cooked": {k: v / cooked * 100 for k, v in totals.items()},
            "yield_pct": cooked / raw_total * 100 if raw_total else None, "totals": totals}
