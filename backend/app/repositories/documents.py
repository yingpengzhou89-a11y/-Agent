from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.documents import JobDescription, Resume


class ResumeRepository:
    async def create(self, session: AsyncSession, resume: Resume) -> Resume:
        if resume.is_current:
            await self.clear_current(session, resume.user_id)
        session.add(resume)
        await session.flush()
        await session.refresh(resume)
        return resume

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[Resume]:
        result = await session.scalars(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )
        return list(result)

    async def get_for_user(self, session: AsyncSession, user_id: UUID, resume_id: UUID) -> Resume:
        resume = await session.scalar(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        if resume is None:
            raise AppError("NOT_FOUND", "未找到该简历", status_code=404)
        return resume

    async def clear_current(self, session: AsyncSession, user_id: UUID) -> None:
        await session.execute(
            update(Resume).where(Resume.user_id == user_id, Resume.is_current.is_(True)).values(is_current=False)
        )


class JobRepository:
    async def create(self, session: AsyncSession, job: JobDescription) -> JobDescription:
        if job.is_current:
            await self.clear_current(session, job.user_id)
        session.add(job)
        await session.flush()
        await session.refresh(job)
        return job

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[JobDescription]:
        result = await session.scalars(
            select(JobDescription)
            .where(JobDescription.user_id == user_id)
            .order_by(JobDescription.created_at.desc())
        )
        return list(result)

    async def get_for_user(self, session: AsyncSession, user_id: UUID, job_id: UUID) -> JobDescription:
        job = await session.scalar(
            select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user_id)
        )
        if job is None:
            raise AppError("NOT_FOUND", "未找到该职位描述", status_code=404)
        return job

    async def clear_current(self, session: AsyncSession, user_id: UUID) -> None:
        await session.execute(
            update(JobDescription)
            .where(JobDescription.user_id == user_id, JobDescription.is_current.is_(True))
            .values(is_current=False)
        )

