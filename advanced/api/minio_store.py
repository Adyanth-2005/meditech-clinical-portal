"""
minio_store.py — patient document storage on MinIO (S3) via boto3.

Design: ONE bucket per document type, with a per-patient PREFIX (folder):
    discharge-reports/PT-001/...   lab-exports/PT-001/...   prescriptions/PT-001/...
This is the correct S3 pattern — a new patient simply gets a new folder inside
the existing buckets the moment their first file is uploaded (no per-patient
buckets, which is an anti-pattern).

The pure helpers (bucket routing, key building, discharge rendering) are unit-
tested; the boto3 calls are isolated and degrade gracefully if MinIO/boto3 are
unavailable.
"""

import io
import os
import datetime as dt
from typing import List, Dict, Optional, Tuple

MINIO_URL = os.environ.get("MINIO_URL", "http://localhost:9000")
MINIO_KEY = os.environ.get("MINIO_KEY", "admin")
MINIO_SEC = os.environ.get("MINIO_SEC", "MeditechSecret123!")

# document kind -> bucket
KIND_BUCKET = {
    "lab": "lab-exports",
    "prescription": "prescriptions",
    "discharge": "discharge-reports",
    "fhir": "fhir-responses",
    "imaging": "dicom-imaging",
    "patient-upload": "patient-uploads",     # documents added by the patient
}
# buckets that are organised by per-patient prefix (scanned when listing a patient)
PATIENT_BUCKETS = ["discharge-reports", "lab-exports", "prescriptions",
                   "fhir-responses", "dicom-imaging", "patient-uploads"]

_CONTENT_TYPES = {
    ".txt": "text/plain", ".json": "application/json", ".csv": "text/csv",
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".hl7": "text/plain", ".dcm": "application/dicom",
}


# ── pure helpers (testable) ──────────────────────────────────────────────────

def content_type_for(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return _CONTENT_TYPES.get(ext, "application/octet-stream")


def bucket_for(kind: str) -> str:
    if kind not in KIND_BUCKET:
        raise ValueError(f"unknown document kind '{kind}'")
    return KIND_BUCKET[kind]


def _ts() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def build_key(pid: str, kind: str, filename: Optional[str] = None) -> str:
    """Per-patient prefix + a sensible filename."""
    if filename:
        safe = os.path.basename(filename).replace(" ", "_")
        return f"{pid}/{safe}"
    default = {"lab": f"lab_{_ts()}.txt", "prescription": f"rx_{_ts()}.txt",
               "discharge": f"discharge_{_ts()}.txt", "fhir": "patient_resource.json",
               "patient-upload": f"upload_{_ts()}.txt"}
    return f"{pid}/{default.get(kind, kind + '_' + _ts() + '.txt')}"


def render_prescription(patient: Dict, medication: str, dosage: str,
                        frequency: str, duration: str, notes: str) -> str:
    name = patient.get("full_name", patient.get("patient_id", ""))
    pid = patient.get("patient_id", "")
    today = dt.date.today().isoformat()
    return (
        "BANGALORE CITY HOSPITAL\n"
        "CLINICAL PRESCRIPTION\n"
        "=======================================================\n"
        f"Patient Name : {name}\n"
        f"Patient ID   : {pid}\n"
        f"Date         : {today}\n\n"
        "Rx\n--\n"
        f"Medication : {medication or 'Not specified'}\n"
        f"Dosage     : {dosage or '-'}\n"
        f"Frequency  : {frequency or '-'}\n"
        f"Duration   : {duration or '-'}\n\n"
        "NOTES\n-----\n"
        f"{notes or 'None'}\n"
        "-------------------------------------------------------\n"
        "Prescribing clinician signature on file\n"
        "Bangalore City Hospital\n")


def render_discharge(patient: Dict, diagnosis: str, medications: str, followup: str) -> str:
    name = patient.get("full_name", patient.get("patient_id", ""))
    pid = patient.get("patient_id", "")
    today = dt.date.today().isoformat()
    return (
        "BANGALORE CITY HOSPITAL\n"
        "DISCHARGE SUMMARY\n"
        "=======================================================\n"
        f"Patient Name   : {name}\n"
        f"Patient ID     : {pid}\n"
        f"Discharge Date : {today}\n\n"
        "PRINCIPAL DIAGNOSIS\n-------------------\n"
        f"{diagnosis or 'Not specified'}\n\n"
        "MEDICATIONS ON DISCHARGE\n------------------------\n"
        f"{medications or 'None'}\n\n"
        "FOLLOW-UP\n---------\n"
        f"{followup or 'As advised'}\n"
        "-------------------------------------------------------\n"
        "Attending Physician signature on file\n"
        "Bangalore City Hospital\n")


def owns_key(pid: str, key: str) -> bool:
    """RBAC: a patient may only touch keys under their own PT prefix."""
    return key.split("/")[0] == pid


# ── boto3 runtime ────────────────────────────────────────────────────────────

_s3 = None

def _client():
    global _s3
    if _s3 is None:
        import boto3
        from botocore.client import Config
        _s3 = boto3.client("s3", endpoint_url=MINIO_URL,
                           aws_access_key_id=MINIO_KEY, aws_secret_access_key=MINIO_SEC,
                           config=Config(signature_version="s3v4"), region_name="us-east-1")
    return _s3


def ensure_bucket(bucket: str):
    s3 = _client()
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)


def list_documents(pid: str) -> List[Dict]:
    s3 = _client()
    out: List[Dict] = []
    for bucket in PATIENT_BUCKETS:
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{pid}/")
        except Exception:
            continue
        for obj in resp.get("Contents", []):
            out.append({"bucket": bucket, "key": obj["Key"],
                        "name": obj["Key"].split("/")[-1], "size": obj["Size"],
                        "modified": obj["LastModified"].isoformat()
                                    if hasattr(obj["LastModified"], "isoformat") else str(obj["LastModified"]),
                        "kind": next((k for k, b in KIND_BUCKET.items() if b == bucket), bucket)})
    out.sort(key=lambda d: d["modified"], reverse=True)
    return out


def get_object(bucket: str, key: str) -> Tuple[bytes, str]:
    s3 = _client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read(), content_type_for(key)


def put_bytes(bucket: str, key: str, data: bytes, content_type: str):
    ensure_bucket(bucket)
    _client().put_object(Bucket=bucket, Key=key, Body=io.BytesIO(data),
                         ContentLength=len(data), ContentType=content_type)


def put_text(bucket: str, key: str, text: str):
    put_bytes(bucket, key, text.encode("utf-8"), content_type_for(key))
