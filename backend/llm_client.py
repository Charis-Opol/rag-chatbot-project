"""
LLM client (proposal §2.5, §2.9.2 step 7).

Generation goes through one of two providers, chosen by LLM_PROVIDER in
.env:

  - "ollama" — local model via Ollama's HTTP API (https://ollama.com).
               Nothing ever leaves the machine.
  - "google" — Google's Generative Language API (Gemini). Requires
               GOOGLE_API_KEY in .env. NOTE: this sends the retrieved
               document context + question to Google's servers — the
               "100% offline / zero data leakage" property only holds
               with LLM_PROVIDER=ollama.

If the configured provider is not reachable (or GOOGLE_API_KEY is
unset), `generate_answer()` falls back to a simple extractive response
built directly from the retrieved context, so the rest of the system
(retrieval, citations, logging) still works before an LLM is wired up.
"""
import re
import requests

from backend.config import settings


class LLMUnavailableError(Exception):
    pass


_WORD_RE = re.compile(r"[A-Za-z0-9]{3,}")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "with", "that", "this", "from",
    "what", "does", "say", "about", "have", "has", "had", "not", "but", "you",
    "your", "can", "will", "would", "shall", "may", "its", "who", "how", "all",
    "any", "our", "their", "such", "into", "under", "over", "than", "then",
}


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text)} - _STOPWORDS


def _call_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(url, json=payload, timeout=settings.LLM_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def _call_google(prompt: str) -> str:
    if not settings.GOOGLE_API_KEY:
        raise LLMUnavailableError("GOOGLE_API_KEY is not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GOOGLE_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    response = requests.post(
        url, params={"key": settings.GOOGLE_API_KEY}, json=payload, timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        # Most commonly a prompt blocked by safety filters — data["promptFeedback"]
        # has the reason, but we don't want to leak that verbatim to end users.
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def _call_llm(prompt: str) -> str:
    if settings.LLM_PROVIDER == "google":
        return _call_google(prompt)
    return _call_ollama(prompt)


def _extractive_fallback(query: str, context_chunks: list[str]) -> str:
    """
    Used only when no LLM is reachable. Rather than dumping whole
    retrieved chunks verbatim (which reads as a disjointed wall of
    document text), search every retrieved chunk — not just the
    top-ranked one, since FAISS ranks by embedding similarity to the
    whole chunk and can rank a chunk highly (e.g. a title page matching
    on "broadband") even when a lower-ranked chunk actually contains the
    answer's specific facts — for the single sentence that best matches
    the question, and return it with its immediate neighbors for
    context. Still 100% extractive/grounded, but reads as a focused
    excerpt instead of a raw paragraph (or title page) dump.
    """
    if not context_chunks:
        return "I couldn't find this in the indexed documents."

    query_terms = _keywords(query)

    best = None  # (adjusted_score, raw_score, chunk_sentences, index)
    for rank, chunk in enumerate(context_chunks):
        sentences = _split_sentences(chunk)
        for i, sentence in enumerate(sentences):
            if len(sentence.split()) < 6:
                continue  # skip section-number headings and other short fragments
            score = len(query_terms & _keywords(sentence))
            # Prefer sentences from higher-ranked (more semantically similar per
            # FAISS) chunks unless a lower-ranked chunk's keyword match is
            # clearly stronger — a single lucky word overlap in an otherwise
            # unrelated chunk shouldn't outrank the top-matched document.
            adjusted = score - rank * 0.5
            if best is None or adjusted > best[0]:
                best = (adjusted, score, sentences, i)

    if best is None:
        # Nothing passed the length filter (e.g. only headings/labels) — lead
        # with the start of the top-ranked chunk instead.
        return " ".join(_split_sentences(context_chunks[0])[:3]).strip() or context_chunks[0].strip()

    _, score, sentences, idx = best
    if score == 0:
        # No sentence anywhere shares a keyword with the question (a
        # broad/generic ask) — lead with the start of the top chunk
        # instead of an arbitrary pick.
        window = _split_sentences(context_chunks[0])[:3]
    else:
        # Always keep the best-matching sentence itself; only *optionally*
        # extend with the next sentence for a bit more context. Never
        # extend backwards — the preceding "sentence" is frequently just
        # the tail fragment of a heading or a chunk-boundary artifact (see
        # regression test: "the broadband goals." preceding a real match).
        window = [sentences[idx]]
        if idx + 1 < len(sentences) and len(sentences[idx + 1].split()) >= 4:
            window.append(sentences[idx + 1])

    # Drop a trailing fragment with no terminal punctuation — it means the
    # window was cut off by a chunk boundary mid-sentence. Only ever trims
    # the appended *next* sentence, never the best match itself.
    if len(window) > 1 and not window[-1].rstrip().endswith((".", "!", "?", '."', '!"', '?"')):
        window = window[:-1]

    excerpt = " ".join(window).strip()
    return excerpt if len(excerpt) <= 700 else excerpt[:700].rsplit(" ", 1)[0] + "…"


def generate_answer(query: str, context_chunks: list[str]) -> tuple[str, bool]:
    """
    Returns (answer_text, used_mock_fallback).
    """
    context_block = "\n\n".join(f"- {c}" for c in context_chunks) if context_chunks else "(no matching context found)"

    prompt = f"""You are the Ministry of ICT and National Guidance's offline regulatory assistant.
Answer the staff member's question using ONLY the context below, which was retrieved from
official ministry documents. If the context does not contain the answer, say so plainly —
never invent information that isn't supported by the context.

Context:
{context_block}

Question: {query}

Answer in 2-4 concise, professional sentences:"""

    try:
        answer = _call_llm(prompt)
        if not answer:
            raise LLMUnavailableError(f"Empty response from {settings.LLM_PROVIDER}")
        return answer, False
    except (requests.RequestException, LLMUnavailableError):
        return _extractive_fallback(query, context_chunks), True
