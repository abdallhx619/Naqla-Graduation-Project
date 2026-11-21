"""Naqla training reference (spec v1.2) — no rounding anywhere.

CALC-11 exercise energy (MET), CALC-12 e1RM, CALC-13 volume & intensity, CALC-14 PR detection.
"""
from __future__ import annotations

from collections import defaultdict

# ---------- CALC-11: MET table, 2024 Adult Compendium (values used unchanged) ----------
MET_TABLE = {
    "02050": (6.0, "Resistance training, vigorous (power lifting / bodybuilding)"),
    "02052": (5.0, "Squats / deadlift, slow or explosive"),
    "02054": (3.5, "Resistance training, multiple exercises, 8-15 reps"),
    "02055": (5.8, "Circuit / supersets"),
    "02056": (3.0, "Bodyweight exercises, general"),
    "02057": (6.5, "Bodyweight exercises, high intensity"),
    "17152": (2.8, "Walking 2.0-2.4 mph"),
    "17170": (3.0, "Walking 2.5 mph"),
    "17190": (3.8, "Walking 2.8-3.4 mph"),
    "17200": (4.8, "Walking 3.5-3.9 mph, brisk"),
    "17220": (5.5, "Walking 4.0-4.4 mph"),
    "12028": (6.5, "Running 4-4.2 mph"),
    "12030": (8.5, "Running 5.0-5.2 mph"),
    "12050": (9.3, "Running 6-6.3 mph"),
    "12070": (11.0, "Running 7 mph"),
    "12090": (12.0, "Running 8 mph"),
    "12120": (14.8, "Running 10 mph"),
    "01200": (6.8, "Stationary bike, general"),
    "01220": (6.0, "Stationary bike 90-100 W"),
    "01228": (8.0, "Stationary bike 126-150 W"),
    "01030": (8.0, "Bicycling 12-13.9 mph"),
    "01040": (10.0, "Bicycling 14-15.9 mph"),
}


def exercise_kcal(code: str, weight_kg: float, minutes: float, age: int | None = None) -> dict:
    """Gross kcal = MET x kg x hours (1 MET = 1 kcal/kg/h, Compendium). Net = (MET-1) x kg x hours.
    For tracking only: never added back to the day's food target (fixed daily calories)."""
    if code not in MET_TABLE:
        raise ValueError(f"unknown Compendium code {code}")
    if weight_kg <= 0 or minutes <= 0:
        raise ValueError("weight and minutes must be positive")
    met = MET_TABLE[code][0]
    h = minutes / 60
    return {"met": met, "kcal_gross": met * weight_kg * h, "kcal_net": (met - 1) * weight_kg * h,
            "older_adult_note": age is not None and age >= 60}   # Older Adult Compendium values not used yet


# ---------- CALC-12: e1RM, Brzycki 1993 ----------
MAX_REPS_FOR_E1RM = 10


def e1rm(weight_kg: float, reps: int, rir: int = 0) -> float | None:
    """1RM = w x 36 / (37 - r), r = reps + RIR (reps to failure). Returns None outside 1-10 reps
    (accuracy drops above ~10). Exact at r = 1."""
    if weight_kg <= 0 or reps < 1 or rir < 0:
        raise ValueError("weight > 0, reps >= 1, rir >= 0")
    r = reps + rir
    if r > MAX_REPS_FOR_E1RM:
        return None
    if r == 1:
        return weight_kg          # identical to w*36/36, avoids float noise
    return weight_kg * 36 / (37 - r)


# ---------- CALC-13: volume ----------
HARD_SET_MAX_RIR = 4          # design choice: no consensus definition of a "hard set"


def is_hard_set(s: dict) -> bool:
    if s.get("warmup"):
        return False
    rir = s.get("rir")
    return rir is None or rir <= HARD_SET_MAX_RIR


def weekly_volume(sets: list[dict], muscle_map: dict) -> dict:
    """Fractional sets per muscle (primary = 1, secondary = 0.5; Pelland et al. 2026),
    tonnage (working sets) and mean relative intensity (load / best e1RM in the data).
    sets: {exercise_id, weight_kg, reps, rir?, warmup?}; muscle_map: {exercise_id: {primary: [...], secondary: [...]}}"""
    fractional = defaultdict(float)
    tonnage = 0.0
    hard = 0
    best = {}
    for s in sets:
        e = e1rm(s["weight_kg"], s["reps"], s.get("rir") or 0) if not s.get("warmup") else None
        if e is not None:
            best[s["exercise_id"]] = max(best.get(s["exercise_id"], 0.0), e)
    rel = []
    for s in sets:
        if s.get("warmup"):
            continue
        tonnage += s["weight_kg"] * s["reps"]
        if s["exercise_id"] in best:
            rel.append(s["weight_kg"] / best[s["exercise_id"]])
        if not is_hard_set(s):
            continue
        hard += 1
        m = muscle_map.get(s["exercise_id"])
        if m is None:
            raise ValueError(f"exercise {s['exercise_id']} missing from the muscle map (WRK-01)")
        for mu in m.get("primary", []):
            fractional[mu] += 1.0
        for mu in m.get("secondary", []):
            fractional[mu] += 0.5
    return {"fractional_sets": dict(sorted(fractional.items())), "hard_sets": hard,
            "tonnage_kg": tonnage, "mean_relative_intensity": (sum(rel) / len(rel)) if rel else None}


# ---------- CALC-14: personal records ----------
SPIKE_E1RM = 1.30     # practice: >30 % jump in e1RM vs best -> ask the user to confirm
SPIKE_WEIGHT = 2.0    # practice: load more than double the best load -> likely unit/typo error


def detect_prs(history: list[dict], session: list[dict]) -> dict:
    """history/session sets: {exercise_id, weight_kg, reps, rir?, warmup?}. Warm-ups are ignored.
    PR types: best weight, most reps at >= a weight already lifted, best e1RM, best session volume."""
    prs, flags = [], []
    hist = [s for s in history if not s.get("warmup")]
    by_ex = defaultdict(list)
    for s in hist:
        by_ex[s["exercise_id"]].append(s)
    sess_by_ex = defaultdict(list)
    for s in session:
        if s.get("warmup"):
            continue
        if s["weight_kg"] <= 0 or s["reps"] < 1:
            flags.append({"exercise_id": s["exercise_id"], "flag": "invalid_input"})
            continue
        sess_by_ex[s["exercise_id"]].append(s)
    for ex, ss in sess_by_ex.items():
        h = by_ex.get(ex, [])
        if not h:
            continue                              # first time: baseline, not a PR
        best_w = max(s["weight_kg"] for s in h)
        best_e = max((e for s in h if (e := e1rm(s["weight_kg"], s["reps"], s.get("rir") or 0)) is not None), default=None)
        sus = False
        for s in ss:
            e = e1rm(s["weight_kg"], s["reps"], s.get("rir") or 0)
            if s["weight_kg"] > SPIKE_WEIGHT * best_w or (best_e and e and e > SPIKE_E1RM * best_e):
                sus = True
        if sus:
            flags.append({"exercise_id": ex, "flag": "needs_confirmation"})
            continue
        top_w = max(s["weight_kg"] for s in ss)
        if top_w > best_w:
            prs.append({"exercise_id": ex, "type": "weight", "value": top_w, "previous": best_w})
        for s in ss:
            prev_reps = [x["reps"] for x in h if x["weight_kg"] >= s["weight_kg"]]
            if prev_reps and s["reps"] > max(prev_reps):
                prs.append({"exercise_id": ex, "type": "reps", "weight_kg": s["weight_kg"],
                            "value": s["reps"], "previous": max(prev_reps)})
        es = [e for s in ss if (e := e1rm(s["weight_kg"], s["reps"], s.get("rir") or 0)) is not None]
        if es and best_e is not None and max(es) > best_e:
            prs.append({"exercise_id": ex, "type": "e1rm", "value": max(es), "previous": best_e})
        sess_vol = sum(s["weight_kg"] * s["reps"] for s in ss)
        # previous best single-session volume needs session ids; history entries carry "session_id"
        vols = defaultdict(float)
        for s in h:
            vols[s.get("session_id", "?")] += s["weight_kg"] * s["reps"]
        if vols and sess_vol > max(vols.values()):
            prs.append({"exercise_id": ex, "type": "volume", "value": sess_vol, "previous": max(vols.values())})
    return {"prs": prs, "flags": flags}
