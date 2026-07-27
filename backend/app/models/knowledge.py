from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    index_status: Mapped[str] = mapped_column(String(30), default="PENDING")


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions), nullable=True)


class KnowledgeSearchEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_search_events"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(Text)
    scope_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    top_k: Mapped[int] = mapped_column(Integer)
    result_chunk_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    retrieval_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_count: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)


class KnowledgeSearchFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_search_feedback"
    __table_args__ = (UniqueConstraint("search_event_id", "chunk_id", name="uq_search_feedback_event_chunk"),)

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    search_event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_search_events.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    relevance: Mapped[str] = mapped_column(String(20))
