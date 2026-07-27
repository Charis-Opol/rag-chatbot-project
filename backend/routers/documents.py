"""
Document management routes (Master Design §2 Document Management).
Only the IT Officer (admin) can upload, update, delete, or archive
documents; both roles can list active documents and browse the
Knowledge Explorer.
"""
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend import models, schemas
from backend.security import get_current_user, require_role
from backend.utils_logging import log_action
from backend.document_processor import extract_document, infer_file_type
from backend.chunking import chunk_document
from backend.embeddings import embed_texts
from backend.vector_store import vector_store

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=list[schemas.DocumentOut])
def list_documents(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    docs = db.query(models.Document).filter(models.Document.status == "active").order_by(
        models.Document.upload_date.desc()
    ).all()
    return docs


@router.get("/all", response_model=list[schemas.DocumentOut])
def list_all_documents(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_role("admin")),
):
    """Admin-only: includes archived documents."""
    return db.query(models.Document).order_by(models.Document.upload_date.desc()).all()


@router.get("/explorer", response_model=schemas.ExplorerOut)
def knowledge_explorer(db: Session = Depends(get_db), _user: models.User = Depends(get_current_user)):
    """Groups active documents by category and department for the Knowledge Explorer view."""
    docs = db.query(models.Document).filter(models.Document.status == "active").all()

    def group_by(key_fn):
        buckets = defaultdict(list)
        for d in docs:
            key = key_fn(d) or "Uncategorized"
            buckets[key].append(d)
        return [
            schemas.ExplorerGroup(key=k, count=len(v), documents=[schemas.DocumentOut.model_validate(x) for x in v])
            for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1]))
        ]

    return schemas.ExplorerOut(
        by_category=group_by(lambda d: d.category),
        by_department=group_by(lambda d: d.department),
    )


def _index_document(db: Session, document: models.Document, segments) -> int:
    """Shared chunk -> embed -> FAISS-index logic used by upload and rebuild."""
    chunks = chunk_document(segments, document.title)
    if not chunks:
        return 0
    vectors = embed_texts([c.content for c in chunks])
    metadatas = [
        {
            "document_id": document.document_id,
            "document_title": document.title,
            "page_number": c.page_number,
            "section": c.section,
            "content": c.content,
        }
        for c in chunks
    ]
    positions = vector_store.add(vectors, metadatas)
    for c, pos in zip(chunks, positions):
        db.add(models.DocumentChunk(
            document_id=document.document_id, content=c.content,
            page_number=c.page_number, section=c.section, vector_index=pos,
        ))
    db.commit()
    return len(chunks)


@router.post("/upload", response_model=schemas.DocumentUploadResult)
def upload_document(
    file: UploadFile = File(...),
    department: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    date_published: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_role("admin")),
):
    try:
        file_type = infer_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dest_path = Path(settings.UPLOAD_DIR) / file.filename
    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        segments = extract_document(str(dest_path), file_type)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not process file: {e}")

    title = Path(file.filename).stem

    # Versioning: if a document with the same title is already active,
    # archive it and link the new upload as the next version.
    previous = db.query(models.Document).filter(
        models.Document.title == title, models.Document.status == "active"
    ).first()
    next_version = 1
    supersedes_id = None
    if previous:
        previous.status = "archived"
        next_version = previous.version + 1
        supersedes_id = previous.document_id
        db.commit()

    document = models.Document(
        title=title, file_type=file_type, file_path=str(dest_path),
        uploaded_by=admin.user_id, status="active",
        department=department, author=author, category=category,
        date_published=date_published, version=next_version, supersedes_id=supersedes_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    chunk_count = _index_document(db, document, segments)

    version_note = f" (v{next_version}, supersedes previous version)" if previous else ""
    log_action(db, admin.user_id, f'Uploaded and indexed "{file.filename}"{version_note} — {chunk_count} chunks', tag="ok")

    return schemas.DocumentUploadResult(
        document=schemas.DocumentOut.model_validate(document),
        chunks_indexed=chunk_count,
    )


@router.patch("/{document_id}/archive", response_model=schemas.DocumentOut)
def toggle_archive(
    document_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_role("admin")),
):
    doc = db.query(models.Document).filter(models.Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "archived" if doc.status == "active" else "active"
    db.commit()
    db.refresh(doc)
    log_action(db, admin.user_id, f'{"Archived" if doc.status == "archived" else "Reactivated"} "{doc.title}"', tag="warn")
    return doc


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_role("admin")),
):
    doc = db.query(models.Document).filter(models.Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    title = doc.title
    db.delete(doc)  # cascades to DocumentChunk rows
    db.commit()
    log_action(db, admin.user_id, f'Deleted document "{title}" (note: run rebuild-index to purge its vectors)', tag="deny")
    return {"detail": "Document deleted. Run /admin/rebuild-index to fully purge its vectors from FAISS."}
