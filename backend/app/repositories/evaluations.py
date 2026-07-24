from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.evaluations import AnswerEvaluation


class EvaluationRepository:
    async def create(self, session: AsyncSession, evaluation: AnswerEvaluation) -> AnswerEvaluation:
        session.add(evaluation)
        await session.flush()
        await session.refresh(evaluation)
        return evaluation

    async def get(self, session: AsyncSession, answer_id: UUID) -> AnswerEvaluation:
        evaluation = await session.scalar(
            select(AnswerEvaluation).where(AnswerEvaluation.answer_id == answer_id)
        )
        if evaluation is None:
            raise AppError("NOT_FOUND", "尚未生成该回答的评价", status_code=404)
        return evaluation
