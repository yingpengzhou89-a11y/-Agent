from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.db.session import get_db_session
from app.repositories.progress import ProgressRepository
from app.schemas.progress import ProgressOverview, SkillMasteryRead
from app.services.progress import ProgressService

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])
service = ProgressService()
records = ProgressRepository()


@router.get("/overview", response_model=ProgressOverview)
async def overview(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> ProgressOverview:
    return await service.overview(session, user_id)


@router.get("/skills", response_model=list[SkillMasteryRead])
async def skills(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[SkillMasteryRead]:
    return [SkillMasteryRead.model_validate(item) for item in await records.list_for_user(session, user_id)]


@router.get("/weak-topics", response_model=list[str])
async def weak_topics(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[str]:
    return [item.skill_name for item in (await records.list_for_user(session, user_id))[:5]]


@router.get("/review-plan", response_model=list[SkillMasteryRead])
async def review_plan(
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[SkillMasteryRead]:
    return [SkillMasteryRead.model_validate(item) for item in await records.due_for_user(session, user_id)]
