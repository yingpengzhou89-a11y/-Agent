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
