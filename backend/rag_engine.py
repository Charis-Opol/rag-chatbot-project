"""
RAG engine (proposal §2.4, §2.9.2 steps 5-7, §3.7).

Orchestrates: query embedding -> FAISS similarity search -> local LLM
generation -> citation assembly. This is the module that implements
"processQuery() / retrieveContext() / generateResponse()" from the
ChatbotEngine class in the proposal's class diagram (§3.6.1).
"""
from dataclasses import dataclass
from typing import List

from backend.config import settings
from backend.embeddings import embed_query
from backend.vector_store import vector_store
from backend.llm_client import generate_answer

# Below this similarity score, a retrieved chunk is considered too weak
# to be trustworthy context (prevents confidently answering off-topic
# questions from unrelated document fragments).
MIN_SIMILARITY = 0.28


@dataclass
class RAGSource:
    document: str
    page: str
    section: str
    excerpt: str


@dataclass
class RAGResult:
    answer: str
    grounded: bool
    sources: List[RAGSource]
    mock_mode: bool


def ask(query: str, top_k: int = None) -> RAGResult:
    top_k = top_k or settings.TOP_K

    query_vector = embed_query(query)
    matches = vector_store.search(query_vector, k=top_k)
    matches = [m for m in matches if m.get("score", 0) >= MIN_SIMILARITY]

    if not matches:
        return RAGResult(
            answer="I couldn't find this in the indexed documents. Try rephrasing your question, "
                   "or ask the IT Officer to upload the relevant regulation so it can be indexed.",
            grounded=False,
            sources=[],
            mock_mode=False,
        )

    context_chunks = [m["content"] for m in matches]
    answer_text, used_mock = generate_answer(query, context_chunks)

    sources = [
        RAGSource(
            document=m["document_title"],
            page=m.get("page_number", "-"),
            section=m.get("section", "-"),
            excerpt=m["content"],
        )
        for m in matches
    ]

    return RAGResult(answer=answer_text, grounded=True, sources=sources, mock_mode=used_mock)
