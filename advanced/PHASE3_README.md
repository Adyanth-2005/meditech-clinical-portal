# Advanced Platform — Phase 3: Hybrid RAG (grounded answers)

The Clinical Q&A boxes are now live. A question flows through:

```
question
   │  embed (Ollama nomic-embed-text)
   ├──────────────► Milvus  (dense / cosine, RBAC-filtered)
   └── BM25 ───────► Elasticsearch (sparse, RBAC-filtered)
                          │
              reciprocal-rank fusion  → top-k context
                          │
        Llama 3.1 8B (Ollama) with a strict grounding prompt
                          │
            grounded answer + [n] citations + disclaimer
```

## What it does

- **Hybrid retrieval** (`rag/retrieval.py`) — runs the query against both Milvus
  (dense vectors) and Elasticsearch (BM25 keywords), then fuses the two ranked
  lists with **reciprocal-rank fusion**. If ES is down it falls back to dense-only.
- **RBAC at retrieval** — the same scope filter from Phase 2 is applied to *both*
  stores before fusion:
  - **patient** → own EHR + guidelines only (locked; cannot be widened).
  - **doctor/admin** → a chosen patient (dropdown) or all patients + guidelines.
- **Grounded generation** (`rag/rag.py`) — Llama 3.1 8B is instructed to answer
  **only** from the retrieved context, cite the context numbers it used, and say
  "I don't have enough information…" when the context doesn't support an answer.
- **Guardrails** — refuses with no citation when retrieval is empty or the model
  signals insufficient info; appends a "decision support only" disclaimer.
- **Citations** — the UI shows which chunks (guideline / EHR + patient id) backed
  the answer, plus a grounded/ungrounded badge.

## Run

Everything from earlier phases must be up:

```cmd
REM lab stack (Postgres + Elasticsearch)
cd C:\Users\adyan\Downloads\meditech-lab-fixed\meditech-lab
python run_lab.py

REM Milvus + ingestion (in the advanced venv)
cd advanced
.venv\Scripts\activate
docker compose -f rag\milvus-compose.yml up -d
python rag\ingest.py --demo

REM the gateway (RAG is served from here)
python run_api.py --demo
```

Open **http://localhost:8000**:

- **Doctor** (`dr.sharma` / `doctor123`) → "Clinical Q&A": leave the dropdown on
  *All patients + guidelines* and ask "What is the HbA1c target in type 2 diabetes?",
  or pick **Lakshmi Nair (PT-002)** and ask "What should I adjust for this patient's
  heart failure?" — the answer scopes to her record + HF guideline, with citations.
- **Patient** (`rajan` / `patient123`) → "Ask about my health": "What do my latest
  results mean?" — retrieval is locked to PT-001 + guidelines.

## Notes

- **First answer is slow** (~10–20s) while Llama 3.1 8B warms up on the GPU;
  subsequent answers are faster.
- If a box says *"RAG backend not reachable"*, one of Milvus / Ollama / ingestion
  isn't ready — the gateway stays up regardless so the rest of the UI works.
- Want to prove isolation: as a patient, ask something only another patient's
  record could answer (e.g. about creatinine) — the model will ground only on
  guidelines, never another patient's data, because retrieval is filtered first.

## Tests

```cmd
python -m pytest tests\ -q
```
41 tests, including: RBAC filter building (incl. an injection attempt that must
not reach the Milvus expression), reciprocal-rank fusion, prompt assembly, and
the answer guardrails (empty-context refusal, grounded-with-citations, model
self-refusal) — all via dependency injection, so they run without Milvus/Ollama.

## What's next — Phase 4 (all the advanced extras)

Kibana audit dashboard, live NEWS2 scoring endpoint, clinical decision support
flow, extra hallucination guardrails, and a FHIR-style endpoint.
