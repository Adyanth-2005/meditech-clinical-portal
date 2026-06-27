# Advanced Platform — Phase 4: Clinical extras (all five)

Adds five capabilities on top of the RBAC + hybrid-RAG platform.

## 1. Live NEWS2 early-warning score
`GET /api/patients/{pid}/news2` — computes the National Early Warning Score 2
from the patient's observations (resp rate, SpO2, temperature, systolic BP,
heart rate), returns the aggregate score, per-parameter breakdown, risk band
(low / medium / high), recommended action, and which parameters are missing.
In the UI: **NEWS2 score** button on a patient (doctor and patient views).
RBAC-guarded — a patient can only score themselves.

## 2. Clinical decision support (CDS)
`POST /api/cds/{pid}` (doctor/admin) — bundles the patient's conditions +
observations into a structured prompt, runs it through the RAG pipeline scoped
to that patient, and returns a grounded assessment (key problems / what to
monitor / guideline-based management) **with citations**, plus the NEWS2 score.
In the UI: **Decision support** button on the doctor's patient detail.

## 3. Kibana audit dashboard
Audit events (LOGIN, READ, RAG_QUERY, NEWS2, CDS, FHIR_READ…) are shipped to an
Elasticsearch index `audit-log` (best-effort — never blocks the gateway). Then:
```cmd
python setup_audit_dashboard.py
```
registers a Kibana **Audit Log** data view. In Kibana → Discover → "Audit Log"
(time range Last 1 hour) you can see every access; build a Lens bar chart of
`action` broken down by `user_name` for an access-audit dashboard. The canonical
audit trail still lives in Postgres `audit_log` regardless of ES.

## 4. Extra hallucination guardrails
On top of the empty-context refusal, every answer is now **citation-verified**
(`verify_grounding`): the cited `[n]` numbers must be valid (in range), and the
answer's content words must overlap the cited chunks above a threshold. An
answer with no citation, or an out-of-range citation, is marked **ungrounded**
and its citations are withheld. The response includes a `grounding` object
(`cited`, `invalid_citations`, `support_score`, `supported`).

## 5. FHIR-style endpoints
- `GET /api/fhir/Patient/{pid}` — a minimal FHIR R4 **Patient** resource.
- `GET /api/fhir/Patient/{pid}/everything` — a **Bundle** of Patient +
  Condition + Observation resources.
In the UI: **FHIR resource** button shows the JSON. RBAC-guarded.

Also folded in this phase: the **`/api/chat` LLM fix** (no more `@@@` output) and
the **patient-context-guaranteed retrieval** (a patient's own EHR is always kept
in the RAG context so patient-specific questions ground correctly).

## Run

With the lab stack, Milvus, Ollama and ingestion all up (see earlier phases):

```cmd
cd advanced
.venv\Scripts\activate
python run_api.py --demo          REM or: python -m uvicorn app:app --port 8060  (from api\, with $env:MEDITECH_DEMO=1)
python setup_audit_dashboard.py   REM after logging in once, to register the Kibana view
```

Open the portal, log in as **dr.sharma / doctor123**, click a patient, and use
**NEWS2 score**, **Decision support**, **FHIR resource**. Then look at the
**Audit Log** data view in Kibana to see the access trail building up.

## Tests

```cmd
python -m pytest tests\ -q
```
56 tests. Phase 4 adds NEWS2 scoring (band thresholds, partial vitals), FHIR
mapping (Patient + Bundle, string/dict conditions), grounding verification
(valid/invalid/missing citations), and the CDS prompt assembly — all pure and
runnable without Milvus/Ollama.
