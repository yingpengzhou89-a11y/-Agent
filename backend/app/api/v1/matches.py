from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.db.session import get_db_session
from app.repositories.matches import MatchRepository
from app.schemas.matches import MatchCreate, MatchRead, MatchReport
from app.services.matches import MatchService

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])
service = MatchService()
matches = MatchRepository()


def to_read(match) -> MatchRead:
    return MatchRead(
        id=match.id,
        user_id=match.user_id,
        resume_id=match.resume_id,
        job_id=match.job_id,
        report=MatchReport.model_validate(match.report_json),
        created_at=match.created_at,
    )


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match(
    payload: MatchCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> MatchRead:
    match = await service.create_report(session, user_id, payload.resume_id, payload.job_id)
    return to_read(match)


@router.get("/{match_id}", response_model=MatchRead)
async def get_match(
    match_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> MatchRead:
    return to_read(await matches.get_for_user(session, user_id, match_id))
