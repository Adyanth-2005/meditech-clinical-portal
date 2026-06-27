import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import news2


def test_news2_priya_pt004_medium():
    obs = [{"name": "SpO2", "value": 88, "unit": "%", "flag": "L"},
           {"name": "Body Temp", "value": 38.9, "unit": "C", "flag": "H"},
           {"name": "Resp Rate", "value": 24, "unit": "/min", "flag": "H"}]
    d = news2.news2_from_observations(obs)
    assert d["score"] == 6           # spo2 3 + temp 1 + resp 2
    assert d["risk"] == "medium"
    assert d["any_param_3"] is True  # SpO2 88 scores 3
    assert "sbp" in d["missing"] and "hr" in d["missing"]


def test_news2_vikram_pt007():
    obs = [{"name": "Systolic BP", "value": 90, "unit": "mmHg", "flag": "L"},
           {"name": "Heart Rate", "value": 110, "unit": "bpm", "flag": "H"},
           {"name": "Troponin I", "value": 2.8, "unit": "ng/mL", "flag": "H"}]  # not scored
    d = news2.news2_from_observations(obs)
    assert d["score"] == 4           # sbp 3 + hr 1
    assert d["any_param_3"] is True  # SBP 90 scores 3 -> at least medium
    assert d["risk"] == "medium"


def test_news2_normal_vitals_low():
    obs = [{"name": "Resp Rate", "value": 16}, {"name": "SpO2", "value": 98},
           {"name": "Body Temp", "value": 37.0}, {"name": "Systolic BP", "value": 120},
           {"name": "Heart Rate", "value": 70}]
    d = news2.news2_from_observations(obs)
    assert d["score"] == 0 and d["risk"] == "low" and d["incomplete"] is False


def test_news2_no_vitals_unknown():
    d = news2.news2_from_observations([{"name": "HbA1c", "value": 8.9}])
    assert d["risk"] == "unknown" and d["score"] == 0
