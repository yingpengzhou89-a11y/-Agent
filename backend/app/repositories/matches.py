from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.matches import MatchAnalysis


class MatchRepository:
    async def create(self, session: AsyncSession, match: MatchAnalysis) -> MatchAnalysis:
        session.add(match)
        await session.flush()
        await session.refresh(match)
        return match

    async def get_for_user(self, session: AsyncSession, user_id: UUID, match_id: UUID) -> MatchAnalysis:
        match = await session.scalar(
            select(MatchAnalysis).where(MatchAnalysis.id == match_id, MatchAnalysis.user_id == user_id)
        )
        if match is None:
            raise AppError("NOT_FOUND", "未找到该匹配报告", status_code=404)
        return match

