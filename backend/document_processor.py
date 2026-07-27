"""
Document processing module (proposal §2.9.2 step 1, §3.3.1 req. #5).

Extracts text from PDF, Word (.docx), and Excel (.xlsx) files while
preserving page/section metadata, so every downstream chunk can be
cited back to a specific location in the source document.

Each extractor returns a list of (location_label, text) tuples:
  - PDF   -> location_label = page number, e.g. "12"
  - DOCX  -> location_label = heading/section title nearest the text
  - XLSX  -> location_label = sheet name
"""
import re
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader
from docx import Document as DocxDocument
import openpyxl


def _clean_pdf_text(text: str) -> str:
    """pypdf's default text-extraction mode inserts spurious spaces inside
    words on many PDFs (e.g. "Na tional", "wor k") because it infers word
    boundaries from glyph positioning rather than the PDF's actual text
    structure. extraction_mode="layout" (used below) avoids that, but can
    still leave irregular run of spaces/blank lines from column layout —
    normalize those without touching real content or citation excerpts."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path: str) -> List[Tuple[str, str]]:
    reader = PdfReader(path)
    results = []
    for i, page in enumerate(reader.pages, start=1):
        text = _clean_pdf_text(page.extract_text(extraction_mode="layout") or "")
        if text:
            results.append((str(i), text))
    return results


def extract_docx(path: str) -> List[Tuple[str, str]]:
    doc = DocxDocument(path)
    results = []
    current_heading = "Introduction"
    buffer = []

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            results.append((current_heading, text))

    for para in doc.paragraphs:
        style = (para.style.name or "").lower()
        text = para.text.strip()
        if not text:
            continue
        if "heading" in style or "title" in style:
            flush()
            buffer.clear()
            current_heading = text
        else:
            buffer.append(text)
    flush()
    return results


def extract_xlsx(path: str) -> List[Tuple[str, str]]:
    wb = openpyxl.load_workbook(path, data_only=True)
    results = []
    for sheet in wb.worksheets:
        rows_text = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows_text.append(" | ".join(cells))
        text = "\n".join(rows_text).strip()
        if text:
            results.append((sheet.title, text))
    return results


def extract_document(path: str, file_type: str) -> List[Tuple[str, str]]:
    """
    Dispatch to the correct extractor based on file_type ("PDF" | "DOCX" | "XLSX").
    Returns a list of (location_label, raw_text) segments.
    """
    ext = file_type.upper()
    if ext == "PDF":
        return extract_pdf(path)
    if ext in ("DOC", "DOCX"):
        return extract_docx(path)
    if ext in ("XLS", "XLSX"):
        return extract_xlsx(path)
    raise ValueError(f"Unsupported file type: {file_type}")


def infer_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    mapping = {"pdf": "PDF", "doc": "DOCX", "docx": "DOCX", "xls": "XLSX", "xlsx": "XLSX"}
    if suffix not in mapping:
        raise ValueError(f"Unsupported file extension: .{suffix}")
    return mapping[suffix]
