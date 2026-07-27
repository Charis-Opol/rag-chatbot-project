"""
Local LLM client (proposal §2.5, §2.9.2 step 7).

Talks to Ollama's local HTTP API (https://github.com/ollama/ollama) —
no request ever leaves the machine. This is the ONE file you touch to
swap in a different pretrained model:

  1. Install Ollama:            https://ollama.com
  2. Pull a model:              ollama pull llama3        (or gemma2, mistral, phi3, ...)
  3. Set OLLAMA_MODEL in .env   OLLAMA_MODEL=llama3
  4. Make sure Ollama is running: `ollama serve` (it usually auto-starts)

If Ollama is not reachable, `generate()` falls back to a simple
extractive response built directly from the retrieved context, so the
rest of the system (retrieval, citations, logging) can still be
demoed and tested before the LLM is wired up.
"""
import requests

from backend.config import settings


class LLMUnavailableError(Exception):
    pass


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


def _extractive_fallback(query: str, context_chunks: list[str]) -> str:
    """
    Used only when Ollama can't be reached. Returns the most relevant
    retrieved sentence(s) verbatim so the pipeline still produces a
    grounded (if less fluent) answer instead of failing outright.
    """
    if not context_chunks:
        return "I couldn't find this in the indexed documents."
    combined = " ".join(context_chunks[:2])
    return combined


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
        answer = _call_ollama(prompt)
        if not answer:
            raise LLMUnavailableError("Empty response from Ollama")
        return answer, False
    except (requests.RequestException, LLMUnavailableError):
        return _extractive_fallback(query, context_chunks), True
