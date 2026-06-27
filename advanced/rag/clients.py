"""
clients.py — thin wrappers around Ollama, Milvus and Elasticsearch.

Endpoints (override via env):
  OLLAMA_URL   default http://localhost:11434
  MILVUS_URI   default http://localhost:19530
  ES_URL       default http://localhost:9200
"""

import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
ES_URL     = os.environ.get("ES_URL", "http://localhost:9200")

EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL   = os.environ.get("LLM_MODEL", "llama3.1:8b")
# keep the model resident in VRAM so it isn't unloaded between queries (default
# Ollama behaviour is to evict after 5 min idle, causing a slow reload).
# Ollama wants an int (seconds; -1 = keep loaded forever) or a duration string
# like "30m" — a bare "-1" string is NOT a valid duration, so coerce numerics.
def _keep_alive(v):
    try:
        return int(v)          # "-1" -> -1 (forever), "3600" -> 3600 seconds
    except (TypeError, ValueError):
        return v               # "30m", "24h" pass through as durations
KEEP_ALIVE  = _keep_alive(os.environ.get("OLLAMA_KEEP_ALIVE", "-1"))

COLLECTION = "clinical_chunks"
ES_INDEX = "rag-chunks"


# ── Ollama ───────────────────────────────────────────────────────────────────

def embed_one(text: str) -> list:
    r = requests.post(f"{OLLAMA_URL}/api/embeddings",
                      json={"model": EMBED_MODEL, "prompt": text}, timeout=120)
    r.raise_for_status()
    return r.json()["embedding"]


def embed_many(texts) -> list:
    return [embed_one(t) for t in texts]


def llm_generate(prompt: str, system: str = "", temperature: float = 0.1) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": LLM_MODEL, "messages": messages,
        "stream": False, "keep_alive": KEEP_ALIVE,
        "options": {"temperature": temperature, "num_predict": 512},
    }, timeout=300)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "").strip()


def ollama_up() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).status_code == 200
    except Exception:
        return False


# ── Milvus (pymilvus 3.x MilvusClient API) ───────────────────────────────────

def get_milvus():
    from pymilvus import MilvusClient
    return MilvusClient(uri=MILVUS_URI)


def ensure_collection(client, dim: int, recreate: bool = False):
    from pymilvus import DataType
    if client.has_collection(COLLECTION):
        if not recreate:
            return
        client.drop_collection(COLLECTION)

    schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)
    schema.add_field("text", DataType.VARCHAR, max_length=8000)
    schema.add_field("source_type", DataType.VARCHAR, max_length=32)
    schema.add_field("patient_id", DataType.VARCHAR, max_length=32)
    schema.add_field("department", DataType.VARCHAR, max_length=64)
    schema.add_field("title", DataType.VARCHAR, max_length=256)

    index = client.prepare_index_params()
    index.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE",
                    params={"M": 16, "efConstruction": 200})
    client.create_collection(COLLECTION, schema=schema, index_params=index)


def milvus_search(client, query_vec, limit=5, expr=None):
    res = client.search(
        COLLECTION, data=[query_vec], limit=limit, filter=expr or "",
        output_fields=["text", "source_type", "patient_id", "department", "title"],
        search_params={"metric_type": "COSINE", "params": {"ef": 64}},
    )
    return res[0] if res else []


# ── Elasticsearch (BM25 half of hybrid retrieval) ────────────────────────────

def get_es():
    from elasticsearch import Elasticsearch
    return Elasticsearch(ES_URL, request_timeout=30)


def ensure_es_index(es):
    if es.indices.exists(index=ES_INDEX):
        es.indices.delete(index=ES_INDEX)
    es.indices.create(index=ES_INDEX, mappings={"properties": {
        "text": {"type": "text"},
        "source_type": {"type": "keyword"},
        "patient_id": {"type": "keyword"},
        "department": {"type": "keyword"},
        "title": {"type": "keyword"},
    }})


def es_search(es, query, size=5, patient_scope=None):
    must = [{"match": {"text": query}}]
    if patient_scope:
        # patient may only match their own ehr OR any guideline
        flt = [{"bool": {"should": [
            {"term": {"patient_id": patient_scope}},
            {"term": {"source_type": "guideline"}}]}}]
    else:
        flt = []
    body = {"size": size, "query": {"bool": {"must": must, "filter": flt}}}
    hits = es.search(index=ES_INDEX, body=body)["hits"]["hits"]
    return [{**h["_source"], "_score": h["_score"]} for h in hits]
