import os, sys
from pathlib import Path

os.environ["MEDITECH_DEMO"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

from stores import build_store
from guidelines import build_corpus, SYNTHETIC_GUIDELINES, SYNTHETIC_MONOGRAPHS


def corpus():
    store, _ = build_store()
    return build_corpus(store)


def test_has_guidelines_and_ehr():
    cs = corpus()
    g = [c for c in cs if c["source_type"] == "guideline"]
    e = [c for c in cs if c["source_type"] == "ehr"]
    assert len(g) == len(SYNTHETIC_GUIDELINES) + len(SYNTHETIC_MONOGRAPHS)
    assert len(e) == 8  # 8 seeded patients


def test_guidelines_have_no_patient_id():
    for c in corpus():
        if c["source_type"] == "guideline":
            assert c["patient_id"] == ""


def test_ehr_chunks_are_patient_tagged():
    e = [c for c in corpus() if c["source_type"] == "ehr"]
    pids = {c["patient_id"] for c in e}
    assert "PT-001" in pids and "PT-003" in pids
    for c in e:
        assert c["patient_id"].startswith("PT-")


def test_ehr_text_contains_clinical_detail():
    pt001 = next(c for c in corpus() if c["patient_id"] == "PT-001")
    assert "Rajan Menon" in pt001["text"]
    assert "HbA1c" in pt001["text"]          # observation surfaced
    assert "Endocrinology" in pt001["text"]  # department surfaced


def test_no_chunk_exceeds_milvus_varchar():
    for c in corpus():
        assert len(c["text"]) < 8000
