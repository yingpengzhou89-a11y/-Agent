from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.core.errors import AppError
from app.db.session import get_db_session
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeDocumentRead, KnowledgeSearchRequest, KnowledgeSearchResult
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
    await session.commit()
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
    await session.commit()


@router.post("/documents/{document_id}/reindex", response_model=KnowledgeDocumentRead)
async def reindex_document(
    document_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeDocumentRead:
    document = await service.reindex(session, user_id, document_id)
    await session.commit()
    return KnowledgeDocumentRead.model_validate(document)


@router.post("/search", response_model=list[KnowledgeSearchResult])
async def search(
    payload: KnowledgeSearchRequest,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeSearchResult]:
    return await service.search(session, user_id, payload.query, payload.scope, payload.top_k)
