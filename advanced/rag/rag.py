"""
rag.py — grounded answer generation with citations and guardrails.

answer() is dependency-injected (retrieve_fn, llm_fn) so the grounding logic,
guardrails, prompt assembly and citation extraction are unit-testable without
Milvus or Ollama running.
"""

import re
from typing import List, Dict, Callable, Optional

import clients as C
from retrieval import hybrid_retrieve

_CITE_RE = re.compile(r"\[(\d+)\]")
_WORD_RE = re.compile(r"[a-z]{4,}")  # content-ish words

def verify_grounding(answer_text: str, contexts: List[Dict]) -> Dict:
    """Check citations are valid and the answer overlaps the cited context."""
    cited = sorted({int(n) for n in _CITE_RE.findall(answer_text)})
    n = len(contexts)
    valid = [c for c in cited if 1 <= c <= n]
    invalid = [c for c in cited if c < 1 or c > n]

    # lexical support: fraction of answer content-words found in cited contexts
    cited_text = " ".join(contexts[c - 1]["text"] for c in valid).lower()
    ctx_words = set(_WORD_RE.findall(cited_text))
    ans_words = set(_WORD_RE.findall(answer_text.lower()))
    overlap = (len(ans_words & ctx_words) / len(ans_words)) if ans_words else 0.0

    return {"cited": cited, "invalid_citations": invalid,
            "has_citation": bool(valid), "support_score": round(overlap, 2),
            "supported": bool(valid) and not invalid and overlap >= 0.3}

SYSTEM_PROMPT = (
    "You are a clinical information assistant for a hospital teaching lab. "
    "Use the numbered context provided to answer the question. Synthesise across "
    "several context items when helpful, and cite the context number(s) you used in "
    "square brackets, e.g. [1] or [2][3]. Prefer to give a useful, concise clinical "
    "answer grounded in the context. Do not invent specific doses, lab values, or "
    "facts that are not supported by the context. If the context only partly covers "
    "the question, answer what it does support and briefly note what is not in the "
    "records, rather than refusing outright. Only if NONE of the context is relevant "
    "to the question, reply: 'I don't have enough information in the available "
    "records to answer that.'"
)

DISCLAIMER = ("\n\n_Decision support only — generated from retrieved records and "
              "educational guidelines, not a substitute for clinical judgement._")

GENERAL_NOTE = ("\n\n_General educational guidance from the knowledge base — not "
                "specific to this patient's records._")

REFUSAL = "I don't have enough information in the available records to answer that."


def build_prompt(question: str, contexts: List[Dict]) -> str:
    lines = ["Context:"]
    for i, c in enumerate(contexts, 1):
        tag = c.get("source_type", "")
        who = c.get("patient_id") or ""
        head = f"[{i}] ({tag}{' ' + who if who else ''}) {c.get('title','')}"
        lines.append(head)
        lines.append(c["text"])
    lines.append(f"\nQuestion: {question}\nAnswer (cite context numbers):")
    return "\n".join(lines)


def _citations(contexts: List[Dict]) -> List[Dict]:
    return [{"n": i + 1, "title": c.get("title", ""),
             "source_type": c.get("source_type", ""),
             "patient_id": c.get("patient_id", "")} for i, c in enumerate(contexts)]


def answer(question: str, role: str, linked_id: Optional[str] = None,
           patient_id: Optional[str] = None, k: int = 5,
           retrieve_fn: Optional[Callable] = None,
           llm_fn: Optional[Callable] = None) -> Dict:
    retrieve_fn = retrieve_fn or (lambda q: hybrid_retrieve(q, role, linked_id, patient_id, k))
    llm_fn = llm_fn or C.llm_generate

    contexts = retrieve_fn(question)

    # guardrail 1: nothing retrieved → refuse, don't hallucinate
    if not contexts:
        return {"answer": REFUSAL, "citations": [], "grounded": False,
                "scope": patient_id or (linked_id if role == "patient" else "all"),
                "n_context": 0}

    prompt = build_prompt(question, contexts)
    text = llm_fn(prompt, SYSTEM_PROMPT).strip()

    # guardrail 2: model itself signalled insufficient info
    model_refused = REFUSAL.lower()[:30] in text.lower()
    # guardrail 3: verify citations are valid and the answer is supported by them
    grounding = verify_grounding(text, contexts)
    grounded = (not model_refused) and grounding["has_citation"] and not grounding["invalid_citations"]

    if grounded:
        return {
            "answer": text + DISCLAIMER,
            "citations": _citations(contexts),
            "grounded": True, "grounding": grounding,
            "scope": patient_id or (linked_id if role == "patient" else "all"),
            "n_context": len(contexts),
        }

    # graceful fallback: the model produced a substantive answer but without a clean
    # citation (or cited loosely). Rather than a blunt refusal, surface it as GENERAL
    # guidance with the retrieved sources shown — honest about not being patient-specific.
    if not model_refused and len(text) >= 40:
        # strip any invalid citation markers so we don't show dangling [9]
        clean = _CITE_RE.sub("", text).strip() if grounding["invalid_citations"] else text
        return {
            "answer": clean + GENERAL_NOTE,
            "citations": _citations(contexts),
            "grounded": False, "general": True, "grounding": grounding,
            "scope": patient_id or (linked_id if role == "patient" else "all"),
            "n_context": len(contexts),
        }

    # genuine refusal: nothing relevant / model declined
    return {
        "answer": REFUSAL, "citations": [], "grounded": False,
        "grounding": grounding,
        "scope": patient_id or (linked_id if role == "patient" else "all"),
        "n_context": len(contexts),
    }


def cds_assessment(patient_record: Dict, role: str, patient_id: str,
                   retrieve_fn: Optional[Callable] = None,
                   llm_fn: Optional[Callable] = None) -> Dict:
    """Clinical decision support: structured, grounded assessment for one patient."""
    name = patient_record.get("full_name", patient_id)
    conds = ", ".join(
        c if isinstance(c, str) else f"{c.get('icd10_code','')} {c.get('description','')}"
        for c in (patient_record.get("conditions") or [])) or "none recorded"
    obs = "; ".join(
        f"{o.get('name') or o.get('display_name','')} {o.get('value','')}{o.get('unit','')}"
        f"{' (' + o['flag'] + ')' if o.get('flag') else ''}"
        for o in (patient_record.get("observations") or [])) or "none recorded"
    question = (
        f"Patient {name} ({patient_id}). Active conditions: {conds}. "
        f"Recent observations: {obs}. "
        "Give a brief structured clinical assessment: (1) key problems, "
        "(2) what to monitor, (3) guideline-based management considerations. "
        "Use the context and cite it."
    )
    return answer(question, role=role, linked_id=None, patient_id=patient_id,
                  retrieve_fn=retrieve_fn, llm_fn=llm_fn)
