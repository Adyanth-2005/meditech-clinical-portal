"""
news2.py — NEWS2 (National Early Warning Score 2) from observations.

Pure and unit-tested. Scores only the parameters present in the record and
reports which are missing, so a partial vital set still yields a useful score.
"""

from typing import List, Dict


def _resp(v):   # breaths/min
    if v <= 8: return 3
    if v <= 11: return 1
    if v <= 20: return 0
    if v <= 24: return 2
    return 3

def _spo2(v):   # % (Scale 1)
    if v <= 91: return 3
    if v <= 93: return 2
    if v <= 95: return 1
    return 0

def _temp(v):   # °C
    if v <= 35.0: return 3
    if v <= 36.0: return 1
    if v <= 38.0: return 0
    if v <= 39.0: return 1
    return 2

def _sbp(v):    # mmHg
    if v <= 90: return 3
    if v <= 100: return 2
    if v <= 110: return 1
    if v <= 219: return 0
    return 3

def _hr(v):     # bpm
    if v <= 40: return 3
    if v <= 50: return 1
    if v <= 90: return 0
    if v <= 110: return 1
    if v <= 130: return 2
    return 3


# map observation display names -> (param key, scorer)
_PARAMS = {
    "resp": (["resp rate", "respiratory rate", "respiration"], _resp),
    "spo2": (["spo2", "oxygen saturation", "o2 sat"], _spo2),
    "temp": (["body temp", "temperature", "temp"], _temp),
    "sbp":  (["systolic bp", "systolic", "sbp"], _sbp),
    "hr":   (["heart rate", "pulse", "hr"], _hr),
}


def _match(name: str):
    low = (name or "").lower()
    for key, (aliases, scorer) in _PARAMS.items():
        if any(a in low for a in aliases):
            return key, scorer
    return None, None


def news2_from_observations(observations: List[Dict]) -> Dict:
    breakdown = {}
    for o in observations or []:
        name = o.get("name") or o.get("display_name") or ""
        key, scorer = _match(name)
        if key and key not in breakdown:
            try:
                val = float(o.get("value"))
            except (TypeError, ValueError):
                continue
            pts = scorer(val)
            breakdown[key] = {"value": val, "points": pts,
                              "unit": o.get("unit", ""), "name": name}

    total = sum(b["points"] for b in breakdown.values())
    missing = [k for k in _PARAMS if k not in breakdown]
    any3 = any(b["points"] == 3 for b in breakdown.values())

    if not breakdown:
        risk, action = "unknown", "No scoreable vitals on record."
    elif total >= 7:
        risk, action = "high", "Emergency assessment — continuous monitoring."
    elif total >= 5 or any3:
        risk, action = "medium", "Urgent review by clinician."
    elif total >= 1:
        risk, action = "low", "Routine monitoring; reassess per protocol."
    else:
        risk, action = "low", "Continue routine monitoring."

    return {"score": total, "risk": risk, "action": action,
            "breakdown": breakdown, "missing": missing,
            "incomplete": bool(missing), "any_param_3": any3}
