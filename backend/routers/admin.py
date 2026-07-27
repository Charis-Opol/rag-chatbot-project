"""
Admin routes (Master Design §2 Administrator dashboard):
document index rebuild, user management, system monitoring,
AI insights, and the external AI gateway settings toggle.
"""
import json
from collections import Counter

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.security import require_role, hash_password
from backend.utils_logging import log_action
from backend.document_processor import extract_document
from backend.chunking import chunk_document
from backend.embeddings import embed_texts
from backend.vector_store import vector_store

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------- Logs & stats
@router.get("/logs", response_model=list[schemas.SystemLogOut])
def get_logs(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_role("admin")),
    limit: int = 200,
):
    return db.query(models.SystemLog).order_by(models.SystemLog.timestamp.desc()).limit(limit).all()


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db), _admin: models.User = Depends(require_role("admin"))):
    documents_indexed = db.query(models.Document).filter(models.Document.status == "active").count()
    chunks_embedded = vector_store.count()
    total_users = db.query(models.User).count()
    total_queries = db.query(models.Message).filter(models.Message.sender == "user").count()
    indexed_pages = db.query(models.DocumentChunk).with_entities(
        models.DocumentChunk.document_id, models.DocumentChunk.page_number
    ).distinct().count()
    return schemas.StatsOut(
        documents_indexed=documents_indexed,
        chunks_embedded=chunks_embedded,
        total_users=total_users,
        total_queries=total_queries,
        indexed_pages=indexed_pages,
    )


@router.post("/rebuild-index")
def rebuild_index(db: Session = Depends(get_db), admin: models.User = Depends(require_role("admin"))):
    active_docs = db.query(models.Document).filter(models.Document.status == "active").all()

    all_texts, all_meta = [], []
    db.query(models.DocumentChunk).delete()

    for doc in active_docs:
        segments = extract_document(doc.file_path, doc.file_type)
        chunks = chunk_document(segments, doc.title)
        for c in chunks:
            all_texts.append(c.content)
            all_meta.append({
                "document_id": doc.document_id,
                "document_title": doc.title,
                "page_number": c.page_number,
                "section": c.section,
                "content": c.content,
            })

    vectors = embed_texts(all_texts) if all_texts else np.zeros((0, 384), dtype="float32")
    vector_store.rebuild(vectors, all_meta)

    for pos, meta in enumerate(all_meta):
        db.add(models.DocumentChunk(
            document_id=meta["document_id"], content=meta["content"],
            page_number=meta["page_number"], section=meta["section"], vector_index=pos,
        ))
    db.commit()

    log_action(db, admin.user_id, f"Rebuilt knowledge base index ({len(all_texts)} chunks from {len(active_docs)} documents)", tag="ok")
    return {"documents_processed": len(active_docs), "chunks_indexed": len(all_texts)}


# ---------------------------------------------------------------- User management
@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _admin: models.User = Depends(require_role("admin"))):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.patch("/users/{user_id}/toggle-active", response_model=schemas.UserOut)
def toggle_user_active(
    user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(require_role("admin")),
):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    log_action(db, admin.user_id, f'{"Disabled" if not user.is_active else "Re-enabled"} account for {user.full_name}', tag="warn")
    return user


@router.post("/users/{user_id}/reset-password", response_model=schemas.UserOut)
def reset_password(
    user_id: int, payload: schemas.PasswordResetRequest,
    db: Session = Depends(get_db), admin: models.User = Depends(require_role("admin")),
):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    log_action(db, admin.user_id, f"Reset password for {user.full_name}", tag="warn")
    return user


# ---------------------------------------------------------------- AI Insights
@router.get("/insights", response_model=schemas.InsightsOut)
def get_insights(db: Session = Depends(get_db), _admin: models.User = Depends(require_role("admin"))):
    user_messages = db.query(models.Message).filter(models.Message.sender == "user").all()

    normalized = Counter(m.message_text.strip().lower() for m in user_messages)
    top_questions = [{"question": q, "count": c} for q, c in normalized.most_common(8)]

    gaps = db.query(models.Message).filter(
        models.Message.sender == "bot", models.Message.grounded == False  # noqa: E712
    ).order_by(models.Message.timestamp.desc()).limit(10).all()
    # Pair each ungrounded bot reply with the user question right before it
    knowledge_gaps = []
    for bot_msg in gaps:
        prior = db.query(models.Message).filter(
            models.Message.session_id == bot_msg.session_id,
            models.Message.sender == "user",
            models.Message.timestamp <= bot_msg.timestamp,
        ).order_by(models.Message.timestamp.desc()).first()
        if prior:
            knowledge_gaps.append({"question": prior.message_text, "timestamp": bot_msg.timestamp.isoformat()})

    recent_activity = db.query(models.SystemLog).order_by(models.SystemLog.timestamp.desc()).limit(15).all()

    return schemas.InsightsOut(
        top_questions=top_questions,
        knowledge_gaps=knowledge_gaps,
        recent_activity=[schemas.SystemLogOut.model_validate(l) for l in recent_activity],
    )


# ---------------------------------------------------------------- Settings (external AI gateway)
def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    return row.value if row else default


def _set_setting(db: Session, key: str, value: str):
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))
    db.commit()


@router.get("/settings", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db), _admin: models.User = Depends(require_role("admin"))):
    return schemas.SettingsOut(
        external_ai_enabled=_get_setting(db, "external_ai_enabled", "false") == "true",
        external_ai_provider=_get_setting(db, "external_ai_provider", ""),
    )


@router.patch("/settings", response_model=schemas.SettingsOut)
def update_settings(
    payload: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_role("admin")),
):
    if payload.external_ai_enabled is not None:
        _set_setting(db, "external_ai_enabled", "true" if payload.external_ai_enabled else "false")
        log_action(db, admin.user_id, f'{"Enabled" if payload.external_ai_enabled else "Disabled"} external AI gateway', tag="warn")
    if payload.external_ai_provider is not None:
        _set_setting(db, "external_ai_provider", payload.external_ai_provider)
    return get_settings(db, admin)
