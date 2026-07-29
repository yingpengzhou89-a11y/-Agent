from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluations import AnswerEvaluation
from app.models.interviews import InterviewAnswer, InterviewQuestion, InterviewSession
from app.models.progress import InterviewReport, SkillMastery


class ReportRepository:
    async def get_for_session(self, session: AsyncSession, session_id: UUID) -> InterviewReport | None:
        return await session.scalar(select(InterviewReport).where(InterviewReport.session_id == session_id))

    async def save(self, session: AsyncSession, report: InterviewReport) -> InterviewReport:
        session.add(report)
        await session.flush()
        await session.refresh(report)
        return report

    async def evaluated_items(self, session: AsyncSession, session_id: UUID):
        result = await session.execute(
            select(InterviewQuestion, InterviewAnswer, AnswerEvaluation)
            .join(InterviewAnswer, InterviewAnswer.question_id == InterviewQuestion.id)
            .join(AnswerEvaluation, AnswerEvaluation.answer_id == InterviewAnswer.id)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.order_index)
        )
        return result.all()

    async def list_history_for_user(self, session: AsyncSession, user_id: UUID, limit: int = 20):
        result = await session.execute(
            select(InterviewReport, InterviewSession)
            .join(InterviewSession, InterviewSession.id == InterviewReport.session_id)
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.completed_at.desc(), InterviewReport.created_at.desc())
            .limit(limit)
        )
        return result.all()


class ProgressRepository:
    async def get(self, session: AsyncSession, user_id: UUID, skill_name: str) -> SkillMastery | None:
        return await session.scalar(
            select(SkillMastery).where(
                SkillMastery.user_id == user_id, SkillMastery.skill_name == skill_name
            )
        )

    async def save(self, session: AsyncSession, record: SkillMastery) -> SkillMastery:
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[SkillMastery]:
        result = await session.scalars(
            select(SkillMastery)
            .where(SkillMastery.user_id == user_id)
            .order_by(SkillMastery.mastery_score.asc(), SkillMastery.skill_name)
        )
        return list(result)

    async def due_for_user(self, session: AsyncSession, user_id: UUID):
        result = await session.scalars(
            select(SkillMastery)
            .where(SkillMastery.user_id == user_id)
            .order_by(SkillMastery.next_review_at.asc())
        )
        return list(result)
