"""
app.py — Meditech RBAC gateway (Phase 1).

Run (demo, no external services):   MEDITECH_DEMO=1 python -m uvicorn app:app --port 8000
Run (against the lab's Postgres):   python -m uvicorn app:app --port 8000
Then open http://localhost:8000

Seeded logins (demo + first Postgres boot):
    admin     / admin123     (admin   — can enroll users, see audit)
    dr.sharma / doctor123    (doctor  — reads all patients)
    rajan     / patient123   (patient — sees only PT-001)
"""

import os
from pathlib import Path

import jwt
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import verify_password, create_token, decode_token
from stores import build_store
import news2, fhir, es_audit, familial_risk, minio_store

HERE = Path(__file__).resolve().parent
STORE, STORE_KIND = build_store()

app = FastAPI(title="Meditech RBAC Gateway", version="1.0-phase1")
bearer = HTTPBearer(auto_error=False)


# ── models ────────────────────────────────────────────────────────────────────

class LoginReq(BaseModel):
    username: str
    password: str

class EnrollReq(BaseModel):
    username: str
    password: str
    role: str
    full_name: str = ""
    linked_id: str | None = None

class RagReq(BaseModel):
    question: str
    patient_id: str | None = None


class FamilialReq(BaseModel):
    condition: str
    relatives: list[str] = []


# ── auth dependencies ──────────────────────────────────────────────────────────

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        return decode_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

def require(*roles):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Requires role: {', '.join(roles)}")
        return user
    return dep


# ── auth routes ────────────────────────────────────────────────────────────────

@app.post("/api/login")
def login(req: LoginReq):
    rec = STORE.get_user(req.username)
    if not rec or not verify_password(req.password, rec["hash"]) or not rec["user"].active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    u = rec["user"]
    STORE.audit(u.username, "LOGIN", "app_users", u.username)
    es_audit.ship(u.username, "LOGIN", "app_users", u.username, role=u.role)
    return {"token": create_token(u.username, u.role, u.linked_id),
            "role": u.role, "full_name": u.full_name, "linked_id": u.linked_id}

@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"username": user["sub"], "role": user["role"], "linked_id": user.get("linked_id")}


# ── clinical routes (RBAC + row-level scoping) ──────────────────────────────────

@app.get("/api/patients")
def list_patients(user: dict = Depends(require("doctor", "admin"))):
    STORE.audit(user["sub"], "LIST", "patients", "ALL")
    return STORE.list_patients()

@app.get("/api/patients/{pid}")
def get_patient(pid: str, user: dict = Depends(current_user)):
    # patients may only read their own record
    if user["role"] == "patient" and user.get("linked_id") != pid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own record")
    p = STORE.get_patient(pid)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    STORE.audit(user["sub"], "READ", "patients", pid)
    return p

@app.get("/api/me/record")
def my_record(user: dict = Depends(require("patient"))):
    pid = user.get("linked_id")
    p = STORE.get_patient(pid)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No record linked to your account")
    STORE.audit(user["sub"], "READ", "patients", pid)
    return p


# ── admin routes ─────────────────────────────────────────────────────────────

@app.post("/api/admin/enroll")
def enroll(req: EnrollReq, user: dict = Depends(require("admin"))):
    try:
        u = STORE.create_user(req.username, req.password, req.role,
                              req.linked_id, req.full_name or req.username, user["sub"])
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    STORE.audit(user["sub"], "ENROLL", "app_users", req.username)
    return {"ok": True, "user": u.public()}

@app.get("/api/admin/users")
def users(user: dict = Depends(require("admin"))):
    return STORE.list_users()

@app.get("/api/admin/audit")
def audit_log(limit: int = 100, user: dict = Depends(require("admin"))):
    return STORE.list_audit(limit)


# ── Phase 4: NEWS2, clinical decision support, FHIR ─────────────────────────────

def _patient_or_403(pid: str, user: dict):
    if user["role"] == "patient" and user.get("linked_id") != pid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own record")
    p = STORE.get_patient(pid)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return p

@app.get("/api/patients/{pid}/news2")
def patient_news2(pid: str, user: dict = Depends(current_user)):
    p = _patient_or_403(pid, user)
    STORE.audit(user["sub"], "NEWS2", "patients", pid)
    es_audit.ship(user["sub"], "NEWS2", "patients", pid, role=user["role"])
    return news2.news2_from_observations(p.get("observations"))

@app.post("/api/cds/{pid}")
def cds(pid: str, user: dict = Depends(require("doctor", "admin"))):
    p = STORE.get_patient(pid)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    STORE.audit(user["sub"], "CDS", "patients", pid)
    es_audit.ship(user["sub"], "CDS", "patients", pid, role=user["role"])
    try:
        import sys; from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))
        from rag import cds_assessment
        out = cds_assessment(p, role=user["role"], patient_id=pid)
        out["news2"] = news2.news2_from_observations(p.get("observations"))
        return out
    except Exception as e:
        return {"answer": "CDS backend not reachable (needs Milvus + Ollama). " + str(e),
                "citations": [], "grounded": False,
                "news2": news2.news2_from_observations(p.get("observations"))}

@app.get("/api/fhir/Patient/{pid}")
def fhir_patient(pid: str, user: dict = Depends(current_user)):
    p = _patient_or_403(pid, user)
    STORE.audit(user["sub"], "FHIR_READ", "patients", pid)
    es_audit.ship(user["sub"], "FHIR_READ", "patients", pid, role=user["role"])
    resource = fhir.to_fhir_patient(p)
    try:  # archive to MinIO (best-effort)
        import json as _json
        minio_store.put_text("fhir-responses", f"{pid}/patient_resource.json",
                             _json.dumps(resource, indent=2))
    except Exception:
        pass
    return resource

@app.get("/api/fhir/Patient/{pid}/everything")
def fhir_everything(pid: str, user: dict = Depends(current_user)):
    p = _patient_or_403(pid, user)
    STORE.audit(user["sub"], "FHIR_BUNDLE", "patients", pid)
    es_audit.ship(user["sub"], "FHIR_BUNDLE", "patients", pid, role=user["role"])
    return fhir.to_fhir_bundle(p)


@app.get("/api/fhir/metadata")
def fhir_metadata(user: dict = Depends(current_user)):
    return fhir.capability_statement()


@app.get("/api/fhir/Observation")
def fhir_search_observation(patient: str, user: dict = Depends(current_user)):
    p = _patient_or_403(patient, user)
    STORE.audit(user["sub"], "FHIR_SEARCH", "Observation", patient)
    es_audit.ship(user["sub"], "FHIR_SEARCH", "Observation", patient, role=user["role"])
    return fhir.search_bundle(p, "Observation")


@app.get("/api/fhir/Condition")
def fhir_search_condition(patient: str, user: dict = Depends(current_user)):
    p = _patient_or_403(patient, user)
    STORE.audit(user["sub"], "FHIR_SEARCH", "Condition", patient)
    es_audit.ship(user["sub"], "FHIR_SEARCH", "Condition", patient, role=user["role"])
    return fhir.search_bundle(p, "Condition")


@app.get("/api/fhir/MedicationRequest")
def fhir_search_medication(patient: str, user: dict = Depends(current_user)):
    p = _patient_or_403(patient, user)
    STORE.audit(user["sub"], "FHIR_SEARCH", "MedicationRequest", patient)
    es_audit.ship(user["sub"], "FHIR_SEARCH", "MedicationRequest", patient, role=user["role"])
    return fhir.search_bundle(p, "MedicationRequest")


@app.post("/api/fhir/Observation", status_code=status.HTTP_201_CREATED)
def fhir_create_observation(resource: dict, user: dict = Depends(require("doctor", "admin"))):
    if resource.get("resourceType") != "Observation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "resourceType must be Observation")
    ref = (resource.get("subject") or {}).get("reference", "")
    pid = ref.split("/")[-1] if ref else "unknown"
    try:  # archive the posted resource to MinIO (best-effort)
        import json as _json, datetime as _dt
        minio_store.put_text("fhir-responses",
                             f"{pid}/observation_{_dt.datetime.now():%Y%m%d-%H%M%S}.json",
                             _json.dumps(resource, indent=2))
    except Exception:
        pass
    STORE.audit(user["sub"], "FHIR_CREATE", "Observation", pid)
    es_audit.ship(user["sub"], "FHIR_CREATE", "Observation", pid, role=user["role"])
    return resource


@app.get("/api/familial-risk/conditions")
def familial_conditions(user: dict = Depends(current_user)):
    return {"conditions": familial_risk.conditions(),
            "relations": sorted(set(familial_risk.DEGREE.keys()))}

@app.post("/api/familial-risk")
def familial_assess(req: FamilialReq, user: dict = Depends(current_user)):
    try:
        res = familial_risk.assess(req.condition, req.relatives)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    STORE.audit(user["sub"], "FAMILIAL_RISK", "risk", req.condition)
    es_audit.ship(user["sub"], "FAMILIAL_RISK", "risk", req.condition, role=user["role"])
    return res


# ── Patient documents (MinIO object storage) ────────────────────────────────────

@app.get("/api/patients/{pid}/documents")
def list_documents(pid: str, user: dict = Depends(current_user)):
    _patient_or_403(pid, user)
    try:
        docs = minio_store.list_documents(pid)
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"Document store unavailable: {e}")
    STORE.audit(user["sub"], "DOC_LIST", "documents", pid)
    es_audit.ship(user["sub"], "DOC_LIST", "documents", pid, role=user["role"])
    return {"patient_id": pid, "documents": docs}


@app.get("/api/documents/{bucket}/{key:path}")
def get_document(bucket: str, key: str, user: dict = Depends(current_user)):
    # RBAC: patients may only read keys under their own PT prefix
    if user["role"] == "patient" and not minio_store.owns_key(user.get("linked_id", ""), key):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own documents")
    try:
        data, ctype = minio_store.get_object(bucket, key)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    STORE.audit(user["sub"], "DOC_READ", "documents", key)
    es_audit.ship(user["sub"], "DOC_READ", "documents", key, role=user["role"])
    inline = ctype.startswith(("text/", "application/json", "image/"))
    disp = "inline" if inline else "attachment"
    return Response(content=data, media_type=ctype,
                    headers={"Content-Disposition": f'{disp}; filename="{key.split("/")[-1]}"'})


@app.post("/api/patients/{pid}/documents")
async def upload_document(
        pid: str, kind: str = Form(...),
        text: str = Form(None), diagnosis: str = Form(None),
        medications: str = Form(None), followup: str = Form(None),
        medication: str = Form(None), dosage: str = Form(None),
        frequency: str = Form(None), duration: str = Form(None), notes: str = Form(None),
        file: UploadFile = File(None),
        user: dict = Depends(current_user)):
    # RBAC: patients may only add their OWN documents, and only as a patient upload
    # (clinical documents — prescription / discharge / lab — are clinician-authored).
    if user["role"] == "patient":
        if user.get("linked_id") != pid:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only add to your own record")
        if kind != "patient-upload":
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Patients can only add personal documents, not clinical ones")
    elif user["role"] not in ("doctor", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")

    p = STORE.get_patient(pid)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    try:
        bucket = minio_store.bucket_for(kind)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    try:
        if kind == "discharge" and not file:
            body = minio_store.render_discharge(p, diagnosis, medications, followup)
            key = minio_store.build_key(pid, kind)
            minio_store.put_text(bucket, key, body)
        elif kind == "prescription" and not file and not text and medication:
            body = minio_store.render_prescription(p, medication, dosage, frequency, duration, notes)
            key = minio_store.build_key(pid, kind)
            minio_store.put_text(bucket, key, body)
        elif file is not None:
            data = await file.read()
            key = minio_store.build_key(pid, kind, file.filename)
            minio_store.put_bytes(bucket, key, data, minio_store.content_type_for(file.filename))
        elif text:
            key = minio_store.build_key(pid, kind)
            minio_store.put_text(bucket, key, text)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide a file, text, or form fields")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Upload failed: {e}")

    STORE.audit(user["sub"], "DOC_UPLOAD", bucket, key)
    es_audit.ship(user["sub"], "DOC_UPLOAD", bucket, key, role=user["role"])
    return {"ok": True, "bucket": bucket, "key": key}


# ── RAG (Phase 3 — hybrid retrieval + Llama 3.1 8B, RBAC-scoped) ────────────────

@app.post("/api/rag/query")
def rag_query(req: RagReq, user: dict = Depends(current_user)):
    role = user["role"]
    # patients are hard-locked to their own data; doctors/admins may scope to a
    # patient via the dropdown (None = all patients + guidelines).
    if role == "patient":
        linked_id = user.get("linked_id")
        patient_id = None
        scope = linked_id
    else:
        linked_id = None
        patient_id = req.patient_id or None
        scope = patient_id or "all"

    STORE.audit(user["sub"], "RAG_QUERY", "rag", scope or "ALL")
    es_audit.ship(user["sub"], "RAG_QUERY", "rag", scope or "ALL", role=role)

    # Real pipeline needs Milvus + Ollama (and ideally ES) running on the host.
    # Imported lazily so the gateway still boots for the rest of the UI if the
    # RAG services aren't up yet.
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "rag")))
        from rag import answer
        result = answer(req.question, role=role, linked_id=linked_id, patient_id=patient_id)
        result["role"] = role
        return result
    except Exception as e:
        return {
            "answer": ("RAG backend not reachable. Make sure Milvus is up "
                       "(docker compose -f rag/milvus-compose.yml up -d), Ollama is "
                       "running, and you've run rag/ingest.py.\n\nDetail: " + str(e)),
            "citations": [], "grounded": False, "scope": scope, "role": role,
            "n_context": 0,
        }


@app.get("/api/health")
def health():
    return {"ok": True, "store": STORE_KIND, "phase": 1}


# ── serve the login UI (mounted last so /api/* wins) ────────────────────────────

app.mount("/", StaticFiles(directory=str(HERE / "frontend"), html=True), name="ui")
