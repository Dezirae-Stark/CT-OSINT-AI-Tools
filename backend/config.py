"""
GhostExodus OSINT Platform — Configuration
All settings loaded from .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_PHONE: str = ""

    # JWT Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRY_HOURS: int = 24

    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.1:8b"
    EMBED_MODEL: str = "nomic-embed-text"
    LLM_CONTEXT_WINDOW: int = 4096

    # Storage paths
    CHROMA_PERSIST_DIR: str = "./data/chromadb"
    SQLITE_PATH: str = "./data/sqlite/ghostexodus.db"
    EVIDENCE_DIR: str = "./data/evidence"
    REPORTS_DIR: str = "./data/reports"
    TELEGRAM_SESSION_PATH: str = "./data/telegram"

    # SMTP Alerts
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ALERT_EMAIL_TO: str = ""

    # ntfy.sh push notifications
    NTFY_TOPIC: str = ""
    NTFY_SERVER: str = "https://ntfy.sh"

    # Environment
    ENV: str = "production"
    FRONTEND_DEV_ORIGIN: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
