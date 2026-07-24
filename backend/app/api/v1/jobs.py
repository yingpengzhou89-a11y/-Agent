from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.db.session import get_db_session
from app.repositories.documents import JobRepository
from app.schemas.analysis import JobAnalysisOutput
from app.schemas.documents import JobCreate, JobRead
from app.services.analysis import JobAnalysisService
from app.services.documents import JobService
from app.services.model_gateway import OpenAICompatibleGateway

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
service = JobService()
jobs = JobRepository()
analysis_service = JobAnalysisService(OpenAICompatibleGateway())


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    job = await service.create(session, user_id, payload)
    await session.commit()
    return JobRead.model_validate(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[JobRead]:
    return [JobRead.model_validate(item) for item in await jobs.list_for_user(session, user_id)]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> JobRead:
    return JobRead.model_validate(await jobs.get_for_user(session, user_id, job_id))


@router.post("/{job_id}/analyze", response_model=JobAnalysisOutput)
async def analyze_job(
    job_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> JobAnalysisOutput:
    result = await analysis_service.analyze(session, user_id, job_id)
    await session.commit()
    return result
