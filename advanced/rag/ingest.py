"""
ingest.py — populate Milvus (dense) and Elasticsearch (BM25) for hybrid RAG.

Prereqs (all must be running):
  • Ollama with nomic-embed-text   (ollama pull nomic-embed-text)
  • Milvus standalone              (docker compose -f rag/milvus-compose.yml up -d)
  • Elasticsearch (the lab stack)  (docker compose up -d)
  • PostgreSQL (the lab stack)     — or run with --demo to use the in-memory data

Usage:
  python rag/ingest.py            # corpus from the lab's Postgres
  python rag/ingest.py --demo     # corpus from the in-memory seed data
  python rag/ingest.py --recreate # drop & rebuild the Milvus collection
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from guidelines import build_corpus, EMBED_DIM
from chunking import chunk_documents
import clients as C


def preflight():
    ok = True
    if not C.ollama_up():
        print(f"  ✗ Ollama not reachable at {C.OLLAMA_URL} — start it and `ollama pull {C.EMBED_MODEL}`")
        ok = False
    else:
        print(f"  ✓ Ollama up ({C.OLLAMA_URL})")
    return ok


def main():
    recreate = "--recreate" in sys.argv
    if "--demo" in sys.argv:
        os.environ["MEDITECH_DEMO"] = "1"

    from stores import build_store
    store, kind = build_store()
    print(f"== Meditech RAG ingestion ==  (data source: {kind})\n")

    if not preflight():
        sys.exit(1)

    print("\n-- Building corpus --")
    docs = build_corpus(store)
    print(f"  {len(docs)} source documents")

    print("\n-- Hybrid chunking (structure -> semantic -> recursive) --")
    use_sem = "--no-semantic" not in sys.argv
    embed_fn = C.embed_many if use_sem else None
    if not use_sem:
        print("  (semantic layer disabled via --no-semantic; structural+recursive only)")
    chunks = chunk_documents(docs, embed_fn=embed_fn)
    n_g = sum(1 for c in chunks if c["source_type"] == "guideline")
    n_e = sum(1 for c in chunks if c["source_type"] == "ehr")
    strat = {}
    for c in chunks:
        strat[c["strategy"]] = strat.get(c["strategy"], 0) + 1
    multi = sum(1 for c in chunks if c["n_chunks"] > 1)
    print(f"  {len(chunks)} chunks  ({n_g} guideline, {n_e} EHR; {multi} from split docs)")
    print("  strategy breakdown: " + ", ".join(f"{k}={v}" for k, v in sorted(strat.items())))

    print("\n-- Embedding (Ollama / %s) --" % C.EMBED_MODEL)
    vectors = []
    for i, c in enumerate(chunks, 1):
        vectors.append(C.embed_one(c["text"]))
        print(f"\r  embedded {i}/{len(chunks)}", end="", flush=True)
    dim = len(vectors[0])
    print(f"\n  vector dim = {dim}")
    if dim != EMBED_DIM:
        print(f"  ! expected {EMBED_DIM}; collection will use {dim}")

    print("\n-- Loading Milvus --")
    mc = C.get_milvus()
    C.ensure_collection(mc, dim=dim, recreate=recreate)
    rows = [{"vector": vectors[i], "text": c["text"], "source_type": c["source_type"],
             "patient_id": c["patient_id"], "department": c["department"], "title": c["title"]}
            for i, c in enumerate(chunks)]
    mc.insert(C.COLLECTION, data=rows)
    try:
        mc.flush(C.COLLECTION)
    except Exception:
        pass  # some client builds auto-flush; load still works
    mc.load_collection(C.COLLECTION)
    print(f"  ✓ inserted {len(rows)} rows into Milvus collection '{C.COLLECTION}'")

    print("\n-- Loading Elasticsearch (BM25) --")
    try:
        es = C.get_es()
        C.ensure_es_index(es)
        for c in chunks:
            es.index(index=C.ES_INDEX, document={
                "text": c["text"], "source_type": c["source_type"],
                "patient_id": c["patient_id"], "department": c["department"], "title": c["title"]})
        es.indices.refresh(index=C.ES_INDEX)
        print(f"  ✓ indexed {len(chunks)} chunks into ES index '{C.ES_INDEX}'")
    except Exception as e:
        print(f"  ! ES indexing skipped ({e}); dense-only retrieval will still work")

    print("\n✓ Ingestion complete. Run: python rag/verify_milvus.py")


if __name__ == "__main__":
    main()
