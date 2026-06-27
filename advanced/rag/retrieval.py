"""
retrieval.py — hybrid retrieval for the Meditech RAG.

  dense (Milvus / cosine)  +  sparse (Elasticsearch / BM25)
       └────────── reciprocal-rank fusion ──────────┘
                    ▲ both pre-filtered by RBAC

Patient-context guarantee: when a query is scoped to a specific patient, that
patient's own EHR chunk(s) are fetched explicitly and placed first, so they are
never crowded out of the top-k by topically-similar guideline chunks.

RBAC scope (build_rbac):
  • patient            → own EHR + all guidelines, nothing else
  • doctor/admin + pid → that patient's EHR + guidelines
  • doctor/admin, none → everything (all patients + guidelines)
"""

import re
from typing import List, Dict, Optional

import clients as C

_PID_RE = re.compile(r"^PT-\w+$")


def _safe_pid(pid: Optional[str]) -> Optional[str]:
    return pid if pid and _PID_RE.match(pid) else None


def build_rbac(role: str, linked_id: Optional[str], patient_id: Optional[str]):
    if role == "patient":
        pid = _safe_pid(linked_id)
        if not pid:
            return 'source_type == "guideline"', "__none__"
        return f'patient_id == "{pid}" or source_type == "guideline"', pid
    pid = _safe_pid(patient_id)
    if pid:
        return f'patient_id == "{pid}" or source_type == "guideline"', pid
    return "", None


def scoped_pid(role, linked_id, patient_id) -> Optional[str]:
    return _safe_pid(linked_id) if role == "patient" else _safe_pid(patient_id)


def reciprocal_rank_fusion(rank_lists: List[List[str]], k: int = 60) -> List[str]:
    scores: Dict[str, float] = {}
    for lst in rank_lists:
        for rank, key in enumerate(lst):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def merge_keep_patient(patient_chunks: List[Dict], fused_chunks: List[Dict],
                       k: int, min_patient: int = 1) -> List[Dict]:
    """Guarantee >=min_patient patient chunks, then fill with fused results, dedup by text."""
    out: List[Dict] = []
    seen = set()

    def add(c):
        if c["text"] not in seen:
            seen.add(c["text"]); out.append(c)

    for c in patient_chunks[:min_patient]:
        add(c)
    for c in fused_chunks:
        if len(out) >= k:
            break
        add(c)
    for c in patient_chunks[min_patient:]:
        if len(out) >= k:
            break
        add(c)
    return out[:k]


def _entity_to_chunk(e) -> Dict:
    return {"text": e["text"], "title": e["title"], "source_type": e["source_type"],
            "patient_id": e["patient_id"], "department": e.get("department", "")}


def hybrid_retrieve(question: str, role: str, linked_id: Optional[str],
                    patient_id: Optional[str], k: int = 6) -> List[Dict]:
    milvus_expr, es_scope = build_rbac(role, linked_id, patient_id)
    pid = scoped_pid(role, linked_id, patient_id)

    qvec = C.embed_one(question)
    mc = C.get_milvus()

    by_key: Dict[str, Dict] = {}
    dense_rank: List[str] = []
    for h in C.milvus_search(mc, qvec, limit=k * 2, expr=milvus_expr):
        c = _entity_to_chunk(h["entity"])
        by_key[c["text"]] = c
        dense_rank.append(c["text"])

    sparse_rank: List[str] = []
    try:
        for h in C.es_search(C.get_es(), question, size=k * 2,
                             patient_scope=(None if es_scope is None else es_scope)):
            c = {"text": h["text"], "title": h.get("title", ""),
                 "source_type": h.get("source_type", ""),
                 "patient_id": h.get("patient_id", ""), "department": h.get("department", "")}
            by_key.setdefault(c["text"], c)
            sparse_rank.append(c["text"])
    except Exception:
        pass

    fused = [by_key[t] for t in reciprocal_rank_fusion([dense_rank, sparse_rank]) if t in by_key]

    if pid:
        patient_chunks: List[Dict] = []
        for h in C.milvus_search(mc, qvec, limit=3, expr=f'patient_id == "{pid}"'):
            patient_chunks.append(_entity_to_chunk(h["entity"]))
        return merge_keep_patient(patient_chunks, fused, k=k, min_patient=1)

    return fused[:k]
