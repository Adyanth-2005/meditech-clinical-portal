import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rag"))

import retrieval as R
import rag as RAG


# ── RBAC filter building ──────────────────────────────────────────────────────

def test_rbac_patient_locked_to_self_plus_guidelines():
    expr, scope = R.build_rbac("patient", "PT-001", "PT-003")  # patient passes someone else
    assert 'patient_id == "PT-001"' in expr and 'source_type == "guideline"' in expr
    assert "PT-003" not in expr           # cannot widen to another patient
    assert scope == "PT-001"


def test_rbac_doctor_all_when_no_patient():
    expr, scope = R.build_rbac("doctor", None, None)
    assert expr == "" and scope is None    # unrestricted


def test_rbac_doctor_scoped_to_selected_patient():
    expr, scope = R.build_rbac("doctor", None, "PT-002")
    assert 'patient_id == "PT-002"' in expr and scope == "PT-002"


def test_rbac_rejects_malformed_patient_id():
    # injection attempt must not reach the filter expression
    expr, scope = R.build_rbac("doctor", None, 'PT-1" or patient_id != "')
    assert expr == "" and scope is None


# ── reciprocal-rank fusion ────────────────────────────────────────────────────

def test_rrf_rewards_agreement():
    dense = ["a", "b", "c"]
    sparse = ["b", "a", "d"]
    fused = R.reciprocal_rank_fusion([dense, sparse])
    # 'a' (ranks 0,1) and 'b' (ranks 1,0) beat items appearing in only one list
    assert set(fused[:2]) == {"a", "b"}
    assert "c" in fused and "d" in fused


def test_rrf_handles_empty_list():
    assert R.reciprocal_rank_fusion([[], ["x"]]) == ["x"]


# ── patient-context guarantee (merge_keep_patient) ────────────────────────────

def _c(text, st="guideline", pid=""):
    return {"text": text, "title": text, "source_type": st, "patient_id": pid, "department": ""}

def test_merge_keeps_patient_chunk_even_when_guidelines_dominate():
    patient = [_c("Suresh creatinine 2.4 eGFR 38 K 5.2", "ehr", "PT-003")]
    fused = [_c("CKD staging"), _c("CKD monograph 1"), _c("hyperkalaemia"),
             _c("CKD monograph 2"), _c("CKD monograph 3")]
    out = R.merge_keep_patient(patient, fused, k=5, min_patient=1)
    assert out[0]["patient_id"] == "PT-003"          # patient EHR is first
    assert len(out) == 5
    assert any(c["source_type"] == "guideline" for c in out)  # guidelines still present

def test_merge_dedups_by_text():
    patient = [_c("dup", "ehr", "PT-001")]
    fused = [_c("dup"), _c("other")]
    out = R.merge_keep_patient(patient, fused, k=5)
    texts = [c["text"] for c in out]
    assert texts.count("dup") == 1

def test_merge_no_patient_chunks_falls_back_to_fused():
    out = R.merge_keep_patient([], [_c("a"), _c("b")], k=5)
    assert [c["text"] for c in out] == ["a", "b"]


# ── prompt + citations ────────────────────────────────────────────────────────

def test_build_prompt_numbers_and_labels_context():
    ctx = [{"text": "HbA1c target below 7%.", "title": "T2DM", "source_type": "guideline", "patient_id": ""},
           {"text": "Rajan HbA1c 8.9.", "title": "EHR — Rajan", "source_type": "ehr", "patient_id": "PT-001"}]
    p = RAG.build_prompt("What is the target?", ctx)
    assert "[1]" in p and "[2]" in p and "PT-001" in p and "Question:" in p


# ── answer() guardrails (injected fakes — no Milvus/Ollama needed) ────────────

def test_answer_refuses_when_no_context():
    out = RAG.answer("anything", role="doctor",
                     retrieve_fn=lambda q: [],            # nothing retrieved
                     llm_fn=lambda p, s: "should not be called")
    assert out["grounded"] is False and out["n_context"] == 0
    assert out["citations"] == []
    assert "enough information" in out["answer"].lower()


def test_answer_grounded_path_returns_citations_and_disclaimer():
    ctx = [{"text": "HbA1c goal below 7%.", "title": "T2DM", "source_type": "guideline", "patient_id": ""}]
    out = RAG.answer("target?", role="doctor",
                     retrieve_fn=lambda q: ctx,
                     llm_fn=lambda p, s: "Aim for under 7% [1].")
    assert out["grounded"] is True
    assert out["n_context"] == 1
    assert out["citations"][0]["title"] == "T2DM"
    assert "decision support only" in out["answer"].lower()


def test_answer_passes_through_model_refusal():
    ctx = [{"text": "unrelated text", "title": "X", "source_type": "guideline", "patient_id": ""}]
    out = RAG.answer("unanswerable?", role="doctor",
                     retrieve_fn=lambda q: ctx,
                     llm_fn=lambda p, s: "I don't have enough information in the available records to answer that.")
    assert out["grounded"] is False
    assert out["citations"] == []


# ── grounding verification (Phase 4) ──────────────────────────────────────────

def test_verify_grounding_valid_citation_supported():
    ctx = [{"text": "For type 2 diabetes a reasonable HbA1c goal is below seven percent.",
            "title": "T2DM", "source_type": "guideline", "patient_id": ""}]
    g = RAG.verify_grounding("The HbA1c goal is below seven percent for diabetes [1].", ctx)
    assert g["has_citation"] and g["invalid_citations"] == [] and g["supported"]


def test_verify_grounding_flags_out_of_range_citation():
    ctx = [{"text": "only one chunk", "title": "A", "source_type": "guideline", "patient_id": ""}]
    g = RAG.verify_grounding("Answer with a bad ref [5].", ctx)
    assert g["invalid_citations"] == [5] and g["supported"] is False


def test_verify_grounding_no_citation_unsupported():
    ctx = [{"text": "chunk", "title": "A", "source_type": "guideline", "patient_id": ""}]
    g = RAG.verify_grounding("An answer with no citations at all.", ctx)
    assert g["has_citation"] is False and g["supported"] is False


def test_answer_ungrounded_when_no_citation():
    ctx = [{"text": "HbA1c goal below seven percent.", "title": "T2DM",
            "source_type": "guideline", "patient_id": ""}]
    out = RAG.answer("target?", role="doctor",
                     retrieve_fn=lambda q: ctx,
                     llm_fn=lambda p, s: "Aim for under seven percent.")  # no [n]
    assert out["grounded"] is False           # citation required for grounding
    assert out["grounding"]["has_citation"] is False


def test_cds_assessment_builds_and_grounds():
    rec = {"patient_id": "PT-003", "full_name": "Suresh Patel",
           "conditions": ["CKD Stage 3 (N18.3)"],
           "observations": [{"name": "eGFR", "value": 38, "unit": "mL/min", "flag": "L"}]}
    captured = {}
    def fake_llm(prompt, system):
        captured["prompt"] = prompt
        return "Monitor renal function and potassium [1]."
    ctx = [{"text": "CKD is staged by eGFR; ACE inhibitors slow decline.",
            "title": "CKD", "source_type": "guideline", "patient_id": ""}]
    out = RAG.cds_assessment(rec, role="doctor", patient_id="PT-003",
                             retrieve_fn=lambda q: ctx, llm_fn=fake_llm)
    assert "Suresh Patel" in captured["prompt"] and "eGFR" in captured["prompt"]
    assert out["grounded"] is True
