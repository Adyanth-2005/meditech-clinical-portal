import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

import chunking as ch


# ── layer 1: structure-aware ──────────────────────────────────────────────────

def test_structural_splits_markdown_headers():
    text = "# A\nalpha line\n## B\nbeta line\n## C\ngamma line"
    blocks = ch.structural_split(text)
    assert len(blocks) == 3
    assert blocks[0].startswith("# A")


def test_structural_splits_hl7_segments():
    hl7 = "MSH|^~\\&|x\rPID|1||PT-001\rOBX|1|NM|HbA1c||8.9"
    # use real CRs
    hl7 = hl7.replace("\r", "\n")
    blocks = ch.structural_split(hl7)
    assert len(blocks) == 3
    assert blocks[1].startswith("PID|")


def test_structural_falls_back_to_paragraphs():
    text = "para one here.\n\npara two here.\n\npara three."
    assert len(ch.structural_split(text)) == 3


# ── layer 2: semantic (injected fake embed_fn) ────────────────────────────────

def _fake_embed(sentences):
    # vocab-based bag-of-words vectors -> sentences sharing words look similar
    vocab = ["heart", "failure", "ejection", "kidney", "creatinine", "egfr", "potassium"]
    out = []
    for s in sentences:
        low = s.lower()
        out.append([1.0 if w in low else 0.0 for w in vocab])
    return out


def test_semantic_split_breaks_on_topic_change():
    sents = [
        "Heart failure lowers the ejection fraction.",   # topic A
        "Heart failure causes ejection problems.",       # topic A
        "Kidney disease raises creatinine and egfr.",    # topic B
        "Kidney potassium and creatinine rise.",         # topic B
    ]
    groups = ch.semantic_split(sents, _fake_embed, threshold=0.3)
    assert len(groups) == 2
    assert "Heart" in groups[0] and "Kidney" in groups[1]


def test_semantic_single_sentence():
    assert ch.semantic_split(["only one"], _fake_embed) == ["only one"]


# ── layer 3: recursive token + overlap ────────────────────────────────────────

def test_recursive_split_respects_max_tokens_and_overlaps():
    text = " ".join(f"w{i}" for i in range(400))
    pieces = ch.recursive_split(text, max_tokens=100, overlap=20)
    assert len(pieces) > 1
    for p in pieces:
        assert ch.count_tokens(p) <= 100 + 5
    # overlap: end of piece 0 reappears at start of piece 1
    tail = pieces[0].split()[-5:]
    assert any(t in pieces[1].split()[:25] for t in tail)


def test_short_text_is_single_chunk():
    assert ch.recursive_split("just a short sentence", max_tokens=600) == ["just a short sentence"]


# ── orchestrator + metadata propagation ───────────────────────────────────────

def test_hybrid_chunk_long_doc_produces_multiple():
    cs = ch.hybrid_chunk(ch._DEMO, max_tokens=60, overlap=10)
    assert len(cs) >= 3
    assert all(c["tokens"] <= 60 + 8 for c in cs)
    assert all(c["strategy"].startswith("structural") for c in cs)


def test_chunk_documents_propagates_rbac_metadata():
    docs = [{"text": ch._DEMO, "source_type": "guideline", "patient_id": "",
             "department": "Cardiology", "title": "HF"},
            {"text": "Short EHR note for PT-001.", "source_type": "ehr",
             "patient_id": "PT-001", "department": "Endocrinology", "title": "EHR — Rajan"}]
    out = ch.chunk_documents(docs, embed_fn=None, max_tokens=60, overlap=10)
    hf = [c for c in out if c["source_type"] == "guideline"]
    ehr = [c for c in out if c["source_type"] == "ehr"]
    assert len(hf) >= 3 and all(c["patient_id"] == "" for c in hf)
    assert len(ehr) == 1 and ehr[0]["patient_id"] == "PT-001"
    # multi-part titles
    assert any(re.search(r"\(part \d+/\d+\)", c["title"]) for c in hf)
