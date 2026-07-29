from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.knowledge import KnowledgeSearchEvent
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    KnowledgeCitationFeedbackCreate,
    KnowledgeDocumentRead,
    BulkReindexRead,
    EmbeddingStatusRead,
    KnowledgeRetrievalQualityRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
service = KnowledgeService()
repository = KnowledgeRepository()


@router.post("/documents", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    source_type: Annotated[str, Form(...)],
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeDocumentRead:
    if source_type not in {"project_docs", "knowledge_base"}:
        raise AppError("VALIDATION_ERROR", "source_type 必须为 project_docs 或 knowledge_base", status_code=422)
    if not file.filename:
        raise AppError("FILE_PARSE_ERROR", "缺少文件名", status_code=422)
    document = await service.ingest_file(session, user_id, source_type, file.filename, await file.read())
    return KnowledgeDocumentRead.model_validate(document)


@router.get("/documents", response_model=list[KnowledgeDocumentRead])
async def list_documents(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeDocumentRead]:
    return [KnowledgeDocumentRead.model_validate(item) for item in await repository.list_documents(session, user_id)]


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentRead)
async def get_document(
    document_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeDocumentRead:
    return KnowledgeDocumentRead.model_validate(await repository.get_document(session, user_id, document_id))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await service.delete(session, user_id, document_id)


@router.post("/documents/{document_id}/reindex", response_model=KnowledgeDocumentRead)
async def reindex_document(
    document_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeDocumentRead:
    document = await service.reindex(session, user_id, document_id)
    return KnowledgeDocumentRead.model_validate(document)


@router.get("/embedding-status", response_model=EmbeddingStatusRead)
async def embedding_status(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> EmbeddingStatusRead:
    return await service.embedding_status(session, user_id)


@router.post("/documents/reindex-all", response_model=BulkReindexRead)
async def reindex_all_documents(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> BulkReindexRead:
    return await service.reindex_all(session, user_id)


@router.post("/documents/rechunk-and-reindex-all", response_model=BulkReindexRead)
async def rechunk_and_reindex_all_documents(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> BulkReindexRead:
    return await service.rechunk_and_reindex_all(session, user_id)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search(
    payload: KnowledgeSearchRequest,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeSearchResponse:
    results, retrieval_config, latency_ms = await service.search_with_trace(
        session, user_id, payload.query, payload.scope, payload.top_k
    )
    event = await repository.create_search_event(
        session,
        KnowledgeSearchEvent(
            user_id=user_id,
            query=payload.query,
            scope_json=payload.scope,
            top_k=payload.top_k,
            result_chunk_ids_json=[str(result.chunk_id) for result in results],
            retrieval_config_json=retrieval_config,
            result_count=len(results),
            latency_ms=latency_ms,
        ),
    )
    return KnowledgeSearchResponse(
        search_id=event.id,
        results=results,
        retrieval_config=retrieval_config,
    )


@router.post("/search/{search_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def record_feedback(
    search_id: UUID,
    payload: KnowledgeCitationFeedbackCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await service.record_feedback(
        session, user_id, search_id, payload.chunk_id, payload.relevance
    )


@router.get("/quality", response_model=KnowledgeRetrievalQualityRead)
async def quality_overview(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRetrievalQualityRead:
    return await service.quality_overview(session, user_id)
