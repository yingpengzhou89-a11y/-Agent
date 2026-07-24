from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.user import User
from app.core.config import settings
from app.core.errors import AppError
from app.repositories.documents import JobRepository, ResumeRepository
from app.repositories.users import UserRepository
from app.schemas.documents import JobCreate, ResumeCreate
from app.services.documents import JobService, ResumeService


@pytest.mark.asyncio
async def test_resume_file_upload_extracts_text_and_preserves_source(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'upload.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    original_storage_dir = settings.storage_dir
    settings.storage_dir = str(tmp_path / "uploads")
    try:
        async with session_factory() as session:
            user = await UserRepository().create(session, User(display_name="Candidate"))
            await session.commit()
            resume = await ResumeService().create_from_file(
                session, user.id, "candidate.txt", "Python、FastAPI 与 RAG 项目".encode(), "候选人简历"
            )
            await session.commit()
            assert resume.file_type == "txt"
            assert resume.raw_text == "Python、FastAPI 与 RAG 项目"
            assert resume.file_path is not None and Path(resume.file_path).is_file()
    finally:
        settings.storage_dir = original_storage_dir
        await engine.dispose()


@pytest.mark.asyncio
async def test_resume_and_job_are_scoped_to_the_current_user(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        users = UserRepository()
        primary_user = await users.create(session, User(display_name="Primary"))
        other_user = await users.create(session, User(display_name="Other"))
        await session.commit()

        resume_service = ResumeService()
        first_resume = await resume_service.create(
            session,
            primary_user.id,
            ResumeCreate(name="first", raw_text="Python experience", is_current=True),
        )
        await session.commit()

        second_resume = await resume_service.create(
            session,
            primary_user.id,
            ResumeCreate(name="second", raw_text="FastAPI experience", is_current=True),
        )
        await session.commit()
        await session.refresh(first_resume)

        assert first_resume.is_current is False
        assert second_resume.is_current is True
        assert len(await ResumeRepository().list_for_user(session, primary_user.id)) == 2
        assert await ResumeRepository().list_for_user(session, other_user.id) == []

        job = await JobService().create(
            session,
            primary_user.id,
            JobCreate(title="AI Application Engineer", raw_text="FastAPI and RAG", is_current=True),
        )
        await session.commit()

        assert (await JobRepository().get_for_user(session, primary_user.id, job.id)).id == job.id
        with pytest.raises(AppError):
            await JobRepository().get_for_user(session, other_user.id, job.id)

    await engine.dispose()
