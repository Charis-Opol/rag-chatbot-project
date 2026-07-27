"""
Central configuration for the Offline RAG Chatbot backend.

All values are read from environment variables (see .env.example).
Nothing in this file makes an outbound network call — the system
is designed to run entirely on the ministry's local network.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Security
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./storage/db.sqlite3"

    # Storage
    UPLOAD_DIR: str = "./data/uploads"
    VECTOR_STORE_DIR: str = "./data/vector_store"

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Chunking
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    # Retrieval
    TOP_K: int = 3

    # Text generation provider: "google" (Gemini API) or "ollama" (local, fully offline)
    LLM_PROVIDER: str = "google"
    LLM_TIMEOUT_SECONDS: int = 60

    # Google Generative AI (Gemini) — used when LLM_PROVIDER=google
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = "gemini-2.0-flash"

    # Local LLM (Ollama) — used when LLM_PROVIDER=ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # CORS
    CORS_ORIGINS: str = "*"

    # Seed admin
    DEFAULT_ADMIN_NAME: str = "IT Officer"
    DEFAULT_ADMIN_EMAIL: str = "admin@moict.go.ug"
    DEFAULT_ADMIN_PASSWORD: str = "ChangeMe123!"

    # Seed demo staff account
    DEFAULT_STAFF_NAME: str = "Ministry Staff Demo"
    DEFAULT_STAFF_EMAIL: str = "staff@moict.go.ug"
    DEFAULT_STAFF_PASSWORD: str = "StaffDemo123!"


settings = Settings()

# Ensure required directories exist on import
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.VECTOR_STORE_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
