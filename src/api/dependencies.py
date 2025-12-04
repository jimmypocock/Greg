"""
FastAPI dependency injection for shared resources.

These dependencies are lazily initialized on first use and cached.
"""

import logging
from typing import Optional

from src.config.settings import Config
from src.documents.processor import DocumentProcessor
from src.rag.chain import UnifiedQAChain
from src.vectorstore.manager import VectorStoreManager

logger = logging.getLogger(__name__)

# Singleton instances
_config: Optional[Config] = None
_doc_processor: Optional[DocumentProcessor] = None
_unified_qa_chain: Optional[UnifiedQAChain] = None
_vector_store_manager: Optional[VectorStoreManager] = None


def get_config() -> Config:
    """Get the application configuration."""
    global _config
    if _config is None:
        _config = Config()
        _config.create_directories()
    return _config


def get_doc_processor() -> DocumentProcessor:
    """Get the document processor (lazy initialization)."""
    global _doc_processor
    if _doc_processor is None:
        logger.info("Initializing document processor...")
        _doc_processor = DocumentProcessor()
    return _doc_processor


def get_unified_qa_chain() -> UnifiedQAChain:
    """Get the unified QA chain (lazy initialization)."""
    global _unified_qa_chain
    if _unified_qa_chain is None:
        logger.info("Initializing unified QA chain...")
        _unified_qa_chain = UnifiedQAChain()
    return _unified_qa_chain


def get_vector_store_manager() -> VectorStoreManager:
    """Get the vector store manager."""
    global _vector_store_manager
    if _vector_store_manager is None:
        config = get_config()
        _vector_store_manager = VectorStoreManager(
            config.VECTOR_STORE_DIR,
            config.UPLOAD_DIR
        )
    return _vector_store_manager


def cleanup_resources():
    """Clean up all resources on shutdown."""
    global _doc_processor, _unified_qa_chain, _vector_store_manager

    if _doc_processor is not None:
        try:
            logger.info("Cleaning up document processor...")
            if hasattr(_doc_processor, 'embeddings'):
                del _doc_processor.embeddings
            del _doc_processor
            _doc_processor = None
        except Exception as e:
            logger.error(f"Error cleaning up document processor: {e}")

    if _unified_qa_chain is not None:
        try:
            logger.info("Cleaning up unified QA chain...")
            if hasattr(_unified_qa_chain, 'llm'):
                del _unified_qa_chain.llm
            if hasattr(_unified_qa_chain, 'embeddings'):
                del _unified_qa_chain.embeddings
            if hasattr(_unified_qa_chain, 'vector_store'):
                del _unified_qa_chain.vector_store
            del _unified_qa_chain
            _unified_qa_chain = None
        except Exception as e:
            logger.error(f"Error cleaning up unified QA chain: {e}")

    _vector_store_manager = None

    # Force garbage collection
    import gc
    gc.collect()

    logger.info("Resource cleanup completed")
