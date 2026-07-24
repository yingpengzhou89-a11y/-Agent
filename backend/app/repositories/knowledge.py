from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.knowledge import DocumentChunk, KnowledgeDocument


class KnowledgeRepository:
    async def create_document(self, session: AsyncSession, document: KnowledgeDocument) -> KnowledgeDocument:
        session.add(document)
        await session.flush()
        await session.refresh(document)
        return document

    async def get_document(
        self, session: AsyncSession, user_id: UUID, document_id: UUID
    ) -> KnowledgeDocument:
        document = await session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id, KnowledgeDocument.user_id == user_id
            )
        )
        if document is None:
            raise AppError("NOT_FOUND", "未找到该知识库文档", status_code=404)
        return document

    async def list_documents(self, session: AsyncSession, user_id: UUID) -> list[KnowledgeDocument]:
        result = await session.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.user_id == user_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(result)

    async def replace_chunks(
        self, session: AsyncSession, document: KnowledgeDocument, chunks: list[DocumentChunk]
    ) -> None:
        existing = await session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        for chunk in existing:
            await session.delete(chunk)
        session.add_all(chunks)
        await session.flush()

    async def chunks_for_document(self, session: AsyncSession, document_id: UUID) -> list[DocumentChunk]:
        result = await session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.created_at)
        )
        return list(result)

    async def chunks_for_user(
        self, session: AsyncSession, user_id: UUID, source_types: list[str]
    ) -> list[tuple[DocumentChunk, KnowledgeDocument]]:
        statement = (
            select(DocumentChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
            .where(DocumentChunk.user_id == user_id, KnowledgeDocument.user_id == user_id)
        )
        if source_types:
            statement = statement.where(KnowledgeDocument.source_type.in_(source_types))
        return list((await session.execute(statement)).all())

    async def vector_chunks_for_user(
        self, session: AsyncSession, user_id: UUID, source_types: list[str], query_vector: list[float]
    ) -> list[tuple[DocumentChunk, KnowledgeDocument]]:
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        statement = (
            select(DocumentChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.user_id == user_id,
                KnowledgeDocument.user_id == user_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(20)
        )
        if source_types:
            statement = statement.where(KnowledgeDocument.source_type.in_(source_types))
        return list((await session.execute(statement)).all())
