# Advanced Platform — Phase 6: Patient Documents (MinIO)

Adds a document layer backed by MinIO object storage, integrated into the portal.

## What it does

A **Documents** panel on the doctor's patient detail (and a read-only version on
the patient's own record). It lists that patient's files and lets a clinician add:

- **Lab report** — type text OR upload a file (PDF/CSV/image)
- **Prescription** — type text OR upload a file
- **Discharge summary** — fill diagnosis / medications / follow-up; the server
  renders a formatted summary document

Files are stored in MinIO using the correct **per-document-type bucket +
per-patient prefix** layout (NOT a bucket per patient, which is an S3
anti-pattern):

```
lab-exports/PT-001/CBC_1234.txt
prescriptions/PT-001/rx_5678.txt
discharge-reports/PT-001/discharge_20260610-101500.txt
fhir-responses/PT-001/patient_resource.json
```

A new patient automatically gets a folder inside the existing buckets the moment
their first document is uploaded — no bucket creation per patient.

Also: the **FHIR endpoint now archives** each generated resource to
`fhir-responses/PT-xxx/` (best-effort), so the four stores are wired together —
the gateway generates a FHIR resource and persists it to object storage.

## Endpoints (all RBAC-scoped)

- `GET  /api/patients/{pid}/documents` — list a patient's files (patient → own only).
- `GET  /api/documents/{bucket}/{key}` — view/download one file (patient → own prefix only).
- `POST /api/patients/{pid}/documents` — upload (doctor/admin); multipart form with
  `kind` = lab | prescription | discharge, plus a `file` or `text` (or discharge fields).

RBAC verified: a patient gets 403 listing/reading another patient's documents and
403 on any upload; doctors/admins can read and write for any patient.

## Install (new dependencies)

The document feature needs two packages in your venv:

```powershell
cd C:\Users\adyan\Downloads\meditech-lab-fixed\meditech-lab\advanced
.venv\Scripts\activate
pip install boto3 python-multipart
```

(`boto3` talks to MinIO over the S3 API; `python-multipart` lets FastAPI accept
file uploads. Both are now in `requirements-advanced.txt`.)

## Populate more documents

```powershell
python seed_documents.py            # lab + prescription + discharge for the core 8
python seed_documents.py --patients PT-001 PT-003 PT-007
```

Fills `lab-exports`, `prescriptions`, and `discharge-reports` so the buckets look
full. Re-runnable. View results in the MinIO console (http://localhost:9001) or
in the portal's Documents panel.

## Tests

```cmd
python -m pytest tests\ -q
```
75 tests. Phase 6 adds the MinIO store helpers (bucket routing, per-patient key
building + sanitisation, ownership/RBAC prefix check, content-type detection,
discharge rendering) — all pure and runnable without a live MinIO.
