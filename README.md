# Ministry Knowledge Intelligence Assistant
### Offline RAG Platform for Regulatory & Compliance Standards — Ministry of ICT and National Guidance

A complete, runnable implementation of the Master System Design: a FastAPI
backend with document management (metadata + versioning), user management,
audit logging, an AI Insights dashboard, a Knowledge Explorer, an AI
Document Assistant, an optional external AI gateway toggle, and a FAISS-based
offline RAG chat engine — plus a premium frontend wired to all of it.

The frontend **auto-detects** whether the backend is running:
- Backend reachable → **LIVE mode**: real accounts, real retrieval, real (or mock-fallback) LLM answers.
- Backend not reachable → falls back to an **offline demo mode** with mock data, so `frontend/index.html` still works standalone for a quick walkthrough.

```
rag-chatbot-project/
├── backend/
│   ├── main.py                 App entrypoint — mounts frontend + all API routers
│   ├── config.py                 Settings, loaded from .env
│   ├── database.py                SQLAlchemy engine/session
│   ├── models.py                   ORM tables: Role, User, Document (+ metadata/versioning),
│   │                                  DocumentChunk, ChatSession, Message, SystemLog, Setting
│   ├── schemas.py                   Pydantic request/response models
│   ├── security.py                   JWT auth + role-based access control
│   ├── document_processor.py          PDF / DOCX / XLSX text extraction (page/section aware)
│   ├── chunking.py                     Splits text into overlapping chunks
│   ├── embeddings.py                    SentenceTransformers wrapper (local, offline after first run)
│   ├── vector_store.py                   FAISS index + metadata persistence
│   ├── llm_client.py                      ⭐ Ollama integration — swap models here
│   ├── rag_engine.py                       Retrieval + generation orchestration
│   ├── init_db.py                           Creates tables, seeds demo accounts
│   └── routers/
│       ├── auth_routes.py                    /auth/login, /auth/register, /auth/me
│       ├── documents.py                       upload (with metadata + auto-versioning),
│       │                                        list, archive, delete, /documents/explorer
│       ├── chat.py                             /chat/ask, /chat/messages/{id}/rate, sessions
│       ├── assistant.py                         /assistant/summarize — temporary, non-indexed
│       │                                          document analysis (summarize/risks/simplify)
│       └── admin.py                             logs, stats, rebuild-index, user management,
│                                                   /admin/insights, /admin/settings (external AI toggle)
├── frontend/
│   └── index.html              Full UI — login, chat, Knowledge Explorer, AI Document Assistant,
│                                  AI Insights, admin dashboard, user management, settings
├── data/
│   ├── uploads/                  Uploaded source files
│   └── vector_store/               FAISS index + metadata.json
├── storage/                        SQLite database file
├── requirements.txt
└── .env.example                    Copy to .env and edit
```

---

## 1. Setup

```bash
cd rag-chatbot-project
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # edit SECRET_KEY and passwords before real use
python -m backend.init_db         # creates the database + seeds demo accounts
```

Two demo accounts are seeded:

| Role       | Email                  | Password         |
|------------|-------------------------|-------------------|
| IT Officer | admin@moict.go.ug       | ChangeMe123!      |
| Staff      | staff@moict.go.ug       | StaffDemo123!     |

**Change these** (or edit `.env` before running `init_db`) before any real deployment.

## 2. Run

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — serves the UI and the API from one process.
Swagger docs: **http://localhost:8000/docs**.

## 3. Feature map — Master Design Prompt → implementation

| Master Design section | What's implemented |
|---|---|
| §2 Document Management | Upload PDF/DOCX/XLSX with title, department, author, category, date published; archive/delete; **auto-versioning** — re-uploading a file with the same title archives the old one and links it as a prior version (`supersedes_id`) |
| §2 User Management | Admin can list users, disable/re-enable accounts, reset passwords (`/admin/users/*`) |
| §2 System Monitoring | `/admin/stats` — documents indexed, indexed pages, chunks embedded, total queries, total users; `/admin/logs` — full audit trail |
| §3 Welcome Dashboard | Personalized greeting, quick-action buttons (Search ICT regulations / Find compliance requirements / Summarize a policy / Explain a guideline / Compare regulations), suggested questions |
| §4 AI Chat Interface | Real-time chat, per-session history, copy response, export conversation, thumbs up/down rating, source citations with document/page/section |
| §5 RAG Architecture | Query → embed → FAISS search → context injection → local LLM → answer + sources, exactly as diagrammed |
| §6 Knowledge Base Storage | Original file + extracted text + metadata + embeddings + basic version history, all local |
| §7 Local AI Model Integration | Ollama client with model swap via one env var; sentence-transformers embeddings; FAISS vector store — works fully offline once models are cached |
| §8 External AI Gateway | `/admin/settings` toggle (`external_ai_enabled`, `external_ai_provider`) — **off by default**; ministry document content is never sent externally regardless of this setting (only the RAG pipeline touches indexed documents) |
| §9 AI Document Assistant | `/assistant/summarize` — upload a one-off file, get a summary / compliance-risk scan / plain-language explanation; **not** added to the permanent knowledge base or FAISS index |
| §9 Knowledge Explorer | `/documents/explorer` groups active documents by category and department |
| §9 AI Insights Dashboard | `/admin/insights` — most-asked questions, knowledge gaps (questions the KB couldn't answer), recent activity feed |
| §9 Smart Search | Natural-language questions work directly — no separate keyword mode needed |
| §10 Security | JWT auth, bcrypt password hashing, role-based access control on every admin route, full audit logging of uploads/logins/queries/admin actions |
| §11 UI Design | Dark charcoal / white / soft gold / deep green palette, Space Grotesk + Inter + IBM Plex Mono type system — no default "corporate blue AI" look |

## 4. Integrating a pretrained local LLM (Ollama)

The system runs and answers questions **without** any LLM installed — it
falls back to returning the retrieved passage directly (an "extractive
fallback" badge appears in the chat UI and AI Document Assistant). To get
real generated answers:

```bash
# 1. Install Ollama — https://ollama.com
curl -fsSL https://ollama.com/install.sh | sh      # macOS/Linux

# 2. Pull a model
ollama pull llama3        # or: gemma2, mistral, phi3

# 3. Point the backend at it (.env)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Restart uvicorn — no code changes needed. Every generation call goes through
**`backend/llm_client.py`**, the single seam for swapping models or runtimes
(llama.cpp server, vLLM, LM Studio's OpenAI-compatible endpoint, etc.).

## 5. What's simulated vs. real

| Component | Status |
|---|---|
| Auth, JWT, RBAC, audit logging | Real |
| Document upload, metadata, auto-versioning | Real |
| PDF/DOCX/XLSX extraction (page/section aware) | Real |
| Chunking | Real (simple word-window splitter — swap in a smarter one if needed) |
| Embeddings | Real (local sentence-transformers; downloads once from HuggingFace, then fully offline) |
| Vector search | Real (FAISS, persisted to disk) |
| LLM generation | Real via Ollama **if installed**; otherwise extractive fallback (clearly flagged in the UI) |
| Knowledge Explorer, AI Insights, user management, settings | Real, all backed by the database |
| AI Document Assistant | Real — processes the file in a temp directory only, never persists it |
| External AI gateway | Real toggle + audit logging; no external provider is wired up yet — `admin.py`'s settings endpoints are the integration point when you're ready to add one |
| Frontend | Real UI, calls the live API; falls back to mock data only if the backend is unreachable |

## 6. Next steps

- Swap `IndexFlatIP` for `IndexIVFFlat` / `IndexHNSWFlat` once the document collection is large enough that flat search gets slow.
- Add streaming responses (`stream: true` in `llm_client.py`) for a token-by-token typing effect.
- Wire an actual external AI provider behind the `/admin/settings` toggle if you want the optional gateway to do something beyond logging its own state.
- Add `pytest` coverage — extraction / chunking / embeddings / vector store / LLM client are all independent, easily-testable modules.
- Move `SECRET_KEY` and default passwords out of the `.env.example` defaults before any real ministry deployment.
