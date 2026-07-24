from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.interviews import InterviewAnswer, InterviewPlan, InterviewQuestion, InterviewSession


class InterviewPlanRepository:
    async def create(self, session: AsyncSession, plan: InterviewPlan) -> InterviewPlan:
        session.add(plan)
        await session.flush()
        await session.refresh(plan)
        return plan

    async def get_for_user(self, session: AsyncSession, user_id: UUID, plan_id: UUID) -> InterviewPlan:
        plan = await session.scalar(
            select(InterviewPlan).where(InterviewPlan.id == plan_id, InterviewPlan.user_id == user_id)
        )
        if plan is None:
            raise AppError("NOT_FOUND", "未找到该面试计划", status_code=404)
        return plan


class InterviewSessionRepository:
    async def create(self, session: AsyncSession, interview: InterviewSession) -> InterviewSession:
        session.add(interview)
        await session.flush()
        await session.refresh(interview)
        return interview

    async def get_for_user(self, session: AsyncSession, user_id: UUID, session_id: UUID) -> InterviewSession:
        interview = await session.scalar(
            select(InterviewSession).where(
                InterviewSession.id == session_id, InterviewSession.user_id == user_id
            )
        )
        if interview is None:
            raise AppError("NOT_FOUND", "未找到该面试会话", status_code=404)
        return interview

    async def get_question(
        self, session: AsyncSession, session_id: UUID, order_index: int
    ) -> InterviewQuestion | None:
        return await session.scalar(
            select(InterviewQuestion).where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.order_index == order_index,
            )
        )

    async def add_question(self, session: AsyncSession, question: InterviewQuestion) -> InterviewQuestion:
        session.add(question)
        await session.flush()
        await session.refresh(question)
        return question

    async def get_answer_by_key(
        self, session: AsyncSession, question_id: UUID, idempotency_key: str
    ) -> InterviewAnswer | None:
        return await session.scalar(
            select(InterviewAnswer).where(
                InterviewAnswer.question_id == question_id,
                InterviewAnswer.idempotency_key == idempotency_key,
            )
        )

    async def add_answer(self, session: AsyncSession, answer: InterviewAnswer) -> InterviewAnswer:
        session.add(answer)
        await session.flush()
        await session.refresh(answer)
        return answer

    async def get_answer_for_question(
        self, session: AsyncSession, question_id: UUID
    ) -> InterviewAnswer | None:
        return await session.scalar(
            select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
        )

    async def get_answer_for_user(
        self, session: AsyncSession, user_id: UUID, answer_id: UUID
    ) -> InterviewAnswer:
        answer = await session.scalar(
            select(InterviewAnswer).where(InterviewAnswer.id == answer_id, InterviewAnswer.user_id == user_id)
        )
        if answer is None:
            raise AppError("NOT_FOUND", "未找到该回答", status_code=404)
        return answer

    async def list_fingerprints(self, session: AsyncSession, session_id: UUID) -> list[str]:
        result = await session.scalars(
            select(InterviewQuestion.question_fingerprint).where(InterviewQuestion.session_id == session_id)
        )
        return list(result)
