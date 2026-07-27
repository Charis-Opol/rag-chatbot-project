"""
FastAPI application entrypoint.

Run with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs will be available at http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import auth_routes, documents, chat, admin, assistant

app = FastAPI(
    title="Ministry Knowledge Intelligence Assistant API",
    description="Ministry of ICT and National Guidance — offline RAG knowledge management platform backend.",
    version="2.0.0",
)

origins = ["*"] if settings.CORS_ORIGINS.strip() == "*" else [
    o.strip() for o in settings.CORS_ORIGINS.split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(assistant.router)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "mode": "offline"}


# Serve the frontend (index.html) directly from the backend, so the
# whole system can be reached from a single http://localhost:8000/ URL.
# IMPORTANT: this mount is registered LAST — Starlette matches routes in
# registration order, and a mount at "/" would otherwise swallow every
# request (including /api/health and all API routes) before they're checked.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
