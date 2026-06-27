"""
verify_milvus.py — sanity-check the loaded collection with a couple of searches.

  python rag/verify_milvus.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clients as C


def run(query, expr=None, label=""):
    vec = C.embed_one(query)
    hits = C.milvus_search(C.get_milvus(), vec, limit=4, expr=expr)
    print(f"\nQ: {query}   {label}")
    for h in hits:
        e = h["entity"]
        print(f"  [{h['distance']:.3f}] {e['source_type']:9} {e['patient_id'] or '-':7} {e['title']}")


def main():
    mc = C.get_milvus()
    if not mc.has_collection(C.COLLECTION):
        print("Collection missing — run rag/ingest.py first."); sys.exit(1)
    print("Collection rows:", mc.get_collection_stats(C.COLLECTION))

    # 1) open clinical question — should surface guideline chunks
    run("What HbA1c target for type 2 diabetes?", label="(unfiltered)")
    # 2) patient-scoped (simulating RBAC for PT-001): own EHR + guidelines only
    run("How are this patient's kidney and sugar results?",
        expr='patient_id == "PT-001" or source_type == "guideline"',
        label='(RBAC scope = PT-001)')
    # 3) prove isolation: PT-001 scope must NOT return PT-003's EHR
    run("creatinine and potassium",
        expr='patient_id == "PT-001" or source_type == "guideline"',
        label='(PT-001 scope — must not leak PT-003 EHR)')


if __name__ == "__main__":
    main()
