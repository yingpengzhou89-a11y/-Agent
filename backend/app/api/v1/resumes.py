from uuid import UUID

from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.db.session import get_db_session
from app.repositories.documents import ResumeRepository
from app.schemas.analysis import ResumeAnalysisOutput
from app.schemas.documents import ResumeCreate, ResumeRead
from app.services.analysis import ResumeAnalysisService
from app.services.documents import ResumeService
from app.services.model_gateway import OpenAICompatibleGateway

router = APIRouter(prefix="/api/v1/resumes", tags=["resumes"])
service = ResumeService()
resumes = ResumeRepository()
analysis_service = ResumeAnalysisService(OpenAICompatibleGateway())


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(
    payload: ResumeCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeRead:
    resume = await service.create(session, user_id, payload)
    await session.commit()
    return ResumeRead.model_validate(resume)


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: Annotated[UploadFile, File(...)],
    name: Annotated[str | None, Form()] = None,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeRead:
    if not file.filename:
        from app.core.errors import AppError
        raise AppError("FILE_PARSE_ERROR", "未提供简历文件名", status_code=422)
    resume = await service.create_from_file(session, user_id, file.filename, await file.read(), name)
    await session.commit()
    return ResumeRead.model_validate(resume)


@router.get("", response_model=list[ResumeRead])
async def list_resumes(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[ResumeRead]:
    return [ResumeRead.model_validate(item) for item in await resumes.list_for_user(session, user_id)]


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeRead:
    return ResumeRead.model_validate(await resumes.get_for_user(session, user_id, resume_id))


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysisOutput)
async def analyze_resume(
    resume_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ResumeAnalysisOutput:
    result = await analysis_service.analyze(session, user_id, resume_id)
    await session.commit()
    return result
