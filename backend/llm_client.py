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
