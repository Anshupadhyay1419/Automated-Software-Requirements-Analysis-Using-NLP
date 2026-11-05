"""All settings in one place. Values come from the .env file or use these defaults."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")  # empty means "pick automatically"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))

SAVED_MODELS_DIR = PROJECT_ROOT / "backend" / "saved_models"
SAMPLES_DIR = PROJECT_ROOT / "samples"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _database_url() -> str:
    """Relative SQLite paths are resolved from the project root, not the current folder."""
    url = os.getenv("DATABASE_URL", "sqlite:///backend/data/app.db")
    prefix = "sqlite:///"
    if url.startswith(prefix) and not Path(url[len(prefix):]).is_absolute():
        return prefix + (PROJECT_ROOT / url[len(prefix):]).as_posix()
    return url


DATABASE_URL = _database_url()
