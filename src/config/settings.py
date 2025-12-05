import os
import multiprocessing
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
    # Legacy alias for backwards compatibility
    LOCAL_LLM_MODEL = LLM_MODEL

    # Embedding settings
    # Provider: "openai" (1536 dim, paid) or "local" (384 dim, free)
    # Auto-detects based on OPENAI_API_KEY if not specified
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER")  # None = auto-detect
    # Model: depends on provider
    # - OpenAI: text-embedding-3-small (default), text-embedding-ada-002, text-embedding-3-large
    # - Local: all-MiniLM-L6-v2 (default), all-mpnet-base-v2, etc.
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")  # None = provider default

    # Directories
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", "./vector_stores"))

    # File constraints
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 100))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Performance settings optimized for M3
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", 2048))

    # M3 specific optimizations
    NUM_THREADS = int(os.getenv("NUM_THREADS", 8))  # M3 has 8 cores
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 4))
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 2))  # Smaller batch for embeddings to prevent GPU OOM

    # Memory management
    MAX_MEMORY_GB = int(os.getenv("MAX_MEMORY_GB", 8))

    # Model parameters
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
    TOP_P = float(os.getenv("TOP_P", 0.9))

    @classmethod
    def create_directories(cls):
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        cls.VECTOR_STORE_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_optimal_settings(cls):
        """Get optimal settings based on available memory."""
        try:
            import psutil
            available_memory = psutil.virtual_memory().available / (1024**3)  # GB

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
