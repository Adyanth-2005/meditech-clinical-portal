"""
chunking.py — hybrid document chunker (structure → semantic → recursive).

Three strategies, layered (each handles what the previous can't):

  1. STRUCTURE-AWARE  split on real boundaries first:
        • markdown headers (#, ##, ###)
        • HL7 v2 segments (lines like MSH|, PID|, OBX|)
        • blank-line paragraphs
     A chunk never straddles two unrelated sections.

  2. SEMANTIC  within each structural block, embed sentences and cut where the
     similarity between adjacent sentences drops below a threshold, so each
     piece is one coherent idea. Needs an embed_fn; skipped if none supplied.

  3. RECURSIVE TOKEN + OVERLAP  safety net: anything still over `max_tokens`
     is windowed into ~max_tokens pieces with ~overlap carry-over, so nothing
     exceeds the embedding model's context.

Pure/testable: the semantic layer takes an injected `embed_fn`, so it can be
unit-tested without Ollama.
"""

import re
from typing import Callable, List, Optional, Dict

DEFAULT_MAX_TOKENS = 600
DEFAULT_OVERLAP = 80          # ~13%
DEFAULT_SEM_THRESHOLD = 0.55
MIN_CHUNK_TOKENS = 40


# ── token + sentence helpers ─────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"\w+|[^\w\s]")
def count_tokens(text: str) -> int:
    """Approximate token count (regex word/punct units; close to real tokenizers)."""
    return len(_TOKEN_RE.findall(text))

_SENT_RE = re.compile(r"(?<=[.!?])\s+")
def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENT_RE.split(text.strip()) if s.strip()]

def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ── layer 1: structure-aware ─────────────────────────────────────────────────

_HL7_SEG = re.compile(r"^[A-Z][A-Z0-9]{2}\|")

def structural_split(text: str) -> List[str]:
    """Split into structural blocks: header-led sections, HL7 segments, paragraphs."""
    lines = text.splitlines()
    # HL7 message? (most lines look like segments)
    seg_lines = [ln for ln in lines if _HL7_SEG.match(ln.strip())]
    if seg_lines and len(seg_lines) >= max(2, len(lines) // 2):
        return [ln.strip() for ln in lines if ln.strip()]

    # markdown-header sections: start a new block at each heading
    blocks, cur = [], []
    has_headers = any(re.match(r"^#{1,6}\s", ln) for ln in lines)
    if has_headers:
        for ln in lines:
            if re.match(r"^#{1,6}\s", ln) and cur:
                blocks.append("\n".join(cur).strip()); cur = [ln]
            else:
                cur.append(ln)
        if cur:
            blocks.append("\n".join(cur).strip())
        return [b for b in blocks if b]

    # fallback: blank-line paragraphs
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip()]


# ── layer 2: semantic ────────────────────────────────────────────────────────

def semantic_split(sentences: List[str], embed_fn: Callable[[List[str]], List[list]],
                   threshold: float = DEFAULT_SEM_THRESHOLD) -> List[str]:
    """Group consecutive sentences, breaking where adjacent similarity < threshold."""
    if len(sentences) <= 1:
        return [" ".join(sentences)] if sentences else []
    embs = embed_fn(sentences)
    groups, cur = [], [sentences[0]]
    for i in range(len(sentences) - 1):
        sim = _cosine(embs[i], embs[i + 1])
        if sim < threshold:
            groups.append(" ".join(cur)); cur = [sentences[i + 1]]
        else:
            cur.append(sentences[i + 1])
    groups.append(" ".join(cur))
    return groups


# ── layer 3: recursive token + overlap ───────────────────────────────────────

def recursive_split(text: str, max_tokens: int = DEFAULT_MAX_TOKENS,
                    overlap: int = DEFAULT_OVERLAP) -> List[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    words = text.split()
    ratio = count_tokens(text) / max(len(words), 1)      # tokens per word
    max_words = max(1, int(max_tokens / ratio))
    ov_words = max(0, min(int(overlap / ratio), max_words - 1))
    step = max(1, max_words - ov_words)
    out = []
    for i in range(0, len(words), step):
        out.append(" ".join(words[i:i + max_words]))
        if i + max_words >= len(words):
            break
    return out


def _merge_small(chunks: List[str], min_tokens: int, max_tokens: int) -> List[str]:
    """Glue sub-sentence fragments onto the previous chunk when too small."""
    out: List[str] = []
    for c in chunks:
        if out and count_tokens(c) < min_tokens and \
           count_tokens(out[-1]) + count_tokens(c) <= max_tokens:
            out[-1] = out[-1] + " " + c
        else:
            out.append(c)
    return out


# ── orchestrator ─────────────────────────────────────────────────────────────

def hybrid_chunk(text: str, embed_fn: Optional[Callable] = None,
                 max_tokens: int = DEFAULT_MAX_TOKENS, overlap: int = DEFAULT_OVERLAP,
                 sem_threshold: float = DEFAULT_SEM_THRESHOLD) -> List[Dict]:
    """Return chunks as dicts: {text, tokens, strategy}."""
    results: List[Dict] = []
    for block in structural_split(text):
        # layer 2 (only worth it on blocks with several sentences)
        sents = split_sentences(block)
        if embed_fn and len(sents) > 2 and count_tokens(block) > max_tokens * 0.4:
            pieces = [(p, "structural+semantic") for p in
                      semantic_split(sents, embed_fn, sem_threshold)]
        else:
            pieces = [(block, "structural")]
        # layer 3
        for piece, strat in pieces:
            if count_tokens(piece) > max_tokens:
                for w in recursive_split(piece, max_tokens, overlap):
                    results.append({"text": w, "strategy": strat + "+recursive"})
            else:
                results.append({"text": piece, "strategy": strat})

    merged = _merge_small([r["text"] for r in results], MIN_CHUNK_TOKENS, max_tokens)
    # re-attach strategy by position-ish (best effort); recompute tokens
    strat_by_text = {r["text"]: r["strategy"] for r in results}
    final = []
    for t in merged:
        final.append({"text": t, "tokens": count_tokens(t),
                      "strategy": strat_by_text.get(t, "structural+merged")})
    return [c for c in final if c["text"].strip()]


def chunk_documents(docs: List[Dict], embed_fn: Optional[Callable] = None,
                    max_tokens: int = DEFAULT_MAX_TOKENS, overlap: int = DEFAULT_OVERLAP
                    ) -> List[Dict]:
    """Expand corpus documents into chunks, propagating RBAC metadata."""
    out: List[Dict] = []
    for d in docs:
        pieces = hybrid_chunk(d["text"], embed_fn=embed_fn,
                              max_tokens=max_tokens, overlap=overlap)
        n = len(pieces)
        for i, p in enumerate(pieces):
            title = d["title"] if n == 1 else f"{d['title']} (part {i+1}/{n})"
            out.append({"text": p["text"], "source_type": d["source_type"],
                        "patient_id": d["patient_id"], "department": d["department"],
                        "title": title, "chunk_index": i, "n_chunks": n,
                        "strategy": p["strategy"], "tokens": p["tokens"]})
    return out


# ── CLI demo ─────────────────────────────────────────────────────────────────

_DEMO = """# Heart Failure Management

Heart failure with reduced ejection fraction is defined by an ejection fraction
at or below 40 percent. Diagnosis is supported by an elevated natriuretic peptide
such as BNP. Symptoms include breathlessness, fatigue and fluid retention.

## Pharmacological therapy

Guideline-directed medical therapy rests on four pillars. An ARNI or ACE inhibitor
is combined with a beta-blocker. A mineralocorticoid receptor antagonist is added.
An SGLT2 inhibitor completes the regimen and reduces hospitalisation.

## Monitoring

Patients are monitored for renal function and serum potassium after starting an
MRA. Weight is tracked daily as a marker of fluid status. Worsening symptoms
prompt escalation of diuretic therapy and review in clinic.
"""

if __name__ == "__main__":
    import sys
    text = _DEMO if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    print("Structural blocks:", len(structural_split(text)))
    for i, c in enumerate(hybrid_chunk(text, max_tokens=60, overlap=10), 1):
        print(f"\n--- chunk {i}  [{c['strategy']}, {c['tokens']} tok] ---\n{c['text']}")
