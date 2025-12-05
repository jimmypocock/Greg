"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class QuestionRequest(BaseModel):
    """Request body for asking questions."""
    model_config = {"protected_namespaces": ()}

    question: str
    document_id: str
    max_results: int = 5
    model_name: Optional[str] = None
    temperature: float = 0.7
    use_web_search: bool = False
    stream: bool = False


class URLProcessRequest(BaseModel):
    """Request body for processing a URL."""
    model_config = {"protected_namespaces": ()}

    url: str
    model: str = "mistral"
    chunk_size: int = 800
    temperature: float = 0.7


class ModelInfo(BaseModel):
    """Information about an available LLM model."""
    model_config = {"protected_namespaces": ()}

    name: str
    provider: str  # "ollama", "openai", "anthropic", "google"
    size: Optional[str] = None
    modified: Optional[str] = None
    available: bool = True


class UploadResponse(BaseModel):
    """Response after uploading a document."""
    model_config = {"protected_namespaces": ()}

    document_id: str
    pages: int
    chunks: int
    processing_time: float
    message: str


class AnswerResponse(BaseModel):
    """Response containing an answer to a question."""
    model_config = {"protected_namespaces": ()}

    answer: str
    sources: List[Any]
    document_id: str
    processing_time: float
    llm_model: str


class DocumentInfo(BaseModel):
    """Information about a processed document."""
    model_config = {"protected_namespaces": ()}

    document_id: str
    filename: str
    pages: int
    chunks: Any  # Can be int or 'N/A'
    upload_date: str
    model_used: str


class DocumentListResponse(BaseModel):
    """Response containing list of documents."""
    model_config = {"protected_namespaces": ()}

    documents: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = {"protected_namespaces": ()}

    status: str
    memory: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    optimal_settings: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StorageStatsResponse(BaseModel):
    """Storage statistics response."""
    model_config = {"protected_namespaces": ()}

    total_stores: int
    total_size_mb: float
    stores: List[Dict[str, Any]]
    storage_path: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response."""
    model_config = {"protected_namespaces": ()}

    message: str


class JobCreatedResponse(BaseModel):
    """Response when a background job is created."""
    model_config = {"protected_namespaces": ()}

    job_id: str
    status: str = "pending"
    message: str
    websocket_url: str
