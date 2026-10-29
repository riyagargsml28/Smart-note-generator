"""
Configuration module for Smart Notes Generator.
Handles environment variables, file upload constraints, model settings, and application paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration settings."""

    # Security & Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-notes-secret-key-lecture-ai-2026")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    PORT = int(os.environ.get("PORT", 5000))
    HOST = os.environ.get("HOST", "127.0.0.1")

    # Directory Paths
    BASE_DIR = BASE_DIR
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    SAMPLES_FOLDER = BASE_DIR / "samples"
    DATABASE_PATH = BASE_DIR / "smart_notes.db"

    # Upload Constraints
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
    ALLOWED_DOCUMENT_EXTENSIONS = {"txt", "pdf", "docx", "md"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "webm", "ogg", "flac", "aac"}

    # AI & Speech Recognition settings (Google Gemini 3.5 Flash)
    GEMINI_API_KEY = (
        os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
    ).strip()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip()

    # Backwards-compatibility aliases
    OPENAI_API_KEY = GEMINI_API_KEY
    OPENAI_MODEL = GEMINI_MODEL
    WHISPER_MODEL = GEMINI_MODEL

    # Fallback / Offline Demo Mode
    # If True, when no API key is provided, the system uses the intelligent
    # rule-based heuristic generator so beginners can test the app without an external account.
    ALLOW_OFFLINE_FALLBACK = os.environ.get("ALLOW_OFFLINE_FALLBACK", "True").lower() in ("true", "1", "yes")

    # Note Detail Level presets
    DETAIL_LEVELS = {
        "short": {
            "name": "Short / Quick Review",
            "description": "High-level summary, core formulas, essential terms, and quick revision questions.",
            "section_depth": "concise",
            "max_sections": 3,
            "revision_count": 3,
            "mcq_count": 3
        },
        "medium": {
            "name": "Medium / Balanced Study Notes",
            "description": "Standard lecture notes covering all main topics, definitions, examples, and comprehensive Q&A.",
            "section_depth": "balanced",
            "max_sections": 5,
            "revision_count": 5,
            "mcq_count": 5
        },
        "detailed": {
            "name": "Detailed / Deep Dive",
            "description": "In-depth academic notes including complete topic segmentation, detailed examples, formulas, glossary, and extensive quizzes.",
            "section_depth": "comprehensive",
            "max_sections": 8,
            "revision_count": 8,
            "mcq_count": 8
        }
    }


# Ensure upload directory exists
Config.UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
