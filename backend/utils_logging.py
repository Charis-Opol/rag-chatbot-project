"""Tiny helper so every router logs actions to SystemLogs the same way."""
from typing import Optional
from sqlalchemy.orm import Session

from backend import models


def log_action(db: Session, user_id: Optional[int], action: str, tag: str = "ok"):
    entry = models.SystemLog(user_id=user_id, action=action, tag=tag)
    db.add(entry)
    db.commit()
