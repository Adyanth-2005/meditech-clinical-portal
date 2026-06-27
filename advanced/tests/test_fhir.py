import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import fhir


REC = {"patient_id": "PT-001", "full_name": "Rajan Menon", "gender": "M",
       "dob": "1970-04-12",
       "conditions": [{"icd10_code": "E11.65", "description": "T2DM"}],
       "observations": [{"name": "HbA1c", "value": 8.9, "unit": "%", "flag": "H"}]}


def test_fhir_patient_shape():
    p = fhir.to_fhir_patient(REC)
    assert p["resourceType"] == "Patient"
    assert p["id"] == "PT-001"
    assert p["gender"] == "male"
    assert p["birthDate"] == "1970-04-12"
    assert p["name"][0]["family"] == "Menon" and p["name"][0]["given"] == ["Rajan"]


def test_fhir_bundle_includes_condition_and_observation():
    b = fhir.to_fhir_bundle(REC)
    assert b["resourceType"] == "Bundle"
    kinds = [e["resource"]["resourceType"] for e in b["entry"]]
    assert "Patient" in kinds and "Condition" in kinds and "Observation" in kinds
    obs = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Observation")
    assert obs["valueQuantity"]["value"] == 8.9


def test_fhir_handles_string_conditions():
    rec = {"patient_id": "PT-X", "full_name": "Test User", "gender": "F",
           "conditions": ["Hypertension (I10)"], "observations": []}
    b = fhir.to_fhir_bundle(rec)
    cond = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Condition")
    assert "Hypertension" in cond["code"]["text"]
