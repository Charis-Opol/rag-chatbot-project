"""
Pydantic schemas — request/response contracts for the API.
"""
import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Auth ----------
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "staff"   # "admin" | "staff"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    email: str
    role_name: str
    is_active: bool = True
    created_at: datetime.datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PasswordResetRequest(BaseModel):
    new_password: str


# ---------- Documents ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: int
    title: str
    file_type: str
    status: str
    upload_date: datetime.datetime
    uploaded_by: Optional[int] = None
    department: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    date_published: Optional[str] = None
    version: int = 1
    supersedes_id: Optional[int] = None


class DocumentUploadResult(BaseModel):
    document: DocumentOut
    chunks_indexed: int


class ExplorerGroup(BaseModel):
    key: str
    count: int
    documents: List[DocumentOut]


class ExplorerOut(BaseModel):
    by_category: List[ExplorerGroup]
    by_department: List[ExplorerGroup]


# ---------- Chat ----------
class ChatAskRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class SourceCitation(BaseModel):
    document: str
    page: Optional[str] = None
    section: Optional[str] = None
    excerpt: str


class ChatAskResponse(BaseModel):
    session_id: int
    message_id: int
    answer: str
    grounded: bool
    sources: List[SourceCitation]
    mock_mode: bool = False  # true if Ollama wasn't reachable and a fallback extractive answer was used


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message_id: int
    sender: str
    message_text: str
    timestamp: datetime.datetime
    source_document: Optional[str] = None
    page_number: Optional[str] = None
    rating: Optional[int] = None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_id: int
    title: str
    created_at: datetime.datetime


class RateMessageRequest(BaseModel):
    rating: int   # +1 or -1


# ---------- AI Document Assistant (temporary, non-indexed documents) ----------
class SummarizeResponse(BaseModel):
    mode: str
    result: str
    mock_mode: bool = False


# ---------- Admin ----------
class SystemLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    log_id: int
    action: str
    tag: str
    timestamp: datetime.datetime
    user_id: Optional[int] = None


class StatsOut(BaseModel):
    documents_indexed: int
    chunks_embedded: int
    total_users: int
    total_queries: int
    indexed_pages: int


class InsightsOut(BaseModel):
    top_questions: List[dict]        # [{question, count}]
    knowledge_gaps: List[dict]       # [{question, timestamp}]
    recent_activity: List[SystemLogOut]


class SettingsOut(BaseModel):
    external_ai_enabled: bool = False
    external_ai_provider: str = ""


class SettingsUpdate(BaseModel):
    external_ai_enabled: Optional[bool] = None
    external_ai_provider: Optional[str] = None
