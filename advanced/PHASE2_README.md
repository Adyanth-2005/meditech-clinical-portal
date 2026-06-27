# Advanced Platform — Phase 2: Milvus + Ingestion

This phase stands up a **production-style Milvus Standalone** vector database and
loads the RAG corpus (synthetic clinical guidelines + per-patient EHR) into both
**Milvus** (dense vectors) and **Elasticsearch** (BM25) so Phase 3 can do hybrid
retrieval.

## What gets created

- **Milvus Standalone** (Docker) — 3 containers: `milvus-standalone`, `milvus-etcd`,
  `milvus-minio`. Pinned to the Milvus 2.6 line to match your **pymilvus 3.0** client.
  Milvus's internal MinIO/etcd are **not** published to host ports, so they can't
  clash with the lab's MinIO (9000/9001). Only `19530` (client) and `9091` (health)
  are exposed.
- A Milvus collection **`clinical_chunks`** — fields: `vector(768)`, `text`,
  `source_type`, `patient_id`, `department`, `title`; HNSW index, COSINE metric.
- An Elasticsearch index **`rag-chunks`** with the same content for keyword search.

Every chunk carries RBAC metadata: guideline chunks have `patient_id=""` (anyone
may read); EHR chunks are tagged with their `patient_id` so retrieval can be
scoped per patient.

## Prerequisites

1. **Ollama** running with the embedding model:
   ```cmd
   ollama pull nomic-embed-text
   ```
2. **The lab stack** running (for Postgres + Elasticsearch):
   ```cmd
   cd C:\Users\adyan\Downloads\meditech-lab-fixed\meditech-lab
   python run_lab.py
   ```
3. Use the **venv** so pymilvus/protobuf stay isolated (see PHASE1 note):
   ```cmd
   cd advanced
   .venv\Scripts\activate
   ```

## Steps

```cmd
cd C:\Users\adyan\Downloads\meditech-lab-fixed\meditech-lab\advanced

REM 1. Start Milvus (first run pulls ~1 GB of images; standalone needs ~90s to go healthy)
docker compose -f rag\milvus-compose.yml up -d

REM 2. Wait until healthy, then check:
docker ps --filter "name=milvus"

REM 3. Ingest the corpus (embeds via Ollama, loads Milvus + ES)
python rag\ingest.py            REM uses the lab's Postgres
REM   or, with no Postgres needed:
python rag\ingest.py --demo

REM 4. Verify with a few similarity searches (incl. an RBAC-scoped one)
python rag\verify_milvus.py
```

`verify_milvus.py` runs three searches and prints what came back, including a
**PT-001-scoped** query that must surface PT-001's EHR + guidelines but **never**
another patient's records — the retrieval-level half of RBAC.

## Hybrid chunking (structure → semantic → recursive)

Ingestion no longer stores one vector per document — it runs a **three-layer
hybrid chunker** (`rag/chunking.py`) so the pipeline is ready for long, real
documents, not just the short synthetic ones:

1. **Structure-aware** — splits on markdown headers, HL7 v2 segments, or
   blank-line paragraphs first, so a chunk never straddles unrelated sections.
2. **Semantic** — within each section, embeds sentences and cuts where adjacent
   sentence similarity drops below a threshold, so each chunk is one idea.
   (Uses Ollama; disable with `--no-semantic`.)
3. **Recursive token + overlap** — anything still over ~600 tokens is windowed
   with ~13% overlap so nothing exceeds the embedding context.

Each stored chunk keeps its RBAC metadata (`source_type`, `patient_id`,
`department`), a multi-part title (`… (part 2/3)`), and a `strategy` tag showing
which layers produced it. Short records (most of the synthetic corpus) naturally
stay as a single chunk; the two longer "monograph" documents get split, so you
can see the layers engage. The ingest output prints a strategy breakdown.

See it in isolation:
```cmd
python rag\chunking.py
```



- **"this version of sdk is incompatible with server"** — your pymilvus (3.0) and
  the Milvus image are out of step. Bump the server: `set MILVUS_VERSION=v2.6.11`
  then re-run `docker compose -f rag\milvus-compose.yml up -d`. (Or match the other
  way: `pip install "pymilvus==2.5.*"` for a 2.5 server.)
- **Milvus slow to start** — `milvus-standalone` waits for etcd+minio to be healthy
  and then needs ~60–90s itself. `docker logs milvus-standalone` shows progress.
- **Memory** — Milvus standalone wants ~4 GB; your Docker has 31 GB allocated, so
  it runs alongside the lab comfortably.
- **Stop Milvus:** `docker compose -f rag\milvus-compose.yml down`
  (add `-v` to wipe its vectors).

## What's next — Phase 3

Hybrid retrieval (Milvus dense + ES BM25 → reciprocal-rank fusion → RBAC filter)
answered by **Ollama / Llama 3.1 8B** with citations and guardrails. The
`/api/rag/query` endpoint and the Clinical Q&A boxes from Phase 1 get swapped from
the stub to the real pipeline — patient queries stay locked to their own data.
