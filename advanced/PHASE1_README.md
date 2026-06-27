# Advanced Platform — Phase 1: RBAC + Login UI

This adds a **FastAPI gateway** with real authentication, role-based access
control, audit logging, and a three-role login UI on top of the base lab.

## Roles

| Role | Can do |
|------|--------|
| **admin** | Enrol new users (the only role that can), view the audit log, list users |
| **doctor** | Read **all** patient records (clinical cross-reference), use Clinical Q&A |
| **patient** | See **only their own** record; RAG queries are locked to their own data |

Every user has a separate login ID + password. Passwords are bcrypt-hashed;
sessions use JWTs (8-hour expiry).

## Run it

Two modes. **Demo mode needs nothing else running** — great for a first look.

```powershell
cd advanced
python -m pip install -r requirements-advanced.txt

# Option 1 — demo (in-memory, no Postgres):
python run_api.py --demo

# Option 2 — against the lab's PostgreSQL (docker compose must be up):
python run_api.py
```

Open **http://localhost:8000**.

### Seeded logins (demo, and on first Postgres boot)

```
admin     / admin123      (admin)
dr.sharma / doctor123     (doctor)
rajan     / patient123    (patient → PT-001)
```

Log in as **admin** to enrol more users (e.g. a `patient` linked to `PT-002`,
or another `doctor`), then log in as them to see RBAC in action.

## What to try

1. **admin** → enrol a patient user linked to `PT-002` → log out → log in as
   that user → you can see only PT-002, and `/api/patients/PT-001` returns 403.
2. **doctor** (`dr.sharma`) → see all 8 patients, click any for detail.
3. **admin** → watch the **audit log** fill with LOGIN / READ / ENROLL events
   (in Postgres mode these land in the existing `audit_log` table, so
   `SELECT * FROM audit_log` shows them too).

## Postgres mode notes

- On first start the gateway creates an `app_users` table and seeds the three
  logins. It does **not** touch your existing EHR tables.
- Clinical reads come straight from `patients/observations/conditions`.
- Connection defaults to `host=localhost port=5432 dbname=healthcare_db
  user=admin password=adminpassword`; override with the `MEDITECH_PG_DSN` env var.

## Tests

```powershell
cd advanced
python -m pytest tests/ -q
```
17 tests cover password/JWT handling and every RBAC rule (a patient cannot list
patients, cannot read another patient, RAG scope is forced to their own id, a
doctor cannot enrol, etc.).

## What's next

- **Phase 2** — Milvus Standalone in docker-compose + an ingestion job that
  chunks clinical guidelines and per-patient EHR into vectors.
- **Phase 3** — Hybrid RAG (Milvus dense + Elasticsearch BM25, RBAC-filtered)
  answered by **Ollama / Llama 3.1 8B** with citations and safety guardrails.
  The `/api/rag/query` endpoint and the Clinical Q&A boxes are already wired and
  RBAC-scoped — Phase 3 swaps the stub for the real retrieval+LLM pipeline.
- **Phase 4** — Kibana audit dashboard, live NEWS2 scoring, clinical decision
  support, hallucination guardrails, FHIR-style endpoint.
