import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import minio_store as M


def test_bucket_routing():
    assert M.bucket_for("lab") == "lab-exports"
    assert M.bucket_for("prescription") == "prescriptions"
    assert M.bucket_for("discharge") == "discharge-reports"


def test_unknown_kind_raises():
    try:
        M.bucket_for("nope"); assert False
    except ValueError:
        pass


def test_build_key_uses_patient_prefix():
    k = M.build_key("PT-001", "lab")
    assert k.startswith("PT-001/") and k.endswith(".txt")
    k2 = M.build_key("PT-001", "lab", "My Report.csv")
    assert k2 == "PT-001/My_Report.csv"          # sanitised, prefixed


def test_owns_key_enforces_prefix():
    assert M.owns_key("PT-001", "PT-001/lab_x.txt") is True
    assert M.owns_key("PT-001", "PT-003/lab_x.txt") is False


def test_content_type_detection():
    assert M.content_type_for("a.json") == "application/json"
    assert M.content_type_for("a.csv") == "text/csv"
    assert M.content_type_for("a.bin") == "application/octet-stream"


def test_render_discharge_includes_clinical_fields():
    p = {"patient_id": "PT-001", "full_name": "Rajan Menon"}
    out = M.render_discharge(p, "T2DM + HTN", "Metformin 1000mg BD", "Review in 4 weeks")
    assert "Rajan Menon" in out and "PT-001" in out
    assert "T2DM + HTN" in out and "Metformin" in out and "Review in 4 weeks" in out
    assert "DISCHARGE SUMMARY" in out


def test_render_prescription_includes_rx_fields():
    p = {"patient_id": "PT-002", "full_name": "Lakshmi Nair"}
    out = M.render_prescription(p, "Atorvastatin", "20mg", "OD at night", "3 months", "fasting lipids in 12w")
    assert "CLINICAL PRESCRIPTION" in out
    assert "Lakshmi Nair" in out and "PT-002" in out
    assert "Atorvastatin" in out and "20mg" in out and "OD at night" in out and "3 months" in out
    assert "fasting lipids in 12w" in out


def test_patient_upload_routes_to_own_bucket():
    assert M.bucket_for("patient-upload") == "patient-uploads"
    assert "patient-uploads" in M.PATIENT_BUCKETS
    k = M.build_key("PT-001", "patient-upload")
    assert k.startswith("PT-001/")
