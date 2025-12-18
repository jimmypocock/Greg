import os
from pathlib import Path

from dotenv import load_dotenv

from packages.core.config.validation import get_optional, get_required

load_dotenv()


class Config:
    """
    Application configuration.

    Required vars (no defaults - must be in .env):
        - LLM_PROVIDER, LLM_MODEL
        - UPLOAD_DIR, VECTOR_STORE_DIR

    Tuning params (sensible defaults):
        - CHUNK_SIZE, CHUNK_OVERLAP, MAX_CONTEXT_LENGTH
        - NUM_THREADS, BATCH_SIZE, EMBEDDING_BATCH_SIZE
        - MAX_FILE_SIZE_MB, MAX_MEMORY_GB
        - TEMPERATURE, TOP_P
    """

    # LLM Settings (required)
    LLM_PROVIDER = get_required("LLM_PROVIDER")
    LLM_MODEL = get_required("LLM_MODEL")

    # Embedding settings (optional - auto-detects)
    EMBEDDING_PROVIDER = get_optional("EMBEDDING_PROVIDER")
    EMBEDDING_MODEL = get_optional("EMBEDDING_MODEL")

    # Directories (required)
    UPLOAD_DIR = Path(get_required("UPLOAD_DIR"))
    VECTOR_STORE_DIR = Path(get_required("VECTOR_STORE_DIR"))

    # File constraints (tuning - has default)
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # RAG settings (tuning - has defaults)
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "2048"))

    # Performance settings (tuning - has defaults)
    NUM_THREADS = int(os.getenv("NUM_THREADS", "8"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "4"))
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "2"))

    # Memory management (tuning - has default)
    MAX_MEMORY_GB = int(os.getenv("MAX_MEMORY_GB", "8"))

    # Model parameters (tuning - has defaults)
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    TOP_P = float(os.getenv("TOP_P", "0.9"))

    # Auth settings (tuning - has defaults)
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "10"))

    # Ollama settings (optional - has default)
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # CORS settings (optional)
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

    # Internal API key for server-to-server communication (Next.js → Backend)
    # This should be a long, random secret shared between your frontend server and backend
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

    # Stripe settings (optional - for subscriptions)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")  # Pro plan price ID
    STRIPE_PRICE_ID_ENTERPRISE = os.getenv("STRIPE_PRICE_ID_ENTERPRISE")  # Enterprise plan price ID

    @classmethod
    def create_directories(cls):
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        cls.VECTOR_STORE_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_optimal_settings(cls):
        """Get optimal settings based on available memory."""
        try:
            import psutil

            available_memory = psutil.virtual_memory().available / (1024**3)

            if available_memory < 4:
                return {
                    "model": cls.LLM_MODEL,
                    "chunk_size": 500,
                    "batch_size": 2,
                }
            elif available_memory < 8:
                return {
                    "model": cls.LLM_MODEL,
                    "chunk_size": 800,
                    "batch_size": 4,
                }
            else:
                return {
                    "model": cls.LLM_MODEL,
                    "chunk_size": 1000,
                    "batch_size": 8,
                }
        except Exception:
            return {
                "model": cls.LLM_MODEL,
                "chunk_size": cls.CHUNK_SIZE,
                "batch_size": cls.BATCH_SIZE,
            }
