"""
ORM models — implements the database design behind the Ministry of ICT
Knowledge Intelligence Assistant: Users, Roles, Documents (with metadata
and version history), DocumentChunks, ChatSessions, Messages, SystemLogs,
and Settings (feature toggles such as the external AI gateway).
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(20), unique=True, nullable=False)  # "admin" | "staff"

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    role = relationship("Role", back_populates="users")
    documents = relationship("Document", back_populates="uploader")
    chat_sessions = relationship("ChatSession", back_populates="user")
    logs = relationship("SystemLog", back_populates="user")

    @property
    def role_name(self) -> str:
        return self.role.role_name if self.role else "unknown"


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)   # PDF / DOCX / XLSX
    file_path = Column(Text, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.user_id"))
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="active")     # active / archived

    # --- Metadata (Master Design Prompt §2 Document Management) ---
    department = Column(String(150), nullable=True)
    author = Column(String(150), nullable=True)
    category = Column(String(100), nullable=True)
    date_published = Column(String(20), nullable=True)   # free-text date as supplied by uploader
    version = Column(Integer, default=1)
    supersedes_id = Column(Integer, ForeignKey("documents.document_id"), nullable=True)

    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.document_id"), nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(String(20), nullable=True)
    section = Column(String(255), nullable=True)
    vector_index = Column(Integer, nullable=True)  # position of this chunk's embedding inside the FAISS index

    document = relationship("Document", back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), default="New conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.session_id"), nullable=False)
    sender = Column(String(10), nullable=False)   # "user" | "bot"
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    source_document = Column(Text, nullable=True)  # JSON-encoded list of source citations
    page_number = Column(String(20), nullable=True)
    rating = Column(Integer, nullable=True)          # +1 helpful / -1 not helpful, set by the asking user
    grounded = Column(Boolean, default=True)          # False when no KB match was found — feeds "knowledge gaps"

    session = relationship("ChatSession", back_populates="messages")


class SystemLog(Base):
    __tablename__ = "system_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    action = Column(Text, nullable=False)
    tag = Column(String(20), default="ok")   # ok / warn / deny
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="logs")


class Setting(Base):
    """Simple key/value settings store — used for admin-controlled feature
    toggles such as the optional external AI gateway (Master Design §8)."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
