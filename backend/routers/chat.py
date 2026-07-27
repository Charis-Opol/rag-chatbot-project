"""
Chat routes (Master Design §4 AI Chat Interface).
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.security import get_current_user
from backend.utils_logging import log_action
from backend.rag_engine import ask as rag_ask

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask", response_model=schemas.ChatAskResponse)
def ask_question(
    payload: schemas.ChatAskRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if payload.session_id:
        session = db.query(models.ChatSession).filter(
            models.ChatSession.session_id == payload.session_id,
            models.ChatSession.user_id == user.user_id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = models.ChatSession(
            user_id=user.user_id,
            title=payload.message[:60] + ("…" if len(payload.message) > 60 else ""),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(models.Message(session_id=session.session_id, sender="user", message_text=payload.message))
    db.commit()

    result = rag_ask(payload.message)

    sources_json = json.dumps([{
        "document": s.document, "page": s.page, "section": s.section, "excerpt": s.excerpt,
    } for s in result.sources])

    bot_message = models.Message(
        session_id=session.session_id, sender="bot", message_text=result.answer,
        source_document=sources_json,
        page_number=result.sources[0].page if result.sources else None,
        grounded=result.grounded,
    )
    db.add(bot_message)
    db.commit()
    db.refresh(bot_message)

    log_action(db, user.user_id, f'Asked: "{payload.message[:60]}"', tag="ok" if result.grounded else "warn")

    return schemas.ChatAskResponse(
        session_id=session.session_id,
        message_id=bot_message.message_id,
        answer=result.answer,
        grounded=result.grounded,
        sources=[schemas.SourceCitation(**s.__dict__) for s in result.sources],
        mock_mode=result.mock_mode,
    )


@router.post("/messages/{message_id}/rate", response_model=schemas.MessageOut)
def rate_message(
    message_id: int, payload: schemas.RateMessageRequest,
    db: Session = Depends(get_db), user: models.User = Depends(get_current_user),
):
    msg = db.query(models.Message).join(models.ChatSession).filter(
        models.Message.message_id == message_id,
        models.ChatSession.user_id == user.user_id,
        models.Message.sender == "bot",
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.rating = payload.rating
    db.commit()
    db.refresh(msg)
    log_action(db, user.user_id, f"Rated a response {'helpful' if payload.rating > 0 else 'not helpful'}", tag="ok")
    return msg


@router.get("/sessions", response_model=list[schemas.ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.ChatSession).filter(models.ChatSession.user_id == user.user_id).order_by(
        models.ChatSession.created_at.desc()
    ).all()


@router.get("/sessions/{session_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    session = db.query(models.ChatSession).filter(
        models.ChatSession.session_id == session_id, models.ChatSession.user_id == user.user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return db.query(models.Message).filter(models.Message.session_id == session_id).order_by(
        models.Message.timestamp.asc()
    ).all()
