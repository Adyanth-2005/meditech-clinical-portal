import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import familial_risk as FR


def test_conditions_listed():
    keys = {c["key"] for c in FR.conditions()}
    assert "type2_diabetes" in keys and "huntington" in keys


def test_empiric_no_history_equals_baseline():
    r = FR.assess("type2_diabetes", [])
    assert r["estimated_pct"] == r["baseline_pct"]
    assert r["category"] == "average"


def test_empiric_first_degree_raises_risk():
    base = FR.assess("type2_diabetes", [])
    one = FR.assess("type2_diabetes", ["parent"])
    two = FR.assess("type2_diabetes", ["parent", "sibling"])
    assert one["estimated_pct"] > base["estimated_pct"]
    assert two["estimated_pct"] > one["estimated_pct"]   # more relatives → higher
    assert two["risk_ratio"] > 1


def test_second_degree_weaker_than_first():
    fd = FR.assess("coronary_heart_disease", ["parent"])["estimated_pct"]
    sd = FR.assess("coronary_heart_disease", ["grandparent"])["estimated_pct"]
    assert sd < fd                                        # attenuated for 2nd-degree


def test_risk_is_capped():
    r = FR.assess("hypertension", ["parent", "sibling", "mother", "father", "brother", "sister"])
    assert r["estimated_pct"] <= FR.RISK_CEILING * 100


def test_mendelian_dominant_affected_parent_is_50():
    r = FR.assess("huntington", ["parent"])
    assert r["estimated_pct"] == 50.0 and r["category"] == "high"
    assert r["inheritance"] == "autosomal dominant"


def test_mendelian_recessive_affected_sibling_is_25():
    r = FR.assess("cystic_fibrosis", ["sibling"])
    assert r["estimated_pct"] == 25.0 and r["model"] == "mendelian"


def test_unknown_condition_raises():
    try:
        FR.assess("not_a_condition", ["parent"])
        assert False
    except ValueError:
        pass


def test_disclaimer_present():
    assert "counselling" in FR.assess("type2_diabetes", [])["disclaimer"]


# ── liability-threshold model specifics ───────────────────────────────────────

def test_normal_helpers_accurate():
    assert abs(FR._ppf(0.975) - 1.959964) < 1e-4
    assert abs(FR._cdf(0.0) - 0.5) < 1e-9
    assert abs(FR._pdf(0.0) - 0.3989423) < 1e-6


def test_liability_reproduces_schizophrenia_benchmark():
    # K=1%, h2=0.8, one first-degree relative -> observed recurrence ~9-10%
    FR.EMPIRIC["_scz"] = {"label": "Scz", "K": 0.01, "h2": 0.8, "source": "test"}
    try:
        r = FR._empiric("_scz", ["sibling"])
        assert 7.5 <= r["estimated_pct"] <= 11.0   # matches published ~9-10%
    finally:
        del FR.EMPIRIC["_scz"]


def test_t2dm_first_degree_in_realistic_range():
    r = FR.assess("type2_diabetes", ["parent"])
    assert 15.0 <= r["estimated_pct"] <= 25.0       # ~2x baseline, realistic
    assert 1.5 <= r["risk_ratio"] <= 2.5


def test_result_exposes_method_heritability_and_refs():
    r = FR.assess("breast_cancer", ["mother"])
    assert r["method"].startswith("Falconer")
    assert r["heritability"] == 0.31
    assert any("Polderman" in ref for ref in r["references"])
