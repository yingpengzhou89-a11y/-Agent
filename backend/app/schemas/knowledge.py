from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


KnowledgeSourceType = Literal["project_docs", "knowledge_base"]


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    source_type: str
    parse_status: str
    index_status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    scope: list[KnowledgeSourceType] = Field(default_factory=lambda: ["project_docs", "knowledge_base"])
    top_k: int = Field(default=8, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    content: str
    source_type: str
    source_name: str
    score: float = Field(ge=0)


class KnowledgeSearchResponse(BaseModel):
    search_id: UUID
    results: list[KnowledgeSearchResult]
    retrieval_config: dict[str, str | bool]


class KnowledgeCitationFeedbackCreate(BaseModel):
    chunk_id: UUID
    relevance: Literal["helpful", "not_helpful"]


class KnowledgeRetrievalQualityRead(BaseModel):
    search_count: int
    zero_result_rate: float = Field(ge=0, le=1)
    average_latency_ms: float = Field(ge=0)
    feedback_count: int
    feedback_coverage_rate: float = Field(ge=0, le=1)
    helpful_rate: float | None = Field(default=None, ge=0, le=1)


class EmbeddingStatusRead(BaseModel):
    configured: bool
    model: str
    dimensions: int
    indexed_document_count: int
    pending_document_count: int


class BulkReindexRead(BaseModel):
    total_document_count: int
    indexed_document_count: int
    failed_document_count: int
    failures: list[dict[str, str]] = []
