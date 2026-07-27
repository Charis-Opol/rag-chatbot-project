"""
Chunking module (proposal §2.9.2 step 2).

Splits extracted text segments into smaller, overlapping chunks sized
for embedding, while carrying forward the page/section metadata of
the segment each chunk came from.
"""
from dataclasses import dataclass
from typing import List, Tuple

from backend.config import settings


@dataclass
class Chunk:
    content: str
    page_number: str
    section: str


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple sliding-window splitter on whitespace-aware boundaries."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    approx_words_per_chunk = max(chunk_size // 6, 20)   # ~6 chars/word average
    approx_overlap_words = max(overlap // 6, 5)

    while start < len(words):
        end = min(start + approx_words_per_chunk, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = end - approx_overlap_words
    return chunks


def chunk_document(segments: List[Tuple[str, str]], doc_title: str) -> List[Chunk]:
    """
    segments: list of (location_label, text) from document_processor.extract_document
    For PDFs, location_label is a page number -> page_number field is set, section is derived.
    For DOCX/XLSX, location_label is a heading/sheet name -> section field is set.
    """
    all_chunks: List[Chunk] = []
    for location_label, text in segments:
        pieces = _split_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        for idx, piece in enumerate(pieces):
            if location_label.isdigit():
                page_number = location_label
                section = f"Section {idx + 1}" if len(pieces) > 1 else "Full page"
            else:
                page_number = "-"
                section = location_label
            all_chunks.append(Chunk(content=piece, page_number=page_number, section=section))
    return all_chunks
