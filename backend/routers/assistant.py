"""
AI Document Assistant (Master Design §9): lets any signed-in user upload
a temporary document and ask for a summary, a compliance-risk scan, or a
plain-language explanation — WITHOUT permanently indexing it into the
Ministry knowledge base. Nothing here touches FAISS or the Document table;
the file is processed in memory/temp storage only for this one request.
"""
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.security import get_current_user
from backend.utils_logging import log_action
from backend.document_processor import extract_document, infer_file_type
from backend.llm_client import _call_ollama, LLMUnavailableError
import requests

router = APIRouter(prefix="/assistant", tags=["AI Document Assistant"])

MODE_PROMPTS = {
    "summarize": "Summarize the following document in 4-6 clear, professional sentences.",
    "risks": "Read the following document and identify any compliance or regulatory risks it raises. "
             "List them as short bullet points. If there are none, say so plainly.",
    "simplify": "Explain the following document in simple, plain language a non-specialist ministry "
                "employee could understand in under a minute.",
}


@router.post("/summarize")
def summarize_document(
    file: UploadFile = File(...),
    mode: str = Form("summarize"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if mode not in MODE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"mode must be one of {list(MODE_PROMPTS)}")

    try:
        file_type = infer_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / file.filename
        with tmp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            segments = extract_document(str(tmp_path), file_type)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not process file: {e}")

    full_text = "\n\n".join(text for _, text in segments)[:12000]  # guard against huge documents
    if not full_text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in this document.")

    prompt = f"{MODE_PROMPTS[mode]}\n\nDocument:\n{full_text}\n\nResponse:"

    try:
        result = _call_ollama(prompt)
        if not result:
            raise LLMUnavailableError()
        mock_mode = False
    except (requests.RequestException, LLMUnavailableError):
        # Extractive fallback: return the first ~3 sentences as a crude stand-in
        sentences = full_text.replace("\n", " ").split(". ")
        result = ". ".join(sentences[:3]).strip()
        if result and not result.endswith("."):
            result += "."
        result = result or "Local LLM not available and no readable text to summarize."
        mock_mode = True

    log_action(db, user.user_id, f'Used AI Document Assistant ({mode}) on "{file.filename}"', tag="ok")

    return {"mode": mode, "result": result, "mock_mode": mock_mode}
