"""
familial_risk.py — estimate disease risk from family history.

Two transparent, literature-grounded models (no fabricated ML, no genome data):

  • LIABILITY-THRESHOLD model (complex/polygenic diseases)
      The Falconer–Reich model: liability to disease is a continuous
      normally-distributed trait; those above a threshold T are affected.
      Given population prevalence K and narrow-sense heritability h², a relative
      of an affected proband (additive relatedness r: 1st-degree 0.5, 2nd 0.25,
      3rd 0.125) has an upward-shifted liability, giving recurrence risk

          K_R = 1 − Φ( (T − r·h²·a) / √(1 − (r·h²)²·a·(a−T)) ),  a = φ(T)/K

      This is the standard quantitative-genetics method, not a multiplicative
      hand-wave. Refs: Falconer DS, Ann Hum Genet 1965; Falconer & Mackay,
      Introduction to Quantitative Genetics (1996).

  • MENDELIAN model (single-gene): exact transmission probabilities.

Heritabilities are representative twin-study values (Polderman et al., Nature
Genetics 2015, doi:10.1038/ng.3285; Mucci et al., JAMA 2016 for cancers; Gatz
et al., Arch Gen Psychiatry 2006 for Alzheimer's). Prevalences are
representative lifetime-risk figures from standard epidemiology. These remain
EDUCATIONAL estimates — not a validated clinical tool or genetic counselling.
"""

import math
from typing import List, Dict

# ── normal-distribution helpers (pure Python; no scipy) ──────────────────────

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)

def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI

def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))

def _ppf(p: float) -> float:
    """Inverse normal CDF — Acklam's rational approximation (|err| < 1e-9)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ── relationship → additive genetic relatedness ──────────────────────────────

DEGREE = {  # value = genetic degree; relatedness r = 0.5**degree
    "parent": 1, "mother": 1, "father": 1, "sibling": 1, "brother": 1, "sister": 1, "child": 1,
    "grandparent": 2, "grandmother": 2, "grandfather": 2,
    "aunt": 2, "uncle": 2, "half-sibling": 2, "niece": 2, "nephew": 2,
    "cousin": 3, "first-cousin": 3, "great-grandparent": 3,
}

def _relatedness(degree: int) -> float:
    return 0.5 ** degree    # 1st=0.5, 2nd=0.25, 3rd=0.125


# ── disease parameters: prevalence K, heritability h², source ────────────────

EMPIRIC = {
    "type2_diabetes":        {"label": "Type 2 Diabetes",        "K": 0.110, "h2": 0.45,
                              "source": "h²≈0.45 twin studies (Polderman 2015); lifetime risk ~11%"},
    "coronary_heart_disease":{"label": "Coronary Heart Disease", "K": 0.180, "h2": 0.40,
                              "source": "h²≈0.40 twin studies; lifetime risk ~18%"},
    "hypertension":          {"label": "Hypertension",           "K": 0.300, "h2": 0.30,
                              "source": "h²≈0.30 (BP liability); prevalence ~30%"},
    "breast_cancer":         {"label": "Breast Cancer",          "K": 0.125, "h2": 0.31,
                              "source": "h²≈0.31 Nordic twin study (Mucci 2016); lifetime risk ~12.5%"},
    "colorectal_cancer":     {"label": "Colorectal Cancer",      "K": 0.043, "h2": 0.15,
                              "source": "h²≈0.15 Nordic twin study (Mucci 2016); lifetime risk ~4.3%"},
    "alzheimers":            {"label": "Alzheimer's Disease",    "K": 0.100, "h2": 0.60,
                              "source": "h²≈0.60 twin studies (Gatz 2006); lifetime risk ~10%"},
}

MENDELIAN = {
    "huntington":      {"label": "Huntington's Disease", "inheritance": "autosomal dominant"},
    "cystic_fibrosis": {"label": "Cystic Fibrosis",      "inheritance": "autosomal recessive"},
    "sickle_cell":     {"label": "Sickle Cell Disease",  "inheritance": "autosomal recessive"},
}

REFERENCES = [
    "Falconer DS (1965) Ann Hum Genet 29:51–76 — liability-threshold model.",
    "Falconer & Mackay (1996) Introduction to Quantitative Genetics, 4th ed.",
    "Polderman TJC et al. (2015) Nat Genet 47:702–709 (doi:10.1038/ng.3285).",
    "Mucci LA et al. (2016) JAMA 315:68–76 — heritability of cancers, Nordic twins.",
    "Gatz M et al. (2006) Arch Gen Psychiatry 63:168–174 — Alzheimer heritability.",
]

RISK_CEILING = 0.90


def conditions() -> List[Dict]:
    out = [{"key": k, "label": v["label"], "model": "liability-threshold",
            "source": v["source"]} for k, v in EMPIRIC.items()]
    out += [{"key": k, "label": v["label"], "model": "mendelian",
             "inheritance": v["inheritance"]} for k, v in MENDELIAN.items()]
    return out


def _empiric(key: str, relatives: List[str]) -> Dict:
    cond = EMPIRIC[key]
    K, h2 = cond["K"], cond["h2"]
    T = _ppf(1.0 - K)
    a = _pdf(T) / K                      # mean liability of affected individuals

    # conditional mean shift: additive over relatives (independent lineages);
    # variance reduction taken from the single most-informative relative.
    mean_shift = 0.0
    max_rho2 = 0.0
    factors = []
    for rel in relatives:
        deg = DEGREE.get(rel.lower())
        if not deg:
            continue
        rho = _relatedness(deg) * h2     # liability correlation with proband
        mean_shift += rho * a
        max_rho2 = max(max_rho2, rho * rho)
        factors.append({"relation": rel, "degree": deg, "relatedness": round(_relatedness(deg), 3)})

    mean_shift = min(mean_shift, a)       # cannot exceed the affected mean
    var_R = max(1e-6, 1.0 - max_rho2 * a * (a - T))
    if relatives and mean_shift > 0:
        K_R = 1.0 - _cdf((T - mean_shift) / math.sqrt(var_R))
    else:
        K_R = K
    K_R = max(K, min(RISK_CEILING, K_R))
    ratio = K_R / K if K else 1.0

    if ratio >= 3 or K_R >= 0.5:
        category = "high"
    elif ratio >= 1.5:
        category = "moderate"
    else:
        category = "average"
    return {
        "condition": cond["label"], "model": "liability-threshold",
        "method": "Falconer–Reich liability-threshold model",
        "baseline_pct": round(K * 100, 1), "estimated_pct": round(K_R * 100, 1),
        "risk_ratio": round(ratio, 2), "heritability": h2, "category": category,
        "factors": factors, "source": cond["source"],
        "explanation": (
            f"Using a liability-threshold model with heritability h²={h2} and a "
            f"population lifetime risk of {round(K*100,1)}%, the family history "
            f"entered shifts the estimated lifetime risk to ~{round(K_R*100,1)}% "
            f"({round(ratio,2)}× baseline)."),
    }


def _mendelian(key: str, relatives: List[str]) -> Dict:
    cond = MENDELIAN[key]
    inh = cond["inheritance"]
    rels = [r.lower() for r in relatives]
    has_parent = any(r in ("parent", "mother", "father") for r in rels)
    has_sibling = any(r in ("sibling", "brother", "sister") for r in rels)
    has_second = any(DEGREE.get(r) == 2 for r in rels)

    if inh == "autosomal dominant":
        if has_parent:
            prob, note = 0.5, "An affected parent transmits the variant with 50% probability (autosomal dominant)."
        elif has_sibling:
            prob, note = 0.25, "An affected sibling implies a likely affected parent; transmission risk is ~25%."
        elif has_second:
            prob, note = 0.25, "An affected second-degree relative gives roughly 25% risk of carrying the variant."
        else:
            prob, note = 0.0, "No close affected relative entered."
    else:  # autosomal recessive
        if has_sibling:
            prob, note = 0.25, "An affected sibling means both parents are obligate carriers; each child has 25% risk."
        elif has_parent:
            prob, note = 0.5, ("An affected parent is an obligate transmitter of one variant; risk of being "
                               "affected depends on the other parent's carrier status (often low).")
        else:
            prob, note = 0.0, "Recessive risk is low without an affected sibling or known carrier parents."

    category = "high" if prob >= 0.5 else "moderate" if prob >= 0.25 else "average"
    return {
        "condition": cond["label"], "model": "mendelian",
        "method": "Mendelian single-gene inheritance", "inheritance": inh,
        "baseline_pct": None, "estimated_pct": round(prob * 100, 1),
        "risk_ratio": None, "category": category,
        "factors": [{"relation": r, "degree": DEGREE.get(r.lower(), 0)} for r in relatives],
        "explanation": note, "source": f"Textbook {inh} transmission probabilities",
    }


def assess(condition_key: str, relatives: List[str]) -> Dict:
    if condition_key in EMPIRIC:
        res = _empiric(condition_key, relatives)
    elif condition_key in MENDELIAN:
        res = _mendelian(condition_key, relatives)
    else:
        raise ValueError(f"unknown condition '{condition_key}'")
    res["references"] = REFERENCES
    res["disclaimer"] = ("Educational estimate from family history using the Falconer "
                         "liability-threshold model and Mendelian inheritance — not a "
                         "validated clinical tool or a substitute for genetic counselling.")
    return res
