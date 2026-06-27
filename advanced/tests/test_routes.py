import os, sys
from pathlib import Path

# force in-memory store before importing the app
os.environ["MEDITECH_DEMO"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from fastapi.testclient import TestClient
import app as appmod

client = TestClient(appmod.app)


def tok(username, password):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


def test_login_bad_creds():
    assert client.post("/api/login", json={"username": "admin", "password": "nope"}).status_code == 401


def test_admin_can_enroll_and_list():
    t = tok("admin", "admin123")
    r = client.post("/api/admin/enroll", headers=hdr(t), json={
        "username": "dr.rao", "password": "pw12345", "role": "doctor", "full_name": "Dr Rao"})
    assert r.status_code == 200, r.text
    users = client.get("/api/admin/users", headers=hdr(t)).json()
    assert any(u["username"] == "dr.rao" for u in users)


def test_doctor_cannot_enroll():
    t = tok("dr.sharma", "doctor123")
    assert client.post("/api/admin/enroll", headers=hdr(t), json={
        "username": "x", "password": "pw12345", "role": "doctor"}).status_code == 403


def test_doctor_lists_all_patients():
    t = tok("dr.sharma", "doctor123")
    ps = client.get("/api/patients", headers=hdr(t)).json()
    assert len(ps) >= 8


def test_patient_cannot_list_patients():
    t = tok("rajan", "patient123")
    assert client.get("/api/patients", headers=hdr(t)).status_code == 403


def test_patient_reads_only_own_record():
    t = tok("rajan", "patient123")
    assert client.get("/api/patients/PT-001", headers=hdr(t)).status_code == 200   # own
    assert client.get("/api/patients/PT-002", headers=hdr(t)).status_code == 403   # someone else


def test_patient_me_record():
    t = tok("rajan", "patient123")
    rec = client.get("/api/me/record", headers=hdr(t)).json()
    assert rec["patient_id"] == "PT-001"
    assert any(o["flag"] == "H" for o in rec["observations"])


def test_enroll_patient_requires_valid_patient_id():
    t = tok("admin", "admin123")
    bad = client.post("/api/admin/enroll", headers=hdr(t), json={
        "username": "ghost", "password": "pw12345", "role": "patient", "linked_id": "PT-999"})
    assert bad.status_code == 400


def test_rag_scope_is_rbac_bound():
    # patient query is forced to their own id regardless of what they pass
    t = tok("rajan", "patient123")
    d = client.post("/api/rag/query", headers=hdr(t),
                    json={"question": "anything", "patient_id": "PT-002"}).json()
    assert d["scope"] == "PT-001"


def test_no_token_is_401():
    assert client.get("/api/patients").status_code == 401


def test_health():
    h = client.get("/api/health").json()
    assert h["ok"] and h["store"] == "in-memory demo"


def test_ui_served():
    r = client.get("/")
    assert r.status_code == 200 and "Clinical Portal" in r.text
